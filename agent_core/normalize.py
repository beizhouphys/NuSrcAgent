from __future__ import annotations

import math
from pathlib import Path

from analysis_backend.sources import load_builtin_catalog, read_source_catalog
from agent_core.schemas import AnalysisConfig, AnalysisType, ConfigError, NormalizedAnalysis, NormalizedSource, WeightMode
from agent_core.validate import resolve_path


def normalize_config(config: AnalysisConfig, repo_root: str | Path | None = None, warnings: list[str] | None = None) -> NormalizedAnalysis:
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    if config.analysis.type == AnalysisType.SINGLE_SOURCE:
        sources = normalize_single_source(config)
    else:
        sources = normalize_source_set(config, root)
    return NormalizedAnalysis(schema_version=config.schema_version, analysis_type=config.analysis.type.value, time_mode=config.analysis.time_mode, likelihood_mode=config.analysis.likelihood_mode, sample=config.data.sample, sources=sources, spectral_indices=list(config.stacking.spectral_indices), gamma_mode=config.stacking.gamma_mode, include_uniform_baseline=config.stacking.include_uniform_baseline, background_method=config.background.method, n_trials=config.background.n_trials, random_seed=config.background.random_seed, event_abs_dec_max_deg=config.background.event_abs_dec_max_deg, event_dec_min_deg=config.background.event_dec_min_deg, event_dec_max_deg=config.background.event_dec_max_deg, catalog_operation=config.analysis.catalog_operation, warnings=list(warnings or []))


def normalize_single_source(config: AnalysisConfig) -> list[NormalizedSource]:
    if config.source is None or config.source.ra_deg is None or config.source.dec_deg is None:
        raise ConfigError("source.ra_deg and source.dec_deg are required")
    return [make_source(1, config.source.name or "source_0001", config.source.ra_deg, config.source.dec_deg, 1.0, {})]


def normalize_source_set(config: AnalysisConfig, root: Path) -> list[NormalizedSource]:
    if config.catalog is not None:
        return normalize_catalog(config, root)
    return normalize_inline_sources(config)


def normalize_catalog(config: AnalysisConfig, root: Path) -> list[NormalizedSource]:
    if config.catalog is None or config.catalog.ra_column is None or config.catalog.dec_column is None:
        raise ConfigError("catalog input, catalog.ra_column, and catalog.dec_column are required")
    if config.catalog.builtin is not None:
        rows = load_builtin_catalog(config.catalog.builtin, root)
    elif config.catalog.file is not None:
        rows = read_rows(resolve_path(root, config.catalog.file))
    else:
        raise ConfigError("catalog requires exactly one of file or builtin")
    raw_weights = get_raw_weights(config, rows)
    weights = normalize_weights(raw_weights) if config.weights.normalize else raw_weights
    sources = []
    for index, row in enumerate(rows):
        name = row.get(config.catalog.name_column or "", "") or f"source_{index + 1:04d}"
        ra_deg = float(row[config.catalog.ra_column])
        dec_deg = float(row[config.catalog.dec_column])
        coordinate_columns = {config.catalog.name_column, config.catalog.ra_column, config.catalog.dec_column}
        metadata = {key: value for key, value in row.items() if key not in coordinate_columns}
        sources.append(make_source(index + 1, name, ra_deg, dec_deg, weights[index], metadata))
    return sources


def normalize_inline_sources(config: AnalysisConfig) -> list[NormalizedSource]:
    if config.sources is None:
        raise ConfigError("sources list is required when catalog.file is not provided")
    rows = [{"name": source.name or f"source_{index + 1:04d}", "ra_deg": source.ra_deg, "dec_deg": source.dec_deg} for index, source in enumerate(config.sources)]
    raw_weights = get_inline_raw_weights(config, len(rows))
    weights = normalize_weights(raw_weights) if config.weights.normalize else raw_weights
    return [make_source(index + 1, str(row["name"]), float(row["ra_deg"]), float(row["dec_deg"]), weights[index], dict(row)) for index, row in enumerate(rows)]


def read_rows(path: Path) -> list[dict[str, str]]:
    rows, _ = read_source_catalog(path)
    return rows


def get_raw_weights(config: AnalysisConfig, rows: list[dict[str, str]]) -> list[float]:
    if config.weights.mode == WeightMode.UNIFORM:
        return [1.0 for _ in rows]
    if config.weights.mode == WeightMode.COLUMN:
        if config.weights.column is None:
            raise ConfigError("weights.column is required")
        return [float(row[config.weights.column]) for row in rows]
    return get_manual_weights(config, len(rows))


def get_inline_raw_weights(config: AnalysisConfig, n_sources: int) -> list[float]:
    if config.weights.mode == WeightMode.UNIFORM:
        return [1.0 for _ in range(n_sources)]
    if config.weights.mode == WeightMode.COLUMN:
        raise ConfigError("weights.mode='column' requires catalog.file")
    return get_manual_weights(config, n_sources)


def get_manual_weights(config: AnalysisConfig, n_sources: int) -> list[float]:
    if config.weights.values is None:
        raise ConfigError("weights.values is required when weights.mode='manual'")
    if len(config.weights.values) != n_sources:
        raise ConfigError("weights.values length must match the number of input sources")
    return list(config.weights.values)


def normalize_weights(weights: list[float]) -> list[float]:
    if any(weight < 0.0 for weight in weights):
        raise ConfigError("catalog weights must be non-negative")
    total = sum(weights)
    if total <= 0.0:
        raise ConfigError("at least one catalog weight must be positive")
    return [weight / total for weight in weights]


def make_source(source_number: int, name: str, ra_deg: float, dec_deg: float, weight: float, metadata: dict[str, object]) -> NormalizedSource:
    return NormalizedSource(source_number=source_number, name=name, ra_deg=ra_deg, dec_deg=dec_deg, ra_rad=math.radians(ra_deg), dec_rad=math.radians(dec_deg), weight=weight, metadata=metadata)
