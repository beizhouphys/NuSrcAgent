"""Persist and review the primary single-source fit before flux calculations."""
from __future__ import annotations

import copy
import fcntl
import json
import traceback
from pathlib import Path

from agent_core.analysis_agent import AnalysisAgent, AgentRun
from agent_core.cpu import execution_metadata, positive_cpu_count
from agent_core.config_io import load_config_file
from agent_core.file_cache import sha256_file
from agent_core.normalize import normalize_config
from agent_core.report import write_run_artifacts
from agent_core.review import review_run
from agent_core.schemas import ConfigError
from agent_core.simple_yaml import load_simple_yaml
from agent_core.task_state import refresh_readiness, save_task, stable_payload_hash, utc_now
from agent_core.validate import validate_config

FLOW = "single_source_two_stage_v1"
FLUX_FIELDS = ("flux_upper_limit_cl", "flux_upper_limit_gammas", "flux_measurement_ts_threshold")


def configure_single_source_stages(task):
    """New wrapper tasks only; historical records keep their execution contract."""
    if task["workflow"] != "single_source" or task.get("parameters", {}).get("gaussian_score_baseline", {}).get("value") is not None:
        return
    task["execution_flow"] = FLOW
    task["planned_tools"] = ["run_agent_wrap.py run", "run_agent_wrap.py run --stage flux",
                             "run_agent_wrap.py review-run"]


