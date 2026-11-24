"""Configuration models for generic catalog time-dependent analyses."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

AnalysisMode = Literal['single_source', 'stacking']
PeriodSelection = Literal['window_overlap', 'anchor_inside']
PDFBackend = Literal['skyllh', 'precomputed']
LikelihoodFamily = Literal['skyllh_conditional']
TimeProfileType = Literal['box', 'gaussian']


@dataclass(frozen=True)
class TimeProfileConfig:
    """Fixed source-time profile used by the signal hypothesis."""

    type: TimeProfileType = 'box'
    center_mjd_column: str | None = None
    sigma_days_column: str | None = None
    tail_tolerance: float = 1e-12

    @classmethod
    def from_dict(cls, values: dict[str, Any] | None) -> TimeProfileConfig:
        values = values or {}
        profile_type = str(values.get('type', 'box'))
        if profile_type not in ('box', 'gaussian'):
            raise ValueError('time_profile.type must be box or gaussian')
        columns = values.get('columns', {})
        if not isinstance(columns, dict):
            raise TypeError('time_profile.columns must be a mapping')
        center = columns.get('center_mjd')
        sigma = columns.get('sigma_days')
        tolerance = float(values.get('tail_tolerance', 1e-12))
        if not 0.0 < tolerance < 1.0:
            raise ValueError('time_profile.tail_tolerance must lie strictly between zero and one')
        if profile_type == 'gaussian':
            missing = [name for name, value in (('center_mjd', center), ('sigma_days', sigma)) if not value]
            if missing:
                raise ValueError(f'time_profile.columns is missing required Gaussian mappings: {missing}')
        elif center is not None or sigma is not None:
            raise ValueError('time_profile.columns.center_mjd and sigma_days are only valid for Gaussian profiles')
        return cls(
            type=profile_type,  # type: ignore[arg-type]
            center_mjd_column=None if center is None else str(center),
            sigma_days_column=None if sigma is None else str(sigma),
            tail_tolerance=tolerance,
        )


@dataclass(frozen=True)
class DatasetConfig:
    """SkyLLH public-data sample and detector phases."""

    sample: str
    names: tuple[str, ...]
    label: str | None = None
    base_path: Path | None = None
    sub_path_fmt: str | None = None
    cache_dir: Path | None = None

    @classmethod
    def from_dict(cls, values: dict[str, Any], base_dir: Path | None = None) -> DatasetConfig:
        if base_dir is None:
            base_dir = Path.cwd()
        names = tuple(str(name) for name in values.get('names', ()))
        if not names:
            raise ValueError('dataset.names must contain at least one dataset name')
        base_path = values.get('base_path')
        if base_path is not None:
            base_path = Path(base_path).expanduser()
            if not base_path.is_absolute():
                base_path = (base_dir / base_path).resolve()
        cache_dir = values.get('cache_dir')
        if cache_dir is not None:
            cache_dir = Path(cache_dir).expanduser()
            if not cache_dir.is_absolute():
                cache_dir = (base_dir / cache_dir).resolve()
        return cls(
            sample=str(values['sample']),
            names=names,
            label=None if values.get('label') is None else str(values['label']),
            base_path=base_path,
            sub_path_fmt=None if values.get('sub_path_fmt') is None else str(values['sub_path_fmt']),
            cache_dir=cache_dir,
        )


def _resolve_path(value: str | Path, base_dir: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return path


@dataclass(frozen=True)
class PrecomputedPhasePDFConfig:
    """Supplied DR2 PDF products and row-order inputs for one analysis phase.

    ``event_paths`` lists the public event CSV files in the exact order used to
    create the event-indexed background table.  It makes a combined response
    product usable with any subset or combination of DR2 detector seasons
    without relying on filenames or an implicit catalog-specific layout.
    """

    signal_path: Path
    background_path: Path
    event_paths: tuple[Path, ...]
    provenance_path: Path | None = None

    @classmethod
    def from_dict(cls, values: dict[str, Any], base_dir: Path) -> PrecomputedPhasePDFConfig:
        event_paths = tuple(_resolve_path(value, base_dir) for value in values.get('event_paths', ()))
        if not event_paths:
            raise ValueError('each precomputed PDF phase must specify at least one event_paths entry')
        provenance = values.get('provenance_path')
        return cls(
            signal_path=_resolve_path(values['signal_path'], base_dir),
            background_path=_resolve_path(values['background_path'], base_dir),
            event_paths=event_paths,
            provenance_path=None if provenance is None else _resolve_path(provenance, base_dir),
        )


@dataclass(frozen=True)
class PDFConfig:
    """Select the native SkyLLH/cache or supplied DR2 PDF implementation."""

    backend: PDFBackend = 'skyllh'
    phases: dict[str, PrecomputedPhasePDFConfig] = field(default_factory=dict)
    gamma_interpolation: str = 'linear_density'
    verify_event_coordinates: bool = True

    @classmethod
    def from_dict(
        cls,
        values: dict[str, Any] | None,
        *,
        dataset_names: tuple[str, ...],
        base_dir: Path,
    ) -> PDFConfig:
        values = values or {}
        backend = str(values.get('backend', 'skyllh'))
        if backend not in ('skyllh', 'precomputed'):
            raise ValueError('pdfs.backend must be skyllh or precomputed')
        interpolation = str(values.get('gamma_interpolation', 'linear_density'))
        if interpolation != 'linear_density':
            raise ValueError('only pdfs.gamma_interpolation: linear_density is currently supported')
        phase_values = values.get('phases', {})
        if not isinstance(phase_values, dict):
            raise TypeError('pdfs.phases must be a mapping keyed by dataset name')
        phases = {str(name): PrecomputedPhasePDFConfig.from_dict(item, base_dir) for name, item in phase_values.items()}
        if backend == 'precomputed':
            missing = sorted(set(dataset_names).difference(phases))
            extra = sorted(set(phases).difference(dataset_names))
            if missing:
                raise ValueError(f'pdfs.phases is missing configured datasets: {missing}')
            if extra:
                raise ValueError(f'pdfs.phases contains datasets not selected by dataset.names: {extra}')
        elif phases:
            raise ValueError('pdfs.phases is only valid with pdfs.backend: precomputed')
        return cls(
            backend=backend,  # type: ignore[arg-type]
            phases=phases,
            gamma_interpolation=interpolation,
            verify_event_coordinates=bool(values.get('verify_event_coordinates', True)),
        )


@dataclass(frozen=True)
class CatalogColumnConfig:
    """Map analysis concepts to columns in an arbitrary CSV catalog."""

    source_id: str
    name: str
    ra_deg: str
    dec_deg: str
    weight: str
    time_start_mjd: str | None = None
    time_end_mjd: str | None = None
    time_anchor_mjd: str | None = None

    @classmethod
    def from_dict(
        cls,
        values: dict[str, Any],
        time_profile: TimeProfileConfig | None = None,
    ) -> CatalogColumnConfig:
        time_profile = time_profile or TimeProfileConfig()
        required = ['source_id', 'name', 'ra_deg', 'dec_deg', 'weight']
        if time_profile.type == 'box':
            required.extend(('time_start_mjd', 'time_end_mjd'))
        missing = [key for key in required if not values.get(key)]
        if missing:
            raise ValueError(f'catalog.columns is missing required mappings: {missing}')
        return cls(
            **{key: str(values[key]) for key in ('source_id', 'name', 'ra_deg', 'dec_deg', 'weight')},
            time_start_mjd=None if values.get('time_start_mjd') is None else str(values['time_start_mjd']),
            time_end_mjd=None if values.get('time_end_mjd') is None else str(values['time_end_mjd']),
            time_anchor_mjd=(None if values.get('time_anchor_mjd') is None else str(values['time_anchor_mjd'])),
        )


@dataclass(frozen=True)
class CatalogSelectionConfig:
    """Catalog cuts that are independent of a specific source class."""

    required_true_fields: tuple[str, ...] = ()
    required_false_fields: tuple[str, ...] = ()
    dec_min_deg: float = -90.0
    dec_max_deg: float = 90.0
    period_selection: PeriodSelection = 'window_overlap'

    @classmethod
    def from_dict(cls, values: dict[str, Any] | None) -> CatalogSelectionConfig:
        values = values or {}
        period_selection = str(values.get('period_selection', 'window_overlap'))
        if period_selection not in ('window_overlap', 'anchor_inside'):
            raise ValueError('catalog.selection.period_selection must be window_overlap or anchor_inside')
        dec_min = float(values.get('dec_min_deg', -90.0))
        dec_max = float(values.get('dec_max_deg', 90.0))
        if not -90.0 <= dec_min < dec_max <= 90.0:
            raise ValueError('catalog selection declination bounds must satisfy -90 <= min < max <= 90')
        return cls(
            required_true_fields=tuple(str(v) for v in values.get('required_true_fields', ())),
            required_false_fields=tuple(str(v) for v in values.get('required_false_fields', ())),
            dec_min_deg=dec_min,
            dec_max_deg=dec_max,
            period_selection=period_selection,  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class CatalogConfig:
    """Input catalog definition."""

    path: Path
    columns: CatalogColumnConfig
    label: str | None = None
    selection: CatalogSelectionConfig = field(default_factory=CatalogSelectionConfig)
    delimiter: str = ','
    time_profile: TimeProfileConfig = field(default_factory=TimeProfileConfig)

    @classmethod
    def from_dict(
        cls,
        values: dict[str, Any],
        base_dir: Path,
        time_profile: TimeProfileConfig | None = None,
    ) -> CatalogConfig:
        time_profile = time_profile or TimeProfileConfig()
        path = Path(values['path']).expanduser()
        if not path.is_absolute():
            path = (base_dir / path).resolve()
        delimiter = str(values.get('delimiter', ','))
        if len(delimiter) != 1:
            raise ValueError('catalog.delimiter must be exactly one character')
        return cls(
            path=path,
            columns=CatalogColumnConfig.from_dict(values['columns'], time_profile=time_profile),
            label=None if values.get('label') is None else str(values['label']),
            selection=CatalogSelectionConfig.from_dict(values.get('selection')),
            delimiter=delimiter,
            time_profile=time_profile,
        )


@dataclass(frozen=True)
class SpectrumConfig:
    """Power-law spectral hypothesis."""

    gamma: float = 2.0
    fit_gamma: bool = False
    gamma_min: float = 1.0
    gamma_max: float = 4.0
    reference_energy_gev: float = 1e3
    reference_flux: float = 1.0
    gamma_grid_step: float = 0.1

    @classmethod
    def from_dict(cls, values: dict[str, Any] | None) -> SpectrumConfig:
        values = values or {}
        result = cls(
            gamma=float(values.get('gamma', 2.0)),
            fit_gamma=bool(values.get('fit_gamma', False)),
            gamma_min=float(values.get('gamma_min', 1.0)),
            gamma_max=float(values.get('gamma_max', 4.0)),
            reference_energy_gev=float(values.get('reference_energy_gev', 1e3)),
            reference_flux=float(values.get('reference_flux', 1.0)),
            gamma_grid_step=float(values.get('gamma_grid_step', 0.1)),
        )
        if not result.gamma_min <= result.gamma <= result.gamma_max:
            raise ValueError('spectrum.gamma must lie within [gamma_min, gamma_max]')
        if result.gamma_grid_step <= 0:
            raise ValueError('spectrum.gamma_grid_step must be positive')
        return result


@dataclass(frozen=True)
class LikelihoodConfig:
    """Fit and event-selection settings."""

    family: LikelihoodFamily = 'skyllh_conditional'
    ns_seed: float = 1.0
    ns_min: float = 0.0
    ns_max: float = 1000.0
    minimizer: str = 'LBFGS'
    event_selection_angle_deg: float = 10.0
    event_selection_method: str = 'source_time_spatial_box'

    @classmethod
    def from_dict(cls, values: dict[str, Any] | None) -> LikelihoodConfig:
        values = values or {}
        family = str(values.get('family', 'skyllh_conditional'))
        result = cls(
            family=family,  # type: ignore[arg-type]
            ns_seed=float(values.get('ns_seed', 1.0)),
            ns_min=float(values.get('ns_min', 0.0)),
            ns_max=float(values.get('ns_max', 1000.0)),
            minimizer=str(values.get('minimizer', 'LBFGS')),
            event_selection_angle_deg=float(values.get('event_selection_angle_deg', 10.0)),
            event_selection_method=str(values.get('event_selection_method', 'source_time_spatial_box')),
        )
        if result.family != 'skyllh_conditional':
            raise ValueError(
                'likelihood.family must be skyllh_conditional; poisson_extended is archived '
                'under archive/poisson_extended'
            )
        if not result.ns_min <= result.ns_seed <= result.ns_max:
            raise ValueError('likelihood.ns_seed must lie within [ns_min, ns_max]')
        if result.minimizer not in ('LBFGS', 'minuit'):
            raise ValueError('likelihood.minimizer must be LBFGS or minuit')
        if result.event_selection_angle_deg <= 0:
            raise ValueError('likelihood.event_selection_angle_deg must be positive')
        if result.event_selection_method not in ('source_time_spatial_box', 'spatial_box'):
            raise ValueError('likelihood.event_selection_method must be source_time_spatial_box or spatial_box')
        return result


@dataclass(frozen=True)
class BackgroundTrialsConfig:
    """Background-only trial defaults."""

    method: str = 'seasonal_time_scrambling'
    seed: int = 1
    n_trials: int = 100

    @classmethod
    def from_dict(cls, values: dict[str, Any] | None) -> BackgroundTrialsConfig:
        values = values or {}
        result = cls(
            method=str(values.get('method', 'seasonal_time_scrambling')),
            seed=int(values.get('seed', 1)),
            n_trials=int(values.get('n_trials', 100)),
        )
        if result.method != 'seasonal_time_scrambling':
            raise ValueError('only seasonal_time_scrambling is currently supported')
        if 'rate_estimator' in values:
            raise ValueError(
                'background.rate_estimator belonged to the archived poisson_extended framework'
            )
        if result.n_trials <= 0:
            raise ValueError('background.n_trials must be positive')
        return result


@dataclass(frozen=True)
class CatalogAnalysisConfig:
    """Complete configuration for one catalog analysis."""

    mode: AnalysisMode
    dataset: DatasetConfig
    catalog: CatalogConfig
    pdfs: PDFConfig = field(default_factory=PDFConfig)
    spectrum: SpectrumConfig = field(default_factory=SpectrumConfig)
    likelihood: LikelihoodConfig = field(default_factory=LikelihoodConfig)
    background: BackgroundTrialsConfig = field(default_factory=BackgroundTrialsConfig)
    single_source: str | None = None

    @property
    def time_profile(self) -> TimeProfileConfig:
        return self.catalog.time_profile

    @classmethod
    def from_dict(cls, values: dict[str, Any], base_dir: Path | None = None) -> CatalogAnalysisConfig:
        if base_dir is None:
            base_dir = Path.cwd()
        mode = str(values.get('mode', 'stacking'))
        if mode not in ('single_source', 'stacking'):
            raise ValueError('mode must be single_source or stacking')
        single_source = values.get('single_source')
        if mode == 'single_source' and not single_source:
            raise ValueError('single_source must be specified when mode is single_source')
        dataset = DatasetConfig.from_dict(values['dataset'], base_dir=base_dir)
        time_profile = TimeProfileConfig.from_dict(values.get('time_profile'))
        return cls(
            mode=mode,  # type: ignore[arg-type]
            single_source=None if single_source is None else str(single_source),
            dataset=dataset,
            catalog=CatalogConfig.from_dict(values['catalog'], base_dir=base_dir, time_profile=time_profile),
            pdfs=PDFConfig.from_dict(values.get('pdfs'), dataset_names=dataset.names, base_dir=base_dir),
            spectrum=SpectrumConfig.from_dict(values.get('spectrum')),
            likelihood=LikelihoodConfig.from_dict(values.get('likelihood')),
            background=BackgroundTrialsConfig.from_dict(values.get('background')),
        )


def load_analysis_config(path: str | Path) -> CatalogAnalysisConfig:
    """Load and validate a catalog-analysis YAML file."""

    path = Path(path).expanduser().resolve()
    with path.open(encoding='utf-8') as stream:
        values = yaml.safe_load(stream)
    if not isinstance(values, dict):
        raise TypeError('analysis configuration must contain a YAML mapping')
    return CatalogAnalysisConfig.from_dict(values, base_dir=path.parent)
