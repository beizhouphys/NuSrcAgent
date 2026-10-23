from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional

from analysis_backend.sources import load_builtin_catalog, read_source_catalog
from agent_core.catalog_inspector import inspect_catalog, inspect_coordinates, inspect_numeric_column, inspect_weight_candidates
from agent_core.task_state import create_task_record, parameter, questions_for_missing, refresh_readiness
from agent_core.coordinates import CoordinateError, canonical_source, catalog_source


def plan_single_task(original_request: str, name: str, ra_deg: float, dec_deg: float, gamma: Optional[float], data_sample: str = "icecube_public_ps_14yr_dr2", gamma_mode: str = "fitted", likelihood_mode: str = "spatial_energy", event_abs_dec_max_deg: Optional[float] = None, event_dec_min_deg: Optional[float] = None, event_dec_max_deg: Optional[float] = None, coordinates=None) -> Dict[str, Any]:
    planning_errors: List[str] = []
    source = {"name": name, "ra_deg": ra_deg, "dec_deg": dec_deg}
    if coordinates is not None:
        if ra_deg is not None or dec_deg is not None:
            raise CoordinateError("Use --ra-deg/--dec-deg or generic coordinates, not both.")
        source["coordinates"] = dict(coordinates)
    validate_source_values([source], planning_errors)
    validate_planning_values(1, gamma, None, None, None, planning_errors, data_sample, gamma_mode, likelihood_mode, event_abs_dec_max_deg, event_dec_min_deg, event_dec_max_deg)
    parameters = {
        "gamma": parameter(gamma, "user" if gamma is not None else None, gamma is not None),
        "include_uniform_baseline": parameter(False, "system", True),
        "data_sample": parameter(data_sample, "user" if data_sample != "icecube_public_ps_14yr_dr2" else "system_default", True),
        "gamma_mode": parameter(gamma_mode, "system_default", True),
        "likelihood_mode": parameter(likelihood_mode, "system_default", True),
        "event_abs_dec_max_deg": parameter(event_abs_dec_max_deg, "user" if event_abs_dec_max_deg is not None else "system_default", True),
        "event_dec_min_deg": parameter(event_dec_min_deg, "user" if event_dec_min_deg is not None else "system_default", True),
        "event_dec_max_deg": parameter(event_dec_max_deg, "user" if event_dec_max_deg is not None else "system_default", True),
    }
    inputs = {"kind": "inline_sources", "sources": [source], "source_count": 1}
    task = create_task_record(original_request, "analyze_sources", "single_source", "Exactly one input source was provided.", inputs, parameters, planning_errors=planning_errors)
    task["questions"] = combined_questions(task, planning_errors)
    return refresh_readiness(task)


