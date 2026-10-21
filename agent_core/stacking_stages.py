"""Review and persist the two separately reported stages of a joint stack."""
from __future__ import annotations

import copy
import inspect
import math
import json
from pathlib import Path

from agent_core.file_cache import sha256_file
from agent_core.stage_progress import subphase
from agent_core.simple_yaml import load_simple_yaml
from agent_core.task_state import save_task, stable_payload_hash, utc_now


def record_primary(task, task_path, root, run, request_hash):
    if run.result.get("stacking_phase") != "primary":
        return
    receipt = run.run_dir / "primary_result.json"
    receipt.write_text(json.dumps(run.result, indent=2) + "\n")
    files = [p for p in run.run_dir.iterdir() if p.is_file()]
    status = task["status"]
    task["stacking_stages"] = dict(primary=dict(status=status,
        request_sha256=request_hash, run_directory=str(run.run_dir),
        result_file=str(receipt), artifacts_sha256={str(p): sha256_file(p) for p in files},
        chat_summary={key: run.result[key] for key in (
            "ns", "gamma", "gamma_mode", "TS", "pre_trial_p", "pre_trial_significance",
            "p_value_method", "p_value_is_estimate", "significance_convention", "n_sources")},
        review_status=run.review["status"],
        warnings=[c["message"] for c in run.review.get("checks", []) if c.get("status") == "warning"]), flux=dict(status="PENDING"))
    task["artifacts"]["primary_run_directory"] = str(run.run_dir)
    task["status"] = "AWAITING_FLUX"
    task["completion"] = dict(task["completion"], status="AWAITING_FLUX")
    task["active_stage"] = "flux"
    task["attempts"][-1]["stage"] = "primary"
    task["attempts"][-1]["status"] = status
    save_task(task, root, task_path)


def load_primary(task, root, payload):
    stage = task.get("stacking_stages", {}).get("primary", {})
    if stage.get("status") not in {"COMPLETED", "COMPLETED_WITH_WARNINGS"}:
        raise ValueError("Flux stage requires a successfully reviewed primary stage")
    if stage.get("request_sha256") != stable_payload_hash(payload):
        raise ValueError("Scientific request changed after the primary stage; create a new task")
    for path, digest in stage["artifacts_sha256"].items():
        if not Path(path).is_file() or sha256_file(path) != digest:
            raise ValueError("Primary-stage artifact changed: " + path)
    folder = Path(stage["run_directory"])
    provenance = load_simple_yaml((folder / "provenance.yaml").read_text())
    from importlib.metadata import version
    if any(version(name) != expected for name, expected in provenance["packages"].items() if expected is not None):
        raise ValueError("Runtime packages changed after the primary stage; create a new task")
    for key in ("code_sha256", "input_sha256"):
        for name, digest in provenance[key].items():
            path = root / name
            if not path.is_file() or sha256_file(path) != digest:
                raise ValueError("Primary-stage code or input changed: " + name)
    result = json.loads(Path(stage["result_file"]).read_text())
    return result


def execute_flux_stage(task, task_path, root, backend="likelihood", max_safe_retries=1, cpus=1, user_reply=None):
    from agent_core.agent_orchestrator import (
        build_analysis_payload, classify_error, evaluate_completion, write_agent_review,
        SAFE_ERROR_TYPES,
    )
    from agent_core.analysis_agent import AnalysisAgent
    if cpus < 1 or max_safe_retries not in (0, 1):
        raise ValueError("CPU budget must be positive and at most one safe retry is allowed")
    if task.get("status") != "AWAITING_FLUX" or not task["parameters"].get("stacking_flux", {}).get("value"):
        raise ValueError("Flux stage requires AWAITING_FLUX; run the primary stage first")
    if (not isinstance(user_reply, str) or not user_reply.strip()):
        raise ValueError("Flux stage requires the user continuation reply after the primary final answer; use --flux-user-reply")
    payload = build_analysis_payload(task, root)
    with subphase('saved primary checkpoint integrity verification'):
        primary = load_primary(task, root, payload)
    request_hash = stable_payload_hash(payload)
    for retry in range(1 + max_safe_retries):
        number = len(task["attempts"]) + 1
        attempt = dict(attempt=number, stage="flux", request_sha256=request_hash,
                       started_at_utc=utc_now(), status="RUNNING")
        attempt["flux_user_reply"] = user_reply
        task["attempts"].append(attempt)
        task["status"] = "RUNNING"
        task["active_stage"] = "flux"
        save_task(task, root, task_path)
        try:
            with subphase('saved primary checkpoint integrity verification'):
                load_primary(task, root, payload)
            agent = AnalysisAgent(root)
            request = task_path.parent / ("analysis_request_attempt_%d.yaml" % number)
            agent.prepare_request(payload, request)
            options = dict(backend=backend, prepare_only=False, stacking_primary=copy.deepcopy(primary))
            if "cpus" in inspect.signature(agent.run).parameters:
                options["cpus"] = cpus
            run = agent.run(request, **options)
            completion = evaluate_completion(dict(task, artifacts={"run_directory": str(run.run_dir)}), run.review or {})
            attempt.update(ended_at_utc=utc_now(), status=completion["status"],
                           run_directory=str(run.run_dir), review_status=(run.review or {}).get("status"))
            if completion["status"] == "FAILED":
                task["completion"] = completion
                if completion.get("auto_fix_allowed") and retry < max_safe_retries:
                    attempt["recovery"] = dict(action="rerun the identical flux stage once", scientific_parameters_changed=False)
                    continue
                task["status"] = "FAILED"
                task["stacking_stages"]["flux"] = dict(status="FAILED", review_status="fail", run_directory=str(run.run_dir))
            else:
                task["status"] = completion["status"]
                task["completion"] = completion
                task["artifacts"].update(request=str(request), run_directory=str(run.run_dir),
                    review=str(run.run_dir / "review.json"), flux_run_directory=str(run.run_dir))
                settings = payload["analysis"]["stacking_flux"]
                result = run.result
                summary = dict(display_quantity=settings["display_quantity"],
                    intensity_unit="GeV^-1 cm^-2 s^-1 sr^-1", upper_limits=[
                        {key: fit["flux_upper_limit"][key] for key in (
                            "gamma", "confidence_level", "pivot_energy_gev", "phi0_upper_limit", "phi0_unit",
                            "e2_dphi_de_upper_limit_gev_cm2_s", "intensity0_upper_limit",
                            "e2_intensity_upper_limit_gev_cm2_s_sr")}
                        for fit in result.get("flux_upper_limit_fits", [])],
                    generated_files=result.get("generated_files", {}))
                measurement = result.get("flux_measurement", {})
                if measurement.get("reported"):
                    summary["measurement"] = dict(
                        intensity0_hat=measurement["intensity0_hat"], gamma=measurement["gamma"],
                        pivot_energy_gev=measurement["pivot_energy_gev"],
                        intensity0_unit=measurement["intensity0_unit"],
                        intervals=[dict(row, parameter="intensity0", lower=row["lower"]/(4*math.pi),
                                        upper=row["upper"]/(4*math.pi))
                            if row["parameter"] == "phi0" else row for row in measurement["intervals"]])
                task["stacking_stages"]["flux"] = dict(status=task["status"],
                    run_directory=str(run.run_dir), chat_summary=summary, review_status=run.review["status"],
                    warnings=[c["message"] for c in run.review.get("checks", []) if c.get("status") == "warning"])
            write_agent_review(task, task_path.parent)
            save_task(task, root, task_path)
            return task
        except Exception as exc:
            error_type = classify_error(exc)
            attempt.update(ended_at_utc=utc_now(), status="FAILED", error_type=error_type, error=str(exc))
            if error_type in SAFE_ERROR_TYPES and retry < max_safe_retries:
                attempt["recovery"] = dict(action="rerun the identical flux stage once", scientific_parameters_changed=False)
                continue
            task["status"] = "FAILED"
            task["stacking_stages"]["flux"] = dict(status="FAILED", error=str(exc))
            task["completion"] = dict(status="FAILED", checks=[dict(id="flux_stage", status="fail", message=str(exc))])
            write_agent_review(task, task_path.parent)
            save_task(task, root, task_path)
            return task
    return task


