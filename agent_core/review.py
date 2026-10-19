from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List

from agent_core.p_value import local_p_value_estimate
from agent_core.simple_yaml import load_simple_yaml


def review_run(run_directory: str, repo_root: str = ".", write_artifacts: bool = True) -> Dict[str, Any]:
    run_dir = Path(run_directory).expanduser().resolve()
    root = Path(repo_root).expanduser().resolve()
    review: Dict[str, Any] = {"tool": "review_run", "run_directory": str(run_dir), "status": "pass", "checks": [], "metrics": {}, "recommended_actions": []}
    if not run_dir.exists():
        add_check(review, "run_directory", "fail", "run directory does not exist", False)
        return finalize_review(review, run_dir, write_artifacts)
    report = load_yaml_if_present(run_dir / "report.yaml")
    normalized = load_yaml_if_present(run_dir / "config.normalized.yaml")
    add_check(review, "report", "pass" if report else "fail", "report.yaml is readable" if report else "report.yaml is missing or unreadable", False)
    add_check(review, "normalized_config", "pass" if normalized else "fail", "normalized config is readable" if normalized else "config.normalized.yaml is missing or unreadable", False)
    provenance = load_yaml_if_present(run_dir / "provenance.yaml")
    add_check(review, "provenance", "pass" if provenance else "fail", "provenance is readable" if provenance else "provenance is missing or unreadable", False)
    for field, paths in (("config_sha256", list(run_dir.glob("config.original.*"))), ("normalized_sha256", [run_dir / "config.normalized.yaml"])):
        if field in provenance:
            matches = len(paths) == 1 and paths[0].is_file() and hashlib.sha256(paths[0].read_bytes()).hexdigest() == provenance[field]
            add_check(review, field, "pass" if matches else "fail", "configuration hash matches provenance" if matches else "configuration hash differs from recorded provenance", False)
    markdown = run_dir / "report.md"
    add_check(review, "readable_report", "pass" if markdown.is_file() and markdown.stat().st_size > 0 else "fail", "human-readable report is present" if markdown.is_file() else "human-readable report is missing", True)
    if not report or not normalized:
        return finalize_review(review, run_dir, write_artifacts)
    analysis_type = str(report.get("analysis", {}).get("type", ""))
    review["metrics"]["analysis_type"] = analysis_type
    review["metrics"]["n_sources"] = int(report.get("analysis", {}).get("n_sources", 0))
    data_sample = str(report.get("analysis", {}).get("sample", ""))
    if data_sample == "icecube_public_ps_14yr_dr2":
        operation = normalized.get("catalog_operation", "stack") if analysis_type == "catalog_stacking" else "stack"
        if analysis_type == "catalog_stacking":
            consistent = report.get("result", {}).get("catalog_operation", "stack") == operation
            add_check(review, "dr2_catalog_operation", "pass" if consistent else "fail", "catalog operation matches the request" if consistent else "catalog operation does not match the request", False)
        if operation != "scan":
            review_dr2_run(review, report, normalized, root)
        if operation in {"scan", "scan_and_stack"}:
            review_dr2_source_scan(review, run_dir, report, normalized, root)
    elif analysis_type == "catalog_stacking":
        review_catalog_run(review, run_dir, root, report, normalized)
    elif analysis_type == "single_source":
        review_single_run(review, report)
    else:
        add_check(review, "analysis_type", "fail", "unknown analysis type: %s" % analysis_type, False)
    warnings = report.get("warnings", [])
    calibration = report.get("result", {}).get("significance_calibration")
    if calibration is not None:
        known = calibration in {"analytic_approximation", "empirical_calibration", "unavailable"}
        add_check(review, "significance_calibration", "pass" if known else "fail", "local significance uses an analytic approximation; empirical calibration is unavailable" if calibration == "analytic_approximation" else "significance calibration: %s" % calibration, False)
        if calibration == "analytic_approximation":
            count = report.get("diagnostics", {}).get("n_background_trials")
            add_check(review, "background_trials_executed", "pass" if count == 0 else "fail", "ordinary analytic workflow executed zero background trials" if count == 0 else "analytic workflow incorrectly claims executed background trials", False)
    if warnings:
        add_check(review, "backend_warnings", "warning", "%d backend/report warnings require acknowledgement" % len(warnings), False)
        review["metrics"]["backend_warnings"] = warnings
    return finalize_review(review, run_dir, write_artifacts)


