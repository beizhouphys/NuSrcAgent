from __future__ import annotations # cdx

import csv # cdx
import json # cdx
import math # cdx
from pathlib import Path # cdx
from typing import Any, Dict, List # cdx

from agent_core_cdx.simple_yaml_cdx import load_simple_yaml # cdx


def review_run(run_directory: str, repo_root: str = ".", write_artifacts: bool = True) -> Dict[str, Any]: # cdx
    run_dir = Path(run_directory).expanduser().resolve() # cdx
    root = Path(repo_root).expanduser().resolve() # cdx
    review: Dict[str, Any] = {"tool": "review_run", "run_directory": str(run_dir), "status": "pass", "checks": [], "metrics": {}, "recommended_actions": []} # cdx
    if not run_dir.exists(): # cdx
        add_check(review, "run_directory", "fail", "run directory does not exist", False) # cdx
        return finalize_review(review, run_dir, write_artifacts) # cdx
    report = load_yaml_if_present(run_dir / "report_cdx.yaml") # cdx
    normalized = load_yaml_if_present(run_dir / "config.normalized_cdx.yaml") # cdx
    add_check(review, "report", "pass" if report else "fail", "report_cdx.yaml is readable" if report else "report_cdx.yaml is missing or unreadable", False) # cdx
    add_check(review, "normalized_config", "pass" if normalized else "fail", "normalized config is readable" if normalized else "config.normalized_cdx.yaml is missing or unreadable", False) # cdx
    add_check(review, "provenance", "pass" if (run_dir / "provenance_cdx.yaml").exists() else "fail", "provenance file is present" if (run_dir / "provenance_cdx.yaml").exists() else "provenance file is missing", False) # cdx
    if not report or not normalized: # cdx
        return finalize_review(review, run_dir, write_artifacts) # cdx
    analysis_type = str(report.get("analysis", {}).get("type", "")) # cdx
    review["metrics"]["analysis_type"] = analysis_type # cdx
    review["metrics"]["n_sources"] = int(report.get("analysis", {}).get("n_sources", 0)) # cdx
    if analysis_type == "catalog_stacking": # cdx
        review_catalog_run(review, run_dir, root, report, normalized) # cdx
    elif analysis_type == "single_source": # cdx
        review_single_run(review, report) # cdx
    else: # cdx
        add_check(review, "analysis_type", "fail", "unknown analysis type: %s" % analysis_type, False) # cdx
    warnings = report.get("warnings", []) # cdx
    if warnings: # cdx
        add_check(review, "backend_warnings", "warning", "%d backend/report warnings require acknowledgement" % len(warnings), False) # cdx
        review["metrics"]["backend_warnings"] = warnings # cdx
    return finalize_review(review, run_dir, write_artifacts) # cdx


def review_single_run(review: Dict[str, Any], report: Dict[str, Any]) -> None: # cdx
    result = report.get("result", {}) # cdx
    required = ["best_fit_ns", "ts", "pre_trial_p"] # cdx
    missing = [key for key in required if key not in result] # cdx
    add_check(review, "single_result_fields", "fail" if missing else "pass", "missing fields: %s" % ", ".join(missing) if missing else "single-source result fields are present", False) # cdx
    if missing: # cdx
        return # cdx
    ns_hat = finite_float(result["best_fit_ns"]) # cdx
    ts = finite_float(result["ts"]) # cdx
    p_value = finite_float(result["pre_trial_p"]) # cdx
    valid = ns_hat is not None and ts is not None and ts >= 0.0 and p_value is not None and 0.0 <= p_value <= 1.0 # cdx
    add_check(review, "single_numeric_ranges", "pass" if valid else "fail", "single-source values are finite and in valid ranges" if valid else "single-source result contains invalid numeric values", False) # cdx
    review["metrics"].update({"ns_hat": ns_hat, "ts": ts, "pre_trial_p": p_value}) # cdx
    if ns_hat is not None and abs(ns_hat + 10.0) < 0.01: # cdx
        add_check(review, "single_fit_boundary", "warning", "ns_hat is at the lower optimizer boundary", False) # cdx


