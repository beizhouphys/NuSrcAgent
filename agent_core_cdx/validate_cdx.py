from __future__ import annotations # Codex

import csv # Codex
from pathlib import Path # Codex

from agent_core_cdx.schemas_cdx import AnalysisConfig, AnalysisType, ValidationResult, WeightMode # cdx


def validate_config(config: AnalysisConfig, repo_root: str | Path | None = None) -> ValidationResult: # Codex
    root = Path(repo_root) if repo_root is not None else Path.cwd() # Codex
    result = ValidationResult() # Codex
    if config.data.sample not in {"icecube_public_ps_14yr_dr2", "icecube_public_ps_10yr"}: # cdx
        result.errors.append("data.sample must be icecube_public_ps_14yr_dr2 or icecube_public_ps_10yr") # cdx
    if config.data.sample == "icecube_public_ps_10yr" and config.stacking.gamma_mode != "fixed": # cdx
        result.errors.append("the 10-year backend currently supports gamma_mode='fixed' only") # cdx
    if config.analysis.likelihood_mode not in {"spatial_energy", "spatial_only"}: # cdx
        result.errors.append("analysis.likelihood_mode must be spatial_energy or spatial_only") # cdx
    if config.data.sample == "icecube_public_ps_10yr" and config.analysis.likelihood_mode != "spatial_only": # cdx
        result.errors.append("the 10-year backend currently supports likelihood_mode='spatial_only' only") # cdx
    if config.analysis.likelihood_mode == "spatial_only" and config.stacking.gamma_mode != "fixed": # cdx
        result.errors.append("spatial-only analysis requires gamma_mode='fixed'; Gamma is used only for acceptance weights") # cdx
    if config.data.sample == "icecube_public_ps_14yr_dr2": # cdx
        if len(config.stacking.spectral_indices) != 1: # cdx
            result.errors.append("the DR2 backend requires exactly one Gamma seed or fixed value") # cdx
        elif config.analysis.likelihood_mode == "spatial_energy" and config.stacking.gamma_mode == "fitted" and not -4.0 <= config.stacking.spectral_indices[0] <= -1.0: # cdx
            result.errors.append("the default DR2 fitted-Gamma range requires a seed in [-4, -1]") # cdx
        elif config.stacking.gamma_mode == "fixed" and not -6.1 <= config.stacking.spectral_indices[0] <= -0.9: # cdx
            result.errors.append("fixed DR2 Gamma must be within the pre-calculated range [-6.1, -0.9]") # cdx
    if config.analysis.time_mode != "time_integrated": # Codex
        result.errors.append("only time_integrated analysis is supported in this Phase 0 scaffold") # Codex
    if config.background.method != "ra_scramble": # Codex
        result.errors.append("only background.method='ra_scramble' is supported now") # Codex
    if config.background.n_trials <= 0: # Codex
        result.errors.append("background.n_trials must be positive") # Codex
    if config.background.n_trials < 1000: # Codex
        result.warnings.append("background.n_trials < 1000 gives poor p-value resolution") # Codex
    if any(gamma >= 0.0 for gamma in config.stacking.spectral_indices): # Codex
        result.errors.append("stacking.spectral_indices must use the negative power-law convention, for example -2.53") # Codex
    if config.analysis.type == AnalysisType.SINGLE_SOURCE: # Codex
        validate_single_source(config, result) # Codex
    if config.analysis.type == AnalysisType.CATALOG_STACKING: # Codex
        validate_catalog(config, result, root) # Codex
    return result # Codex


def validate_single_source(config: AnalysisConfig, result: ValidationResult) -> None: # Codex
    if config.source is None: # Codex
        result.errors.append("source block is required for single_source") # Codex
        return # Codex
    validate_ra_dec(config.source.ra_deg, config.source.dec_deg, "source", result) # Codex