def review_dr2_run(review: Dict[str, Any], report: Dict[str, Any], normalized: Dict[str, Any], root: Path) -> None:
    result = report.get("result", {})
    likelihood_mode = str(report.get("analysis", {}).get("likelihood_mode") or result.get("likelihood_mode") or "spatial_energy")
    mode_consistent = likelihood_mode in {"spatial_energy", "spatial_only"} and result.get("likelihood_mode") == likelihood_mode
    add_check(review, "dr2_likelihood_mode", "pass" if mode_consistent else "fail", "likelihood mode is explicit and consistent" if mode_consistent else "likelihood mode is missing or inconsistent", False)
    required = ["TS", "ns", "gamma", "gamma_mode", "event_selection", "n_sources"]
    missing = [key for key in required if key not in result]
    add_check(review, "dr2_result_fields", "fail" if missing else "pass", "missing fields: %s" % ", ".join(missing) if missing else "DR2 SkyLLH result fields are present", False)
    if missing:
        return
    ts = finite_float(result.get("TS"))
    ns_hat = finite_float(result.get("ns"))
    gamma = finite_float(result.get("gamma"))
    valid = ts is not None and ts >= 0.0 and ns_hat is not None and ns_hat >= 0.0 and gamma is not None and 0.9 <= gamma <= 6.1
    bounds = result.get("fit_bounds", {})
    ns_bounds = bounds.get("ns")
    gamma_bounds = bounds.get("gamma_skyllh")
    if isinstance(ns_bounds, list) and len(ns_bounds) == 2:
        valid = valid and ns_hat is not None and float(ns_bounds[0]) <= ns_hat <= float(ns_bounds[1])
    if result.get("gamma_mode") == "fitted" and isinstance(gamma_bounds, list) and len(gamma_bounds) == 2:
        valid = valid and gamma is not None and float(gamma_bounds[0]) <= gamma <= float(gamma_bounds[1])
    add_check(review, "dr2_numeric_ranges", "pass" if valid else "fail", "DR2 fit values are finite and in valid ranges" if valid else "DR2 fit contains invalid values", False)
    mode_matches = result.get("gamma_mode") == normalized.get("gamma_mode")
    if result.get("gamma_mode") == "fixed":
        requested_gamma = finite_float(normalized.get("spectral_indices", [None])[0])
        mode_matches = mode_matches and gamma is not None and requested_gamma is not None and abs(gamma + requested_gamma) < 1e-12
    add_check(review, "dr2_gamma_request", "pass" if mode_matches else "fail", "Gamma mode and fixed value match the request" if mode_matches else "Gamma mode or fixed value differs from the request", False)
    if result.get("gamma_mode") == "fitted" and gamma is not None and isinstance(gamma_bounds, list) and len(gamma_bounds) == 2:
        if any(abs(gamma - float(bound)) < 1e-5 for bound in gamma_bounds):
            add_check(review, "dr2_gamma_boundary", "warning", "Gamma at fit boundary; not a precise spectral measurement", False)
    if ns_hat is not None and isinstance(ns_bounds, list) and len(ns_bounds) == 2 and abs(ns_hat - float(ns_bounds[1])) < 1e-5:
        add_check(review, "dr2_ns_upper_boundary", "warning", "ns at upper boundary", False)
    requested_abs_cut = finite_float(normalized.get("event_abs_dec_max_deg"))
    requested_dec_min = finite_float(normalized.get("event_dec_min_deg"))
    requested_dec_max = finite_float(normalized.get("event_dec_max_deg"))
    event_counts = result.get("event_counts", {})
    event_count_values = [integer_value(value) for value in event_counts.values()] if isinstance(event_counts, dict) else []
    event_counts_ok = len(event_count_values) == 4 and all(value is not None and value > 0 for value in event_count_values) and sum(value for value in event_count_values if value is not None) == integer_value(result.get("n_events_total"))
    normalizations = [finite_float(value) for value in result.get("background_spatial_conditional_normalization", {}).values()]
    conditional_normalization_ok = len(normalizations) == 4 and all(value is not None and 0.0 < value <= 1.01 for value in normalizations)
    requested_window = finite_float(normalized.get("source_dec_window_deg")) if len(normalized.get("sources", [])) == 1 else None
    if requested_window is not None:
        window = result.get("source_dec_window") or {}
        before = result.get("event_counts_before_selection", {})
        minimum = finite_float(window.get("minimum_half_width_deg"))
        radius = finite_float(window.get("half_width_deg"))
        lower, upper = finite_float(result.get("event_dec_min_deg")), finite_float(result.get("event_dec_max_deg"))
        center = finite_float(normalized["sources"][0].get("dec_deg"))
        fractions = window.get("retained_fractions", {})
        retained_ok = isinstance(before, dict) and set(before) == set(event_counts) and all(
            integer_value(before[name]) is not None and before[name] >= count >= 0.2 * before[name]
            and finite_float(fractions.get(name)) is not None
            and abs(fractions[name] - count / before[name]) < 1e-12 for name, count in event_counts.items())
        bounds_ok = center is not None and radius is not None and minimum == requested_window and radius >= minimum >= 20.0 and lower is not None and upper is not None and abs(lower - max(-90., center-radius)) < 1e-9 and abs(upper - min(90., center+radius)) < 1e-9
        selection_ok = result.get("event_selection") == "adaptive_source_dec_window" and bounds_ok and retained_ok and window.get("minimum_event_fraction_per_dataset") == 0.2 and event_counts_ok and conditional_normalization_ok
        selection_message = "source-centered Dec window satisfies its minimum half-width and retains at least 20% of every dataset; background spatial PDF is conditioned to it"
    elif requested_abs_cut is not None:
        selection_ok = result.get("event_selection") == "abs_dec_cut" and finite_float(result.get("event_abs_dec_max_deg")) == requested_abs_cut and event_counts_ok and conditional_normalization_ok
        selection_message = "symmetric event declination cut matches the request and the background spatial PDF is conditioned to it"
    elif requested_dec_min is not None or requested_dec_max is not None:
        selection_ok = result.get("event_selection") == "dec_range_cut" and finite_float(result.get("event_dec_min_deg")) == requested_dec_min and finite_float(result.get("event_dec_max_deg")) == requested_dec_max and event_counts_ok and conditional_normalization_ok
        selection_message = "asymmetric event declination cut matches the request and the background spatial PDF is conditioned to it"
    else:
        selection_ok = result.get("event_selection") == "all_events" and event_counts_ok
        selection_message = "all DR2 events are included"
    add_check(review, "dr2_event_selection", "pass" if selection_ok else "fail", selection_message if selection_ok else "DR2 event selection or conditional background normalization does not match the normalized request", False)
    expected_sources = len(normalized.get("sources", []))
    add_check(review, "dr2_source_count", "pass" if int(result.get("n_sources", 0)) == expected_sources else "fail", "source count matches normalized input" if int(result.get("n_sources", 0)) == expected_sources else "source count does not match normalized input", False)
    source_event_pairs = int(result.get("source_event_pairs", 0))
    working_set = result.get("working_set", {})
    dataset_chunks = working_set.get("datasets", {}) if isinstance(working_set, dict) else {}
    chunk_records = list(dataset_chunks.values()) if isinstance(dataset_chunks, dict) else []
    chunked = (source_event_pairs > 0 and working_set.get("cartesian_source_event_arrays_materialized") is False and len(chunk_records) == 4 and all(int(item.get("n_events", 0)) > 0 and int(item.get("event_chunk", 0)) > 0 and int(item.get("source_chunk", 0)) > 0 and 0 < int(item.get("maximum_working_pairs", 0)) <= int(item.get("target_pairs", 0)) for item in chunk_records))
    add_check(review, "dr2_chunked_working_set", "pass" if chunked else "fail", "all source-event pairs are evaluated in bounded exact chunks" if chunked else "DR2 chunk provenance is missing or exceeds its pair budget", False)
    model_weights = [finite_float(value) for value in result.get("w_model", [])]
    valid_model_weights = len(model_weights) == expected_sources and all(value is not None and value >= 0.0 for value in model_weights) and abs(sum(value for value in model_weights if value is not None) - 1.0) < 1e-9
    add_check(review, "dr2_model_weights", "pass" if valid_model_weights else "fail", "w_{j,model} is non-negative and normalized" if valid_model_weights else "w_{j,model} is invalid or not normalized", False)
    dataset_fractions = [finite_float(value) for value in result.get("f_k", {}).values()]
    valid_fractions = len(dataset_fractions) == 4 and all(value is not None and value >= 0.0 for value in dataset_fractions) and abs(sum(value for value in dataset_fractions if value is not None) - 1.0) < 1e-9
    add_check(review, "dr2_dataset_fractions", "pass" if valid_fractions else "fail", "f_k is non-negative and normalized across four datasets" if valid_fractions else "f_k is invalid or not normalized", False)
    minimizer_ok = result.get("minimizer_status", {}).get("warnflag") == 0
    add_check(review, "dr2_minimizer", "pass" if minimizer_ok else "fail", "SkyLLH minimizer converged without warnings" if minimizer_ok else "optimizer did not converge", False)
    provenance = result.get("pdf_provenance", {})
    provenance_paths = [root / str(value) for value in provenance.values()] if isinstance(provenance, dict) else []
    expected_provenance_count = 1 if likelihood_mode == "spatial_only" else 2
    provenance_ok = len(provenance_paths) == expected_provenance_count and all(path.exists() for path in provenance_paths)
    provenance_message = "background spatial-PDF provenance is present" if likelihood_mode == "spatial_only" else "background and signal-energy table provenance files are present"
    add_check(review, "dr2_pdf_provenance", "pass" if provenance_ok else "fail", provenance_message if provenance_ok else "one or more required DR2 PDF provenance files are missing", False)
    if likelihood_mode == "spatial_only":
        normalized_gamma = normalized.get("spectral_indices", [None])[0]
        acceptance_gamma = finite_float(result.get("acceptance_gamma_legacy"))
        fixed_acceptance = result.get("gamma_mode") == "fixed" and result.get("gamma_role") == "acceptance_only" and acceptance_gamma is not None and finite_float(normalized_gamma) is not None and abs(acceptance_gamma - float(normalized_gamma)) < 1e-12
        add_check(review, "dr2_spatial_only_acceptance", "pass" if fixed_acceptance else "fail", "fixed acceptance Gamma matches the normalized request" if fixed_acceptance else "spatial-only acceptance Gamma is not fixed or does not match the request", False)
        no_energy = result.get("energy_pdf") == "not_used" and working_set.get("signal_energy_tables_loaded") is False
        add_check(review, "dr2_spatial_only_energy_exclusion", "pass" if no_energy else "fail", "signal and background energy PDFs are excluded" if no_energy else "spatial-only result indicates that energy tables were used", False)
    review["metrics"].update({"ns_hat": ns_hat, "ts": ts, "gamma": gamma, "gamma_mode": result.get("gamma_mode"), "likelihood_mode": likelihood_mode, "acceptance_gamma_legacy": result.get("acceptance_gamma_legacy")})
    if result.get("p_value_method") in {"analytic_half_chi_square_df1_estimate", "analytic_half_chi_square_df2_estimate"}:
        expected = local_p_value_estimate(result["TS"], normalized.get("gamma_mode"))
        valid_estimate = all(result.get(key) == expected[key] for key in ("p_value_method", "p_value_dof", "p_value_is_estimate", "significance_convention"))
        for key in ("pre_trial_p", "pre_trial_significance"):
            value = finite_float(result.get(key))
            valid_estimate = valid_estimate and value is not None and math.isclose(value, expected[key], rel_tol=1e-12, abs_tol=1e-14)
        add_check(review, "dr2_local_estimate", "pass" if valid_estimate else "fail", "p-value and significance estimates match Gamma mode and declared dof" if valid_estimate else "local estimate, method or dof is inconsistent with Gamma mode", False)
    table_path = result.get("generated_files", {}).get("fit_results")
    if table_path:
        table = read_csv_if_present(Path(table_path))
        table_ok = len(table) == 1
        if table_ok:
            for key in (("TS", "ns", "gamma", "pre_trial_p", "pre_trial_significance") if result.get("p_value_is_estimate") else ("TS", "ns", "gamma")):
                value = finite_float(table[0].get(key))
                reference = finite_float(result.get(key))
                table_ok = table_ok and value is not None and reference is not None and math.isclose(value, reference, rel_tol=1e-12, abs_tol=1e-12)
        add_check(review, "dr2_fit_table", "pass" if table_ok else "fail", "fit CSV matches the numeric report" if table_ok else "fit CSV is missing or inconsistent", False)

    if normalized.get("flux_upper_limit_gammas") and result.get("n_sources") == 1:
        review_flux_suite(review, report, normalized, root)
    elif normalized.get("flux_upper_limit_cl") is not None and not normalized.get("flux_upper_limit_gammas"):
        review_flux_upper_limit(review, result, normalized)


