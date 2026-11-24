"""Artifacts and independent review for the fixed-profile catalog engine."""
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


def _has_stack(normalized):
    if isinstance(normalized, dict):
        analysis_type = normalized["analysis_type"]
        catalog_operation = normalized["catalog_operation"]
    else:
        analysis_type = normalized.analysis_type
        catalog_operation = normalized.catalog_operation
    return (analysis_type != "single_source"
            and catalog_operation in {"stack", "scan_and_stack"})


def _write_observed_likelihood_contours(
    normalized,
    result,
    root,
    run_dir,
    figure_dir,
    prepared=None,
):
    """Create reviewed-fit surfaces without running or depending on trials."""

    if normalized.gamma_mode != "fitted":
        return {}, {"status": "not_applicable_fixed_gamma", "sources": [], "stack": None}

    from analysis_backend.time_dependent.adapter import prepare_analysis
    from analysis_backend.time_dependent.surfaces import (
        build_observed_surface_context,
        save_observed_likelihood_surface,
    )
    from agent_core.plot_time_dependent_standard_report import plot_likelihood_surface

    if prepared is None:
        prepared = prepare_analysis(normalized, root, workers=1, build_engine=False)
    expected = result["time_dependent_engine"]
    for key in ("engine", "spectrum", "likelihood", "dataset_names", "input_sha256", "windows"):
        if prepared.metadata[key] != expected[key]:
            raise ValueError("observed contour reconstruction differs in " + key)
    if expected.get("time_profile") is not None and prepared.metadata["time_profile"] != expected["time_profile"]:
        raise ValueError("observed contour reconstruction differs in time_profile")
    surface_context = build_observed_surface_context(prepared.constructed)

    surface_dir = run_dir / "likelihood_contours"
    plot_dir = figure_dir / "likelihood_contours"
    surface_dir.mkdir(parents=True, exist_ok=True)
    plot_dir.mkdir(parents=True, exist_ok=True)
    files, source_summaries = {}, []
    ranked = sorted(
        enumerate(result["source_results"]),
        key=lambda pair: (-float(pair[1]["fit"]["TS"]), pair[0]),
    )[:3]
    for rank, (source_index, item) in enumerate(ranked, start=1):
        stem_name = f"source_{int(item['source_number']):04d}_likelihood_contour"
        surface_path = surface_dir / f"{stem_name}.npz"
        surface = save_observed_likelihood_surface(
            prepared.constructed,
            surface_path,
            item["fit"],
            source_index=source_index,
            source_name=str(item["source_name"]),
            source_id=str(item["source_number"]),
            context=surface_context,
        )
        plot_stem = plot_dir / stem_name
        plot_likelihood_surface(
            surface_path,
            plot_stem,
            f"Observed single-source likelihood surface: {item['source_name']}",
            r"Single-source signal count $n$",
            {"ns": item["fit"]["ns"], "gamma": item["fit"].get("gamma")},
        )
        prefix = f"source_contour_{rank}"
        files.update({
            f"{prefix}_npz": str(surface_path),
            f"{prefix}_png": str(plot_stem.with_suffix(".png")),
            f"{prefix}_pdf": str(plot_stem.with_suffix(".pdf")),
        })
        source_summaries.append({
            "rank_by_observed_ts": rank,
            "source_index": source_index,
            "source_number": int(item["source_number"]),
            "source_name": str(item["source_name"]),
            "observed_ts": float(item["fit"]["TS"]),
            "surface": surface,
            "png": files[f"{prefix}_png"],
            "pdf": files[f"{prefix}_pdf"],
        })

    stack_summary = None
    if _has_stack(normalized):
        fit = result["stack_result"]
        surface_path = surface_dir / "stacking_likelihood_contour.npz"
        surface = save_observed_likelihood_surface(
            prepared.constructed,
            surface_path,
            fit,
            source_index=None,
            context=surface_context,
        )
        plot_stem = plot_dir / "stacking_likelihood_contour"
        plot_likelihood_surface(
            surface_path,
            plot_stem,
            "Observed time-dependent stacking likelihood surface",
            r"Stacked signal count $n$",
            {"ns": fit["ns"], "gamma": fit.get("gamma")},
        )
        files.update({
            "stack_contour_npz": str(surface_path),
            "stack_contour_png": str(plot_stem.with_suffix(".png")),
            "stack_contour_pdf": str(plot_stem.with_suffix(".pdf")),
        })
        stack_summary = {
            "observed_ts": float(fit["TS"]),
            "surface": surface,
            "png": files["stack_contour_png"],
            "pdf": files["stack_contour_pdf"],
        }
    return files, {"status": "rendered", "sources": source_summaries, "stack": stack_summary}