def review_catalog_run(review: Dict[str, Any], run_dir: Path, root: Path, report: Dict[str, Any], normalized: Dict[str, Any]) -> None: # cdx
    source_path = run_dir / "source_results_cdx.csv" # cdx
    stacking_path = run_dir / "stacking_results_cdx.csv" # cdx
    source_rows = read_csv_if_present(source_path) # cdx
    stacking_rows = read_csv_if_present(stacking_path) # cdx
    expected_sources = int(report.get("analysis", {}).get("n_sources", 0)) # cdx
    add_check(review, "source_table", "pass" if len(source_rows) == expected_sources and expected_sources > 0 else "fail", "source table has %d rows in input order" % len(source_rows) if len(source_rows) == expected_sources else "source table row count does not match the normalized catalog", False) # cdx
    add_check(review, "stacking_table", "pass" if stacking_rows else "fail", "stacking table has %d hypotheses" % len(stacking_rows) if stacking_rows else "stacking table is missing or empty", False) # cdx
    if source_rows: # cdx
        review_source_rows(review, source_rows, expected_sources) # cdx
    if stacking_rows: # cdx
        review_stacking_rows(review, stacking_rows) # cdx
    weights = [finite_float(source.get("weight")) for source in normalized.get("sources", [])] # cdx
    valid_weights = [value for value in weights if value is not None] # cdx
    weight_sum = sum(valid_weights) # cdx
    add_check(review, "weight_normalization", "pass" if len(valid_weights) == expected_sources and abs(weight_sum - 1.0) < 1e-9 else "fail", "normalized source weights sum to one" if abs(weight_sum - 1.0) < 1e-9 else "normalized source weights do not sum to one", False) # cdx
    if valid_weights: # cdx
        max_fraction = max(valid_weights) # cdx
        effective_count = 1.0 / sum(value * value for value in valid_weights) if sum(value * value for value in valid_weights) > 0.0 else 0.0 # cdx
        review["metrics"].update({"weight_sum": weight_sum, "maximum_source_weight": max_fraction, "effective_source_count": effective_count}) # cdx
        if max_fraction > 0.5 or effective_count < min(5.0, expected_sources / 5.0): # cdx
            add_check(review, "weight_concentration", "warning", "stacking weights are strongly concentrated; confirm this is scientifically intended", False) # cdx
    workbook = run_dir / "analysis_results_cdx.xlsx" # cdx
    add_check(review, "excel_workbook", "pass" if workbook.exists() and workbook.stat().st_size > 0 else "fail", "Excel workbook is present" if workbook.exists() else "Excel workbook is missing; rerun output generation without changing scientific inputs", True) # cdx
    qa_file = run_dir / "workbook_qa_cdx" / "key_ranges.ndjson" # cdx
    qa_errors = workbook_error_count(run_dir / "analysis_results_cdx.xlsx.inspect.ndjson") + workbook_error_count(qa_file) # cdx
    qa_status = "pass" if qa_file.exists() and qa_errors == 0 else ("fail" if qa_errors else "warning") # cdx
    add_check(review, "workbook_qa", qa_status, "workbook QA exists with no formula errors" if qa_status == "pass" else ("workbook QA contains formula errors" if qa_errors else "workbook QA artifact is missing"), True) # cdx
    figure_values = report.get("result", {}).get("figures", []) # cdx
    missing_figures = [] # cdx
    for value in figure_values: # cdx
        figure_path = Path(value) # cdx
        if not figure_path.is_absolute(): # cdx
            figure_path = root / figure_path # cdx
        if not valid_pdf(figure_path): # cdx
            missing_figures.append(str(figure_path)) # cdx
    add_check(review, "figures", "pass" if len(figure_values) >= 3 and not missing_figures else "fail", "all expected PDF figures are readable" if not missing_figures and len(figure_values) >= 3 else "one or more expected PDF figures are missing or invalid", True) # cdx