def review_flux_upper_limit(review, result, normalized):
    """Check the requested one-sided construction, conversion and artifacts."""
    from statistics import NormalDist

    limit = result.get("flux_upper_limit", {})
    confidence = finite_float(normalized.get("flux_upper_limit_cl"))
    valid = confidence is not None and 0.5 < confidence < 1 and isinstance(limit, dict)
    expected_q = NormalDist().inv_cdf(confidence) ** 2 if valid else None
    expected = {"confidence_level": confidence, "gamma": result.get("gamma"),
                "critical_q": expected_q, "q_at_upper_limit": expected_q,
                "ns_hat": result.get("ns"), "ns_bound_max": result.get("fit_bounds", {}).get("ns", [None, None])[1]}
    for key, reference in expected.items():
        value, reference = finite_float(limit.get(key)), finite_float(reference)
        valid = valid and value is not None and reference is not None and math.isclose(value, reference, rel_tol=1e-7, abs_tol=1e-6)
    ns_upper = finite_float(limit.get("ns_upper_limit"))
    phi = finite_float(limit.get("phi0_upper_limit"))
    yield100 = finite_float(limit.get("yield_per_phi0_at_100tev"))
    valid = valid and ns_upper is not None and float(result["ns"]) < ns_upper < float(result["fit_bounds"]["ns"][1]) and phi is not None and phi > 0 and yield100 is not None and yield100 > 0
    if valid:
        yield1 = sum(float(values[0]) for values in result["w_acc_by_dataset"].values())
        valid = math.isclose(yield100, yield1 * 100 ** float(result["gamma"]), rel_tol=1e-12)
        for value, reference in ((phi * yield100, ns_upper), (limit.get("e2_dphi_de_upper_limit_gev_cm2_s"), phi * 1e10), (limit.get("e2_dphi_de_upper_limit_tev_cm2_s"), phi * 1e7), (2 * limit.get("log_likelihood_ratio_at_best", float("nan")), result["TS"])):
            value = finite_float(value)
            valid = valid and value is not None and math.isclose(value, reference, rel_tol=1e-7, abs_tol=1e-12)
    valid = valid and result.get("gamma_mode") == "fixed" and result.get("n_sources") == 1 and result.get("likelihood_mode") == "spatial_energy" and limit.get("method") == "asymptotic_fixed_gamma_profile_likelihood" and limit.get("sidedness") == "one_sided_upper" and limit.get("flavor") == "nu_mu+anti_nu_mu" and limit.get("pivot_energy_gev") == 1e5 and limit.get("phi0_unit") == "GeV^-1 cm^-2 s^-1" and limit.get("coverage_validated") is False and limit.get("systematic_uncertainties_included") is False
    for field in ("event_selection", "event_dec_min_deg", "event_dec_max_deg"):
        valid = valid and limit.get(field) == result.get(field)
    add_check(review, "dr2_flux_upper_limit", "pass" if valid else "fail", "one-sided profile threshold, fixed spectrum, units, detector yield and root are consistent; coverage remains unvalidated" if valid else "upper-limit request, construction or flux conversion is inconsistent", False)
    if ns_upper is not None and finite_float(result.get("ns")) is not None and result["ns"] <= 1e-5:
        add_check(review, "dr2_flux_ns_boundary", "warning", "Upper-limit fit has ns at zero; asymptotic coverage at the physical boundary remains unvalidated", False)
    if normalized.get("_flux_suite_member"):
        return
    files = result.get("generated_files", {})
    table = read_csv_if_present(Path(files["flux_upper_limit"])) if files.get("flux_upper_limit") else []
    profile = read_csv_if_present(Path(files["upper_limit_profile"])) if files.get("upper_limit_profile") else []
    tables_ok = len(table) == 1 and len(profile) == len(limit.get("profile", [])) and len(profile) >= 3
    if tables_ok:
        for key in ("confidence_level", "gamma", "ns_upper_limit", "phi0_upper_limit", "critical_q", "q_at_upper_limit"):
            value, reference = finite_float(table[0].get(key)), finite_float(limit.get(key))
            tables_ok = tables_ok and value is not None and reference is not None and math.isclose(value, reference, rel_tol=1e-12, abs_tol=0)
        for row, reference in zip(profile, limit["profile"]):
            for key in ("ns", "log_likelihood_ratio", "q"):
                value = finite_float(row.get(key))
                tables_ok = tables_ok and value is not None and math.isclose(value, reference[key], rel_tol=1e-12, abs_tol=1e-12)
    add_check(review, "dr2_flux_upper_limit_tables", "pass" if tables_ok else "fail", "upper-limit and evaluated-profile CSV files match the numeric report" if tables_ok else "upper-limit tables are missing or inconsistent", False)