def write_artifacts(config_path, config, normalized, result, root):
    from agent_core.report import make_run_id, write_yaml, build_provenance
    from agent_core.analysis_outputs import write_csv
    from agent_core.validate import resolve_path
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    root, config_path = Path(root), Path(config_path)
    prepared = getattr(result, "prepared_analysis", None)
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
    contour_files, contour_summary = _write_observed_likelihood_contours(
        normalized, result, root, run_dir, figure_dir, prepared=prepared
    )
    files.update(contour_files)
    result["observed_likelihood_contours"] = contour_summary
    result["generated_files"] = files
    result["artifact_sha256"] = {key: sha256_file(path) for key, path in files.items()}
    chat_default_figures = [item["png"] for item in contour_summary["sources"]]
    if contour_summary["stack"] is not None:
        chat_default_figures.append(contour_summary["stack"]["png"])
    profile_label = "Gaussian" if normalized.temporal.get("profile") == "gaussian" else "box"
    result["time_dependent_summary"] = dict(source_count=len(normalized.sources), rows=rows,
        results_csv=str(table), figures=files, observed_likelihood_contours=contour_summary,
        chat_default_figures=chat_default_figures,
        note=f"Fixed per-source {profile_label} time profiles; conditional likelihood. Significance awaits matched shared background trials.")
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
    lines = ["# Fixed-profile time-dependent analysis", "", result["time_dependent_summary"]["note"], "",
             "| Hypothesis | n | s | TS |", "| --- | ---: | ---: | ---: |"]
    for row in rows:
        gamma = "unidentified" if row["gamma"] is None else f"{row['gamma']:.7g}"
        lines.append(f"| {row['name']} | {row['ns']:.7g} | {gamma} | {row['TS']:.7g} |")
    lines += ["", "s is positive in E^(-s). No time-integrated significance or flux formula is applied.",
              "See review.md before interpreting these results.", ""]
    if contour_summary["status"] == "rendered":
        lines += ["## Observed likelihood contours", ""]
        for item in contour_summary["sources"]:
            lines.append(f"- {item['source_name']} (observed TS rank {item['rank_by_observed_ts']}): {item['png']}")
        if contour_summary["stack"] is not None:
            lines.append(f"- Stacking analysis: {contour_summary['stack']['png']}")
        lines.append("")
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
        and metadata.get("time_profile", {"type": "box"}).get("type") == settings.get("profile")
        and metadata.get("fit_procedure") == "catalog_continuous_profile_v1")
    windows = metadata.get("windows", [])
    valid = valid and len(windows) == len(sources)
    for source, item, window in zip(sources, records, windows):
        valid = valid and item.get("source_number") == source["source_number"] and item.get("source_name") == source["name"]
        valid = valid and all(item.get(key) == source[key] for key in ("ra_deg", "dec_deg"))
        valid = valid and all(window.get(key) == source[key] for key in ("name", "ra_deg", "dec_deg", "weight"))
        try:
            index = source["source_number"] - 1
            if settings.get("profile") == "box":
                expected = settings.get("windows", [])[index] if "windows" in settings else {
                    "start_mjd": float(source["metadata"][settings["window_columns"]["start"]]),
                    "stop_mjd": float(source["metadata"][settings["window_columns"]["stop"]])}
                valid = valid and all(window[key] == expected[key] for key in ("start_mjd", "stop_mjd"))
            else:
                expected = settings.get("windows", [])[index] if "windows" in settings else {
                    "center_mjd": float(source["metadata"][settings["window_columns"]["center"]]),
                    "sigma_days": float(source["metadata"][settings["window_columns"]["sigma"]])}
                tolerance = float(settings.get("tail_tolerance", 1e-12))
                half_support = expected["sigma_days"] * math.sqrt(-2.0 * math.log(tolerance))
                valid = valid and window["center_mjd"] == expected["center_mjd"]
                valid = valid and window["sigma_days"] == expected["sigma_days"]
                valid = valid and math.isclose(window["start_mjd"], expected["center_mjd"] - half_support)
                valid = valid and math.isclose(window["stop_mjd"], expected["center_mjd"] + half_support)
        except (ValueError, KeyError, IndexError, TypeError):
            valid = False
    add_check(review, "catalog_window_request", "pass" if valid else "fail", "Source order, weights, fixed time profiles and detector phases match the request", False)
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
    artifacts = set(files) == set(hashes) and {"results", "png", "pdf"}.issubset(files)
    contour_summary = result.get("observed_likelihood_contours", {})
    chat_default_figures = result.get("time_dependent_summary", {}).get("chat_default_figures", [])
    if normalized["gamma_mode"] == "fitted":
        expected_sources = sorted(
            enumerate(records), key=lambda pair: (-float(pair[1]["fit"]["TS"]), pair[0])
        )[:3]
        actual_sources = contour_summary.get("sources", [])
        artifacts = artifacts and contour_summary.get("status") == "rendered"
        artifacts = artifacts and len(actual_sources) == len(expected_sources)
        for rank, ((source_index, expected), actual) in enumerate(
            zip(expected_sources, actual_sources), start=1
        ):
            prefix = f"source_contour_{rank}"
            artifacts = artifacts and all(
                f"{prefix}_{suffix}" in files for suffix in ("npz", "png", "pdf")
            )
            artifacts = artifacts and actual.get("source_index") == source_index
            artifacts = artifacts and actual.get("source_number") == expected.get("source_number")
            artifacts = artifacts and actual.get("source_name") == expected.get("source_name")
            artifacts = artifacts and math.isclose(
                float(actual.get("observed_ts", float("nan"))), float(expected["fit"]["TS"])
            )
        expected_stack = _has_stack(normalized)
        artifacts = artifacts and (contour_summary.get("stack") is not None) == expected_stack
        if expected_stack:
            artifacts = artifacts and all(
                f"stack_contour_{suffix}" in files for suffix in ("npz", "png", "pdf")
            )
        expected_chat_figures = [item.get("png") for item in actual_sources]
        if expected_stack:
            expected_chat_figures.append(contour_summary["stack"].get("png"))
        artifacts = artifacts and chat_default_figures == expected_chat_figures
    else:
        artifacts = artifacts and contour_summary == {
            "status": "not_applicable_fixed_gamma", "sources": [], "stack": None
        }
        artifacts = artifacts and not any("contour" in key for key in files)
        artifacts = artifacts and chat_default_figures == []
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