def execute_single_source_stage(task, task_path, repo_root, stage="llh", max_safe_retries=1, user_reply=None, cpus=1):
    """Return after one reviewed stage so the Agent can report it in chat."""
    from agent_core.agent_orchestrator import (
        SAFE_ERROR_TYPES, build_analysis_payload, classify_error, evaluate_completion, write_agent_review)
    cpus = positive_cpu_count(cpus)
    root, task_path = Path(repo_root).resolve(), Path(task_path).resolve()
    if task.get("execution_flow") != FLOW or task.get("workflow") != "single_source":
        raise ValueError("separate stages require a new two-stage single-source task")
    if stage not in {"llh", "flux"}:
        raise ValueError("unknown single-source stage")
    with (task_path.parent / "single_source_execution.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("this single-source task already has an active process") from exc
        # Reject a second process holding an outdated copy of the task state.
        persisted = json.loads(task_path.read_text())
        if persisted != task:
            raise ValueError("task changed since loading; reload it before execution")
        if stage == "flux" and task["status"] != "AWAITING_FLUX":
            raise ValueError(f"flux stage requires AWAITING_FLUX; status={task['status']}")
        if stage == "flux" and (not isinstance(user_reply, str) or not user_reply.strip()):
            raise ValueError("Flux stage requires the user continuation reply after the primary final answer; use --flux-user-reply")
        refresh_readiness(task)
        expected = "READY" if stage == "llh" else "AWAITING_FLUX"
        if task["status"] != expected:
            raise ValueError(f"{stage} stage requires {expected}; status={task['status']}")
        payload = build_analysis_payload(task, root)
        full_hash = stable_payload_hash(payload)
        stage_payload = copy.deepcopy(payload)
        if stage == "llh":
            for field in FLUX_FIELDS:
                stage_payload["analysis"].pop(field, None)
        stage_hash = stable_payload_hash(stage_payload)
        for retry in range(1 + max_safe_retries):
            attempt_number = len(task.get("attempts", [])) + 1
            attempt = dict(attempt=attempt_number, stage=stage, started_at_utc=utc_now(),
                           request_sha256=stage_hash, full_request_sha256=full_hash, status="RUNNING", cpu_budget=cpus)
            if stage == "flux":
                attempt["flux_user_reply"] = user_reply
            task.setdefault("attempts", []).append(attempt)
            task["active_stage"] = stage
            task["status"] = "RUNNING"
            save_task(task, root, task_path)
            try:
                primary = _load_primary(task, payload, root) if stage == "flux" else None
                request_path = task_path.parent / f"analysis_request_{stage}_attempt_{attempt_number}.yaml"
                agent = AnalysisAgent(root)
                agent.prepare_request(stage_payload, request_path)
                run = (agent.run(request_path, cpus=cpus) if stage == "llh"
                       else _run_flux(request_path, primary, root, cpus=cpus))
                attempt.update(ended_at_utc=utc_now(), run_directory=str(run.run_dir),
                               review_status=run.review.get("status"))
                task["artifacts"].update(request=str(request_path), run_directory=str(run.run_dir),
                                          review=str(run.run_dir / "review.json"))
                task["status"] = "REVIEWING"
                completion = evaluate_completion(task, run.review)
                task["completion"] = completion
                attempt["status"] = completion["status"]
                if completion["status"] in {"COMPLETED", "COMPLETED_WITH_WARNINGS"}:
                    if stage == "llh":
                        _save_primary(task, run, full_hash, task_path.parent)
                        # Modes with no supported/requested flux products finish here.
                        pending = any(payload["analysis"].get(field) for field in FLUX_FIELDS)
                        task["status"] = "AWAITING_FLUX" if pending else completion["status"]
                        if pending:
                            task["completion"] = dict(completion, status="AWAITING_FLUX")
                            task["active_stage"] = "flux"
                    else:
                        task.setdefault("stages", {})["flux"] = dict(status=completion["status"],
                            run_directory=str(run.run_dir), completed_at_utc=utc_now())
                        task["status"] = completion["status"]
                    write_agent_review(task, task_path.parent)
                    save_task(task, root, task_path)
                    return task
                retry_allowed = completion.get("auto_fix_allowed", False)
            except Exception as exc:
                error_type = "DATA_VALIDATION_ERROR" if isinstance(exc, (ValueError, KeyError)) else classify_error(exc)
                attempt.update(ended_at_utc=utc_now(), status="FAILED", error_type=error_type,
                               error=str(exc), traceback=traceback.format_exc())
                retry_allowed = error_type in SAFE_ERROR_TYPES
                task["completion"] = dict(status="FAILED", checks=[dict(id=f"{stage}_execution",
                    status="fail", message=str(exc))], auto_fix_allowed=False)
            if retry_allowed and retry < max_safe_retries:
                attempt["recovery"] = dict(action=f"retry identical {stage} stage once",
                                            scientific_parameters_changed=False)
                continue
            task["status"] = "FAILED"
            if stage == "flux":
                task.setdefault("stages", {})["flux"] = dict(status="FAILED", failed_at_utc=utc_now())
            write_agent_review(task, task_path.parent)
            save_task(task, root, task_path)
            return task
    return task


def _save_primary(task, run, full_hash, task_dir):
    # The first report and review remain immutable when the flux stage writes a new run.
    files = {str(p): sha256_file(p) for p in run.run_dir.rglob("*") if p.is_file()}
    checkpoint = dict(result=run.result, full_request_sha256=full_hash, files_sha256=files,
                      run_directory=str(run.run_dir))
    path = task_dir / "single_source_primary.json"
    path.write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")
    task.setdefault("stages", {})["llh"] = dict(status=run.review["status"],
        completed_at_utc=utc_now(), checkpoint=str(path), checkpoint_sha256=sha256_file(path),
        run_directory=str(run.run_dir))
    task["artifacts"].update(llh_run_directory=str(run.run_dir), llh_checkpoint=str(path))
    result = run.result
    task["single_source_llh_summary"] = dict(
        best_fit_ns=result.get("ns", result.get("best_fit_ns")),
        Gamma=result.get("gamma_legacy", result.get("gamma")),
        gamma_convention="dN/dE proportional to (E/E0)^Gamma",
        gamma_mode=run.normalized.gamma_mode, TS=result.get("TS", result.get("ts")),
        p_value=result["pre_trial_p"], significance=result["pre_trial_significance"],
        significance_unit="sigma", p_value_method=result["p_value_method"],
        p_value_is_estimate=result["p_value_is_estimate"], review_status=run.review["status"],
        warnings=[check["message"] for check in run.review.get("checks", []) if check.get("status") == "warning"])


def _load_primary(task, payload, root):
    record = task.get("stages", {}).get("llh", {})
    if record.get("status") not in {"pass", "warning"}:
        raise ValueError("flux stage requires a reviewed primary fit")
    path = Path(record["checkpoint"])
    if sha256_file(path) != record["checkpoint_sha256"]:
        raise ValueError("single-source primary checkpoint hash mismatch")
    checkpoint = json.loads(path.read_text())
    if checkpoint["full_request_sha256"] != stable_payload_hash(payload):
        raise ValueError("scientific request changed after primary maximization")
    for name, digest in checkpoint["files_sha256"].items():
        if sha256_file(name) != digest:
            raise ValueError("primary artifact changed: " + name)
    run_dir = Path(checkpoint["run_directory"])
    provenance = load_simple_yaml((run_dir / "provenance.yaml").read_text())
    from importlib.metadata import version
    if any(version(name) != expected for name, expected in provenance["packages"].items() if expected is not None):
        raise ValueError("runtime packages changed after primary maximization")
    for field in ("code_sha256", "input_sha256"):
        for name, digest in provenance[field].items():
            file_path = Path(name) if Path(name).is_absolute() else root / name
            if sha256_file(file_path) != digest:
                raise ValueError("input or runtime code changed after primary maximization: " + name)
    # The saved numerical result must still pass scientific/artifact review.
    if review_run(str(run_dir), str(root), write_artifacts=False)["status"] == "fail":
        raise ValueError("primary fit no longer passes review")
    result = copy.deepcopy(checkpoint["result"])
    result["primary_run_directory"] = str(run_dir)
    result["primary_checkpoint_sha256"] = record["checkpoint_sha256"]
    return result


def _run_flux(request_path, primary, root, cpus=1):
    config = load_config_file(request_path)
    validation = validate_config(config, root)
    if not validation.ok:
        raise ConfigError("; ".join(validation.errors))
    normalized = normalize_config(config, root, validation.warnings)
    from analysis_backend.skyllh_dr2_stacking import run_dr2_single_source
    specs = [dict(name=s.name, ra_rad=s.ra_rad, dec_rad=s.dec_rad, w_model=s.weight)
             for s in normalized.sources]
    result = run_dr2_single_source(specs, primary_result=primary,
        repo_root=root, gamma_mode=normalized.gamma_mode, gamma=abs(normalized.spectral_indices[0]),
        random_seed=normalized.random_seed, likelihood_mode=normalized.likelihood_mode,
        event_abs_dec_max_deg=normalized.event_abs_dec_max_deg,
        event_dec_min_deg=normalized.event_dec_min_deg, event_dec_max_deg=normalized.event_dec_max_deg,
        source_dec_window_deg=normalized.source_dec_window_deg, fit_procedure=normalized.fit_procedure,
        signal_energy_gamma_interpolation=normalized.signal_energy_gamma_interpolation,
        flux_upper_limit_cl=normalized.flux_upper_limit_cl,
        flux_upper_limit_gammas=normalized.flux_upper_limit_gammas,
        flux_measurement_ts_threshold=normalized.flux_measurement_ts_threshold)
    for key in ("TS", "ns", "gamma", "gamma_legacy", "minimizer_status", "fit_bounds", "fit_procedure"):
        if result[key] != primary[key]:
            raise ValueError("flux stage changed the recorded primary fit: " + key)
    result["single_source_stage"] = "flux"
    result["execution"] = execution_metadata(cpus, normalized)
    run_dir = write_run_artifacts(request_path, config, normalized, result, root)
    review = review_run(str(run_dir), str(root), write_artifacts=True)
    return AgentRun(request_path, normalized, result, run_dir, review)


def chat_stages(task):
    summary = dict(execution_flow=FLOW, single_source_stages=task.get("stages", {}))
    if task.get("single_source_llh_summary"):
        summary["single_source_llh_summary"] = task["single_source_llh_summary"]
    if task.get("status") == "AWAITING_FLUX":
        summary["flux_user_reply_required"] = True
        summary["next_action"] = ("Report single_source_llh_summary in the final answer chat bubble, ask whether to continue "
            "with flux upper limits/measurement and figures, then end this turn. Wait for the user's reply before "
            "run --stage flux --task " + task["task_id"] + " --flux-user-reply '<actual user reply>'.")
    if task.get("stages", {}).get("flux", {}).get("status") in {"COMPLETED", "COMPLETED_WITH_WARNINGS"}:
        result = load_simple_yaml((Path(task["artifacts"]["run_directory"]) / "report.yaml").read_text())["result"]
        flux = dict(generated_files=result.get("generated_files", {}))
        review = json.loads(Path(task["artifacts"]["review"]).read_text())
        flux["warnings"] = [check["message"] for check in review.get("checks", []) if check.get("status") == "warning"]
        if "flux_measurement" in result:
            flux["measurement"] = {k: v for k, v in result["flux_measurement"].items()
                if k in {"reported", "gamma", "gamma_mode", "phi0_hat", "phi0_unit",
                         "pivot_energy_gev", "flavor", "intervals", "warnings"}}
        limit_fields = {"gamma", "confidence_level", "phi0_upper_limit", "phi0_unit",
                        "pivot_energy_gev", "flavor", "ns_upper_limit",
                        "e2_dphi_de_upper_limit_gev_cm2_s"}
        flux["upper_limits"] = [{k: v for k, v in fit["flux_upper_limit"].items() if k in limit_fields}
                                for fit in result.get("flux_upper_limit_fits", [])]
        if "flux_upper_limit" in result:
            flux["upper_limit"] = {k: v for k, v in result["flux_upper_limit"].items() if k in limit_fields}
        summary["single_source_flux_summary"] = flux
    return summary
