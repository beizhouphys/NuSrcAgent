from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum
from typing import Any


class ConfigError(ValueError):
    pass


class AnalysisType(str, Enum):
    SINGLE_SOURCE = "single_source"
    CATALOG_STACKING = "catalog_stacking"


class WeightMode(str, Enum):
    UNIFORM = "uniform"
    COLUMN = "column"
    MANUAL = "manual"


@dataclass
class AnalysisBlock:
    type: AnalysisType
    time_mode: str = "time_integrated"
    likelihood_mode: str = "spatial_energy"
    catalog_operation: str = "stack"
    flux_upper_limit_cl: float | None = None
    flux_upper_limit_gammas: list[float] = field(default_factory=list)
    flux_measurement_ts_threshold: float | None = None
    fit_procedure: str = "skyllh_lbfgs_v1"
    scan_fit_procedure: str | None = None
    stacking_flux: dict[str, Any] = field(default_factory=dict)


@dataclass
class DataBlock:
    sample: str


@dataclass
class SourceBlock:
    name: str | None = None
    ra_deg: float | None = None
    dec_deg: float | None = None


@dataclass
class CatalogBlock:
    file: str | None = None
    builtin: str | None = None
    name_column: str | None = None
    ra_column: str | None = None
    dec_column: str | None = None


@dataclass
class WeightsBlock:
    mode: WeightMode = WeightMode.UNIFORM
    column: str | None = None
    values: list[float] | None = None
    normalize: bool = True


@dataclass
class StackingBlock:
    spectral_indices: list[float] = field(default_factory=lambda: [-2.53])
    include_uniform_baseline: bool = True
    gamma_mode: str = "fixed"


@dataclass
class BackgroundBlock:
    method: str = "ra_scramble"
    n_trials: int = 10000
    random_seed: int = 12345
    event_abs_dec_max_deg: float | None = None
    event_dec_min_deg: float | None = None
    event_dec_max_deg: float | None = None
    source_dec_window_deg: float | None = None


@dataclass
class OutputBlock:
    output_root: str = "data_output/runs"


@dataclass
class AnalysisConfig:
    schema_version: str
    analysis: AnalysisBlock
    data: DataBlock
    source: SourceBlock | None = None
    sources: list[SourceBlock] | None = None
    catalog: CatalogBlock | None = None
    weights: WeightsBlock = field(default_factory=WeightsBlock)
    stacking: StackingBlock = field(default_factory=StackingBlock)
    background: BackgroundBlock = field(default_factory=BackgroundBlock)
    outputs: OutputBlock = field(default_factory=OutputBlock)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AnalysisConfig":
        try:
            analysis_payload = payload["analysis"]
            data_payload = payload["data"]
        except KeyError as exc:
            raise ConfigError(f"missing required block: {exc.args[0]}") from exc
        sample = str(data_payload.get("sample", "icecube_public_ps_14yr_dr2"))
        default_likelihood_mode = "spatial_energy" if sample == "icecube_public_ps_14yr_dr2" else "spatial_only"
        likelihood_mode = str(analysis_payload.get("likelihood_mode", default_likelihood_mode))
        default_gamma_mode = "fitted" if likelihood_mode == "spatial_energy" and sample == "icecube_public_ps_14yr_dr2" else "fixed"
        default_spectral_index = -2.5 if likelihood_mode == "spatial_only" and sample == "icecube_public_ps_14yr_dr2" else (-3.0 if sample == "icecube_public_ps_14yr_dr2" else -2.53)
        return cls(
            schema_version=str(payload.get("schema_version", "0.1")),
            analysis=AnalysisBlock(type=parse_analysis_type(analysis_payload.get("type")), time_mode=str(analysis_payload.get("time_mode", "time_integrated")), likelihood_mode=likelihood_mode, catalog_operation=str(analysis_payload.get("catalog_operation", "stack" if sample == "icecube_public_ps_14yr_dr2" else "scan_and_stack")), flux_upper_limit_cl=optional_float(analysis_payload, "flux_upper_limit_cl"), flux_upper_limit_gammas=[float(value) for value in analysis_payload.get("flux_upper_limit_gammas", [])], flux_measurement_ts_threshold=optional_float(analysis_payload, "flux_measurement_ts_threshold"), fit_procedure=str(analysis_payload.get("fit_procedure", "skyllh_lbfgs_v1")), scan_fit_procedure=optional_str(analysis_payload, "scan_fit_procedure"), stacking_flux=analysis_payload.get("stacking_flux", {})),
            data=DataBlock(sample=sample),
            source=parse_source(payload.get("source")),
            sources=parse_sources(payload.get("sources")),
            catalog=parse_catalog(payload.get("catalog")),
            weights=parse_weights(payload.get("weights")),
            stacking=parse_stacking(payload.get("stacking"), default_gamma_mode=default_gamma_mode, default_spectral_index=default_spectral_index),
            background=parse_background(payload.get("background")),
            outputs=parse_outputs(payload.get("outputs")),
        )


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0


