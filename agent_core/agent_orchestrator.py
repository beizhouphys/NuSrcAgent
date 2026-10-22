from __future__ import annotations

import json
import traceback
from pathlib import Path
from typing import Any, Dict
from agent_core.cpu import positive_worker_count

from agent_core.analysis_agent import AnalysisAgent, build_catalog_request, build_single_source_request
from agent_core.planner import source_from_single_row_catalog
from agent_core.task_state import RUNNABLE_STATE, refresh_readiness, save_task, stable_payload_hash, utc_now


SAFE_ERROR_TYPES = {"OUTPUT_GENERATION_ERROR", "DEPENDENCY_ERROR", "TRANSIENT_IO_ERROR"}


def execute_task(task: Dict[str, Any], task_path: Path, repo_root: Path, backend: str = "likelihood", max_safe_retries: int = 1, workers: int = 1) -> Dict[str, Any]:
    workers = positive_worker_count(workers)
    if task.get("execution_flow") == "single_source_two_stage_v1":
        from agent_core.single_source_stages import execute_single_source_stage
        if backend != "likelihood":
            raise ValueError("two-stage single-source analysis requires the likelihood backend")
        return execute_single_source_stage(task, task_path, repo_root, "llh", max_safe_retries, workers=workers)
    refresh_readiness(task)
    if task.get("status") != RUNNABLE_STATE:
        raise ValueError("task is not ready to run; status=%s; missing=%s" % (task.get("status"), task.get("missing_parameters", [])))
    payload = build_analysis_payload(task, repo_root)
    payload_hash = stable_payload_hash(payload)
    attempts_allowed = 1 + max(0, int(max_safe_retries))
    for _ in range(attempts_allowed):
        attempt_number = len(task.get("attempts", [])) + 1
        attempt = {"attempt": attempt_number, "started_at_utc": utc_now(), "request_sha256": payload_hash, "status": "RUNNING", "cpu_budget": workers}
        task.setdefault("attempts", []).append(attempt)
        task["status"] = "RUNNING"
        save_task(task, repo_root, task_path)
        try:
            agent = AnalysisAgent(repo_root)
            request_path = task_path.parent / ("analysis_request_attempt_%d.yaml" % attempt_number)
            agent.prepare_request(payload, request_path)
            run = agent.run(request_path, backend=backend, prepare_only=False, workers=workers)
            attempt.update({"ended_at_utc": utc_now(), "run_directory": str(run.run_dir), "review_status": run.review.get("status") if run.review else "fail"})
            task["artifacts"] = {"request": str(request_path), "run_directory": str(run.run_dir), "review": str(run.run_dir / "review.json") if run.run_dir else None}
            task["status"] = "REVIEWING"
            completion = evaluate_completion(task, run.review or {})
            task["completion"] = completion
            attempt["status"] = completion["status"]
            if completion["status"] in {"COMPLETED", "COMPLETED_WITH_WARNINGS"}:
                task["status"] = completion["status"]
                if payload["analysis"].get("stacking_flux"):
                    from agent_core.stacking_stages import record_primary
                    record_primary(task, task_path, repo_root, run, payload_hash)
                write_agent_review(task, task_path.parent)
                save_task(task, repo_root, task_path)
                return task
            auto_fixable = completion.get("auto_fix_allowed", False)
            if auto_fixable and attempt_number < attempts_allowed:
                attempt["recovery"] = {"action": "rerun the identical request once", "scientific_parameters_changed": False}
                task["status"] = RUNNABLE_STATE
                save_task(task, repo_root, task_path)
                continue
            task["status"] = "FAILED"
            write_agent_review(task, task_path.parent)
            save_task(task, repo_root, task_path)
            return task
        except Exception as exc:
            error_type = classify_error(exc)
            attempt.update({"ended_at_utc": utc_now(), "status": "FAILED", "error_type": error_type, "error": str(exc), "traceback": traceback.format_exc()})
            if error_type in SAFE_ERROR_TYPES and attempt_number < attempts_allowed:
                attempt["recovery"] = {"action": "rerun the identical request once", "scientific_parameters_changed": False}
                task["status"] = RUNNABLE_STATE
                save_task(task, repo_root, task_path)
                continue
            task["status"] = "FAILED"
            task["completion"] = {"status": "FAILED", "checks": [{"id": "execution", "status": "fail", "message": str(exc)}], "auto_fix_allowed": False}
            write_agent_review(task, task_path.parent)
            save_task(task, repo_root, task_path)
            return task
    return task


