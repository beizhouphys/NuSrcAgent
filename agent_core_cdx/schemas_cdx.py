from __future__ import annotations # Codex

from dataclasses import dataclass, field, fields, is_dataclass # Codex
from enum import Enum # Codex
from typing import Any # Codex


class ConfigError(ValueError): # Codex
    pass # Codex


class AnalysisType(str, Enum): # Codex
    SINGLE_SOURCE = "single_source" # Codex
    CATALOG_STACKING = "catalog_stacking" # Codex


class WeightMode(str, Enum): # Codex
    UNIFORM = "uniform" # Codex
    COLUMN = "column" # Codex
    MANUAL = "manual" # Codex


@dataclass # Codex
class AnalysisBlock: # Codex
    type: AnalysisType # Codex
    time_mode: str = "time_integrated" # Codex


@dataclass # Codex
class DataBlock: # Codex
    sample: str # Codex


@dataclass # Codex
class SourceBlock: # Codex
    name: str | None = None # Codex
    ra_deg: float | None = None # Codex
    dec_deg: float | None = None # Codex


@dataclass # Codex
class CatalogBlock: # Codex
    file: str | None = None # Codex
    name_column: str | None = None # Codex
    ra_column: str | None = None # Codex
    dec_column: str | None = None # Codex


@dataclass # Codex
class WeightsBlock: # Codex
    mode: WeightMode = WeightMode.UNIFORM # Codex
    column: str | None = None # Codex
    values: list[float] | None = None # Codex
    normalize: bool = True # Codex


@dataclass # Codex
class StackingBlock: # Codex
    spectral_indices: list[float] = field(default_factory=lambda: [-2.53]) # Codex
    include_uniform_baseline: bool = True # Codex


@dataclass # Codex
class BackgroundBlock: # Codex
    method: str = "ra_scramble" # Codex
    n_trials: int = 10000 # Codex
    random_seed: int = 12345 # Codex


@dataclass # Codex
class OutputBlock: # Codex
    output_root: str = "data_output/runs_cdx" # cdx


@dataclass # Codex
class AnalysisConfig: # Codex
    schema_version: str # Codex
    analysis: AnalysisBlock # Codex
    data: DataBlock # Codex
    source: SourceBlock | None = None # Codex
    sources: list[SourceBlock] | None = None # Codex
    catalog: CatalogBlock | None = None # Codex
    weights: WeightsBlock = field(default_factory=WeightsBlock) # Codex
    stacking: StackingBlock = field(default_factory=StackingBlock) # Codex
    background: BackgroundBlock = field(default_factory=BackgroundBlock) # Codex
    outputs: OutputBlock = field(default_factory=OutputBlock) # Codex

    @classmethod # Codex
    def from_dict(cls, payload: dict[str, Any]) -> "AnalysisConfig": # Codex
        try: # Codex
            analysis_payload = payload["analysis"] # Codex
            data_payload = payload["data"] # Codex
        except KeyError as exc: # Codex
            raise ConfigError(f"missing required block: {exc.args[0]}") from exc # Codex
        return cls( # Codex
            schema_version=str(payload.get("schema_version", "0.1")), # Codex
            analysis=AnalysisBlock(type=parse_analysis_type(analysis_payload.get("type")), time_mode=str(analysis_payload.get("time_mode", "time_integrated"))), # Codex
            data=DataBlock(sample=str(data_payload.get("sample", "icecube_public_ps_10yr"))), # Codex
            source=parse_source(payload.get("source")), # Codex
            sources=parse_sources(payload.get("sources")), # Codex
            catalog=parse_catalog(payload.get("catalog")), # Codex
            weights=parse_weights(payload.get("weights")), # Codex
            stacking=parse_stacking(payload.get("stacking")), # Codex
            background=parse_background(payload.get("background")), # Codex
            outputs=parse_outputs(payload.get("outputs")), # Codex
        ) # Codex


@dataclass # Codex
class ValidationResult: # Codex
    errors: list[str] = field(default_factory=list) # Codex
    warnings: list[str] = field(default_factory=list) # Codex

    @property # Codex
    def ok(self) -> bool: # Codex
        return len(self.errors) == 0 # Codex


@dataclass # Codex
class NormalizedSource: # Codex
    source_number: int # Codex
    name: str # Codex
    ra_deg: float # Codex
    dec_deg: float # Codex
    ra_rad: float # Codex
    dec_rad: float # Codex
    weight: float # Codex
    metadata: dict[str, Any] = field(default_factory=dict) # Codex