def review_dr2_source_scan(review, run_dir, report, normalized, root):
    sources = normalized.get("sources", [])
    records = report.get("result", {}).get("source_results")
    complete = isinstance(records, list) and len(records) == len(sources) and len(sources) > 0
    add_check(review, "dr2_scan_complete", "pass" if complete else "fail", "one independent fit per input source" if complete else "source scan is missing or incomplete", False)
    if not complete:
        return
    table = read_csv_if_present(run_dir / "source_results.csv")
    table_ok = len(table) == len(sources)
    metrics = []
    for number, (source, item) in enumerate(zip(sources, records), start=1):
        fit = item.get("fit", {}) if isinstance(item, dict) else {}
        identity_ok = isinstance(item, dict) and item.get("source_number") == source.get("source_number") and item.get("source_name") == source.get("name")
        for field in ("ra_deg", "dec_deg"):
            value = finite_float(item.get(field)) if isinstance(item, dict) else None
            identity_ok = identity_ok and value is not None and abs(value - float(source[field])) < 1e-10
        add_check(review, "source_%d_identity" % number, "pass" if identity_ok else "fail", "source identity and input order match" if identity_ok else "source scan identity or order differs from the input", False)
        single_normalized = dict(normalized, sources=[dict(source, weight=1.0)])
        single_report = dict(report, result=fit)
        child = {"checks": [], "metrics": {}}
        if isinstance(fit, dict):
            review_dr2_run(child, single_report, single_normalized, root)
        else:
            add_check(child, "fit", "fail", "source fit is unreadable", False)
        for check in child["checks"]:
            review["checks"].append(dict(check, id="source_%d_%s" % (number, check["id"])))
        metrics.append(dict(child["metrics"], source_number=number, source_name=source.get("name")))
        if number <= len(table):
            row = table[number - 1]
            table_ok = table_ok and integer_value(row.get("source_number")) == source.get("source_number") and row.get("source_name") == source.get("name")
            for field in ("ra_deg", "dec_deg"):
                coordinate = finite_float(row.get(field))
                table_ok = table_ok and coordinate is not None and abs(coordinate - float(source[field])) < 1e-10
            columns = [("TS", "TS"), ("ns", "ns"), ("gamma_skyllh", "gamma")]
            if fit.get("p_value_is_estimate"):
                columns.extend([("pre_trial_p_approx", "pre_trial_p"), ("pre_trial_significance", "pre_trial_significance")])
            for column, key in columns:
                value = finite_float(row.get(column))
                reference = finite_float(fit.get(key)) if isinstance(fit, dict) else None
                table_ok = table_ok and value is not None and reference is not None and math.isclose(value, reference, rel_tol=1e-12, abs_tol=1e-12)
    add_check(review, "dr2_scan_table", "pass" if table_ok else "fail", "source CSV matches the reviewed fits" if table_ok else "source CSV is missing, incomplete, reordered, or inconsistent", False)
    review["metrics"]["source_fits"] = metrics


