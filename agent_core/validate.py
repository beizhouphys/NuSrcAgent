from __future__ import annotations

import math
from pathlib import Path

from analysis_backend.sources import BUILTIN_CATALOG_NAMES, load_builtin_catalog, read_source_catalog
from agent_core.schemas import AnalysisConfig, AnalysisType, ValidationResult, WeightMode


def validate_config(config: AnalysisConfig, repo_root: str | Path | None = None) -> ValidationResult:
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    result = ValidationResult()
    confidence = config.analysis.flux_upper_limit_cl
    limit_gammas = config.analysis.flux_upper_limit_gammas
    if confidence is not None:
        if not math.isfinite(confidence) or not 0.5 < confidence < 1.0:
            result.errors.append("analysis.flux_upper_limit_cl must be finite and in (0.5, 1)")
        if config.data.sample != "icecube_public_ps_14yr_dr2" or config.analysis.likelihood_mode != "spatial_energy":
            result.errors.append("Flux upper limits require DR2 spatial+energy analysis")
        if config.analysis.type == AnalysisType.CATALOG_STACKING and (not limit_gammas or config.analysis.catalog_operation == "stack"):
            result.errors.append("Catalog flux upper limits require individual-source scan hypotheses")
        if not limit_gammas and config.stacking.gamma_mode != "fixed":
            result.errors.append("A scalar flux upper limit requires fixed Gamma")
    if limit_gammas:
        if confidence is None or len(set(limit_gammas)) != len(limit_gammas) or any(not math.isfinite(g) or not -6.1 <= g <= -0.9 for g in limit_gammas):
            result.errors.append("Flux upper-limit Gamma hypotheses require a confidence level and unique negative exponents in [-6.1, -0.9]")
    if config.analysis.catalog_operation not in {"stack", "scan", "scan_and_stack"}:
        result.errors.append("analysis.catalog_operation must be stack, scan, or scan_and_stack")
    if config.data.sample == "icecube_public_ps_10yr" and config.analysis.catalog_operation != "scan_and_stack":
        result.errors.append("the DR1 catalog workflow remains scan_and_stack")
    if config.analysis.catalog_operation == "scan" and config.weights.mode != WeightMode.UNIFORM:
        result.errors.append("scan-only fits each source independently and does not accept stacking weights")
    if config.data.sample not in {"icecube_public_ps_14yr_dr2", "icecube_public_ps_10yr"}:
        result.errors.append("data.sample must be icecube_public_ps_14yr_dr2 or icecube_public_ps_10yr")
    if config.data.sample == "icecube_public_ps_10yr" and config.stacking.gamma_mode != "fixed":
        result.errors.append("the 10-year backend currently supports gamma_mode='fixed' only")
    if config.analysis.likelihood_mode not in {"spatial_energy", "spatial_only"}:
        result.errors.append("analysis.likelihood_mode must be spatial_energy or spatial_only")
    if config.data.sample == "icecube_public_ps_10yr" and config.analysis.likelihood_mode != "spatial_only":
        result.errors.append("the 10-year backend currently supports likelihood_mode='spatial_only' only")
    if config.analysis.likelihood_mode == "spatial_only" and config.stacking.gamma_mode != "fixed":
        result.errors.append("spatial-only analysis requires gamma_mode='fixed'; Gamma is used only for acceptance weights")
    if config.data.sample == "icecube_public_ps_14yr_dr2":
        if len(config.stacking.spectral_indices) != 1:
            result.errors.append("the DR2 backend requires exactly one Gamma seed or fixed value")
        elif config.analysis.likelihood_mode == "spatial_energy" and config.stacking.gamma_mode == "fitted" and not -4.0 <= config.stacking.spectral_indices[0] <= -1.0:
            result.errors.append("the default DR2 fitted-Gamma range requires a seed in [-4, -1]")
        elif config.stacking.gamma_mode == "fixed" and not -6.1 <= config.stacking.spectral_indices[0] <= -0.9:
            result.errors.append("fixed DR2 Gamma must be within the pre-calculated range [-6.1, -0.9]")
    if config.analysis.time_mode != "time_integrated":
        result.errors.append("only time_integrated analysis is supported in this Phase 0 scaffold")
    if config.background.method != "ra_scramble":
        result.errors.append("only background.method='ra_scramble' is supported now")
    if config.background.n_trials <= 0:
        result.errors.append("background.n_trials must be positive")
    event_cut = config.background.event_abs_dec_max_deg
    if event_cut is not None and (not math.isfinite(event_cut) or not 0.0 < event_cut <= 90.0):
        result.errors.append("background.event_abs_dec_max_deg must be finite and in (0, 90]")
    if event_cut is not None and config.data.sample != "icecube_public_ps_14yr_dr2":
        result.errors.append("background.event_abs_dec_max_deg is currently supported only for the 14-year DR2 backend")
    event_bounds = [value for value in (config.background.event_dec_min_deg, config.background.event_dec_max_deg) if value is not None]
    if any(not math.isfinite(value) or not -90.0 <= value <= 90.0 for value in event_bounds):
        result.errors.append("background event declination bounds must be finite and in [-90, 90]")
    if config.background.event_dec_min_deg is not None and config.background.event_dec_max_deg is not None and config.background.event_dec_min_deg >= config.background.event_dec_max_deg:
        result.errors.append("background.event_dec_min_deg must be less than background.event_dec_max_deg")
    if event_cut is not None and event_bounds:
        result.errors.append("use either background.event_abs_dec_max_deg or asymmetric event declination bounds, not both")
    if event_bounds and config.data.sample != "icecube_public_ps_14yr_dr2":
        result.errors.append("background event declination bounds are currently supported only for the 14-year DR2 backend")
    window = config.background.source_dec_window_deg
    if window is not None:
        if not math.isfinite(window) or not 20.0 <= window <= 180.0:
            result.errors.append("background.source_dec_window_deg must be finite and in [20, 180]")
        if config.data.sample != "icecube_public_ps_14yr_dr2":
            result.errors.append("Adaptive source windows require the 14-year DR2 sample")
        if event_cut is not None or event_bounds:
            result.errors.append("Adaptive source windows cannot be combined with explicit event cuts")
        if config.analysis.type == AnalysisType.CATALOG_STACKING and config.analysis.catalog_operation == "stack":
            result.errors.append("Adaptive source windows apply to individual fits, not catalog stacking")
    if any(gamma >= 0.0 for gamma in config.stacking.spectral_indices):
        result.errors.append("stacking.spectral_indices must use the negative power-law convention, for example -2.53")
    if config.analysis.type == AnalysisType.SINGLE_SOURCE:
        validate_single_source(config, result)
    if config.analysis.type == AnalysisType.CATALOG_STACKING:
        validate_catalog(config, result, root)
    return result


