from __future__ import annotations # Codex

import hashlib # Codex
import json # Codex
import os # Codex
import platform # Codex
import shutil # Codex
import subprocess # Codex
from datetime import datetime, timezone # Codex
from pathlib import Path # Codex
from typing import Any # Codex

from agent_core_cdx.schemas_cdx import AnalysisConfig, NormalizedAnalysis, to_clean_dict # cdx
from agent_core_cdx.analysis_outputs_cdx import write_catalog_outputs # Codex
from agent_core_cdx.simple_yaml_cdx import dump_simple_yaml # cdx
from agent_core_cdx.validate_cdx import resolve_path # cdx


def make_run_id() -> str: # Codex
    return "run_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "_cdx" # cdx


def write_run_artifacts(config_path: str | Path, config: AnalysisConfig, normalized: NormalizedAnalysis, result: dict[str, object], repo_root: str | Path | None = None) -> Path: # Codex
    root = Path(repo_root) if repo_root is not None else Path.cwd() # Codex
    run_dir = resolve_path(root, config.outputs.output_root) / make_run_id() # Codex
    run_dir.mkdir(parents=True, exist_ok=False) # Codex
    config_source = Path(config_path) # Codex
    shutil.copy2(config_source, run_dir / f"config.original_cdx{config_source.suffix}") # cdx
    if normalized.analysis_type == "catalog_stacking" and result.get("backend") != "mock_phase0": # Codex
        generated_files = write_catalog_outputs(run_dir, normalized, result, root) # Codex
        result["generated_files"] = generated_files # Codex
        result["figures"] = [generated_files["fig1"], generated_files["fig3"], generated_files["fig4"]] # Codex
        workbook_warning = build_excel_workbook(run_dir, root) # Codex
        if workbook_warning is not None: # Codex
            result.setdefault("warnings", []).append(workbook_warning) # Codex
    report = build_report(normalized, result) # Codex
    write_yaml(run_dir / "config.normalized_cdx.yaml", to_clean_dict(normalized)) # cdx
    write_yaml(run_dir / "report_cdx.yaml", report) # cdx
    write_yaml(run_dir / "provenance_cdx.yaml", build_provenance(config_source, normalized)) # cdx
    write_markdown(run_dir / "report_cdx.md", report) # cdx
    return run_dir # Codex


def build_report(normalized: NormalizedAnalysis, result: dict[str, object]) -> dict[str, Any]: # Codex
    warnings = list(normalized.warnings) # Codex
    backend = str(result.get("backend", "mock_phase0")) # Codex
    extra_warnings = result.get("warnings", []) # Codex
    if isinstance(extra_warnings, list): # Codex
        warnings.extend(str(warning) for warning in extra_warnings) # Codex
    if backend == "mock_phase0": # Codex
        warnings.append("mock backend only; replace with likelihood backend before science use") # Codex
    report_result = {key: value for key, value in result.items() if key not in {"backend", "warnings"} and not key.startswith("_")} # Codex
    return {"schema_version": normalized.schema_version, "run": {"status": "completed", "backend": backend}, "analysis": {"type": normalized.analysis_type, "time_mode": normalized.time_mode, "sample": normalized.sample, "n_sources": len(normalized.sources)}, "result": report_result, "diagnostics": {"n_background_trials": normalized.n_trials, "source_weight_sum": sum(source.weight for source in normalized.sources)}, "warnings": warnings} # Codex


def build_provenance(config_path: Path, normalized: NormalizedAnalysis) -> dict[str, object]: # Codex
    return {"created_at_utc": datetime.now(timezone.utc).isoformat(), "python_version": platform.python_version(), "config_path": str(config_path), "config_sha256": sha256_file(config_path), "normalized_sha256": sha256_text(dump_simple_yaml(to_clean_dict(normalized)))} # Codex


def write_yaml(path: Path, payload: dict[str, Any]) -> None: # Codex
    with path.open("w", encoding="utf-8") as handle: # Codex
        handle.write(dump_simple_yaml(payload)) # Codex


def write_json(path: Path, payload: dict[str, Any]) -> None: # Codex
    with path.open("w", encoding="utf-8") as handle: # Codex
        json.dump(payload, handle, indent=2, sort_keys=True) # Codex
        handle.write("\n") # Codex


def write_markdown(path: Path, report: dict[str, Any]) -> None: # Codex
    lines = ["# HE Neutrino Analysis Report", "", f"Status: `{report['run']['status']}`", f"Backend: `{report['run']['backend']}`", "", "## Result", ""] # Codex
    for key, value in report["result"].items(): # Codex
        lines.append(f"- {key}: `{value}`") # Codex
    lines.extend(["", "## Warnings", ""]) # Codex
    if report["warnings"]: # Codex
        lines.extend([f"- {warning}" for warning in report["warnings"]]) # Codex
    else: # Codex
        lines.append("- None") # Codex
    lines.append("") # Codex
    with path.open("w", encoding="utf-8") as handle: # Codex
        handle.write("\n".join(lines)) # Codex


def sha256_file(path: Path) -> str: # Codex
    digest = hashlib.sha256() # Codex
    with path.open("rb") as handle: # Codex
        for chunk in iter(lambda: handle.read(1024 * 1024), b""): # Codex
            digest.update(chunk) # Codex
    return digest.hexdigest() # Codex


def sha256_text(text: str) -> str: # Codex
    return hashlib.sha256(text.encode("utf-8")).hexdigest() # Codex


def build_excel_workbook(run_dir: Path, repo_root: Path) -> str | None: # Codex
    bundled_root = Path.home()/".cache/codex-runtimes/codex-primary-runtime/dependencies/node" # Codex
    bundled_node = bundled_root/"bin/node" # Codex
    node_executable = os.environ.get("CODEX_NODE_EXECUTABLE") or shutil.which("node") or (str(bundled_node) if bundled_node.exists() else None) # Codex
    if node_executable is None: # Codex
        return "Excel workbook was not generated because no Node.js executable was configured; CSV outputs are available." # Codex
    bundled_modules = bundled_root/"node_modules" # Codex
    dependency_directory = os.environ.get("CODEX_NODE_MODULES") or (str(bundled_modules) if bundled_modules.exists() else None) # Codex
    local_node_modules = repo_root/"node_modules" # Codex
    created_dependency_link = False # Codex
    if not local_node_modules.exists() and dependency_directory is not None: # Codex
        local_node_modules.symlink_to(Path(dependency_directory), target_is_directory=True) # Codex
        created_dependency_link = True # Codex
    builder = repo_root/"build_analysis_workbook_cdx.mjs" # Codex
    payload = run_dir/"workbook_payload_cdx.json" # Codex
    output = run_dir/"analysis_results_cdx.xlsx" # Codex
    qa_directory = run_dir/"workbook_qa_cdx" # Codex
    try: # Codex
        subprocess.run([node_executable, str(builder), str(payload), str(output), str(qa_directory)], cwd=repo_root, check=True, capture_output=True, text=True) # Codex
    except subprocess.CalledProcessError as exc: # Codex
        message = (exc.stderr or exc.stdout or str(exc)).strip() # Codex
        return f"Excel workbook generation failed: {message}" # Codex
    finally: # Codex
        if created_dependency_link: # Codex
            local_node_modules.unlink() # Codex
    return None # Codex
