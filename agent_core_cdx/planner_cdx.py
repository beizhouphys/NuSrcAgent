from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent_core_cdx.catalog_inspector_cdx import inspect_catalog
from agent_core_cdx.task_state_cdx import create_task_record, parameter, questions_for_missing, refresh_readiness


def plan_single_task(original_request: str, name: str, ra_deg: float, dec_deg: float, gamma: Optional[float]) -> Dict[str, Any]:
    planning_errors: List[str] = []
    validate_source_values([{"name": name, "ra_deg": ra_deg, "dec_deg": dec_deg}], planning_errors)
    validate_planning_values(1, gamma, None, None, None, planning_errors)
    parameters = {
        "gamma": parameter(gamma, "user" if gamma is not None else None, gamma is not None),
        "include_uniform_baseline": parameter(False, "system", True),
    }
    inputs = {"kind": "inline_sources", "sources": [{"name": name, "ra_deg": ra_deg, "dec_deg": dec_deg}], "source_count": 1}
    task = create_task_record(original_request, "analyze_sources", "single_source", "Exactly one input source was provided.", inputs, parameters, planning_errors=planning_errors)
    task["questions"] = combined_questions(task, planning_errors)
    return refresh_readiness(task)


def plan_catalog_task(original_request: str, repo_root: Path, catalog: Optional[str], sources: Optional[List[Dict[str, Any]]], name_column: Optional[str], ra_column: Optional[str], dec_column: Optional[str], gamma: Optional[float], weight_mode: Optional[str], weight_column: Optional[str], weight_meaning: Optional[str], manual_weights: Optional[List[float]], include_uniform_baseline: bool = True) -> Dict[str, Any]:
    planning_errors: List[str] = []
    inspection = None
    supplied_columns = {"name": name_column is not None, "ra": ra_column is not None, "dec": dec_column is not None}
    if catalog is not None:
        catalog_path = Path(catalog).expanduser()
        if not catalog_path.is_absolute():
            catalog_path = repo_root / catalog_path
        inspection = inspect_catalog(str(catalog_path), name_column, ra_column, dec_column, weight_column)
        source_count = int(inspection.get("row_count", 0))
        inferred = inspection.get("inferred_columns", {})
        name_column = inferred.get("name") or name_column
        ra_column = inferred.get("ra_deg") or ra_column
        dec_column = inferred.get("dec_deg") or dec_column
        if inspection.get("status") == "fail":
            planning_errors.extend(str(value) for value in inspection.get("errors", []))
        add_inspection_errors(inspection, planning_errors)
        inputs = {"kind": "catalog", "catalog": catalog, "source_count": source_count, "inspection": inspection}
    else:
        source_count = len(sources or [])
        inputs = {"kind": "inline_sources", "sources": list(sources or []), "source_count": source_count}
        if source_count == 0:
            planning_errors.append("at least one source or a catalog is required")
        validate_source_values(list(sources or []), planning_errors)
    workflow = "single_source" if source_count == 1 else "catalog_scan_and_stacking"
    reason = "Exactly one input source was provided." if source_count == 1 else "%d input sources require a catalog-wide single-source scan plus stacking." % source_count
    parameters = {
        "gamma": parameter(gamma, "user" if gamma is not None else None, gamma is not None),
        "name_column": parameter(name_column, "user" if supplied_columns["name"] else "agent_inferred", name_column is not None),
        "ra_column": parameter(ra_column, "user" if supplied_columns["ra"] else "agent_inferred", ra_column is not None),
        "dec_column": parameter(dec_column, "user" if supplied_columns["dec"] else "agent_inferred", dec_column is not None),
        "weight_mode": parameter(weight_mode, "user" if weight_mode is not None else None, weight_mode is not None),
        "weight_column": parameter(weight_column, "user" if weight_column is not None else None, weight_column is not None),
        "weight_meaning": parameter(weight_meaning, "user" if weight_meaning is not None else None, weight_meaning is not None),
        "manual_weights": parameter(manual_weights, "user" if manual_weights is not None else None, manual_weights is not None),
        "include_uniform_baseline": parameter(bool(include_uniform_baseline), "system_default", True),
    }
    if workflow == "single_source":
        parameters["weight_mode"] = parameter("uniform", "system", True)
    validate_planning_values(source_count, gamma, weight_mode, weight_column, manual_weights, planning_errors)
    task = create_task_record(original_request, "analyze_sources", workflow, reason, inputs, parameters, planning_errors=planning_errors)
    task["questions"] = combined_questions(task, planning_errors)
    return refresh_readiness(task)


