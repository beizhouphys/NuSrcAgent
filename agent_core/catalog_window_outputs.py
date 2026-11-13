"""Artifacts and independent review for the fixed-window catalog engine."""
from pathlib import Path
import csv
import math
import shutil

from agent_core.file_cache import sha256_file
from agent_core.schemas import to_clean_dict
from agent_core.temporal import temporal_errors, unavailable_significance


def result_rows(normalized, result):
    rows = []
    operation = normalized["catalog_operation"]
    if normalized["analysis_type"] == "single_source" or operation in {"scan", "scan_and_stack"}:
        for item in result["source_results"]:
            rows.append(dict(hypothesis="source", source_number=item["source_number"],
                name=item["source_name"], **{key: item["fit"][key] for key in ("TS", "ns", "gamma", "gamma_status", "fit_ok")}))
    if normalized["analysis_type"] != "single_source" and operation in {"stack", "scan_and_stack"}:
        rows.append(dict(hypothesis="stack", source_number=0, name="catalog",
            **{key: result["stack_result"][key] for key in ("TS", "ns", "gamma", "gamma_status", "fit_ok")}))
    return rows


def write_artifacts(config_path, config, normalized, result, root):
    from agent_core.report import make_run_id, write_yaml, build_provenance
    from agent_core.analysis_outputs import write_csv
    from agent_core.validate import resolve_path
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    root, config_path = Path(root), Path(config_path)
    from agent_core.time_dependent_trials import code_identity
    result["time_dependent_engine"]["code_identity"] = code_identity(root)
    run_dir = resolve_path(root, config.outputs.output_root) / make_run_id()
    run_dir.mkdir(parents=True, exist_ok=False)
    shutil.copy2(config_path, run_dir / ("config.original" + config_path.suffix))
    norm = to_clean_dict(normalized)
    rows = result_rows(norm, result)
    table = run_dir / "time_dependent_results.csv"
    write_csv(table, list(rows[0]), rows)
    figure_dir = root / "figures" / run_dir.name
    figure_dir.mkdir(parents=True, exist_ok=True)
    files = dict(results=str(table))
    fig, ax = plt.subplots(figsize=(7, 4), layout="constrained")
    ax.plot(range(1, len(rows)+1), [row["TS"] for row in rows], "o")
    ax.set(xlabel="Requested hypothesis (input order; stack last)", ylabel="TS")
    for suffix in ("png", "pdf"):
        path = figure_dir / ("time_dependent_ts." + suffix)
        fig.savefig(path, dpi=170)
        files[suffix] = str(path)
    plt.close(fig)
    result["generated_files"] = files
    result["artifact_sha256"] = {key: sha256_file(path) for key, path in files.items()}
    result["time_dependent_summary"] = dict(source_count=len(normalized.sources), rows=rows,
        results_csv=str(table), figures=files,
        note="Fixed per-source boxes; conditional likelihood. Significance awaits matched shared background trials.")
    report = dict(schema_version=normalized.schema_version, run=dict(status="completed", backend=result["backend"]),
        analysis=dict(type=normalized.analysis_type, time_mode="time_dependent", sample=normalized.sample,
            likelihood_mode=normalized.likelihood_mode, n_sources=len(normalized.sources)), result=result,
        diagnostics=dict(n_background_trials=0, requested_background_trials=0), warnings=[])
    write_yaml(run_dir / "config.normalized.yaml", norm)
    write_yaml(run_dir / "report.yaml", report)
    provenance = build_provenance(config_path, normalized, root, config)
    provenance["normalized_sha256"] = sha256_file(run_dir / "config.normalized.yaml")
    provenance["time_dependent_input_sha256"] = result["time_dependent_engine"]["input_sha256"]
    write_yaml(run_dir / "provenance.yaml", provenance)
    lines = ["# Fixed-window time-dependent analysis", "", result["time_dependent_summary"]["note"], "",
             "| Hypothesis | ns | Gamma | TS |", "| --- | ---: | ---: | ---: |"]
    for row in rows:
        gamma = "unidentified" if row["gamma"] is None else f"{row['gamma']:.7g}"
        lines.append(f"| {row['name']} | {row['ns']:.7g} | {gamma} | {row['TS']:.7g} |")
    lines += ["", "Gamma is positive in E^(-Gamma). No time-integrated significance or flux formula is applied.",
              "See review.md before interpreting these results.", ""]
    (run_dir / "report.md").write_text("\n".join(lines))
    return run_dir


