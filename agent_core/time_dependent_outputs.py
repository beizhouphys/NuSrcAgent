"""Time-dependent artifacts and review without time-integrated p-value formulas."""
from __future__ import annotations

import csv
import math
from pathlib import Path
import shutil

from agent_core.file_cache import sha256_file
from agent_core.schemas import to_clean_dict
from agent_core.temporal import parameter_mode, temporal_errors, unavailable_significance


NOTE = ("Time-dependent p-values and significances are unavailable. Background trials must repeat "
        "the complete recorded temporal/spectral search and selected catalog. The time-dependent "
        "scrambling method awaits owner approval; this task executes zero background trials. "
        "The statistic is 2 log(L_hat/L_ns=0), without an additional duration penalty.")


def fit_records(normalized, result):
    if normalized["analysis_type"] == "single_source":
        return [dict(source_number=1, source_name=normalized["sources"][0]["name"], fit=result)]
    return result.get("source_results", [])


def fit_row(record):
    fit = record["fit"]
    temporal = fit["temporal"]
    return dict(source_number=record["source_number"], source_name=record["source_name"],
        TS=fit["TS"], ns=fit["ns"], gamma=fit["gamma"], gamma_mode=fit["gamma_mode"],
        profile=temporal["settings"]["profile"], t0_mjd=temporal["t0_mjd"],
        width_days=temporal["width_days"], width_meaning=temporal["width_meaning"],
        t0_mode=temporal["t0_mode"], width_mode=temporal["width_mode"],
        p_value=None, significance=None, calibration="unavailable")


def write_time_dependent_artifacts(config_path, config, normalized, result, root):
    from agent_core.report import make_run_id, write_yaml, build_provenance
    from agent_core.analysis_outputs import write_csv
    from agent_core.validate import resolve_path
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    root, config_path = Path(root), Path(config_path)
    run_dir = resolve_path(root, config.outputs.output_root)/make_run_id()
    run_dir.mkdir(parents=True, exist_ok=False)
    shutil.copy2(config_path, run_dir/("config.original"+config_path.suffix))
    norm = to_clean_dict(normalized)
    records = fit_records(norm, result)
    rows = [fit_row(record) for record in records]
    table = run_dir/"time_dependent_results.csv"
    write_csv(table, list(rows[0]), rows)
    files = {"results": str(table)}
    plots = []
    figure_dir = root/"figures"/run_dir.name
    figure_dir.mkdir(parents=True, exist_ok=True)
    for record in records:
        fit = record["fit"]
        temporal = fit["temporal"]
        trace = temporal["evaluations"]
        trace_path = run_dir/f"time_search_{record['source_number']:04d}.csv"
        write_csv(trace_path, list(trace[0]), trace)
        files[f"search_{record['source_number']}"] = str(trace_path)
        center, width = temporal["t0_mjd"], temporal["width_days"]
        radius = 4*width if normalized.temporal["profile"] == "gaussian" else width
        times = np.linspace(center-radius, center+radius, 1001)
        shape = (np.exp(-.5*((times-center)/width)**2) if normalized.temporal["profile"] == "gaussian"
                 else (np.abs(times-center) <= width/2).astype(float))
        with plt.rc_context({"font.family": "serif", "pdf.fonttype": 42}):
            fig, ax = plt.subplots(figsize=(7., 3.8), layout="constrained")
            ax.plot(times, shape, color="#2458a6", linestyle="-", label=record["source_name"])
            ax.set(xlabel="Time (MJD, UT1)", ylabel="Intrinsic time profile / peak", ylim=(-.03, 1.08))
            ax.ticklabel_format(axis="x", style="plain", useOffset=False)
            ax.legend(frameon=False)
            ax.set_title("Gaussian profile" if normalized.temporal["profile"] == "gaussian" else "Box profile")
            stem = figure_dir/f"time_profile_{record['source_number']:04d}"
            for suffix in ("png", "pdf"):
                path = stem.with_suffix("."+suffix)
                fig.savefig(path, dpi=170)
                files[f"profile_{record['source_number']}_{suffix}"] = str(path)
            plt.close(fig)
        plots.append(dict(source_number=record["source_number"], png=files[f"profile_{record['source_number']}_png"],
                          pdf=files[f"profile_{record['source_number']}_pdf"]))
    result["generated_files"] = files
    result["artifact_sha256"] = {key: sha256_file(path) for key, path in files.items()}
    result["time_dependent_summary"] = dict(source_count=len(rows), rows=rows, note=NOTE,
        results_csv=str(table), profiles=plots)
    result.update(unavailable_significance())
    report = dict(schema_version=normalized.schema_version, run=dict(status="completed", backend=result["backend"]),
        analysis=dict(type=normalized.analysis_type, time_mode="time_dependent", sample=normalized.sample,
                      likelihood_mode=normalized.likelihood_mode, n_sources=len(rows)), result=result,
        diagnostics=dict(n_background_trials=0, requested_background_trials=0), warnings=[])
    write_yaml(run_dir/"config.normalized.yaml", norm)
    write_yaml(run_dir/"report.yaml", report)
    write_yaml(run_dir/"provenance.yaml", build_provenance(config_path, normalized, root, config))
    lines = ["# Time-dependent source analysis", "", NOTE, "",
        "| Source | ns | Gamma | TS | t0 (MJD, UT1) | Width (days) | Width meaning |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |"]
    for row in rows:
        gamma = "fixed shape" if row["gamma"] is None else f"{row['gamma']:.6g}"
        lines.append(f"| {row['source_name']} | {row['ns']:.6g} | {gamma} | {row['TS']:.6g} | {row['t0_mjd']:.9f} | {row['width_days']:.9g} | {row['width_meaning']} |")
    lines += ["", "Gamma follows dN/dE proportional to E^(-Gamma), with the recorded fixed/fitted mode.",
              "Time profiles show the intrinsic shape; the likelihood normalizes separately over each dataset's good-run intervals.",
              "The recorded seeded temporal search does not certify a unique global maximum.",
              "", "Review: [review.md](review.md).", ""]
    (run_dir/"report.md").write_text("\n".join(lines))
    return run_dir


