from __future__ import annotations # Codex

from pathlib import Path # Codex

from agent_core_cdx.schemas_cdx import ConfigError, NormalizedAnalysis # cdx
from likelihood_backend_catalog_cdx import run_catalog_time_integrated # Codex
from likelihood_backend_single_source_cdx import run_single_source_time_integrated # cdx


def run_likelihood_backend(normalized: NormalizedAnalysis, repo_root: str | Path | None = None) -> dict[str, object]: # Codex
    if normalized.time_mode != "time_integrated": # Codex
        raise ConfigError("likelihood backend Phase 1.1 only supports time_integrated") # Codex
    if normalized.analysis_type == "catalog_stacking": # Codex
        return run_catalog_time_integrated(normalized, repo_root=repo_root or ".") # Codex
    if normalized.analysis_type != "single_source": # Codex
        raise ConfigError("unsupported analysis type") # Codex
    if len(normalized.sources) != 1: # Codex
        raise ConfigError("likelihood backend Phase 1.1 expects exactly one source") # Codex
    source = normalized.sources[0] # Codex
    return run_single_source_time_integrated(source.ra_deg, source.dec_deg, repo_root=repo_root or ".", gamma=normalized.spectral_indices[0]) # cdx
