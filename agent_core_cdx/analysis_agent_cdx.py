from __future__ import annotations # Codex

from dataclasses import dataclass # Codex
from pathlib import Path # Codex
from typing import Any # Codex

from agent_core_cdx.config_io_cdx import load_config_file # Codex
from agent_core_cdx.likelihood_backend_cdx import run_likelihood_backend # Codex
from agent_core_cdx.mock_backend_cdx import run_mock_backend # Codex
from agent_core_cdx.normalize_cdx import normalize_config # Codex
from agent_core_cdx.report_cdx import write_run_artifacts # Codex
from agent_core_cdx.review_cdx import review_run # cdx
from agent_core_cdx.schemas_cdx import ConfigError, NormalizedAnalysis # Codex
from agent_core_cdx.simple_yaml_cdx import dump_simple_yaml # Codex
from agent_core_cdx.validate_cdx import validate_config # Codex


@dataclass # Codex
class AgentRun: # Codex
    config_path: Path # Codex
    normalized: NormalizedAnalysis # Codex
    result: dict[str, Any] # Codex
    run_dir: Path | None # Codex
    review: dict[str, Any] | None = None # cdx


class AnalysisAgent: # Codex
    """Orchestrates validated single-source and catalog-stacking analyses.""" # Codex

    def __init__(self, repo_root: str | Path) -> None: # Codex
        self.repo_root = Path(repo_root).resolve() # Codex

    def prepare_request(self, payload: dict[str, Any], request_path: str | Path) -> Path: # Codex
        path = Path(request_path) # Codex
        if not path.is_absolute(): # Codex
            path = self.repo_root / path # Codex
        path.parent.mkdir(parents=True, exist_ok=True) # Codex
        with path.open("w", encoding="utf-8") as handle: # Codex
            handle.write(dump_simple_yaml(payload)) # Codex
        return path # Codex

    def run(self, config_path: str | Path, backend: str = "likelihood", prepare_only: bool = False) -> AgentRun: # Codex
        path = Path(config_path) # Codex
        if not path.is_absolute(): # Codex
            path = self.repo_root / path # Codex
        config = load_config_file(path) # Codex
        validation = validate_config(config, self.repo_root) # Codex
        if not validation.ok: # Codex
            raise ConfigError("; ".join(validation.errors)) # Codex
        normalized = normalize_config(config, self.repo_root, validation.warnings) # Codex
        if prepare_only: # Codex
            return AgentRun(config_path=path, normalized=normalized, result={}, run_dir=None) # Codex
        result = run_mock_backend(normalized) if backend == "mock" else run_likelihood_backend(normalized, self.repo_root) # Codex
        run_dir = write_run_artifacts(path, config, normalized, result, self.repo_root) # Codex
        review = review_run(str(run_dir), str(self.repo_root), write_artifacts=True) # cdx
        return AgentRun(config_path=path, normalized=normalized, result=result, run_dir=run_dir, review=review) # cdx


def build_single_source_request(name: str, ra_deg: float, dec_deg: float, spectral_index: float, output_root: str, data_sample: str = "icecube_public_ps_14yr_dr2", gamma_mode: str = "fitted", likelihood_mode: str | None = None) -> dict[str, Any]: # cdx
    payload = base_request("single_source", output_root, data_sample, likelihood_mode) # Codex
    payload["source"] = {"name": name, "ra_deg": ra_deg, "dec_deg": dec_deg} # Codex
    payload["stacking"] = {"spectral_indices": [spectral_index], "gamma_mode": gamma_mode, "include_uniform_baseline": False} # cdx
    return payload # Codex


def build_catalog_request(catalog: str | None, sources: list[dict[str, Any]] | None, name_column: str | None, ra_column: str | None, dec_column: str | None, weight_column: str | None, manual_weights: list[float] | None, spectral_indices: list[float], include_uniform_baseline: bool, output_root: str, data_sample: str = "icecube_public_ps_14yr_dr2", gamma_mode: str = "fitted", likelihood_mode: str | None = None) -> dict[str, Any]: # Codex
    payload = base_request("catalog_stacking", output_root, data_sample, likelihood_mode) # Codex
    if catalog is not None: # Codex
        payload["catalog"] = {"file": catalog, "name_column": name_column, "ra_column": ra_column, "dec_column": dec_column} # Codex
    else: # Codex
        payload["sources"] = sources or [] # Codex
    if weight_column is not None: # Codex
        payload["weights"] = {"mode": "column", "column": weight_column, "normalize": True} # Codex
    elif manual_weights is not None: # Codex
        payload["weights"] = {"mode": "manual", "values": manual_weights, "normalize": True} # Codex
    else: # Codex
        payload["weights"] = {"mode": "uniform", "normalize": True} # Codex
    payload["stacking"] = {"spectral_indices": spectral_indices, "gamma_mode": gamma_mode, "include_uniform_baseline": include_uniform_baseline} # Codex
    return payload # Codex


def base_request(analysis_type: str, output_root: str, data_sample: str = "icecube_public_ps_14yr_dr2", likelihood_mode: str | None = None) -> dict[str, Any]: # Codex
    selected_mode = likelihood_mode or ("spatial_energy" if data_sample == "icecube_public_ps_14yr_dr2" else "spatial_only") # cdx
    return {"schema_version": "0.2", "analysis": {"type": analysis_type, "time_mode": "time_integrated", "likelihood_mode": selected_mode}, "data": {"sample": data_sample}, "background": {"method": "ra_scramble", "n_trials": 10000, "random_seed": 12345}, "outputs": {"output_root": output_root}} # Codex
