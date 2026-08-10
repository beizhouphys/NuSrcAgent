from __future__ import annotations # Codex

import math # cdx
from pathlib import Path # Codex

from agent_core_cdx.schemas_cdx import ConfigError, NormalizedAnalysis # cdx
from analysis_backend_cdx.catalog_cdx import run_catalog_time_integrated # Codex
from analysis_backend_cdx.single_source_cdx import run_single_source_time_integrated # cdx

DR2_SAMPLE = "icecube_public_ps_14yr_dr2" # cdx


def run_likelihood_backend(normalized: NormalizedAnalysis, repo_root: str | Path | None = None) -> dict[str, object]: # Codex
    if normalized.time_mode != "time_integrated": # Codex
        raise ConfigError("likelihood backend Phase 1.1 only supports time_integrated") # Codex
    if normalized.sample == DR2_SAMPLE: # cdx
        try: # cdx
            from analysis_backend_cdx.skyllh_dr2_stacking_cdx import run_dr2_stacking # cdx
        except ModuleNotFoundError as exc: # cdx
            raise ConfigError("the 14-year DR2 backend requires the pinned SkyLLH v26 environment") from exc # cdx
        specs = [{"name": source.name, "ra_rad": source.ra_rad, "dec_rad": source.dec_rad, "w_model": source.weight} for source in normalized.sources] # cdx
        gamma_legacy = float(normalized.spectral_indices[0]) # cdx
        result = run_dr2_stacking(specs, repo_root=repo_root or ".", gamma_mode=normalized.gamma_mode, gamma=abs(gamma_legacy), random_seed=normalized.random_seed, likelihood_mode=normalized.likelihood_mode) # cdx
        backend_name = "skyllh_v26_dr2_spatial_only" if normalized.likelihood_mode == "spatial_only" else "skyllh_v26_dr2_spatial_energy" # cdx
        result.update({"backend": backend_name, "ts": result["TS"], "best_fit_ns": result["ns"], "pre_trial_p": math.erfc((max(float(result["TS"]), 0.0) / 2.0) ** 0.5) / 2.0}) # cdx
        return result # cdx
    if normalized.sample != "icecube_public_ps_10yr": # cdx
        raise ConfigError(f"unsupported data sample: {normalized.sample}") # cdx
    if normalized.analysis_type == "catalog_stacking": # Codex
        return run_catalog_time_integrated(normalized, repo_root=repo_root or ".") # Codex
    if normalized.analysis_type != "single_source": # Codex
        raise ConfigError("unsupported analysis type") # Codex
    if len(normalized.sources) != 1: # Codex
        raise ConfigError("likelihood backend Phase 1.1 expects exactly one source") # Codex
    source = normalized.sources[0] # Codex
    return run_single_source_time_integrated(source.ra_deg, source.dec_deg, repo_root=repo_root or ".", gamma=normalized.spectral_indices[0]) # cdx