def review_artifacts(review, report, normalized, root):
    from agent_core.review import add_check
    result = report["result"]
    settings = normalized["temporal"]
    metadata = result.get("time_dependent_engine", {})
    sources, records = normalized["sources"], result.get("source_results", [])
    valid = (not temporal_errors(settings) and normalized["sample"] == "icecube_public_ps_14yr_dr2"
        and result.get("temporal_scope") == "per_source_catalog_windows"
        and result.get("catalog_operation") == normalized["catalog_operation"]
        and len(records) == len(sources) and len(sources) > 0
        and metadata.get("likelihood_family") == "skyllh_conditional"
        and metadata.get("dataset_names") == settings["datasets"]
        and metadata.get("fit_procedure") == "catalog_continuous_profile_v1")
    windows = metadata.get("windows", [])
    valid = valid and len(windows) == len(sources)
    for source, item, window in zip(sources, records, windows):
        valid = valid and item.get("source_number") == source["source_number"] and item.get("source_name") == source["name"]
        valid = valid and all(item.get(key) == source[key] for key in ("ra_deg", "dec_deg"))
        valid = valid and all(window.get(key) == source[key] for key in ("name", "ra_deg", "dec_deg", "weight"))
        try:
            index = source["source_number"] - 1
            expected = settings.get("windows", [])[index] if "windows" in settings else {
                "start_mjd": float(source["metadata"][settings["window_columns"]["start"]]),
                "stop_mjd": float(source["metadata"][settings["window_columns"]["stop"]])}
            valid = valid and all(window[key] == expected[key] for key in ("start_mjd", "stop_mjd"))
        except (ValueError, KeyError, IndexError, TypeError):
            valid = False
    add_check(review, "catalog_window_request", "pass" if valid else "fail", "Source order, weights, time windows and detector phases match the request", False)
    fits = [item["fit"] for item in records] + [result.get("stack_result", {})]
    for i, fit in enumerate(fits):
        ok = fit.get("fit_ok") is True
        try:
            ok = ok and math.isfinite(fit["TS"]) and fit["TS"] >= 0 and math.isfinite(fit["ns"]) and 0 <= fit["ns"] <= settings.get("ns_max", 1000.)
            gamma = fit.get("gamma")
            bounds = normalized.get("gamma_bounds")
            lower, upper = (-bounds[1], -bounds[0]) if bounds else (1., 4.)
            if normalized["gamma_mode"] == "fixed":
                ok = ok and (gamma == -normalized["spectral_indices"][0] or (fit["ns"] == 0 and gamma is None))
            elif fit["ns"] > 0:
                ok = ok and gamma is not None and math.isfinite(gamma) and lower <= gamma <= upper
            else:
                ok = ok and gamma is None
            ok = ok and all(fit.get(key) == value for key, value in unavailable_significance().items())
        except (TypeError, KeyError):
            ok = False
        add_check(review, f"catalog_fit_{i}", "pass" if ok else "fail", "Fit convergence, parameter ranges and unavailable significance", False)
        if ok and fit["ns"] > 0 and (math.isclose(fit["ns"], settings.get("ns_max", 1000.)) or
            (normalized["gamma_mode"] == "fitted" and any(math.isclose(fit["gamma"], x, abs_tol=1e-6) for x in (lower, upper)))):
            add_check(review, f"catalog_boundary_{i}", "warning", "A fitted parameter is at its requested boundary", False)
    files, hashes = result.get("generated_files", {}), result.get("artifact_sha256", {})
    artifacts = set(files) == set(hashes) == {"results", "png", "pdf"}
    try:
        artifacts = artifacts and all(sha256_file(path) == hashes[key] for key, path in files.items())
        with Path(files["results"]).open() as stream:
            rows = list(csv.DictReader(stream))
        expected_rows = result_rows(normalized, result)
        artifacts = artifacts and len(rows) == len(expected_rows)
        for actual, expected in zip(rows, expected_rows):
            artifacts = artifacts and all(actual[key] == ("" if value is None else str(value)) for key, value in expected.items())
    except (OSError, KeyError, ValueError):
        artifacts = False
    add_check(review, "catalog_window_artifacts", "pass" if artifacts else "fail", "Tables and figures match recorded fits and hashes", False)
    inputs = metadata.get("input_sha256", {})
    try:
        verified = bool(inputs) and all(sha256_file(Path(root)/path) == value for path, value in inputs.items())
    except OSError:
        verified = False
    add_check(review, "catalog_window_inputs", "pass" if verified else "fail", "Numerical input identities are unchanged", False)
    calibration = report.get("diagnostics") == dict(n_background_trials=0, requested_background_trials=0) and all(result.get(key) == value for key, value in unavailable_significance().items())
    add_check(review, "catalog_window_calibration", "pass" if calibration else "fail", "Observed fit executes zero trials and no analytic significance estimate", False)
