from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


TASK_SCHEMA_VERSION = "0.1"
AGENT_WRAPPER_VERSION = "0.2.0-private-alpha.3" # cdx
TERMINAL_STATES = {"COMPLETED", "COMPLETED_WITH_WARNINGS", "FAILED"}
RUNNABLE_STATE = "READY"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_task_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return "task_%s_cdx" % stamp


def parameter(value: Any = None, source: Optional[str] = None, confirmed: bool = False, meaning: Optional[str] = None) -> Dict[str, Any]:
    result = {"value": value, "source": source, "confirmed": bool(confirmed)}
    if meaning is not None:
        result["meaning"] = meaning
    return result


def create_task_record(original_request: str, intent: str, workflow: str, reason: str, inputs: Dict[str, Any], parameters: Dict[str, Dict[str, Any]], questions: Optional[List[str]] = None, planning_errors: Optional[List[str]] = None) -> Dict[str, Any]:
    task_id = make_task_id()
    now = utc_now()
    task = {
        "schema_version": TASK_SCHEMA_VERSION,
        "agent_wrapper_version": AGENT_WRAPPER_VERSION,
        "task_id": task_id,
        "created_at_utc": now,
        "updated_at_utc": now,
        "original_request": original_request,
        "intent": intent,
        "workflow": workflow,
        "selection_reason": reason,
        "planned_tools": tools_for_workflow(workflow),
        "inputs": inputs,
        "parameters": parameters,
        "questions": list(questions or []),
        "planning_errors": list(planning_errors or []),
        "missing_parameters": [],
        "status": "DRAFT",
        "user_confirmations": [],
        "attempts": [],
        "artifacts": {},
        "completion": {"status": "not_evaluated", "checks": []},
    }
    refresh_readiness(task)
    return task


def required_parameter_names(task: Dict[str, Any]) -> List[str]:
    names = ["gamma"]
    if task.get("workflow") == "catalog_scan_and_stacking":
        names.append("weight_mode")
        mode = task.get("parameters", {}).get("weight_mode", {}).get("value")
        if mode == "column":
            names.extend(["weight_column", "weight_meaning"])
        elif mode == "manual":
            names.append("manual_weights")
    return names


def tools_for_workflow(workflow: str) -> List[str]:
    mapping = {
        "single_source": ["run_analysis_agent_cdx.py single", "review-run"],
        "catalog_scan_and_stacking": ["inspect-catalog", "run_analysis_agent_cdx.py catalog", "review-run"],
        "inspect_catalog": ["inspect-catalog"],
        "review_existing_run": ["review-run"],
        "resume_task": ["run_agent_wrap_cdx.py resume"],
    }
    return list(mapping.get(workflow, []))


def refresh_readiness(task: Dict[str, Any]) -> Dict[str, Any]:
    missing = []
    for name in required_parameter_names(task):
        item = task.get("parameters", {}).get(name)
        if not isinstance(item, dict) or missing_parameter_value(item.get("value")) or not item.get("confirmed", False):
            missing.append(name)
    task["missing_parameters"] = missing
    if task.get("planning_errors"):
        task["status"] = "AWAITING_CONFIRMATION"
    elif missing or task.get("questions"):
        task["status"] = "AWAITING_CONFIRMATION"
    elif task.get("status") not in TERMINAL_STATES and task.get("status") not in {"RUNNING", "REVIEWING"}:
        task["status"] = RUNNABLE_STATE
    task["updated_at_utc"] = utc_now()
    return task


def missing_parameter_value(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def confirm_parameters(task: Dict[str, Any], values: Dict[str, Any], meanings: Optional[Dict[str, str]] = None, actor: str = "user") -> Dict[str, Any]:
    if task.get("status") in TERMINAL_STATES or task.get("status") in {"RUNNING", "REVIEWING"}:
        raise ValueError("parameters cannot be changed while a task is running or after it has reached a terminal state; create a new task")
    allowed = {"gamma", "weight_mode", "weight_column", "weight_meaning", "manual_weights", "include_uniform_baseline", "name_column", "ra_column", "dec_column"}
    unknown = sorted(set(values) - allowed)
    if unknown:
        raise ValueError("unsupported confirmation parameters: %s" % ", ".join(unknown))
    for name, value in values.items():
        if value is None:
            continue
        task.setdefault("parameters", {})[name] = parameter(value, actor, True, (meanings or {}).get(name))
        task.setdefault("user_confirmations", []).append({"parameter": name, "value": value, "actor": actor, "confirmed_at_utc": utc_now()})
    task["questions"] = questions_for_missing(task)
    return refresh_readiness(task)


def questions_for_missing(task: Dict[str, Any]) -> List[str]:
    questions = []
    parameters = task.get("parameters", {})
    gamma = parameters.get("gamma", {})
    if missing_parameter_value(gamma.get("value")) or not gamma.get("confirmed", False):
        questions.append("Which negative source spectral index gamma should be used?")
    if task.get("workflow") == "catalog_scan_and_stacking":
        mode = parameters.get("weight_mode", {})
        if missing_parameter_value(mode.get("value")) or not mode.get("confirmed", False):
            questions.append("Should stacking use uniform, catalog-column, or manual weights?")
        elif mode.get("value") == "column":
            column = parameters.get("weight_column", {})
            meaning = parameters.get("weight_meaning", {})
            if missing_parameter_value(column.get("value")) or not column.get("confirmed", False):
                questions.append("Which catalog column should be used as the stacking weight?")
            if missing_parameter_value(meaning.get("value")) or not meaning.get("confirmed", False):
                questions.append("What physical quantity and units does the selected weight column represent?")
        elif mode.get("value") == "manual":
            weights = parameters.get("manual_weights", {})
            if missing_parameter_value(weights.get("value")) or not weights.get("confirmed", False):
                questions.append("Provide one non-negative manual weight for each input source, in input order.")
    return questions


def task_directory(repo_root: Path, task_id: str) -> Path:
    return repo_root / "data_output" / "agent_tasks_cdx" / task_id


def save_task(task: Dict[str, Any], repo_root: Path, path: Optional[Path] = None) -> Path:
    target = path or (task_directory(repo_root, str(task["task_id"])) / "task_cdx.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    task["updated_at_utc"] = utc_now()
    with target.open("w", encoding="utf-8") as handle:
        json.dump(task, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return target


def load_task(path_value: str, repo_root: Path) -> tuple[Dict[str, Any], Path]:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        candidate = repo_root / path
        if candidate.exists():
            path = candidate
        else:
            path = task_directory(repo_root, path_value) / "task_cdx.json"
    if path.is_dir():
        path = path / "task_cdx.json"
    if not path.exists():
        raise ValueError("task file does not exist: %s" % path)
    with path.open("r", encoding="utf-8") as handle:
        task = json.load(handle)
    if not isinstance(task, dict) or "task_id" not in task:
        raise ValueError("invalid agent task file: %s" % path)
    return task, path


def stable_payload_hash(payload: Dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