@dataclass # Codex
class NormalizedAnalysis: # Codex
    schema_version: str # Codex
    analysis_type: str # Codex
    time_mode: str # Codex
    sample: str # Codex
    sources: list[NormalizedSource] # Codex
    spectral_indices: list[float] # Codex
    include_uniform_baseline: bool # Codex
    background_method: str # Codex
    n_trials: int # Codex
    random_seed: int # Codex
    warnings: list[str] = field(default_factory=list) # Codex


def parse_source(payload: Any) -> SourceBlock | None: # Codex
    if payload is None: # Codex
        return None # Codex
    return SourceBlock(name=optional_str(payload, "name"), ra_deg=optional_float(payload, "ra_deg"), dec_deg=optional_float(payload, "dec_deg")) # Codex


def parse_sources(payload: Any) -> list[SourceBlock] | None: # Codex
    if payload is None: # Codex
        return None # Codex
    if not isinstance(payload, list): # Codex
        raise ConfigError("sources must be a list") # Codex
    sources: list[SourceBlock] = [] # Codex
    for item in payload: # Codex
        source = parse_source(item) # Codex
        if source is None: # Codex
            raise ConfigError("each sources item must be a mapping") # Codex
        sources.append(source) # Codex
    return sources # Codex


def parse_catalog(payload: Any) -> CatalogBlock | None: # Codex
    if payload is None: # Codex
        return None # Codex
    return CatalogBlock(file=optional_str(payload, "file"), name_column=optional_str(payload, "name_column"), ra_column=optional_str(payload, "ra_column"), dec_column=optional_str(payload, "dec_column")) # Codex


def parse_weights(payload: Any) -> WeightsBlock: # Codex
    if payload is None: # Codex
        return WeightsBlock() # Codex
    values = payload.get("values") # Codex
    if values is not None and not isinstance(values, list): # Codex
        raise ConfigError("weights.values must be a list") # Codex
    return WeightsBlock(mode=parse_weight_mode(payload.get("mode", "uniform")), column=optional_str(payload, "column"), values=None if values is None else [float(value) for value in values], normalize=bool(payload.get("normalize", True))) # Codex


def parse_stacking(payload: Any) -> StackingBlock: # Codex
    if payload is None: # Codex
        return StackingBlock() # Codex
    spectral_indices = payload.get("spectral_indices", [-2.53]) # Codex
    if not isinstance(spectral_indices, list) or len(spectral_indices) == 0: # Codex
        raise ConfigError("stacking.spectral_indices must be a non-empty list") # Codex
    return StackingBlock(spectral_indices=[float(value) for value in spectral_indices], include_uniform_baseline=bool(payload.get("include_uniform_baseline", True))) # Codex


def parse_background(payload: Any) -> BackgroundBlock: # Codex
    if payload is None: # Codex
        return BackgroundBlock() # Codex
    return BackgroundBlock(method=str(payload.get("method", "ra_scramble")), n_trials=int(payload.get("n_trials", 10000)), random_seed=int(payload.get("random_seed", 12345))) # Codex


def parse_outputs(payload: Any) -> OutputBlock: # Codex
    if payload is None: # Codex
        return OutputBlock() # Codex
    return OutputBlock(output_root=str(payload.get("output_root", "data_output/runs_cdx"))) # cdx


def parse_analysis_type(value: Any) -> AnalysisType: # Codex
    try: # Codex
        return AnalysisType(str(value)) # Codex
    except ValueError as exc: # Codex
        raise ConfigError("analysis.type must be single_source or catalog_stacking") from exc # Codex


def parse_weight_mode(value: Any) -> WeightMode: # Codex
    try: # Codex
        return WeightMode(str(value)) # Codex
    except ValueError as exc: # Codex
        raise ConfigError("weights.mode must be uniform, column, or manual") from exc # Codex


def optional_str(payload: dict[str, Any], key: str) -> str | None: # Codex
    value = payload.get(key) # Codex
    return None if value is None else str(value) # Codex


def optional_float(payload: dict[str, Any], key: str) -> float | None: # Codex
    value = payload.get(key) # Codex
    return None if value is None else float(value) # Codex


def to_clean_dict(value: Any) -> Any: # Codex
    if isinstance(value, Enum): # Codex
        return value.value # Codex
    if is_dataclass(value): # Codex
        return {field.name: to_clean_dict(getattr(value, field.name)) for field in fields(value)} # Codex
    if isinstance(value, list): # Codex
        return [to_clean_dict(item) for item in value] # Codex
    if isinstance(value, dict): # Codex
        return {str(key): to_clean_dict(item) for key, item in value.items()} # Codex
    return value # Codex