def validate_single_source(config: AnalysisConfig, result: ValidationResult) -> None:
    if config.source is None:
        result.errors.append("source block is required for single_source")
        return
    validate_ra_dec(config.source.ra_deg, config.source.dec_deg, "source", result)


def validate_catalog(config: AnalysisConfig, result: ValidationResult, root: Path) -> None:
    if (config.catalog is None) == (config.sources is None):
        result.errors.append("catalog_stacking requires exactly one of catalog or sources")
        return
    if config.sources is not None:
        validate_inline_sources(config, result)
        return
    if config.catalog.ra_column is None or config.catalog.dec_column is None:
        result.errors.append("catalog.ra_column and catalog.dec_column are required")
        return
    if (config.catalog.file is None) == (config.catalog.builtin is None):
        result.errors.append("catalog requires exactly one of file or builtin")
        return
    if config.catalog.builtin is not None:
        if config.catalog.builtin not in BUILTIN_CATALOG_NAMES:
            result.errors.append(f"unknown built-in source catalog: {config.catalog.builtin}")
            return
        rows = load_builtin_catalog(config.catalog.builtin, root)
        columns = list(rows[0])
        n_sources = len(rows)
    else:
        path = resolve_path(root, config.catalog.file)
        if not path.exists():
            result.errors.append(f"catalog file does not exist: {path}")
            return
        columns = read_columns(path)
        n_sources = count_rows(path)
    for column in [config.catalog.name_column, config.catalog.ra_column, config.catalog.dec_column]:
        if column is not None and column not in columns:
            result.errors.append(f"catalog column is missing: {column}")
    if config.weights.mode == WeightMode.COLUMN and config.weights.column not in columns:
        result.errors.append(f"weights.column is missing: {config.weights.column}")
    if config.weights.mode == WeightMode.COLUMN and config.weights.column is None:
        result.errors.append("weights.column is required when weights.mode='column'")
    if config.weights.mode == WeightMode.MANUAL:
        validate_manual_weights(config, n_sources, result)


def validate_inline_sources(config: AnalysisConfig, result: ValidationResult) -> None:
    if config.sources is None or len(config.sources) == 0:
        result.errors.append("sources must contain at least one coordinate")
        return
    for index, source in enumerate(config.sources, start=1):
        if source is None:
            result.errors.append(f"sources[{index}] must be a mapping")
        else:
            validate_ra_dec(source.ra_deg, source.dec_deg, f"sources[{index}]", result)
    if config.weights.mode == WeightMode.COLUMN:
        result.errors.append("weights.mode='column' requires catalog.file")
    if config.weights.mode == WeightMode.MANUAL:
        validate_manual_weights(config, len(config.sources), result)


def validate_manual_weights(config: AnalysisConfig, n_sources: int, result: ValidationResult) -> None:
    if config.weights.values is None:
        result.errors.append("weights.values is required when weights.mode='manual'")
        return
    if len(config.weights.values) != n_sources:
        result.errors.append("weights.values length must match the number of input sources")
    if any(weight < 0.0 for weight in config.weights.values):
        result.errors.append("manual weights must be non-negative")
    if sum(config.weights.values) <= 0.0:
        result.errors.append("at least one manual weight must be positive")


def validate_ra_dec(ra_deg: float | None, dec_deg: float | None, label: str, result: ValidationResult) -> None:
    if ra_deg is None or not 0.0 <= ra_deg < 360.0:
        result.errors.append(f"{label}.ra_deg must be in [0, 360)")
    if dec_deg is None or not -90.0 <= dec_deg <= 90.0:
        result.errors.append(f"{label}.dec_deg must be in [-90, 90]")


def resolve_path(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def read_columns(path: Path) -> list[str]:
    _, columns = read_source_catalog(path)
    return columns


def count_rows(path: Path) -> int:
    rows, _ = read_source_catalog(path)
    return len(rows)