def plan_catalog_task(original_request: str, repo_root: Path, catalog: Optional[str], sources: Optional[List[Dict[str, Any]]], name_column: Optional[str], ra_column: Optional[str], dec_column: Optional[str], gamma: Optional[float], weight_mode: Optional[str], weight_column: Optional[str], weight_meaning: Optional[str], manual_weights: Optional[List[float]], include_uniform_baseline: bool = True, data_sample: str = "icecube_public_ps_14yr_dr2", gamma_mode: str = "fitted", likelihood_mode: str = "spatial_energy", built_in_catalog: Optional[str] = None, event_abs_dec_max_deg: Optional[float] = None, event_dec_min_deg: Optional[float] = None, event_dec_max_deg: Optional[float] = None, catalog_operation: Optional[str] = None, coordinates=None) -> Dict[str, Any]:
    planning_errors: List[str] = []
    operation = catalog_operation or ("stack" if data_sample == "icecube_public_ps_14yr_dr2" else "scan_and_stack")
    validate_catalog_operation(operation, data_sample, weight_mode, weight_column, manual_weights, planning_errors)
    if operation == "scan" and weight_mode is None:
        weight_mode = "uniform"
    inspection = None
    supplied_columns = {"name": name_column is not None, "ra": ra_column is not None, "dec": dec_column is not None}
    if built_in_catalog is not None:
        if coordinates:
            raise CoordinateError("Built-in catalogs already define ICRS RA/Dec in degrees; do not override their coordinate system.")
        rows = load_builtin_catalog(built_in_catalog, repo_root)
        columns = list(rows[0])
        name_column = name_column or "source_name"
        ra_column = ra_column or "ra_deg"
        dec_column = dec_column or "dec_deg"
        inspection = inspect_builtin_rows(rows, columns, built_in_catalog, name_column, ra_column, dec_column, weight_column)
        source_count = len(rows)
        add_inspection_errors(inspection, planning_errors)
        inputs = {"kind": "built_in_catalog", "built_in_catalog": built_in_catalog, "source_count": source_count, "inspection": inspection}
    elif catalog is not None:
        catalog_path = Path(catalog).expanduser()
        if not catalog_path.is_absolute():
            catalog_path = repo_root / catalog_path
        inspection = inspect_catalog(str(catalog_path), name_column, ra_column, dec_column, weight_column, coordinates)
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
    if source_count == 1:
        reason = "Exactly one input source was provided."
    elif data_sample == "icecube_public_ps_14yr_dr2":
        reason = "%d input sources select the SkyLLH DR2 catalog-stacking workflow." % source_count
    else:
        reason = "%d input sources require the legacy catalog-wide single-source scan plus stacking." % source_count
    parameters = {
        "gamma": parameter(gamma, "user" if gamma is not None else None, gamma is not None),
        "name_column": parameter(name_column, "user" if supplied_columns["name"] else "agent_inferred", name_column is not None),
        "ra_column": parameter(ra_column, "user" if supplied_columns["ra"] else "agent_inferred", ra_column is not None),
        "dec_column": parameter(dec_column, "user" if supplied_columns["dec"] else "agent_inferred", dec_column is not None),
        "coordinates": parameter((inspection or {}).get("coordinates") or coordinates or {}, "user" if coordinates else "agent_inferred", True),
        "weight_mode": parameter(weight_mode, "user" if weight_mode is not None else None, weight_mode is not None),
        "weight_column": parameter(weight_column, "user" if weight_column is not None else None, weight_column is not None),
        "weight_meaning": parameter(weight_meaning, "user" if weight_meaning is not None else None, weight_meaning is not None),
        "manual_weights": parameter(manual_weights, "user" if manual_weights is not None else None, manual_weights is not None),
        "catalog_operation": parameter(operation, "user" if catalog_operation is not None else "system_default", True),
        "include_uniform_baseline": parameter(bool(include_uniform_baseline), "system_default", True),
        "data_sample": parameter(data_sample, "user" if data_sample != "icecube_public_ps_14yr_dr2" else "system_default", True),
        "gamma_mode": parameter(gamma_mode, "system_default", True),
        "likelihood_mode": parameter(likelihood_mode, "system_default", True),
        "event_abs_dec_max_deg": parameter(event_abs_dec_max_deg, "user" if event_abs_dec_max_deg is not None else "system_default", True),
        "event_dec_min_deg": parameter(event_dec_min_deg, "user" if event_dec_min_deg is not None else "system_default", True),
        "event_dec_max_deg": parameter(event_dec_max_deg, "user" if event_dec_max_deg is not None else "system_default", True),
    }
    if workflow == "single_source":
        parameters["weight_mode"] = parameter("uniform", "system", True)
    elif data_sample == "icecube_public_ps_14yr_dr2":
        reason = "%d input sources select DR2 catalog operation '%s'." % (source_count, operation)
        if operation == "scan":
            parameters["weight_mode"] = parameter("uniform", "system", True)
    validate_planning_values(source_count, gamma, weight_mode, weight_column, manual_weights, planning_errors, data_sample, gamma_mode, likelihood_mode, event_abs_dec_max_deg, event_dec_min_deg, event_dec_max_deg)
    task = create_task_record(original_request, "analyze_sources", workflow, reason, inputs, parameters, planning_errors=planning_errors)
    task["questions"] = combined_questions(task, planning_errors)
    return refresh_readiness(task)


def validate_catalog_operation(operation, data_sample, weight_mode, weight_column, manual_weights, errors):
    if operation not in {"stack", "scan", "scan_and_stack"}:
        errors.append("catalog operation must be stack, scan, or scan_and_stack")
    if data_sample == "icecube_public_ps_10yr" and operation != "scan_and_stack":
        errors.append("the DR1 catalog workflow remains scan_and_stack")
    if operation == "scan" and (weight_mode not in {None, "uniform"} or weight_column is not None or manual_weights is not None):
        errors.append("scan-only fits each source independently and does not accept stacking weights")


