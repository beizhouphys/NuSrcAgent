from __future__ import annotations

import hashlib
from agent_core.file_cache import sha256_file
import importlib.metadata
import os
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent_core.p_value import local_p_value_estimate
from agent_core.schemas import AnalysisConfig, NormalizedAnalysis, to_clean_dict
from agent_core.analysis_outputs import write_catalog_outputs
from agent_core.analysis_outputs import write_csv
from agent_core.simple_yaml import dump_simple_yaml
from agent_core.validate import resolve_path
from agent_core.environment import _required_paths


def add_significance(result: dict[str, object], gamma_mode: str) -> None:
    """Attach the declared local estimate to each ordinary fit."""
    primary = [result, *(item["fit"] for item in result.get("source_results", []))]
    fits = [*primary, *(child for fit in primary for child in fit.get("flux_upper_limit_fits", []))]
    for fit in fits:
        ts = fit.get("TS", fit.get("ts"))
        if ts is not None:
            fit.update(local_p_value_estimate(ts, fit.get("gamma_mode", gamma_mode)))


def make_run_id() -> str:
    return "run_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ""


def write_run_artifacts(config_path: str | Path, config: AnalysisConfig, normalized: NormalizedAnalysis, result: dict[str, object], repo_root: str | Path | None = None) -> Path:
    add_significance(result, normalized.gamma_mode)
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    run_dir = resolve_path(root, config.outputs.output_root) / make_run_id()
    run_dir.mkdir(parents=True, exist_ok=False)
    config_source = Path(config_path)
    shutil.copy2(config_source, run_dir / f"config.original{config_source.suffix}")
    if normalized.sample == "icecube_public_ps_14yr_dr2" and "TS" in result:
        row = {key: result.get(key) for key in ("TS", "ns", "gamma", "gamma_legacy", "gamma_mode", "n_sources", "pre_trial_p", "pre_trial_significance", "significance_convention", "p_value_dof", "p_value_is_estimate")}
        row["p_value_method"] = result["p_value_method"]
        table = run_dir / "fit_results.csv"
        write_csv(table, list(row), [row])
        result.setdefault("generated_files", {})["fit_results"] = str(table)
    if "source_results" in result:
        rows = []
        for item in result["source_results"]:
            fit = item["fit"]
            rows.append({"source_number": item["source_number"], "source_name": item["source_name"], "ra_deg": item["ra_deg"], "dec_deg": item["dec_deg"], "TS": fit["TS"], "ns": fit["ns"], "gamma_skyllh": fit["gamma"], "gamma_legacy": fit["gamma_legacy"], "gamma_mode": fit["gamma_mode"], "pre_trial_p_approx": fit["pre_trial_p"], "pre_trial_significance": fit["pre_trial_significance"], "significance_convention": fit["significance_convention"], "p_value_method": fit["p_value_method"], "p_value_dof": fit["p_value_dof"], "p_value_is_estimate": fit["p_value_is_estimate"]})
        table = run_dir / "source_results.csv"
        write_csv(table, list(rows[0]) if rows else [], rows)
        result.setdefault("generated_files", {})["source_results"] = str(table)
    if normalized.analysis_type == "catalog_stacking" and result.get("backend") != "mock_phase0" and "_stacking_results" in result:
        generated_files = write_catalog_outputs(run_dir, normalized, result, root)
        result["generated_files"] = generated_files
        result["figures"] = [generated_files["fig1"], generated_files["fig3"], generated_files["fig4"]]
        workbook_warning = build_excel_workbook(run_dir, root)
        if workbook_warning is not None:
            result.setdefault("warnings", []).append(workbook_warning)
    from agent_core.flux_outputs import write_flux_outputs
    write_flux_outputs(run_dir, normalized, result, root)
    report = build_report(normalized, result)
    write_yaml(run_dir / "config.normalized.yaml", to_clean_dict(normalized))
    write_yaml(run_dir / "report.yaml", report)
    write_yaml(run_dir / "provenance.yaml", build_provenance(config_source, normalized, root, config))
    write_markdown(run_dir / "report.md", report)
    return run_dir


