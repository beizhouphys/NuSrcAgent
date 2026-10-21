from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from time import monotonic
from agent_core.cpu import execution_metadata, positive_worker_count
from agent_core.stage_progress import StageProgress
from agent_core.schemas import to_clean_dict

from agent_core.config_io import load_config_file
from agent_core.likelihood_backend import run_likelihood_backend
from agent_core.normalize import normalize_config
from agent_core.report import write_run_artifacts
from agent_core.review import review_run
from agent_core.schemas import ConfigError, NormalizedAnalysis
from agent_core.simple_yaml import dump_simple_yaml
from agent_core.validate import validate_config


@dataclass
class AgentRun:
    config_path: Path
    normalized: NormalizedAnalysis
    result: dict[str, Any]
    run_dir: Path | None
    review: dict[str, Any] | None = None


class AnalysisAgent:
    """Orchestrates validated single-source and catalog-stacking analyses."""

    def __init__(self, repo_root: str | Path) -> None:
        self.repo_root = Path(repo_root).resolve()

    def prepare_request(self, payload: dict[str, Any], request_path: str | Path) -> Path:
        path = Path(request_path)
        if not path.is_absolute():
            path = self.repo_root / path
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            handle.write(dump_simple_yaml(payload))
        return path
    def run(self, config_path: str | Path, backend: str = "likelihood", prepare_only: bool = False, stacking_primary=None, workers: int = 1) -> AgentRun:
        workers = positive_worker_count(workers)
        path = Path(config_path)
        if not path.is_absolute():
            path = self.repo_root / path
        started = monotonic()
        config = load_config_file(path)
        validation = validate_config(config, self.repo_root)
        if not validation.ok:
            raise ConfigError("; ".join(validation.errors))
        normalized = normalize_config(config, self.repo_root, validation.warnings)
        if prepare_only:
            return AgentRun(config_path=path, normalized=normalized, result={}, run_dir=None)
        if backend != "likelihood":
            raise ConfigError("unsupported analysis backend: %s" % backend)
        plan = StageProgress(self.repo_root, to_clean_dict(normalized),
                             'flux' if stacking_primary is not None else 'primary', started=started)
        try:
            with plan.phase('request preparation'):
                pass  # Includes validation/normalization since method entry.
            with plan.phase('analysis'):
                result = (run_likelihood_backend(normalized, self.repo_root, workers=workers) if stacking_primary is None
                          else run_likelihood_backend(normalized, self.repo_root, stacking_primary=stacking_primary, workers=workers))
                result["execution"] = execution_metadata(workers, normalized)
            with plan.phase('output generation'):
                run_dir = write_run_artifacts(path, config, normalized, result, self.repo_root)
            with plan.phase('scientific review'):
                review = review_run(str(run_dir), str(self.repo_root), write_artifacts=True)
            plan.finish(run_dir)
        finally:
            plan.abort()
        return AgentRun(config_path=path, normalized=normalized, result=result, run_dir=run_dir, review=review)


def build_single_source_request(name: str, ra_deg: float, dec_deg: float, spectral_index: float, output_root: str, data_sample: str = "icecube_public_ps_14yr_dr2", gamma_mode: str = "fitted", likelihood_mode: str | None = None, event_abs_dec_max_deg: float | None = None, event_dec_min_deg: float | None = None, event_dec_max_deg: float | None = None) -> dict[str, Any]:
    payload = base_request("single_source", output_root, data_sample, likelihood_mode)
    payload["background"]["event_abs_dec_max_deg"] = event_abs_dec_max_deg
    payload["background"]["event_dec_min_deg"] = event_dec_min_deg
    payload["background"]["event_dec_max_deg"] = event_dec_max_deg
    payload["source"] = {"name": name, "ra_deg": ra_deg, "dec_deg": dec_deg}
    payload["stacking"] = {"spectral_indices": [spectral_index], "gamma_mode": gamma_mode, "include_uniform_baseline": False}
    return payload


def build_catalog_request(catalog: str | None, sources: list[dict[str, Any]] | None, name_column: str | None, ra_column: str | None, dec_column: str | None, weight_column: str | None, manual_weights: list[float] | None, spectral_indices: list[float], include_uniform_baseline: bool, output_root: str, data_sample: str = "icecube_public_ps_14yr_dr2", gamma_mode: str = "fitted", likelihood_mode: str | None = None, built_in_catalog: str | None = None, event_abs_dec_max_deg: float | None = None, event_dec_min_deg: float | None = None, event_dec_max_deg: float | None = None, catalog_operation: str | None = None) -> dict[str, Any]:
    payload = base_request("catalog_stacking", output_root, data_sample, likelihood_mode)
    if catalog_operation is not None:
        payload["analysis"]["catalog_operation"] = catalog_operation
    payload["background"]["event_abs_dec_max_deg"] = event_abs_dec_max_deg
    payload["background"]["event_dec_min_deg"] = event_dec_min_deg
    payload["background"]["event_dec_max_deg"] = event_dec_max_deg
    if built_in_catalog is not None:
        payload["catalog"] = {"builtin": built_in_catalog, "name_column": name_column, "ra_column": ra_column, "dec_column": dec_column}
    elif catalog is not None:
        payload["catalog"] = {"file": catalog, "name_column": name_column, "ra_column": ra_column, "dec_column": dec_column}
    else:
        payload["sources"] = sources or []
    if weight_column is not None:
        payload["weights"] = {"mode": "column", "column": weight_column, "normalize": True}
    elif manual_weights is not None:
        payload["weights"] = {"mode": "manual", "values": manual_weights, "normalize": True}
    else:
        payload["weights"] = {"mode": "uniform", "normalize": True}
    payload["stacking"] = {"spectral_indices": spectral_indices, "gamma_mode": gamma_mode, "include_uniform_baseline": include_uniform_baseline}
    return payload


def base_request(analysis_type: str, output_root: str, data_sample: str = "icecube_public_ps_14yr_dr2", likelihood_mode: str | None = None) -> dict[str, Any]:
    selected_mode = likelihood_mode or ("spatial_energy" if data_sample == "icecube_public_ps_14yr_dr2" else "spatial_only")
    return {"schema_version": "0.2", "analysis": {"type": analysis_type, "time_mode": "time_integrated", "likelihood_mode": selected_mode}, "data": {"sample": data_sample}, "background": {"method": "ra_scramble", "n_trials": 10000, "random_seed": 12345}, "outputs": {"output_root": output_root}}