def validate_planning_values(source_count: int, gamma: Optional[float], weight_mode: Optional[str], weight_column: Optional[str], manual_weights: Optional[List[float]], errors: List[str]) -> None:
    if gamma is not None and (not math.isfinite(float(gamma)) or gamma >= 0.0):
        errors.append("gamma must use the negative power-law convention")
    if weight_mode is not None and weight_mode not in {"uniform", "column", "manual"}:
        errors.append("weight mode must be uniform, column, or manual")
    if weight_mode == "column" and not weight_column:
        errors.append("column weighting requires a weight column")
    if weight_mode == "manual":
        if manual_weights is None or len(manual_weights) != source_count:
            errors.append("manual weights must contain one value per source")
        elif any(not math.isfinite(float(value)) or value < 0.0 for value in manual_weights) or not math.isfinite(sum(manual_weights)) or sum(manual_weights) <= 0.0:
            errors.append("manual weights must be non-negative with a positive sum")


def validate_source_values(sources: List[Dict[str, Any]], errors: List[str]) -> None:
    for index, source in enumerate(sources, start=1):
        try:
            ra_deg = float(source.get("ra_deg"))
            dec_deg = float(source.get("dec_deg"))
        except (TypeError, ValueError):
            errors.append("source %d coordinates must be numeric" % index)
            continue
        if not math.isfinite(ra_deg) or not 0.0 <= ra_deg < 360.0:
            errors.append("source %d RA must be finite and in [0, 360) degrees" % index)
        if not math.isfinite(dec_deg) or not -90.0 <= dec_deg <= 90.0:
            errors.append("source %d Dec must be finite and in [-90, 90] degrees" % index)


def add_inspection_errors(inspection: Dict[str, Any], errors: List[str]) -> None:
    coordinate_review = inspection.get("coordinate_review", {})
    if coordinate_review.get("missing_rows") or coordinate_review.get("invalid_rows"):
        errors.append("catalog contains missing or invalid coordinates and must be corrected before execution")
    selected = inspection.get("selected_weight_review")
    if selected:
        row_count = int(inspection.get("row_count", 0))
        if selected.get("numeric_rows") != row_count or selected.get("negative_rows", 0) or selected.get("sum", 0.0) <= 0.0:
            errors.append("selected weight column must be numeric, non-negative, and have a positive sum")


def combined_questions(task: Dict[str, Any], errors: List[str]) -> List[str]:
    questions = questions_for_missing(task)
    for error in errors:
        if "gamma" in error:
            questions.append("Provide a finite negative gamma value.")
        elif "manual weights" in error:
            questions.append("Provide one finite non-negative manual weight per source, with a positive total.")
        elif "coordinate" in error or " RA " in error or " Dec " in error:
            questions.append("Correct the source coordinates or catalog coordinate columns before execution.")
        elif "column" in error:
            questions.append("Correct or identify the required catalog column before execution.")
    return list(dict.fromkeys(questions))


def source_from_single_row_catalog(task: Dict[str, Any], repo_root: Path) -> Dict[str, Any]:
    inputs = task["inputs"]
    path = Path(inputs["catalog"])
    if not path.is_absolute():
        path = repo_root / path
    delimiter = "\t" if path.suffix.lower() in {".tsv", ".tab"} else ","
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter=delimiter))
    if len(rows) != 1:
        raise ValueError("single-source catalog must contain exactly one row")
    row = rows[0]
    parameters = task["parameters"]
    name_column = parameters["name_column"]["value"]
    ra_column = parameters["ra_column"]["value"]
    dec_column = parameters["dec_column"]["value"]
    return {"name": row.get(name_column, "source_0001") if name_column else "source_0001", "ra_deg": float(row[ra_column]), "dec_deg": float(row[dec_column])}


def revalidate_task_plan(task: Dict[str, Any], repo_root: Path) -> Dict[str, Any]:
    errors: List[str] = []
    inputs = task.get("inputs", {})
    parameters = task.get("parameters", {})
    source_count = int(inputs.get("source_count", 0))
    if inputs.get("kind") == "catalog":
        catalog_path = Path(str(inputs.get("catalog", ""))).expanduser()
        if not catalog_path.is_absolute():
            catalog_path = repo_root / catalog_path
        inspection = inspect_catalog(
            str(catalog_path),
            parameters.get("name_column", {}).get("value"),
            parameters.get("ra_column", {}).get("value"),
            parameters.get("dec_column", {}).get("value"),
            parameters.get("weight_column", {}).get("value") if parameters.get("weight_mode", {}).get("value") == "column" else None,
        )
        inputs["inspection"] = inspection
        source_count = int(inspection.get("row_count", 0))
        inputs["source_count"] = source_count
        if inspection.get("status") == "fail":
            errors.extend(str(value) for value in inspection.get("errors", []))
        add_inspection_errors(inspection, errors)
    gamma = parameters.get("gamma", {}).get("value")
    weight_mode = parameters.get("weight_mode", {}).get("value")
    weight_column = parameters.get("weight_column", {}).get("value")
    manual_weights = parameters.get("manual_weights", {}).get("value")
    if inputs.get("kind") == "inline_sources":
        validate_source_values(list(inputs.get("sources", [])), errors)
    validate_planning_values(source_count, gamma, weight_mode, weight_column, manual_weights, errors)
    task["planning_errors"] = errors
    task["questions"] = combined_questions(task, errors)
    return refresh_readiness(task)