def review_single_run(review: Dict[str, Any], report: Dict[str, Any]) -> None:
    result = report.get("result", {})
    required = ["best_fit_ns", "ts", "pre_trial_p"]
    missing = [key for key in required if key not in result]
    add_check(review, "single_result_fields", "fail" if missing else "pass", "missing fields: %s" % ", ".join(missing) if missing else "single-source result fields are present", False)
    if missing:
        return
    ns_hat = finite_float(result["best_fit_ns"])
    ts = finite_float(result["ts"])
    p_value = finite_float(result["pre_trial_p"])
    valid = ns_hat is not None and ts is not None and ts >= 0.0 and p_value is not None and 0.0 <= p_value <= 1.0
    add_check(review, "single_numeric_ranges", "pass" if valid else "fail", "single-source values are finite and in valid ranges" if valid else "single-source result contains invalid numeric values", False)
    review["metrics"].update({"ns_hat": ns_hat, "ts": ts, "pre_trial_p": p_value})
    if ns_hat is not None and abs(ns_hat + 10.0) < 0.01:
        add_check(review, "single_fit_boundary", "warning", "ns_hat is at the lower optimizer boundary", False)


def review_catalog_run(review: Dict[str, Any], run_dir: Path, root: Path, report: Dict[str, Any], normalized: Dict[str, Any]) -> None:
    source_path = run_dir / "source_results.csv"
    stacking_path = run_dir / "stacking_results.csv"
    source_rows = read_csv_if_present(source_path)
    stacking_rows = read_csv_if_present(stacking_path)
    expected_sources = int(report.get("analysis", {}).get("n_sources", 0))
    add_check(review, "source_table", "pass" if len(source_rows) == expected_sources and expected_sources > 0 else "fail", "source table has %d rows in input order" % len(source_rows) if len(source_rows) == expected_sources else "source table row count does not match the normalized catalog", False)
    add_check(review, "stacking_table", "pass" if stacking_rows else "fail", "stacking table has %d hypotheses" % len(stacking_rows) if stacking_rows else "stacking table is missing or empty", False)
    if source_rows:
        review_source_rows(review, source_rows, expected_sources)
    if stacking_rows:
        review_stacking_rows(review, stacking_rows)
    weights = [finite_float(source.get("weight")) for source in normalized.get("sources", [])]
    valid_weights = [value for value in weights if value is not None]
    weight_sum = sum(valid_weights)
    add_check(review, "weight_normalization", "pass" if len(valid_weights) == expected_sources and abs(weight_sum - 1.0) < 1e-9 else "fail", "normalized source weights sum to one" if abs(weight_sum - 1.0) < 1e-9 else "normalized source weights do not sum to one", False)
    if valid_weights:
        max_fraction = max(valid_weights)
        effective_count = 1.0 / sum(value * value for value in valid_weights) if sum(value * value for value in valid_weights) > 0.0 else 0.0
        review["metrics"].update({"weight_sum": weight_sum, "maximum_source_weight": max_fraction, "effective_source_count": effective_count})
        if max_fraction > 0.5 or effective_count < min(5.0, expected_sources / 5.0):
            add_check(review, "weight_concentration", "warning", "stacking weights are strongly concentrated; confirm this is scientifically intended", False)
    workbook = run_dir / "analysis_results.xlsx"
    add_check(review, "excel_workbook", "pass" if workbook.exists() and workbook.stat().st_size > 0 else "fail", "Excel workbook is present" if workbook.exists() else "Excel workbook is missing; rerun output generation without changing scientific inputs", True)
    qa_file = run_dir / "workbook_qa" / "key_ranges.ndjson"
    qa_errors = workbook_error_count(run_dir / "analysis_results.xlsx.inspect.ndjson") + workbook_error_count(qa_file)
    qa_status = "pass" if qa_file.exists() and qa_errors == 0 else ("fail" if qa_errors else "warning")
    add_check(review, "workbook_qa", qa_status, "workbook QA exists with no formula errors" if qa_status == "pass" else ("workbook QA contains formula errors" if qa_errors else "workbook QA artifact is missing"), True)
    figure_values = report.get("result", {}).get("figures", [])
    missing_figures = []
    for value in figure_values:
        figure_path = Path(value)
        if not figure_path.is_absolute():
            figure_path = root / figure_path
        if not valid_pdf(figure_path):
            missing_figures.append(str(figure_path))
    add_check(review, "figures", "pass" if len(figure_values) >= 3 and not missing_figures else "fail", "all expected PDF figures are readable" if not missing_figures and len(figure_values) >= 3 else "one or more expected PDF figures are missing or invalid", True)