def chat_stages(task):
    stages = task.get("stacking_stages", {})
    output = {}
    for name, stage in stages.items():
        if stage.get("status") in {"COMPLETED", "COMPLETED_WITH_WARNINGS"}:
            output[name] = dict(stage["chat_summary"], status=stage["status"],
                                review_status=stage["review_status"], warnings=stage.get("warnings", []))
    if task.get("status") == "AWAITING_FLUX":
        output["flux_user_reply_required"] = True
        output["next_action"] = ("Report the primary result in the final answer chat bubble, ask whether to continue "
            "with flux upper limits/measurement and figures, then end this turn. Wait for the user's reply before "
            "run --task " + task["task_id"] + " --stage flux --flux-user-reply '<actual user reply>'.")
    return output


def stack_flux_markdown(result):
    if result.get("stacking_phase") != "flux":
        return []
    lines = ["", "## Joint-stack intensity", "",
        "Catalog intensity is the sum of the selected source fluxes divided by 4*pi sr. "
        "Each source contributes its normalized intrinsic weight; detector acceptance is applied once. "
        "All quantities below are nu_mu+anti_nu_mu.", "",
        "| Fixed Gamma | One-sided CL | Intensity limit at 100 TeV [GeV^-1 cm^-2 s^-1 sr^-1] | E^2 dI/dE at 100 TeV [GeV cm^-2 s^-1 sr^-1] |",
        "| --- | --- | --- | --- |"]
    for fit in result.get("flux_upper_limit_fits", []):
        limit = fit["flux_upper_limit"]
        lines.append(f"| {limit['gamma']:g} | {100*limit['confidence_level']:g}% | {limit['intensity0_upper_limit']:.8g} | {limit['e2_intensity_upper_limit_gev_cm2_s_sr']:.8g} |")
    m = result.get("flux_measurement", {})
    if m.get("reported"):
        lines.extend(["", "Primary-spectrum measured intensity at 1 TeV: "
            f"`{m['intensity0_hat']:.8g} GeV^-1 cm^-2 s^-1 sr^-1`; Gamma = `{m['gamma']:.8g}`.",
            "", "| Parameter | CL | Profile interval |", "| --- | --- | --- |"])
        for row in m["intervals"]:
            factor = 1/(4*math.pi) if row["parameter"] == "phi0" else 1.
            parameter = "Intensity at 1 TeV [GeV^-1 cm^-2 s^-1 sr^-1]" if row["parameter"] == "phi0" else "Gamma"
            bound = " (bound reached)" if row['lower_at_boundary'] or row['upper_at_boundary'] else ""
            lines.append(f"| {parameter} | {100*row['confidence_level']:.4g}% | [{row['lower']*factor:.8g}, {row['upper']*factor:.8g}]{bound} |")
    else:
        lines.extend(["", "The primary TS does not exceed 9; no measured-intensity intervals or measurement curve are reported."])
    lines.extend(["", "Limits and intervals use the existing asymptotic profile-likelihood construction. "
        "The spectrum figure displays intensity on one vertical axis, including catalog limits and measurements, "
        "and only the two diffuse astrophysical references with their published bands. "
        "No NGC 1068 reference is included. The primary maximization was not repeated."])
    return lines