def build_report(normalized: NormalizedAnalysis, result: dict[str, object]) -> dict[str, Any]:
    add_significance(result, normalized.gamma_mode)
    warnings = list(normalized.warnings)
    backend = str(result.get("backend", "mock_phase0"))
    extra_warnings = result.get("warnings", [])
    if isinstance(extra_warnings, list):
        warnings.extend(str(warning) for warning in extra_warnings)
    if backend == "mock_phase0":
        warnings.append("mock backend only; replace with likelihood backend before science use")
    report_result = {key: value for key, value in result.items() if key not in {"backend", "warnings"} and not key.startswith("_")}
    if backend != "mock_phase0":
        report_result["significance_calibration"] = "analytic_approximation"
        report_result["post_trial_calibration"] = "unavailable"
        estimate = local_p_value_estimate(0.0, normalized.gamma_mode)
        for key in ("p_value_method", "p_value_dof", "p_value_is_estimate", "significance_convention"):
            report_result.setdefault(key, estimate[key])
        if normalized.sample == "icecube_public_ps_10yr" and normalized.analysis_type == "catalog_stacking":
            report_result["source_scan_post_trial_calibration"] = "analytic_approximation"
    return {"schema_version": normalized.schema_version, "run": {"status": "completed", "backend": backend}, "analysis": {"type": normalized.analysis_type, "time_mode": normalized.time_mode, "likelihood_mode": normalized.likelihood_mode, "sample": normalized.sample, "n_sources": len(normalized.sources), "catalog_operation": normalized.catalog_operation if normalized.analysis_type == "catalog_stacking" else None}, "result": report_result, "diagnostics": {"n_background_trials": 0, "requested_background_trials": normalized.n_trials, "source_weight_sum": sum(source.weight for source in normalized.sources)}, "warnings": list(dict.fromkeys(warnings))}


def build_provenance(config_path: Path, normalized: NormalizedAnalysis, repo_root: Path, config: AnalysisConfig) -> dict[str, object]:
    packages = {}
    for name in ("skyllh", "numpy", "scipy", "astropy", "matplotlib"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    code_paths = [repo_root / "run_agent_wrap.py", *sorted((repo_root / "agent_core").glob("*.py")), *sorted((repo_root / "analysis_backend").glob("*.py"))]
    code_hashes = {str(path.relative_to(repo_root)): sha256_file(path) for path in code_paths if path.is_file()}
    input_paths = [repo_root / path for path in _required_paths(normalized.sample, normalized.likelihood_mode)]
    if config.catalog is not None and config.catalog.file is not None:
        input_paths.append(resolve_path(repo_root, config.catalog.file))
    if normalized.flux_upper_limit_gammas:
        input_paths.extend(sorted((repo_root / "data_input/references/neutrino_spectra").glob("*")))
    input_hashes = {str(path): sha256_file(path) for path in input_paths if path.is_file()}
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_root, capture_output=True, text=True)
        commit_id = commit.stdout.strip() if commit.returncode == 0 else None
    except OSError:
        commit_id = None
    return {"created_at_utc": datetime.now(timezone.utc).isoformat(), "python_version": platform.python_version(), "packages": packages, "config_path": str(config_path), "config_sha256": sha256_file(config_path), "normalized_sha256": sha256_text(dump_simple_yaml(to_clean_dict(normalized))), "git_commit": commit_id, "code_sha256": code_hashes, "input_sha256": input_hashes, "random_seed": normalized.random_seed}


