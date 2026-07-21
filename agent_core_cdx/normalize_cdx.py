from __future__ import annotations # Codex

import csv # Codex
import math # Codex
from pathlib import Path # Codex

from agent_core_cdx.schemas_cdx import AnalysisConfig, AnalysisType, ConfigError, NormalizedAnalysis, NormalizedSource, WeightMode # cdx
from agent_core_cdx.validate_cdx import resolve_path # cdx


def normalize_config(config: AnalysisConfig, repo_root: str | Path | None = None, warnings: list[str] | None = None) -> NormalizedAnalysis: # Codex
    root = Path(repo_root) if repo_root is not None else Path.cwd() # Codex
    if config.analysis.type == AnalysisType.SINGLE_SOURCE: # Codex
        sources = normalize_single_source(config) # Codex
    else: # Codex
        sources = normalize_source_set(config, root) # Codex
    return NormalizedAnalysis(schema_version=config.schema_version, analysis_type=config.analysis.type.value, time_mode=config.analysis.time_mode, sample=config.data.sample, sources=sources, spectral_indices=list(config.stacking.spectral_indices), include_uniform_baseline=config.stacking.include_uniform_baseline, background_method=config.background.method, n_trials=config.background.n_trials, random_seed=config.background.random_seed, warnings=list(warnings or [])) # Codex


def normalize_single_source(config: AnalysisConfig) -> list[NormalizedSource]: # Codex
    if config.source is None or config.source.ra_deg is None or config.source.dec_deg is None: # Codex
        raise ConfigError("source.ra_deg and source.dec_deg are required") # Codex
    return [make_source(1, config.source.name or "source_0001", config.source.ra_deg, config.source.dec_deg, 1.0, {})] # Codex


def normalize_source_set(config: AnalysisConfig, root: Path) -> list[NormalizedSource]: # Codex
    if config.catalog is not None: # Codex
        return normalize_catalog(config, root) # Codex
    return normalize_inline_sources(config) # Codex


def normalize_catalog(config: AnalysisConfig, root: Path) -> list[NormalizedSource]: # Codex
    if config.catalog is None or config.catalog.file is None or config.catalog.ra_column is None or config.catalog.dec_column is None: # Codex
        raise ConfigError("catalog.file, catalog.ra_column, and catalog.dec_column are required") # Codex
    rows = read_rows(resolve_path(root, config.catalog.file)) # Codex
    raw_weights = get_raw_weights(config, rows) # Codex
    weights = normalize_weights(raw_weights) if config.weights.normalize else raw_weights # Codex
    sources = [] # Codex
    for index, row in enumerate(rows): # Codex
        name = row.get(config.catalog.name_column or "", "") or f"source_{index + 1:04d}" # Codex
        ra_deg = float(row[config.catalog.ra_column]) # Codex
        dec_deg = float(row[config.catalog.dec_column]) # Codex
        coordinate_columns = {config.catalog.name_column, config.catalog.ra_column, config.catalog.dec_column} # Codex
        metadata = {key: value for key, value in row.items() if key not in coordinate_columns} # Codex
        sources.append(make_source(index + 1, name, ra_deg, dec_deg, weights[index], metadata)) # Codex
    return sources # Codex


def normalize_inline_sources(config: AnalysisConfig) -> list[NormalizedSource]: # Codex
    if config.sources is None: # Codex
        raise ConfigError("sources list is required when catalog.file is not provided") # Codex
    rows = [{"name": source.name or f"source_{index + 1:04d}", "ra_deg": source.ra_deg, "dec_deg": source.dec_deg} for index, source in enumerate(config.sources)] # Codex
    raw_weights = get_inline_raw_weights(config, len(rows)) # Codex
    weights = normalize_weights(raw_weights) if config.weights.normalize else raw_weights # Codex
    return [make_source(index + 1, str(row["name"]), float(row["ra_deg"]), float(row["dec_deg"]), weights[index], dict(row)) for index, row in enumerate(rows)] # Codex


def read_rows(path: Path) -> list[dict[str, str]]: # Codex
    delimiter = "\t" if path.suffix.lower() in {".tsv", ".tab"} else "," # Codex
    with path.open("r", encoding="utf-8", newline="") as handle: # Codex
        return [dict(row) for row in csv.DictReader(handle, delimiter=delimiter)] # Codex


def get_raw_weights(config: AnalysisConfig, rows: list[dict[str, str]]) -> list[float]: # Codex
    if config.weights.mode == WeightMode.UNIFORM: # Codex
        return [1.0 for _ in rows] # Codex
    if config.weights.mode == WeightMode.COLUMN: # Codex
        if config.weights.column is None: # Codex
            raise ConfigError("weights.column is required") # Codex
        return [float(row[config.weights.column]) for row in rows] # Codex
    return get_manual_weights(config, len(rows)) # Codex


def get_inline_raw_weights(config: AnalysisConfig, n_sources: int) -> list[float]: # Codex
    if config.weights.mode == WeightMode.UNIFORM: # Codex
        return [1.0 for _ in range(n_sources)] # Codex
    if config.weights.mode == WeightMode.COLUMN: # Codex
        raise ConfigError("weights.mode='column' requires catalog.file") # Codex
    return get_manual_weights(config, n_sources) # Codex


def get_manual_weights(config: AnalysisConfig, n_sources: int) -> list[float]: # Codex
    if config.weights.values is None: # Codex
        raise ConfigError("weights.values is required when weights.mode='manual'") # Codex
    if len(config.weights.values) != n_sources: # Codex
        raise ConfigError("weights.values length must match the number of input sources") # Codex
    return list(config.weights.values) # Codex


def normalize_weights(weights: list[float]) -> list[float]: # Codex
    if any(weight < 0.0 for weight in weights): # Codex
        raise ConfigError("catalog weights must be non-negative") # Codex
    total = sum(weights) # Codex
    if total <= 0.0: # Codex
        raise ConfigError("at least one catalog weight must be positive") # Codex
    return [weight / total for weight in weights] # Codex


def make_source(source_number: int, name: str, ra_deg: float, dec_deg: float, weight: float, metadata: dict[str, object]) -> NormalizedSource: # Codex
    return NormalizedSource(source_number=source_number, name=name, ra_deg=ra_deg, dec_deg=dec_deg, ra_rad=math.radians(ra_deg), dec_rad=math.radians(dec_deg), weight=weight, metadata=metadata) # Codex