def review_source_rows(review: Dict[str, Any], rows: List[Dict[str, str]], expected_sources: int) -> None:
    numbers = [integer_value(row.get("source_number")) for row in rows]
    add_check(review, "source_order", "pass" if numbers == list(range(1, expected_sources + 1)) else "fail", "source_number preserves one-based input order" if numbers == list(range(1, expected_sources + 1)) else "source_number does not preserve one-based input order", False)
    ranks = [integer_value(row.get("significance_rank")) for row in rows]
    ranks_are_valid = all(rank is not None for rank in ranks) and sorted(ranks) == list(range(1, expected_sources + 1))
    add_check(review, "significance_ranks", "pass" if ranks_are_valid else "fail", "significance ranks form a complete permutation" if ranks_are_valid else "significance ranks are incomplete or duplicated", False)
    invalid = 0
    invalid_coordinates = 0
    unnamed = 0
    boundary = 0
    post_trial_mismatch = 0
    local_p_mismatch = 0
    for row in rows:
        ra_deg = finite_float(row.get("ra_deg"))
        dec_deg = finite_float(row.get("dec_deg"))
        if ra_deg is None or dec_deg is None or not 0.0 <= ra_deg < 360.0 or not -90.0 <= dec_deg <= 90.0:
            invalid_coordinates += 1
        if not str(row.get("source_name", "")).strip():
            unnamed += 1
        ns_hat = finite_float(row.get("ns_hat"))
        ts = finite_float(row.get("ts"))
        pre_trial = finite_float(row.get("pre_trial_p"))
        post_trial = finite_float(row.get("post_trial_p"))
        if ns_hat is None or ts is None or ts < 0.0 or pre_trial is None or not 0.0 <= pre_trial <= 1.0 or post_trial is None or not 0.0 <= post_trial <= 1.0:
            invalid += 1
            continue
        expected_post = 1.0 - (1.0 - pre_trial) ** expected_sources
        expected_pre = 0.5 * math.erfc(math.sqrt(ts / 2.0))
        if abs(pre_trial - expected_pre) > 1e-8:
            local_p_mismatch += 1
        if abs(post_trial - expected_post) > 1e-8:
            post_trial_mismatch += 1
        if abs(ns_hat + 10.0) < 0.01:
            boundary += 1
    add_check(review, "source_numeric_ranges", "pass" if invalid == 0 else "fail", "all source results are finite and in valid ranges" if invalid == 0 else "%d source rows contain invalid numeric results" % invalid, False)
    add_check(review, "source_coordinates", "pass" if invalid_coordinates == 0 and unnamed == 0 else "fail", "source names and coordinates are valid" if invalid_coordinates == 0 and unnamed == 0 else "%d invalid coordinates and %d empty names were found" % (invalid_coordinates, unnamed), False)
    add_check(review, "source_local_p", "pass" if local_p_mismatch == 0 else "fail", "pre-trial p-values match the declared analytic TS approximation" if local_p_mismatch == 0 else "%d pre-trial p-values do not match the declared TS approximation" % local_p_mismatch, False)
    add_check(review, "source_trial_correction", "pass" if post_trial_mismatch == 0 else "fail", "post-trial p-values match the catalog-size correction" if post_trial_mismatch == 0 else "%d post-trial p-values do not match the catalog-size correction" % post_trial_mismatch, False)
    if boundary:
        add_check(review, "source_fit_boundaries", "warning", "%d source fits reached the lower ns optimizer boundary" % boundary, False)
    review["metrics"]["source_lower_boundary_count"] = boundary