@dataclass
class NormalizedSource:
    source_number: int
    name: str
    ra_deg: float
    dec_deg: float
    ra_rad: float
    dec_rad: float
    weight: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedAnalysis:
    schema_version: str
    analysis_type: str
    time_mode: str
    likelihood_mode: str
    sample: str
    sources: list[NormalizedSource]
    spectral_indices: list[float]
    gamma_mode: str
    include_uniform_baseline: bool
    background_method: str
    n_trials: int
    random_seed: int
    event_abs_dec_max_deg: float | None = None
    event_dec_min_deg: float | None = None
    event_dec_max_deg: float | None = None
    source_dec_window_deg: float | None = None
    catalog_operation: str = "stack"
    flux_upper_limit_cl: float | None = None
    flux_upper_limit_gammas: list[float] = field(default_factory=list)
    flux_measurement_ts_threshold: float | None = None
    fit_procedure: str = "skyllh_lbfgs_v1"
    warnings: list[str] = field(default_factory=list)
    scan_fit_procedure: str | None = None
    stacking_flux: dict[str, Any] = field(default_factory=dict)


def parse_source(payload: Any) -> SourceBlock | None:
    if payload is None:
        return None
    return SourceBlock(name=optional_str(payload, "name"), ra_deg=optional_float(payload, "ra_deg"), dec_deg=optional_float(payload, "dec_deg"))


def parse_sources(payload: Any) -> list[SourceBlock] | None:
    if payload is None:
        return None
    if not isinstance(payload, list):
        raise ConfigError("sources must be a list")
    sources: list[SourceBlock] = []
    for item in payload:
        source = parse_source(item)
        if source is None:
            raise ConfigError("each sources item must be a mapping")
        sources.append(source)
    return sources


def parse_catalog(payload: Any) -> CatalogBlock | None:
    if payload is None:
        return None
    return CatalogBlock(file=optional_str(payload, "file"), builtin=optional_str(payload, "builtin"), name_column=optional_str(payload, "name_column"), ra_column=optional_str(payload, "ra_column"), dec_column=optional_str(payload, "dec_column"))


def parse_weights(payload: Any) -> WeightsBlock:
    if payload is None:
        return WeightsBlock()
    values = payload.get("values")
    if values is not None and not isinstance(values, list):
        raise ConfigError("weights.values must be a list")
    return WeightsBlock(mode=parse_weight_mode(payload.get("mode", "uniform")), column=optional_str(payload, "column"), values=None if values is None else [float(value) for value in values], normalize=bool(payload.get("normalize", True)))


def parse_stacking(payload: Any, default_gamma_mode: str = "fixed", default_spectral_index: float = -2.53) -> StackingBlock:
    if payload is None:
        return StackingBlock(spectral_indices=[default_spectral_index], gamma_mode=default_gamma_mode)
    spectral_indices = payload.get("spectral_indices", [default_spectral_index])
    if not isinstance(spectral_indices, list) or len(spectral_indices) == 0:
        raise ConfigError("stacking.spectral_indices must be a non-empty list")
    gamma_mode = str(payload.get("gamma_mode", default_gamma_mode))
    if gamma_mode not in {"fitted", "fixed"}:
        raise ConfigError("stacking.gamma_mode must be fitted or fixed")
    return StackingBlock(spectral_indices=[float(value) for value in spectral_indices], include_uniform_baseline=bool(payload.get("include_uniform_baseline", True)), gamma_mode=gamma_mode)


def parse_background(payload: Any) -> BackgroundBlock:
    if payload is None:
        return BackgroundBlock()
    return BackgroundBlock(method=str(payload.get("method", "ra_scramble")), n_trials=int(payload.get("n_trials", 10000)), random_seed=int(payload.get("random_seed", 12345)), event_abs_dec_max_deg=optional_float(payload, "event_abs_dec_max_deg"), event_dec_min_deg=optional_float(payload, "event_dec_min_deg"), event_dec_max_deg=optional_float(payload, "event_dec_max_deg"), source_dec_window_deg=optional_float(payload, "source_dec_window_deg"))


def parse_outputs(payload: Any) -> OutputBlock:
    if payload is None:
        return OutputBlock()
    return OutputBlock(output_root=str(payload.get("output_root", "data_output/runs")))


def parse_analysis_type(value: Any) -> AnalysisType:
    try:
        return AnalysisType(str(value))
    except ValueError as exc:
        raise ConfigError("analysis.type must be single_source or catalog_stacking") from exc


def parse_weight_mode(value: Any) -> WeightMode:
    try:
        return WeightMode(str(value))
    except ValueError as exc:
        raise ConfigError("weights.mode must be uniform, column, or manual") from exc


def optional_str(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    return None if value is None else str(value)


def optional_float(payload: dict[str, Any], key: str) -> float | None:
    value = payload.get(key)
    return None if value is None else float(value)


def to_clean_dict(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field.name: to_clean_dict(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, list):
        return [to_clean_dict(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_clean_dict(item) for key, item in value.items()}
    return value
