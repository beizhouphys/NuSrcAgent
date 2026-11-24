"""Catalog ingestion and source selection for time-dependent analyses."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from skyllh.core.source_model import PointLikeSource

from .config import CatalogAnalysisConfig, CatalogConfig

TRUE_VALUES = frozenset({'1', 'true', 'yes', 'y', 't'})
FALSE_VALUES = frozenset({'0', 'false', 'no', 'n', 'f', ''})


@dataclass(frozen=True)
class CatalogSourceRecord:
    """Validated, analysis-independent representation of one catalog row."""

    row_number: int
    source_id: str
    name: str
    ra_deg: float
    dec_deg: float
    weight_raw: float | None
    time_start_mjd: float | None
    time_end_mjd: float | None
    time_anchor_mjd: float | None
    time_profile_type: str
    time_sigma_days: float | None
    time_tail_tolerance: float
    metadata: dict[str, str]

    @property
    def time_center_mjd(self) -> float:
        if self.time_start_mjd is None or self.time_end_mjd is None:
            raise ValueError(f'source {self.source_id!r} has no complete time window')
        return 0.5 * (self.time_start_mjd + self.time_end_mjd)

    @property
    def time_width_days(self) -> float:
        if self.time_start_mjd is None or self.time_end_mjd is None:
            raise ValueError(f'source {self.source_id!r} has no complete time window')
        return self.time_end_mjd - self.time_start_mjd

    def to_source(self, weight: float | None = None) -> PointLikeSource:
        """Create the SkyLLH point-source model for this row."""

        source_weight = self.weight_raw if weight is None else weight
        if source_weight is None:
            raise ValueError(f'source {self.source_id!r} has no source weight')
        return PointLikeSource(
            name=self.name,
            ra=np.deg2rad(self.ra_deg),
            dec=np.deg2rad(self.dec_deg),
            weight=source_weight,
        )


@dataclass(frozen=True)
class ExcludedCatalogSource:
    """A valid catalog source that did not pass the configured selection."""

    source: CatalogSourceRecord
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class SelectedCatalogSource:
    """A selected source and quantities derived for the analysis period."""

    source: CatalogSourceRecord
    normalized_weight: float
    observable_window_fraction: float

    def to_source(self) -> PointLikeSource:
        """Create a SkyLLH point source using the raw theoretical weight."""

        return self.source.to_source()


@dataclass(frozen=True)
class CatalogSelectionResult:
    """Selected and excluded sources plus reproducibility metadata."""

    catalog_path: Path
    catalog_sha256: str
    period_start_mjd: float
    period_end_mjd: float
    selected: tuple[SelectedCatalogSource, ...]
    excluded: tuple[ExcludedCatalogSource, ...]

    @property
    def sources(self) -> tuple[PointLikeSource, ...]:
        return tuple(item.to_source() for item in self.selected)

    def to_manifest(self) -> dict[str, Any]:
        """Return a JSON-serializable selection manifest."""

        return {
            'catalog_path': str(self.catalog_path),
            'catalog_sha256': self.catalog_sha256,
            'period_start_mjd': self.period_start_mjd,
            'period_end_mjd': self.period_end_mjd,
            'n_selected': len(self.selected),
            'n_excluded': len(self.excluded),
            'selected': [
                {
                    **asdict(item.source),
                    'normalized_weight': item.normalized_weight,
                    'observable_window_fraction': item.observable_window_fraction,
                }
                for item in self.selected
            ],
            'excluded': [{**asdict(item.source), 'reasons': list(item.reasons)} for item in self.excluded],
        }

    def write_manifest(self, path: str | Path) -> None:
        """Write the selection manifest as deterministic formatted JSON."""

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w', encoding='utf-8') as stream:
            json.dump(self.to_manifest(), stream, indent=2, sort_keys=True)
            stream.write('\n')


def parse_bool(value: str, *, column: str, row_number: int) -> bool:
    """Parse an explicit catalog boolean value."""

    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise ValueError(f'row {row_number}: column {column!r} is not a boolean value: {value!r}')


def _finite_float(row: dict[str, str], column: str, row_number: int) -> float:
    value = row.get(column, '').strip()
    if not value:
        raise ValueError(f'row {row_number}: required numeric column {column!r} is empty')
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f'row {row_number}: column {column!r} is not finite')
    return parsed


def _optional_finite_float(row: dict[str, str], column: str | None, row_number: int) -> float | None:
    if column is None:
        return None
    value = row.get(column, '').strip()
    if not value:
        return None
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f'row {row_number}: column {column!r} is not finite')
    return parsed


def _required_columns(config: CatalogConfig) -> set[str]:
    columns = config.columns
    required = {
        columns.source_id,
        columns.name,
        columns.ra_deg,
        columns.dec_deg,
        columns.weight,
        *config.selection.required_true_fields,
        *config.selection.required_false_fields,
    }
    if config.time_profile.type == 'box':
        assert columns.time_start_mjd is not None and columns.time_end_mjd is not None
        required.update((columns.time_start_mjd, columns.time_end_mjd))
    else:
        assert config.time_profile.center_mjd_column is not None
        assert config.time_profile.sigma_days_column is not None
        required.update((config.time_profile.center_mjd_column, config.time_profile.sigma_days_column))
    if columns.time_anchor_mjd is not None:
        required.add(columns.time_anchor_mjd)
    return required


def load_catalog(config: CatalogConfig) -> tuple[CatalogSourceRecord, ...]:
    """Load and strictly validate all rows of a configured CSV catalog."""

    with config.path.open(encoding='utf-8', newline='') as stream:
        reader = csv.DictReader(stream, delimiter=config.delimiter)
        if reader.fieldnames is None:
            raise ValueError(f'catalog {config.path} has no header')
        missing = sorted(_required_columns(config).difference(reader.fieldnames))
        if missing:
            raise ValueError(f'catalog {config.path} is missing required columns: {missing}')

        records = []
        seen_ids: set[str] = set()
        columns = config.columns
        for row_number, row in enumerate(reader, start=2):
            source_id = row[columns.source_id].strip()
            name = row[columns.name].strip()
            if not source_id:
                raise ValueError(f'row {row_number}: source ID is empty')
            if source_id in seen_ids:
                raise ValueError(f'row {row_number}: duplicate source ID {source_id!r}')
            if not name:
                raise ValueError(f'row {row_number}: source name is empty')

            ra_deg = _finite_float(row, columns.ra_deg, row_number)
            dec_deg = _finite_float(row, columns.dec_deg, row_number)
            weight = _optional_finite_float(row, columns.weight, row_number)
            if config.time_profile.type == 'box':
                time_start = _optional_finite_float(row, columns.time_start_mjd, row_number)
                time_end = _optional_finite_float(row, columns.time_end_mjd, row_number)
                time_sigma = None
            else:
                assert config.time_profile.center_mjd_column is not None
                assert config.time_profile.sigma_days_column is not None
                time_center = _finite_float(row, config.time_profile.center_mjd_column, row_number)
                time_sigma = _finite_float(row, config.time_profile.sigma_days_column, row_number)
                if time_sigma <= 0.0:
                    raise ValueError(f'row {row_number}: Gaussian time sigma must be positive')
                half_support = time_sigma * math.sqrt(-2.0 * math.log(config.time_profile.tail_tolerance))
                time_start = time_center - half_support
                time_end = time_center + half_support
            anchor = _optional_finite_float(row, columns.time_anchor_mjd, row_number)
            if config.time_profile.type == 'gaussian' and anchor is None:
                anchor = time_center

            if not 0.0 <= ra_deg < 360.0:
                raise ValueError(f'row {row_number}: RA must satisfy 0 <= RA < 360 deg')
            if not -90.0 <= dec_deg <= 90.0:
                raise ValueError(f'row {row_number}: declination must lie in [-90, 90] deg')
            if weight is not None and weight <= 0.0:
                raise ValueError(f'row {row_number}: source weight must be positive')
            if time_start is not None and time_end is not None and time_end <= time_start:
                raise ValueError(f'row {row_number}: time window must have positive width')

            records.append(
                CatalogSourceRecord(
                    row_number=row_number,
                    source_id=source_id,
                    name=name,
                    ra_deg=ra_deg,
                    dec_deg=dec_deg,
                    weight_raw=weight,
                    time_start_mjd=time_start,
                    time_end_mjd=time_end,
                    time_anchor_mjd=anchor,
                    time_profile_type=config.time_profile.type,
                    time_sigma_days=time_sigma,
                    time_tail_tolerance=config.time_profile.tail_tolerance,
                    metadata={key: (value or '') for key, value in row.items()},
                )
            )
            seen_ids.add(source_id)

    if not records:
        raise ValueError(f'catalog {config.path} contains no data rows')
    return tuple(records)


def _selection_reasons(
    source: CatalogSourceRecord,
    config: CatalogConfig,
    period_start_mjd: float,
    period_end_mjd: float,
) -> tuple[str, ...]:
    selection = config.selection
    reasons = []
    for field_name in selection.required_true_fields:
        if not parse_bool(source.metadata[field_name], column=field_name, row_number=source.row_number):
            reasons.append(f'{field_name}=false')
    for field_name in selection.required_false_fields:
        if parse_bool(source.metadata[field_name], column=field_name, row_number=source.row_number):
            reasons.append(f'{field_name}=true')
    if source.dec_deg <= selection.dec_min_deg:
        reasons.append('declination_below_or_at_minimum')
    if source.dec_deg > selection.dec_max_deg:
        reasons.append('declination_above_maximum')

    if source.weight_raw is None:
        reasons.append('missing_source_weight')
    if source.time_start_mjd is None or source.time_end_mjd is None:
        reasons.append('missing_time_window')

    has_window = source.time_start_mjd is not None and source.time_end_mjd is not None
    if has_window and selection.period_selection == 'window_overlap':
        if source.time_end_mjd < period_start_mjd or source.time_start_mjd > period_end_mjd:
            reasons.append('time_window_outside_period')
    elif selection.period_selection == 'anchor_inside':
        if source.time_anchor_mjd is None:
            reasons.append('missing_time_anchor')
        elif not period_start_mjd <= source.time_anchor_mjd <= period_end_mjd:
            reasons.append('time_anchor_outside_period')
    return tuple(reasons)


def _observable_fraction(source: CatalogSourceRecord, period_start_mjd: float, period_end_mjd: float) -> float:
    if source.time_start_mjd is None or source.time_end_mjd is None:
        raise ValueError(f'source {source.source_id!r} has no complete time window')
    overlap_start = max(source.time_start_mjd, period_start_mjd)
    overlap_end = min(source.time_end_mjd, period_end_mjd)
    if overlap_end <= overlap_start:
        return 0.0
    if source.time_profile_type == 'box':
        return (overlap_end - overlap_start) / source.time_width_days
    if source.time_sigma_days is None:
        raise ValueError(f'Gaussian source {source.source_id!r} has no time sigma')
    center = source.time_center_mjd
    scale = math.sqrt(2.0) * source.time_sigma_days
    numerator = math.erf((overlap_end - center) / scale) - math.erf((overlap_start - center) / scale)
    denominator = math.erf((source.time_end_mjd - center) / scale) - math.erf(
        (source.time_start_mjd - center) / scale
    )
    return numerator / denominator


def select_catalog_sources(
    config: CatalogAnalysisConfig,
    period_start_mjd: float,
    period_end_mjd: float,
) -> CatalogSelectionResult:
    """Apply catalog cuts and select either one source or the full stack."""

    if not math.isfinite(period_start_mjd) or not math.isfinite(period_end_mjd):
        raise ValueError('analysis period bounds must be finite')
    if period_end_mjd <= period_start_mjd:
        raise ValueError('analysis period must have positive width')

    records = load_catalog(config.catalog)
    selected_records = []
    excluded = []
    for source in records:
        reasons = _selection_reasons(source, config.catalog, period_start_mjd, period_end_mjd)
        if reasons:
            excluded.append(ExcludedCatalogSource(source=source, reasons=reasons))
        else:
            selected_records.append(source)

    if config.mode == 'single_source':
        selector = config.single_source
        matches = [s for s in selected_records if selector in (s.source_id, s.name)]
        if len(matches) != 1:
            raise ValueError(
                f'single-source selector {selector!r} matched {len(matches)} selected sources; expected exactly one'
            )
        chosen = matches[0]
        for source in selected_records:
            if source is not chosen:
                excluded.append(ExcludedCatalogSource(source=source, reasons=('not_selected_single_source',)))
        selected_records = matches

    if not selected_records:
        raise ValueError('catalog selection produced no sources')

    if any(source.weight_raw is None for source in selected_records):
        raise RuntimeError('selected sources unexpectedly contain missing weights')
    weight_sum = math.fsum(float(source.weight_raw) for source in selected_records)
    selected = tuple(
        SelectedCatalogSource(
            source=source,
            normalized_weight=float(source.weight_raw) / weight_sum,
            observable_window_fraction=_observable_fraction(source, period_start_mjd, period_end_mjd),
        )
        for source in selected_records
    )
    catalog_sha256 = hashlib.sha256(config.catalog.path.read_bytes()).hexdigest()
    return CatalogSelectionResult(
        catalog_path=config.catalog.path,
        catalog_sha256=catalog_sha256,
        period_start_mjd=period_start_mjd,
        period_end_mjd=period_end_mjd,
        selected=selected,
        excluded=tuple(excluded),
    )


def selected_sources_to_arrays(
    selected: Iterable[SelectedCatalogSource],
) -> tuple[tuple[PointLikeSource, ...], np.ndarray, np.ndarray]:
    """Return SkyLLH sources plus their box centers and widths."""

    selected = tuple(selected)
    return (
        tuple(item.to_source() for item in selected),
        np.asarray([item.source.time_center_mjd for item in selected], dtype=np.float64),
        np.asarray([item.source.time_width_days for item in selected], dtype=np.float64),
    )