def inspect_builtin_rows(rows, columns, name, name_column, ra_column, dec_column, weight_column):
    result = {"tool": "inspect_catalog", "catalog": f"builtin:{name}", "status": "pass", "errors": [], "warnings": [], "questions": [], "row_count": len(rows), "columns": columns, "inferred_columns": {"name": name_column, "ra_deg": ra_column, "dec_deg": dec_column, "weight": weight_column}}
    result["coordinate_review"] = inspect_coordinates(rows, name_column, ra_column, dec_column)
    if result["coordinate_review"]["invalid_rows"] or result["coordinate_review"]["missing_rows"] or result["coordinate_review"]["duplicate_coordinate_pairs"]:
        result["warnings"].append("catalog coordinates require review")
    result["weight_candidates"] = inspect_weight_candidates(rows, columns, {name_column, ra_column, dec_column})
    if weight_column is not None:
        if weight_column not in columns:
            result["errors"].append("specified weight column is missing: %s" % weight_column)
        else:
            result["selected_weight_review"] = inspect_numeric_column(rows, weight_column)
    elif result["weight_candidates"]:
        result["questions"].append("Use uniform weights or one of these catalog columns: %s?" % ", ".join(item["column"] for item in result["weight_candidates"]))
    else:
        result["questions"].append("Use uniform weights, or provide manual weights?")
    result["status"] = "fail" if result["errors"] else ("warning" if result["warnings"] or result["questions"] else "pass")
    return result


def validate_planning_values(source_count: int, gamma: Optional[float], weight_mode: Optional[str], weight_column: Optional[str], manual_weights: Optional[List[float]], errors: List[str], data_sample: str = "icecube_public_ps_10yr", gamma_mode: str = "fixed", likelihood_mode: str = "spatial_only", event_abs_dec_max_deg: Optional[float] = None, event_dec_min_deg: Optional[float] = None, event_dec_max_deg: Optional[float] = None) -> None:
    if likelihood_mode not in {"spatial_energy", "spatial_only"}:
        errors.append("likelihood mode must be spatial_energy or spatial_only")
    if data_sample == "icecube_public_ps_10yr" and likelihood_mode != "spatial_only":
        errors.append("the 10-year backend currently supports likelihood_mode='spatial_only' only")
    if likelihood_mode == "spatial_only" and gamma_mode != "fixed":
        errors.append("spatial-only analysis requires gamma_mode='fixed'; gamma is the fixed acceptance gamma")
    if event_abs_dec_max_deg is not None and (not math.isfinite(float(event_abs_dec_max_deg)) or not 0.0 < float(event_abs_dec_max_deg) <= 90.0):
        errors.append("event absolute-declination maximum must be finite and in (0, 90] degrees")
    if event_abs_dec_max_deg is not None and data_sample != "icecube_public_ps_14yr_dr2":
        errors.append("event declination cuts are currently supported only for the 14-year DR2 backend")
    range_values = [value for value in (event_dec_min_deg, event_dec_max_deg) if value is not None]
    if any(not math.isfinite(float(value)) or not -90.0 <= float(value) <= 90.0 for value in range_values):
        errors.append("event declination bounds must be finite and in [-90, 90] deg")
    if event_dec_min_deg is not None and event_dec_max_deg is not None and float(event_dec_min_deg) >= float(event_dec_max_deg):
        errors.append("event_dec_min_deg must be less than event_dec_max_deg")
    if event_abs_dec_max_deg is not None and range_values:
        errors.append("use either event_abs_dec_max_deg or asymmetric event declination bounds, not both")
    if range_values and data_sample != "icecube_public_ps_14yr_dr2":
        errors.append("event declination cuts are currently supported only for the 14-year DR2 backend")
    if gamma is not None and not math.isfinite(float(gamma)):
        errors.append("gamma exponent must be finite")
    elif gamma is not None and data_sample == "icecube_public_ps_14yr_dr2" and gamma_mode == "fitted" and not -4.0 <= float(gamma) <= -1.0:
        errors.append("the default DR2 fitted-gamma seed must be in [-4, -1]")

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
            source.update(canonical_source(source))
        except CoordinateError as exc:
            errors.append("source %d coordinates: %s" % (index, exc))
            continue
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
            questions.append("Provide a finite signed power-law exponent and appropriate fit bounds.")
        elif "manual weights" in error:
            questions.append("Provide one finite non-negative manual weight per source, with a positive total.")
        elif "coordinate" in error or " RA " in error or " Dec " in error:
            questions.append(error)
        elif "column" in error:
            questions.append("Correct or identify the required catalog column before execution.")
        else:
            questions.append(error)
    return list(dict.fromkeys(questions))


def source_from_single_row_catalog(task: Dict[str, Any], repo_root: Path) -> Dict[str, Any]:
    inputs = task["inputs"]
    path = Path(inputs["catalog"])
    if not path.is_absolute():
        path = repo_root / path
    rows, _ = read_source_catalog(path)
    if len(rows) != 1:
        raise ValueError("single-source catalog must contain exactly one row")
    row = rows[0]
    parameters = task["parameters"]
    name_column = parameters["name_column"]["value"]
    ra_column = parameters["ra_column"]["value"]
    dec_column = parameters["dec_column"]["value"]
    name = row.get(name_column, "source_0001") if name_column else "source_0001"
    settings = parameters.get("coordinates", {}).get("value")
    if settings:
        return catalog_source(row, name, settings)
    return {"name": name, "ra_deg": float(row[ra_column]), "dec_deg": float(row[dec_column])}