def review_source_rows(review: Dict[str, Any], rows: List[Dict[str, str]], expected_sources: int) -> None: # cdx
    numbers = [integer_value(row.get("source_number")) for row in rows] # cdx
    add_check(review, "source_order", "pass" if numbers == list(range(1, expected_sources + 1)) else "fail", "source_number preserves one-based input order" if numbers == list(range(1, expected_sources + 1)) else "source_number does not preserve one-based input order", False) # cdx
    ranks = [integer_value(row.get("significance_rank")) for row in rows] # cdx
    ranks_are_valid = all(rank is not None for rank in ranks) and sorted(ranks) == list(range(1, expected_sources + 1)) # cdx
    add_check(review, "significance_ranks", "pass" if ranks_are_valid else "fail", "significance ranks form a complete permutation" if ranks_are_valid else "significance ranks are incomplete or duplicated", False) # cdx
    invalid = 0 # cdx
    invalid_coordinates = 0 # cdx
    unnamed = 0 # cdx
    boundary = 0 # cdx
    post_trial_mismatch = 0 # cdx
    local_p_mismatch = 0 # cdx
    for row in rows: # cdx
        ra_deg = finite_float(row.get("ra_deg")) # cdx
        dec_deg = finite_float(row.get("dec_deg")) # cdx
        if ra_deg is None or dec_deg is None or not 0.0 <= ra_deg < 360.0 or not -90.0 <= dec_deg <= 90.0: # cdx
            invalid_coordinates += 1 # cdx
        if not str(row.get("source_name", "")).strip(): # cdx
            unnamed += 1 # cdx
        ns_hat = finite_float(row.get("ns_hat")) # cdx
        ts = finite_float(row.get("ts")) # cdx
        pre_trial = finite_float(row.get("pre_trial_p")) # cdx
        post_trial = finite_float(row.get("post_trial_p")) # cdx
        if ns_hat is None or ts is None or ts < 0.0 or pre_trial is None or not 0.0 <= pre_trial <= 1.0 or post_trial is None or not 0.0 <= post_trial <= 1.0: # cdx
            invalid += 1 # cdx
            continue # cdx
        expected_post = 1.0 - (1.0 - pre_trial) ** expected_sources # cdx
        expected_pre = 0.5 * math.erfc(math.sqrt(ts / 2.0)) # cdx
        if abs(pre_trial - expected_pre) > 1e-8: # cdx
            local_p_mismatch += 1 # cdx
        if abs(post_trial - expected_post) > 1e-8: # cdx
            post_trial_mismatch += 1 # cdx
        if abs(ns_hat + 10.0) < 0.01: # cdx
            boundary += 1 # cdx
    add_check(review, "source_numeric_ranges", "pass" if invalid == 0 else "fail", "all source results are finite and in valid ranges" if invalid == 0 else "%d source rows contain invalid numeric results" % invalid, False) # cdx
    add_check(review, "source_coordinates", "pass" if invalid_coordinates == 0 and unnamed == 0 else "fail", "source names and coordinates are valid" if invalid_coordinates == 0 and unnamed == 0 else "%d invalid coordinates and %d empty names were found" % (invalid_coordinates, unnamed), False) # cdx
    add_check(review, "source_local_p", "pass" if local_p_mismatch == 0 else "fail", "pre-trial p-values match the declared analytic TS approximation" if local_p_mismatch == 0 else "%d pre-trial p-values do not match the declared TS approximation" % local_p_mismatch, False) # cdx
    add_check(review, "source_trial_correction", "pass" if post_trial_mismatch == 0 else "fail", "post-trial p-values match the catalog-size correction" if post_trial_mismatch == 0 else "%d post-trial p-values do not match the catalog-size correction" % post_trial_mismatch, False) # cdx
    if boundary: # cdx
        add_check(review, "source_fit_boundaries", "warning", "%d source fits reached the lower ns optimizer boundary" % boundary, False) # cdx
    review["metrics"]["source_lower_boundary_count"] = boundary # cdx