def review_stacking_rows(review: Dict[str, Any], rows: List[Dict[str, str]]) -> None:
    invalid = 0
    local_p_mismatch = 0
    missing_post_trial = 0
    for row in rows:
        ns_hat = finite_float(row.get("ns_hat"))
        ts = finite_float(row.get("ts"))
        p_value = finite_float(row.get("pre_trial_p"))
        if ns_hat is None or ts is None or ts < 0.0 or p_value is None or not 0.0 <= p_value <= 1.0:
            invalid += 1
        elif abs(p_value - 0.5 * math.erfc(math.sqrt(ts / 2.0))) > 1e-8:
            local_p_mismatch += 1
        if str(row.get("post_trial_p", "")).strip() == "":
            missing_post_trial += 1
    add_check(review, "stacking_numeric_ranges", "pass" if invalid == 0 else "fail", "all stacking results are finite and in valid ranges" if invalid == 0 else "%d stacking rows contain invalid numeric results" % invalid, False)
    add_check(review, "stacking_local_p", "pass" if local_p_mismatch == 0 else "fail", "stacking pre-trial p-values match the declared analytic TS approximation" if local_p_mismatch == 0 else "%d stacking pre-trial p-values do not match the declared TS approximation" % local_p_mismatch, False)
    if missing_post_trial:
        add_check(review, "stacking_post_trial", "pass", "stacking post-trial p-values are unavailable until full background trials are implemented", False)


def add_check(review: Dict[str, Any], check_id: str, status: str, message: str, auto_fix_allowed: bool) -> None:
    review["checks"].append({"id": check_id, "status": status, "message": message, "auto_fix_allowed": auto_fix_allowed})


def finalize_review(review: Dict[str, Any], run_dir: Path, write_artifacts: bool) -> Dict[str, Any]:
    statuses = [check["status"] for check in review["checks"]]
    review["status"] = "fail" if "fail" in statuses else ("warning" if "warning" in statuses else "pass")
    for check in review["checks"]:
        if check["status"] == "fail":
            review["recommended_actions"].append({"check": check["id"], "action": check["message"], "auto_fix_allowed": check["auto_fix_allowed"]})
    if write_artifacts and run_dir.exists():
        with (run_dir / "review.json").open("w", encoding="utf-8") as handle:
            json.dump(review, handle, indent=2, sort_keys=True)
            handle.write("\n")
        with (run_dir / "review.md").open("w", encoding="utf-8") as handle:
            handle.write(render_review_markdown(review))
    return review