def validate_catalog(config: AnalysisConfig, result: ValidationResult, root: Path) -> None: # Codex
    if (config.catalog is None) == (config.sources is None): # Codex
        result.errors.append("catalog_stacking requires exactly one of catalog or sources") # Codex
        return # Codex
    if config.sources is not None: # Codex
        validate_inline_sources(config, result) # Codex
        return # Codex
    if config.catalog.file is None or config.catalog.ra_column is None or config.catalog.dec_column is None: # Codex
        result.errors.append("catalog.file, catalog.ra_column, and catalog.dec_column are required") # Codex
        return # Codex
    path = resolve_path(root, config.catalog.file) # Codex
    if not path.exists(): # Codex
        result.errors.append(f"catalog file does not exist: {path}") # Codex
        return # Codex
    columns = read_columns(path) # Codex
    for column in [config.catalog.name_column, config.catalog.ra_column, config.catalog.dec_column]: # Codex
        if column is not None and column not in columns: # Codex
            result.errors.append(f"catalog column is missing: {column}") # Codex
    if config.weights.mode == WeightMode.COLUMN and config.weights.column not in columns: # Codex
        result.errors.append(f"weights.column is missing: {config.weights.column}") # Codex
    if config.weights.mode == WeightMode.COLUMN and config.weights.column is None: # Codex
        result.errors.append("weights.column is required when weights.mode='column'") # Codex
    if config.weights.mode == WeightMode.MANUAL: # Codex
        validate_manual_weights(config, count_rows(path), result) # Codex


def validate_inline_sources(config: AnalysisConfig, result: ValidationResult) -> None: # Codex
    if config.sources is None or len(config.sources) == 0: # Codex
        result.errors.append("sources must contain at least one coordinate") # Codex
        return # Codex
    for index, source in enumerate(config.sources, start=1): # Codex
        if source is None: # Codex
            result.errors.append(f"sources[{index}] must be a mapping") # Codex
        else: # Codex
            validate_ra_dec(source.ra_deg, source.dec_deg, f"sources[{index}]", result) # Codex
    if config.weights.mode == WeightMode.COLUMN: # Codex
        result.errors.append("weights.mode='column' requires catalog.file") # Codex
    if config.weights.mode == WeightMode.MANUAL: # Codex
        validate_manual_weights(config, len(config.sources), result) # Codex


def validate_manual_weights(config: AnalysisConfig, n_sources: int, result: ValidationResult) -> None: # Codex
    if config.weights.values is None: # Codex
        result.errors.append("weights.values is required when weights.mode='manual'") # Codex
        return # Codex
    if len(config.weights.values) != n_sources: # Codex
        result.errors.append("weights.values length must match the number of input sources") # Codex
    if any(weight < 0.0 for weight in config.weights.values): # Codex
        result.errors.append("manual weights must be non-negative") # Codex
    if sum(config.weights.values) <= 0.0: # Codex
        result.errors.append("at least one manual weight must be positive") # Codex


def validate_ra_dec(ra_deg: float | None, dec_deg: float | None, label: str, result: ValidationResult) -> None: # Codex
    if ra_deg is None or not 0.0 <= ra_deg < 360.0: # Codex
        result.errors.append(f"{label}.ra_deg must be in [0, 360)") # Codex
    if dec_deg is None or not -90.0 <= dec_deg <= 90.0: # Codex
        result.errors.append(f"{label}.dec_deg must be in [-90, 90]") # Codex


def resolve_path(root: Path, value: str) -> Path: # Codex
    path = Path(value) # Codex
    return path if path.is_absolute() else root / path # Codex


def read_columns(path: Path) -> list[str]: # Codex
    delimiter = "\t" if path.suffix.lower() in {".tsv", ".tab"} else "," # Codex
    with path.open("r", encoding="utf-8", newline="") as handle: # Codex
        reader = csv.DictReader(handle, delimiter=delimiter) # Codex
        return list(reader.fieldnames or []) # Codex


def count_rows(path: Path) -> int: # Codex
    delimiter = "\t" if path.suffix.lower() in {".tsv", ".tab"} else "," # Codex
    with path.open("r", encoding="utf-8", newline="") as handle: # Codex
        return sum(1 for _ in csv.DictReader(handle, delimiter=delimiter)) # Codex