def review_stacking_rows(review: Dict[str, Any], rows: List[Dict[str, str]]) -> None: # cdx
    invalid = 0 # cdx
    local_p_mismatch = 0 # cdx
    missing_post_trial = 0 # cdx
    for row in rows: # cdx
        ns_hat = finite_float(row.get("ns_hat")) # cdx
        ts = finite_float(row.get("ts")) # cdx
        p_value = finite_float(row.get("pre_trial_p")) # cdx
        if ns_hat is None or ts is None or ts < 0.0 or p_value is None or not 0.0 <= p_value <= 1.0: # cdx
            invalid += 1 # cdx
        elif abs(p_value - 0.5 * math.erfc(math.sqrt(ts / 2.0))) > 1e-8: # cdx
            local_p_mismatch += 1 # cdx
        if str(row.get("post_trial_p", "")).strip() == "": # cdx
            missing_post_trial += 1 # cdx
    add_check(review, "stacking_numeric_ranges", "pass" if invalid == 0 else "fail", "all stacking results are finite and in valid ranges" if invalid == 0 else "%d stacking rows contain invalid numeric results" % invalid, False) # cdx
    add_check(review, "stacking_local_p", "pass" if local_p_mismatch == 0 else "fail", "stacking pre-trial p-values match the declared analytic TS approximation" if local_p_mismatch == 0 else "%d stacking pre-trial p-values do not match the declared TS approximation" % local_p_mismatch, False) # cdx
    if missing_post_trial: # cdx
        add_check(review, "stacking_post_trial", "warning", "stacking post-trial p-values are unavailable until full background trials are implemented", False) # cdx


def add_check(review: Dict[str, Any], check_id: str, status: str, message: str, auto_fix_allowed: bool) -> None: # cdx
    review["checks"].append({"id": check_id, "status": status, "message": message, "auto_fix_allowed": auto_fix_allowed}) # cdx


def finalize_review(review: Dict[str, Any], run_dir: Path, write_artifacts: bool) -> Dict[str, Any]: # cdx
    statuses = [check["status"] for check in review["checks"]] # cdx
    review["status"] = "fail" if "fail" in statuses else ("warning" if "warning" in statuses else "pass") # cdx
    for check in review["checks"]: # cdx
        if check["status"] == "fail": # cdx
            review["recommended_actions"].append({"check": check["id"], "action": check["message"], "auto_fix_allowed": check["auto_fix_allowed"]}) # cdx
    if write_artifacts and run_dir.exists(): # cdx
        with (run_dir / "review_cdx.json").open("w", encoding="utf-8") as handle: # cdx
            json.dump(review, handle, indent=2, sort_keys=True) # cdx
            handle.write("\n") # cdx
        with (run_dir / "review_cdx.md").open("w", encoding="utf-8") as handle: # cdx
            handle.write(render_review_markdown(review)) # cdx
    return review # cdx


def render_review_markdown(review: Dict[str, Any]) -> str: # cdx
    lines = ["# Analysis Review", "", "Overall status: `%s`" % review["status"], "", "## Checks", ""] # cdx
    lines.extend("- `%s` %s: %s" % (check["status"], check["id"], check["message"]) for check in review["checks"]) # cdx
    lines.extend(["", "## Metrics", ""]) # cdx
    lines.extend("- %s: `%s`" % (key, value) for key, value in review["metrics"].items()) # cdx
    return "\n".join(lines) + "\n" # cdx


def load_yaml_if_present(path: Path) -> Dict[str, Any]: # cdx
    if not path.exists(): # cdx
        return {} # cdx
    try: # cdx
        payload = load_simple_yaml(path.read_text(encoding="utf-8")) # cdx
        return payload if isinstance(payload, dict) else {} # cdx
    except Exception: # cdx
        return {} # cdx


def read_csv_if_present(path: Path) -> List[Dict[str, str]]: # cdx
    if not path.exists(): # cdx
        return [] # cdx
    with path.open("r", encoding="utf-8", newline="") as handle: # cdx
        return [dict(row) for row in csv.DictReader(handle)] # cdx


def valid_pdf(path: Path) -> bool: # cdx
    return path.exists() and path.stat().st_size > 100 and path.read_bytes()[:5] == b"%PDF-" # cdx


def workbook_error_count(path: Path) -> int: # cdx
    if not path.exists(): # cdx
        return 0 # cdx
    text = path.read_text(encoding="utf-8", errors="replace") # cdx
    return sum(text.count(marker) for marker in ["#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#N/A"]) # cdx


def finite_float(value: Any): # cdx
    try: # cdx
        number = float(value) # cdx
        return number if math.isfinite(number) else None # cdx
    except (TypeError, ValueError): # cdx
        return None # cdx


def integer_value(value: Any): # cdx
    try: # cdx
        return int(value) # cdx
    except (TypeError, ValueError): # cdx
        return None # cdx