def revalidate_task_plan(task: Dict[str, Any], repo_root: Path) -> Dict[str, Any]:
    errors: List[str] = []
    inputs = task.get("inputs", {})
    parameters = task.get("parameters", {})
    source_count = int(inputs.get("source_count", 0))
    if inputs.get("kind") == "built_in_catalog":
        rows = load_builtin_catalog(str(inputs.get("built_in_catalog")), repo_root)
        columns = list(rows[0])
        inspection = inspect_builtin_rows(
            rows,
            columns,
            str(inputs.get("built_in_catalog")),
            parameters.get("name_column", {}).get("value") or "source_name",
            parameters.get("ra_column", {}).get("value") or "ra_deg",
            parameters.get("dec_column", {}).get("value") or "dec_deg",
            parameters.get("weight_column", {}).get("value") if parameters.get("weight_mode", {}).get("value") == "column" else None,
        )
        inputs["inspection"] = inspection
        source_count = len(rows)
        inputs["source_count"] = source_count
        add_inspection_errors(inspection, errors)
    elif inputs.get("kind") == "catalog":
        catalog_path = Path(str(inputs.get("catalog", ""))).expanduser()
        if not catalog_path.is_absolute():
            catalog_path = repo_root / catalog_path
        inspection = inspect_catalog(
            str(catalog_path),
            parameters.get("name_column", {}).get("value"),
            parameters.get("ra_column", {}).get("value"),
            parameters.get("dec_column", {}).get("value"),
            parameters.get("weight_column", {}).get("value") if parameters.get("weight_mode", {}).get("value") == "column" else None,
            parameters.get("coordinates", {}).get("value"),
        )
        if inspection.get("coordinates"):
            parameters.setdefault("coordinates", parameter({}, "agent_inferred", True))["value"] = inspection["coordinates"]
            inferred = inspection["inferred_columns"]
            for key in ("name", "ra", "dec"):
                column = inferred.get(key if key == "name" else key + "_deg")
                if column and parameters.get(key + "_column", {}).get("value") != column:
                    parameters[key + "_column"] = parameter(column, "agent_inferred", True)
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
        settings = parameters.get("coordinates", {}).get("value") or {}
        for source in inputs.get("sources", []):
            if "coordinates" in source:
                source["coordinates"].update(settings)
        validate_source_values(list(inputs.get("sources", [])), errors)
    data_sample = str(parameters.get("data_sample", {}).get("value") or "icecube_public_ps_10yr")
    operation = parameters.get("catalog_operation", {}).get("value") or ("stack" if data_sample == "icecube_public_ps_14yr_dr2" else "scan_and_stack")
    validate_catalog_operation(operation, data_sample, weight_mode, weight_column, manual_weights, errors)
    gamma_mode = str(parameters.get("gamma_mode", {}).get("value") or "fixed")
    likelihood_mode = str(parameters.get("likelihood_mode", {}).get("value") or ("spatial_energy" if data_sample == "icecube_public_ps_14yr_dr2" else "spatial_only"))
    event_abs_dec_max_deg = parameters.get("event_abs_dec_max_deg", {}).get("value")
    event_dec_min_deg = parameters.get("event_dec_min_deg", {}).get("value")
    event_dec_max_deg = parameters.get("event_dec_max_deg", {}).get("value")
    validate_planning_values(source_count, gamma, weight_mode, weight_column, manual_weights, errors, data_sample, gamma_mode, likelihood_mode, event_abs_dec_max_deg, event_dec_min_deg, event_dec_max_deg)
    from agent_core.spectrum import validate_spectrum, response_notice
    spectrum = parameters.get("spectrum", {}).get("value") or {}
    bounds = parameters.get("gamma_bounds", {}).get("value")
    if bounds is not None:
        errors = [e for e in errors if e != "the default DR2 fitted-gamma seed must be in [-4, -1]"]
    errors.extend(validate_spectrum(spectrum, gamma, gamma_mode, bounds, repo_root))
    task["spectrum_preparation"] = response_notice(gamma, spectrum, bounds, likelihood_mode)
    task["planning_errors"] = errors
    task["questions"] = combined_questions(task, errors)
    return refresh_readiness(task)