def build_analysis_payload(task: Dict[str, Any], repo_root: Path) -> Dict[str, Any]:
    parameters = task["parameters"]
    gamma = float(parameters["gamma"]["value"])
    data_sample = str(parameters.get("data_sample", {}).get("value") or "icecube_public_ps_14yr_dr2")
    gamma_mode = str(parameters.get("gamma_mode", {}).get("value") or "fitted")
    likelihood_mode = str(parameters.get("likelihood_mode", {}).get("value") or ("spatial_energy" if data_sample == "icecube_public_ps_14yr_dr2" else "spatial_only"))
    event_abs_dec_max_deg = parameters.get("event_abs_dec_max_deg", {}).get("value")
    event_dec_min_deg = parameters.get("event_dec_min_deg", {}).get("value")
    event_dec_max_deg = parameters.get("event_dec_max_deg", {}).get("value")
    inputs = task["inputs"]
    if task["workflow"] == "single_source":
        if inputs["kind"] == "catalog":
            source = source_from_single_row_catalog(task, repo_root)
        else:
            source = inputs["sources"][0]
        payload = build_single_source_request(str(source.get("name") or "source_0001"), float(source["ra_deg"]), float(source["dec_deg"]), gamma, "data_output/runs", data_sample, gamma_mode, likelihood_mode, event_abs_dec_max_deg, event_dec_min_deg, event_dec_max_deg)
        if "source_dec_window_deg" in parameters:
            payload["background"]["source_dec_window_deg"] = parameters["source_dec_window_deg"]["value"]
        for key in ("flux_upper_limit_cl", "flux_upper_limit_gammas", "flux_measurement_ts_threshold", "fit_procedure", "signal_energy_gamma_interpolation", "spectrum", "gamma_bounds"):
            if key in parameters:
                payload["analysis"][key] = parameters[key]["value"]
        return payload
    mode = parameters["weight_mode"]["value"]
    weight_column = parameters["weight_column"]["value"] if mode == "column" else None
    manual_weights = parameters["manual_weights"]["value"] if mode == "manual" else None
    catalog = inputs.get("catalog") if inputs["kind"] == "catalog" else None
    sources = inputs.get("sources") if inputs["kind"] == "inline_sources" else None
    built_in_catalog = inputs.get("built_in_catalog") if inputs["kind"] == "built_in_catalog" else None
    payload = build_catalog_request(catalog, sources, parameters["name_column"]["value"], parameters["ra_column"]["value"], parameters["dec_column"]["value"], weight_column, manual_weights, [gamma], bool(parameters["include_uniform_baseline"]["value"]), "data_output/runs", data_sample, gamma_mode, likelihood_mode, built_in_catalog, event_abs_dec_max_deg, event_dec_min_deg, event_dec_max_deg, parameters.get("catalog_operation", {}).get("value"))
    if "source_dec_window_deg" in parameters:
        payload["background"]["source_dec_window_deg"] = parameters["source_dec_window_deg"]["value"]
    for key in ("flux_upper_limit_cl", "flux_upper_limit_gammas", "scan_fit_procedure", "stacking_flux", "spectrum", "gamma_bounds"):
        if key in parameters:
            payload["analysis"][key] = parameters[key]["value"]
    return payload


def evaluate_completion(task: Dict[str, Any], review: Dict[str, Any]) -> Dict[str, Any]:
    checks = []
    no_missing = not task.get("missing_parameters")
    checks.append({"id": "parameter_gate", "status": "pass" if no_missing else "fail", "message": "all required parameters are confirmed" if no_missing else "required parameters remain unconfirmed"})
    review_status = review.get("status", "fail")
    checks.append({"id": "run_review", "status": review_status, "message": "completed-run review status is %s" % review_status})
    run_directory = task.get("artifacts", {}).get("run_directory")
    checks.append({"id": "run_artifact", "status": "pass" if run_directory else "fail", "message": "run directory is recorded" if run_directory else "run directory is missing"})
    statuses = [item["status"] for item in checks]
    if "fail" in statuses:
        status = "FAILED"
    elif "warning" in statuses:
        status = "COMPLETED_WITH_WARNINGS"
    else:
        status = "COMPLETED"
    failed_review_checks = [item for item in review.get("checks", []) if item.get("status") == "fail"]
    auto_fix_allowed = bool(failed_review_checks) and all(item.get("auto_fix_allowed", False) for item in failed_review_checks)
    return {"status": status, "checks": checks, "review_status": review_status, "auto_fix_allowed": auto_fix_allowed}


def classify_error(exc: Exception) -> str:
    message = (type(exc).__name__ + ": " + str(exc)).lower()
    if any(value in message for value in ["reportlab", "matplotlib", "node.js", "module not found", "modulenotfounderror"]):
        return "DEPENDENCY_ERROR"
    if any(value in message for value in ["excel", "workbook", "pdf", "figure", "output generation"]):
        return "OUTPUT_GENERATION_ERROR"
    if isinstance(exc, (OSError, IOError)):
        return "TRANSIENT_IO_ERROR"
    if isinstance(exc, (ValueError, KeyError)):
        return "DATA_VALIDATION_ERROR"
    return "INTERNAL_ERROR"


def write_agent_review(task: Dict[str, Any], task_dir: Path) -> None:
    payload = {
        "task_id": task.get("task_id"),
        "status": task.get("status"),
        "workflow": task.get("workflow"),
        "completion": task.get("completion", {}),
        "attempts": task.get("attempts", []),
        "artifacts": task.get("artifacts", {}),
    }
    with (task_dir / "agent_review.json").open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    lines = ["# Agent Task Review", "", "Task: `%s`" % task.get("task_id"), "", "Status: `%s`" % task.get("status"), "", "## Completion Checks", ""]
    for check in task.get("completion", {}).get("checks", []):
        lines.append("- `%s` %s: %s" % (check.get("status"), check.get("id"), check.get("message")))
    lines.extend(["", "## Attempts", ""])
    for attempt in task.get("attempts", []):
        lines.append("- Attempt %s: `%s`; request `%s`" % (attempt.get("attempt"), attempt.get("status"), attempt.get("request_sha256")))
    with (task_dir / "agent_review.md").open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def resume_interrupted_task(task: Dict[str, Any]) -> Dict[str, Any]:
    if task.get("status") not in {"RUNNING", "REVIEWING"}:
        raise ValueError("only RUNNING or REVIEWING tasks can be resumed")
    task["status"] = "AWAITING_FLUX" if task.get("active_stage") == "flux" else RUNNABLE_STATE
    task.setdefault("events", []).append({"event": "manual_resume", "at_utc": utc_now()})
    return refresh_readiness(task)