def render_review_markdown(review: Dict[str, Any]) -> str:
    lines = ["# Analysis Review", "", "Overall status: `%s`" % review["status"], "", "## Checks", ""]
    lines.extend("- `%s` %s: %s" % (check["status"], check["id"], check["message"]) for check in review["checks"])
    lines.extend(["", "## Metrics", ""])
    lines.extend("- %s: `%s`" % (key, value) for key, value in review["metrics"].items())
    return "\n".join(lines) + "\n"


def load_yaml_if_present(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = load_simple_yaml(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def read_csv_if_present(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def valid_pdf(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 100 and path.read_bytes()[:5] == b"%PDF-"


def workbook_error_count(path: Path) -> int:
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8", errors="replace")
    return sum(text.count(marker) for marker in ["#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#N/A"])


def finite_float(value: Any):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def integer_value(value: Any):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def review_flux_suite(review, report, normalized, root):
    """Review all fixed hypotheses and the numeric data behind the figure."""
    import json
    from agent_core.file_cache import sha256_file
    result = report["result"]
    fits = result.get("flux_upper_limit_fits", [])
    expected = [-float(g) for g in normalized["flux_upper_limit_gammas"]]
    complete = isinstance(fits, list) and len(fits) == len(expected) and all(
        isinstance(fit, dict) and fit.get("gamma_mode") == "fixed" and fit.get("gamma") == gamma
        for fit, gamma in zip(fits, expected))
    add_check(review, "dr2_flux_hypotheses", "pass" if complete else "fail",
              "fixed-spectrum fits match every requested upper-limit hypothesis" if complete else "missing or inconsistent upper-limit hypotheses", False)
    if not complete:
        return
    for fit, gamma in zip(fits, expected):
        child_normalized = dict(normalized, gamma_mode="fixed", spectral_indices=[-gamma],
                                flux_upper_limit_gammas=[], _flux_suite_member=True)
        child = {"checks": [], "metrics": {}}
        review_dr2_run(child, dict(report, result=fit), child_normalized, root)
        for check in child["checks"]:
            review["checks"].append(dict(check, id=f"flux_gamma_{gamma:g}_{check['id']}"))
    files = result.get("generated_files", {})
    try:
        table = read_csv_if_present(Path(files["flux_upper_limits"]))
        profile = read_csv_if_present(Path(files["upper_limit_profiles"]))
        limits = [fit["flux_upper_limit"] for fit in fits]
        valid = len(table) == len(limits)
        for row, limit in zip(table, limits):
            for key, reference in limit.items():
                if isinstance(reference, (float, int)) and not isinstance(reference, bool):
                    value = finite_float(row.get(key))
                    valid = valid and value is not None and math.isclose(value, reference, rel_tol=1e-12, abs_tol=1e-12)
        expected_profile = [dict(gamma=limit["gamma"], **point) for limit in limits for point in limit["profile"]]
        valid = valid and len(profile) == len(expected_profile)
        for row, reference in zip(profile, expected_profile):
            for key, value in reference.items():
                parsed = finite_float(row.get(key))
                valid = valid and parsed is not None and math.isclose(parsed, value, rel_tol=1e-12, abs_tol=1e-12)
        provenance = json.loads(Path(files["flux_plot_provenance"]).read_text())
        valid = valid and all(Path(path).is_file() and sha256_file(path) == digest for path, digest in provenance["outputs_sha256"].items())
        valid = valid and all(sha256_file(root / path) == digest for path, digest in provenance["reference_sha256"].items())
        valid = valid and all(Path(files["flux_spectrum_"+suffix]).stat().st_size > 100 for suffix in ("png", "pdf", "svg"))
        curves = read_csv_if_present(Path(files["spectrum_curves"]))
        hypotheses = {f"source_gamma_{limit['gamma']:g}": limit for limit in limits}
        references = {"NGC_1068", "diffuse_tracks", "diffuse_starting_tracks"}
        valid = valid and {row["curve"] for row in curves} == set(hypotheses) | references
        for row in curves:
            factor = 4*math.pi if row["curve"].startswith("diffuse") else 1.
            value = float(row["e2_flux"])
            valid = valid and row["e2_flux_unit"] == "GeV cm^-2 s^-1" and float(row["display_factor"]) == factor
            valid = valid and math.isclose(value, float(row["original_e2_flux"])*factor, rel_tol=1e-12, abs_tol=0.)
            if row["curve"] in hypotheses:
                limit = hypotheses[row["curve"]];energy = float(row["energy_gev"])
                expected_value = energy**2 * limit["phi0_upper_limit"] * (energy / 1e5)**(-limit["gamma"])
                valid = valid and math.isclose(value, expected_value, rel_tol=1e-12, abs_tol=0.)
            elif row.get("band_lower"):
                valid = valid and 0 < float(row["band_lower"]) <= float(row["band_upper"])
    except (OSError, ValueError, KeyError, TypeError):
        valid = False
    add_check(review, "dr2_flux_artifacts", "pass" if valid else "fail",
              "limit/profile tables, reference hashes, common flux units, diffuse 4pi conversion and plotted power laws are consistent" if valid else "missing or inconsistent flux tables, figures, reference data or plot provenance", False)