def write_yaml(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        handle.write(dump_simple_yaml(payload))


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = ["# HE Neutrino Analysis Report", "", f"Execution: `{report['run']['status']}`", f"Backend: `{report['run']['backend']}`", "Review: [review.md](review.md) (determines scientific completion status)", "", "## Analysis", ""]
    lines.extend(f"- {key}: `{value}`" for key, value in report["analysis"].items() if value is not None)
    lines.extend(["", "## Result", ""])
    for key, value in report["result"].items():
        if not isinstance(value, (dict, list)):
            lines.append(f"- {key}: `{value}`")
    source_results = report["result"].get("source_results", [])
    if source_results:
        lines.extend(["", "## Independent source fits", "", "Full table: [source_results.csv](source_results.csv)", "", "| Source number | Source | TS | ns | Gamma (SkyLLH) | Local p (estimate) | Significance (one-sided sigma, estimate) |", "| --- | --- | --- | --- | --- | --- | --- | "])
        for item in source_results[:20]:
            fit = item["fit"]
            name = str(item["source_name"]).replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {item['source_number']} | {name} | {fit['TS']:.8g} | {fit['ns']:.8g} | {fit['gamma']:.8g} | {fit['pre_trial_p']:.8g} | {fit['pre_trial_significance']:.8g} |")
        if len(source_results) > 20:
            lines.extend(["", f"Showing the first 20 of {len(source_results)} sources; the CSV contains every source."])
    flux_entries = [(report["result"], "Source")] if not source_results else [(item["fit"], item["source_name"]) for item in source_results]
    if any(fit.get("flux_upper_limit_fits") or fit.get("flux_upper_limit") for fit, _ in flux_entries):
        lines.extend(["", "## Fixed-spectrum flux upper limits", "",
            "Separate constrained fits for each power-law spectrum; the primary fit above keeps its requested Gamma mode.", "",
            "| Source | Fixed Gamma (E^-Gamma) | ns upper limit | phi100 upper limit [GeV^-1 cm^-2 s^-1] | E^2 dPhi/dE at 100 TeV [TeV cm^-2 s^-1] |",
            "| --- | --- | --- | --- | --- |"])
        flux_links = []
        for fit, name in flux_entries[:20]:
            limits = [child["flux_upper_limit"] for child in fit.get("flux_upper_limit_fits", [])]
            if fit.get("flux_upper_limit"):
                limits.append(fit["flux_upper_limit"])
            safe_name = str(name).replace("|", "\\|").replace("\n", " ")
            for limit in limits:
                lines.append(f"| {safe_name} | {limit['gamma']:g} | {limit['ns_upper_limit']:.8g} | {limit['phi0_upper_limit']:.8g} | {limit['e2_dphi_de_upper_limit_tev_cm2_s']:.8g} |")
            for key, value in fit.get("generated_files", {}).items():
                if key.startswith("flux_") or key == "spectrum_curves":
                    flux_links.append(f"[{name}: {key}]({value})")
        lines.extend(["", *flux_links])
        lines.extend(["", "Confidence level and threshold are recorded for every limit. The default is one-sided 95%, 2 Delta ln L = 2.705543454. These are preliminary asymptotic estimates: coverage is unvalidated and detector/PDF systematic uncertainties are excluded. The flux is nu_mu+anti_nu_mu at a 100 TeV pivot; no sr^-1 or all-flavor multiplier is used. Each plotted source curve is one complete power-law hypothesis, not an independent limit in each energy bin. Diffuse references are integrated over the full sky with 4*pi sr and have their own published confidence bands."])
    lines.extend(["", "## Artifacts", "", "- [Complete numeric report](report.yaml)", "- [Configuration](config.normalized.yaml)", "- [Provenance](provenance.yaml)"])
    for key, value in report["result"].get("generated_files", {}).items():
        artifact = Path(value)
        if not artifact.is_absolute():
            artifact = path.parent / artifact if (path.parent / artifact).is_file() else artifact.resolve()
        lines.append(f"- [{key}]({artifact})" if artifact.is_file() else f"- {key}: `{value}`")
    lines.extend(["", "Significance is the one-sided Gaussian equivalent of the reported p-value. Local p-values and significances are estimates: fitted Gamma uses half-chi-square dof=2, fixed Gamma uses dof=1. At TS=0 the reporting convention is p=0.5 and Z=0; empirical and catalog-global calibration are unavailable without the corresponding background trials. This method description does not by itself create a review warning."])
    lines.extend(["", "## Background trials", "", f"- Requested: {report['diagnostics']['requested_background_trials']}", f"- Executed by this workflow: {report['diagnostics']['n_background_trials']}"])
    lines.extend(["", "## Backend warnings", "", "Fit-quality and other material warnings are listed in [review.md](review.md).", ""])
    if report["warnings"]:
        lines.extend([f"- {warning}" for warning in report["warnings"]])
    else:
        lines.append("- None")
    lines.append("")
    with path.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_excel_workbook(run_dir: Path, repo_root: Path) -> str | None:
    node_executable = os.environ.get("CODEX_NODE_EXECUTABLE") or shutil.which("node")
    if node_executable is None:
        return "Excel workbook was not generated because no Node.js executable was configured; CSV outputs are available."
    if not (repo_root/"node_modules/@oai/artifact-tool").exists():
        return "Excel workbook was not generated because the optional project-local workbook dependency is absent; CSV outputs are available."
    builder = repo_root/"tools/build_analysis_workbook.mjs"
    payload = run_dir/"workbook_payload.json"
    output = run_dir/"analysis_results.xlsx"
    qa_directory = run_dir/"workbook_qa"
    try:
        subprocess.run([node_executable, str(builder), str(payload), str(output), str(qa_directory)], cwd=repo_root, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        message = (exc.stderr or exc.stdout or str(exc)).strip()
        return f"Excel workbook generation failed: {message}"
    return None