def review_time_dependent(review, report, normalized, root):
    from agent_core.review import add_check, review_dr2_run
    result = report["result"]
    records = fit_records(normalized, result)
    settings = normalized.get("temporal", {})
    correct = (not temporal_errors(settings) and report["analysis"].get("time_mode") == "time_dependent"
               and normalized.get("sample") == "icecube_public_ps_14yr_dr2"
               and (normalized.get("analysis_type") == "single_source" or normalized.get("catalog_operation") == "scan")
               and len(records) == len(normalized["sources"]) and len(records) > 0)
    add_check(review, "time_dependent_request", "pass" if correct else "fail", "Time-dependent request and source count are consistent", False)
    unavailable = all(result.get(key) == value for key, value in unavailable_significance().items())
    unavailable = unavailable and report["diagnostics"] == dict(n_background_trials=0, requested_background_trials=0)
    add_check(review, "time_dependent_calibration", "pass" if unavailable else "fail", "No time-integrated significance formula or unapproved background trials", False)
    for index, record in enumerate(records):
        if index >= len(normalized["sources"]):
            break
        fit = record["fit"]
        source = normalized["sources"][index]
        sub = dict(normalized, analysis_type="single_source", sources=[dict(source, weight=1.)], catalog_operation="stack")
        subreport = dict(report, result=fit, analysis=dict(report["analysis"], type="single_source", n_sources=1))
        child = dict(checks=[], metrics={})
        review_dr2_run(child, subreport, sub, Path(root))
        for check in child["checks"]:
            review["checks"].append(dict(check, id=f"source_{index+1}_"+check["id"]))
        metadata = fit.get("temporal", {})
        valid = (record.get("source_number") == index+1 and record.get("source_name") == source["name"]
                 and metadata.get("settings") == settings and fit.get("time_mode") == "time_dependent"
                 and metadata.get("background_time_model") == "uniform_livetime"
                 and metadata.get("statistic") == "2_log_likelihood_ratio_no_duration_penalty"
                 and metadata.get("width_meaning") == ("sigma_t" if settings.get("profile") == "gaussian" else "full_box_duration")
                 and all(fit.get(key) == value for key, value in unavailable_significance().items()))
        if normalized["analysis_type"] != "single_source":
            valid = valid and record.get("ra_deg") == source["ra_deg"] and record.get("dec_deg") == source["dec_deg"]
        for name, key in (("t0", "t0_mjd"), ("width", "width_days")):
            value = metadata.get(key)
            try:
                valid = valid and math.isfinite(value) and metadata.get(name+"_mode") == parameter_mode(settings[name])
                if parameter_mode(settings[name]) == "fixed":
                    valid = valid and value == settings[name]["value"]
                else:
                    valid = valid and settings[name]["bounds"][0] <= value <= settings[name]["bounds"][1]
            except (TypeError, KeyError):
                valid = False
        datasets = metadata.get("datasets", {})
        yields = fit.get("w_acc_by_dataset", {})
        try:
            total = sum(values[0] for values in yields.values())
            valid = valid and len(datasets) == 4 and total > 0
            for name, dataset in datasets.items():
                factor = dataset["profile_integral_days"] / dataset["livetime_days"]
                valid = valid and factor >= 0 and math.isclose(factor, dataset["yield_factor"], rel_tol=1e-12)
                valid = valid and math.isclose(fit["f_k"][name], yields[name][0]/total, rel_tol=1e-10, abs_tol=1e-14)
            valid = valid and all(row["success"] for row in metadata["search_results"])
            valid = valid and any(row["TS"] is not None and math.isclose(row["TS"], fit["TS"], rel_tol=1e-12, abs_tol=1e-12)
                                  and row["t0_mjd"] == metadata["t0_mjd"] and row["width_days"] == metadata["width_days"]
                                  for row in metadata["evaluations"])
        except (TypeError, KeyError, ZeroDivisionError):
            valid = False
        add_check(review, f"source_{index+1}_temporal", "pass" if valid else "fail", "Temporal parameters, search convergence and livetime-dependent detector acceptance agree", False)
        if fit.get("ns", 0) > 0:
            boundary = any(parameter_mode(settings[name]) == "fitted" and any(
                abs(metadata[key]-bound) < 1e-6*max(1., settings[name]["bounds"][1]-settings[name]["bounds"][0])
                for bound in settings[name]["bounds"])
                for name, key in (("t0", "t0_mjd"), ("width", "width_days"))) if valid else False
            if boundary:
                add_check(review, f"source_{index+1}_temporal_boundary", "warning", "A fitted temporal parameter is at a requested bound", False)
    files = result.get("generated_files", {})
    hashes = result.get("artifact_sha256", {})
    expected = {"results", *(key for i in range(1, len(records)+1) for key in
                             (f"search_{i}", f"profile_{i}_png", f"profile_{i}_pdf"))}
    artifacts_ok = set(files) == expected and set(hashes) == expected
    try:
        artifacts_ok = artifacts_ok and all(Path(path).is_file() and sha256_file(path) == hashes[key] for key, path in files.items())
        with Path(files["results"]).open() as handle:
            rows = list(csv.DictReader(handle))
        expected_rows = [fit_row(record) for record in records]
        artifacts_ok = artifacts_ok and len(rows) == len(expected_rows)
        for actual, expected_row in zip(rows, expected_rows, strict=True):
            for key, value in expected_row.items():
                if value is None:
                    artifacts_ok = artifacts_ok and actual[key] == ""
                elif isinstance(value, (int, float)):
                    artifacts_ok = artifacts_ok and float(actual[key]) == value
                else:
                    artifacts_ok = artifacts_ok and actual[key] == value
    except (OSError, ValueError, KeyError):
        artifacts_ok = False
    add_check(review, "time_dependent_artifacts", "pass" if artifacts_ok else "fail", "Time-dependent result table, search traces and profile figures match recorded hashes and fit values", False)
