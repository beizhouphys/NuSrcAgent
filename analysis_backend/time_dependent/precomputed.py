"""Strict adapters for supplied, phase-independent DR2 PDF products."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from skyllh.core.pdf import PDF, IsBackgroundPDF, PDFAxis
from skyllh.core.pdfratio import PDFRatio
from skyllh.core.timing import TimeLord
from skyllh.core.trialdata import TrialDataManager

from .config import PrecomputedPhasePDFConfig


def file_sha256(path: str | Path) -> str:
    """Return the SHA-256 digest used in analysis provenance."""

    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class BoundPrecomputedBackground:
    """Event-ordered background densities bound to one loaded SkyLLH dataset."""

    spatial: np.ndarray
    energy: np.ndarray
    raw_row_indices: np.ndarray


class PrecomputedSignalEnergyGrid:
    """Signal-energy density grid indexed by declination bin, energy and gamma."""

    REQUIRED_ARRAYS = (
        'dec_bin_edges_rad',
        'dec_bin_centers_rad',
        'log10_reco_energy',
        'gamma_skyllh',
        'signal_energy_pdf',
    )

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser().resolve()
        with np.load(self.path, allow_pickle=False) as archive:
            missing = [name for name in self.REQUIRED_ARRAYS if name not in archive]
            if missing:
                raise ValueError(f'precomputed signal grid is missing arrays: {missing}')
            self.dec_bin_edges = np.asarray(archive['dec_bin_edges_rad'], dtype=np.float64)
            self.dec_bin_centers = np.asarray(archive['dec_bin_centers_rad'], dtype=np.float64)
            self.log_energy = np.asarray(archive['log10_reco_energy'], dtype=np.float64)
            self.gamma = np.asarray(archive['gamma_skyllh'], dtype=np.float64)
            self.density = np.asarray(archive['signal_energy_pdf'])
            self.axis_order = str(archive['axis_order']) if 'axis_order' in archive else None
            self.spectrum_mode = str(archive['spectrum_mode']) if 'spectrum_mode' in archive else None
        self.gamma_axis_reversed = False
        if np.all(np.diff(self.gamma) < 0):
            self.gamma = self.gamma[::-1].copy()
            self.density = self.density[:, :, ::-1]
            self.gamma_axis_reversed = True
        self._validate()

    def _validate(self) -> None:
        for name, values in (
            ('dec_bin_edges_rad', self.dec_bin_edges),
            ('dec_bin_centers_rad', self.dec_bin_centers),
            ('log10_reco_energy', self.log_energy),
            ('gamma_skyllh', self.gamma),
        ):
            if values.ndim != 1 or len(values) < 2 or not np.all(np.isfinite(values)):
                raise ValueError(f'{name} must be a finite one-dimensional axis')
            if np.any(np.diff(values) <= 0):
                raise ValueError(f'{name} must be strictly increasing')
        expected = (len(self.dec_bin_centers), len(self.log_energy), len(self.gamma))
        if len(self.dec_bin_edges) != len(self.dec_bin_centers) + 1:
            raise ValueError('signal declination edges and centers have inconsistent lengths')
        if self.density.shape != expected:
            raise ValueError(f'signal_energy_pdf has shape {self.density.shape}; expected {expected}')
        if self.density.dtype.kind != 'f' or not np.all(np.isfinite(self.density)) or np.any(self.density < 0):
            raise ValueError('signal_energy_pdf must contain finite nonnegative floating-point densities')
        if self.dec_bin_edges[0] < -np.pi / 2 or self.dec_bin_edges[-1] > np.pi / 2:
            raise ValueError('signal declination edges lie outside [-pi/2, pi/2]')

    def validate_gamma_bounds(self, gamma_min: float, gamma_max: float) -> None:
        if gamma_min >= gamma_max:
            raise ValueError('gamma_min must be smaller than gamma_max')
        if gamma_min < self.gamma[0] or gamma_max > self.gamma[-1]:
            raise ValueError(
                f'gamma range [{gamma_min}, {gamma_max}] lies outside supplied support '
                f'[{self.gamma[0]}, {self.gamma[-1]}]'
            )

    def declination_bins(self, source_decs: Sequence[float]) -> np.ndarray:
        source_decs = np.asarray(source_decs, dtype=np.float64)
        if source_decs.ndim != 1 or not len(source_decs) or not np.all(np.isfinite(source_decs)):
            raise ValueError('source declinations must be a finite non-empty vector')
        if np.any(source_decs < self.dec_bin_edges[0]) or np.any(source_decs > self.dec_bin_edges[-1]):
            raise ValueError('source declination lies outside the supplied signal grid')
        return np.clip(
            np.searchsorted(self.dec_bin_edges, source_decs, side='right') - 1,
            0,
            len(self.dec_bin_centers) - 1,
        ).astype(np.int32)

    @staticmethod
    def _linear_coordinates(axis: np.ndarray, values: np.ndarray, name: str) -> tuple[np.ndarray, np.ndarray]:
        if np.any(~np.isfinite(values)) or np.any(values < axis[0]) or np.any(values > axis[-1]):
            raise ValueError(f'{name} lies outside the supplied grid support')
        lower = np.searchsorted(axis, values, side='right') - 1
        lower = np.clip(lower, 0, len(axis) - 2)
        weight = (values - axis[lower]) / (axis[lower + 1] - axis[lower])
        return lower, weight

    def evaluate(
        self,
        source_bin_indices: Sequence[int],
        log_energy: Sequence[float],
        gamma: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return linearly interpolated densities and their gamma derivatives."""

        bins = np.asarray(source_bin_indices, dtype=np.int64)
        energies = np.asarray(log_energy, dtype=np.float64)
        if bins.shape != energies.shape:
            raise ValueError('source-bin and energy arrays must have identical shapes')
        if np.any(bins < 0) or np.any(bins >= len(self.dec_bin_centers)):
            raise ValueError('source response bin lies outside the supplied signal grid')
        energy_idx, energy_weight = self._linear_coordinates(self.log_energy, energies, 'log energy')
        gamma_idx, gamma_weight = self._linear_coordinates(self.gamma, np.asarray([gamma], dtype=np.float64), 'gamma')
        g = int(gamma_idx[0])
        wg = float(gamma_weight[0])
        e0 = self.density[bins, energy_idx, g]
        e1 = self.density[bins, energy_idx + 1, g]
        next0 = self.density[bins, energy_idx, g + 1]
        next1 = self.density[bins, energy_idx + 1, g + 1]
        at_g = (1.0 - energy_weight) * e0 + energy_weight * e1
        at_next = (1.0 - energy_weight) * next0 + energy_weight * next1
        values = (1.0 - wg) * at_g + wg * at_next
        gradient = (at_next - at_g) / (self.gamma[g + 1] - self.gamma[g])
        return np.asarray(values, dtype=np.float64), np.asarray(gradient, dtype=np.float64)

    def metadata(self) -> dict[str, Any]:
        return {
            'path': str(self.path),
            'sha256': file_sha256(self.path),
            'shape': list(self.density.shape),
            'dtype': str(self.density.dtype),
            'gamma_range': [float(self.gamma[0]), float(self.gamma[-1])],
            'log_energy_range': [float(self.log_energy[0]), float(self.log_energy[-1])],
            'axis_order': self.axis_order,
            'spectrum_mode': self.spectrum_mode,
            'gamma_axis_reversed_to_increasing_skyllh_convention': self.gamma_axis_reversed,
        }


class PrecomputedEventBackgroundTable:
    """Supplied event-indexed spatial and energy background densities.

    The table is first checked against the raw public-data CSV files that
    define its row order.  It can then be bound by native event identity to any
    loaded SkyLLH phase containing an arbitrary subset of those rows.
    """

    ID_FIELDS = ('run', 'event', 'subevent')
    MARK_FIELDS = ('time', 'log_energy', 'ang_err', 'ra', 'dec', 'azi', 'zen')

    def __init__(self, config: PrecomputedPhasePDFConfig):
        self.config = config
        table = np.loadtxt(config.background_path, ndmin=2)
        if table.ndim != 2 or table.shape[1] != 4:
            raise ValueError('precomputed background table must have four columns')
        if not np.all(np.isfinite(table)) or np.any(table[:, 2:] <= 0):
            raise ValueError('precomputed background densities must be finite and positive')
        if np.any(table[:, 0] < 0) or np.any(table[:, 0] > 360) or np.any(np.abs(table[:, 1]) > 90):
            raise ValueError('precomputed background coordinates are outside their physical ranges')

        raw_parts = []
        for path in config.event_paths:
            events = np.loadtxt(path, ndmin=2)
            if events.ndim != 2 or events.shape[1] != 10 or not np.all(np.isfinite(events)):
                raise ValueError(f'invalid public DR2 event table {path}')
            raw_parts.append(events)
        raw = np.concatenate(raw_parts)
        if len(raw) != len(table):
            raise ValueError(f'background table has {len(table)} rows but configured event files have {len(raw)} rows')
        if not np.array_equal(table[:, :2], raw[:, 6:8]):
            raise ValueError('precomputed background RA/declination rows do not match configured event files')
        native_ids = raw[:, :3]
        if np.any(native_ids != np.floor(native_ids)) or np.any(native_ids < 0):
            raise ValueError('native DR2 event identifiers must be nonnegative integers')
        ids = np.empty(len(raw), dtype=[(name, np.int64) for name in self.ID_FIELDS])
        for idx, name in enumerate(self.ID_FIELDS):
            ids[name] = native_ids[:, idx].astype(np.int64)
        order = np.argsort(ids, order=self.ID_FIELDS)
        if len(ids) > 1 and np.any(ids[order][1:] == ids[order][:-1]):
            raise ValueError('configured event files contain duplicate native event identifiers')
        self.table = table
        self.raw_events = raw
        self.native_ids = ids
        self._sorted_ids = ids[order]
        self._sorted_rows = order.astype(np.int64)
        fallback_dtype = [('run', np.int64), *((name, np.float64) for name in self.MARK_FIELDS)]
        fallback = np.empty(len(raw), dtype=fallback_dtype)
        fallback['run'] = native_ids[:, 0].astype(np.int64)
        fallback['time'] = raw[:, 3]
        fallback['log_energy'] = raw[:, 4]
        fallback['ang_err'] = np.deg2rad(raw[:, 5])
        fallback['ra'] = np.deg2rad(raw[:, 6])
        fallback['dec'] = np.deg2rad(raw[:, 7])
        fallback['azi'] = np.deg2rad(raw[:, 8])
        fallback['zen'] = np.deg2rad(raw[:, 9])
        fallback_order = np.argsort(fallback, order=tuple(fallback.dtype.names or ()))
        if len(fallback) > 1 and np.any(fallback[fallback_order][1:] == fallback[fallback_order][:-1]):
            raise ValueError('configured event files contain duplicate immutable-mark fallback identifiers')
        self._sorted_fallback = fallback[fallback_order]
        self._sorted_fallback_rows = fallback_order.astype(np.int64)

    @staticmethod
    def _field_names(events: Any) -> set[str]:
        if hasattr(events, 'field_name_list'):
            return set(events.field_name_list)
        dtype = getattr(events, 'dtype', None)
        return set(dtype.names or ())

    def bind(self, events: Any, *, verify_event_coordinates: bool = True) -> BoundPrecomputedBackground:
        names = self._field_names(events)
        if all(name in names for name in self.ID_FIELDS):
            used_native_ids = True
            query = np.empty(len(events), dtype=self.native_ids.dtype)
            for name in self.ID_FIELDS:
                query[name] = np.asarray(events[name], dtype=np.int64)
            sorted_keys = self._sorted_ids
            sorted_rows = self._sorted_rows
        elif {'run', *self.MARK_FIELDS}.issubset(names):
            used_native_ids = False
            query = np.empty(len(events), dtype=self._sorted_fallback.dtype)
            query['run'] = np.asarray(events['run'], dtype=np.int64)
            for name in self.MARK_FIELDS:
                query[name] = np.asarray(events[name], dtype=np.float64)
            sorted_keys = self._sorted_fallback
            sorted_rows = self._sorted_fallback_rows
        else:
            raise ValueError(
                'loaded events require native (run,event,subevent) fields or the complete immutable-mark fallback'
            )
        positions = np.searchsorted(sorted_keys, query)
        valid = positions < len(sorted_keys)
        matched = np.zeros(len(query), dtype=bool)
        matched[valid] = sorted_keys[positions[valid]] == query[valid]
        if not np.all(matched):
            raise ValueError(f'{np.count_nonzero(~matched)} loaded events are absent from the background row mapping')
        rows = sorted_rows[positions]
        if len(np.unique(rows)) != len(rows):
            raise ValueError('loaded events map to duplicate background rows')
        if verify_event_coordinates:
            required_marks = ('ra', 'dec') if used_native_ids else self.MARK_FIELDS
            for name in required_marks:
                if name not in names:
                    raise ValueError(f'loaded events are missing immutable mark field {name!r}')
            raw_columns = {
                'time': self.raw_events[rows, 3],
                'log_energy': self.raw_events[rows, 4],
                'ang_err': np.deg2rad(self.raw_events[rows, 5]),
                'ra': np.deg2rad(self.raw_events[rows, 6]),
                'dec': np.deg2rad(self.raw_events[rows, 7]),
                'azi': np.deg2rad(self.raw_events[rows, 8]),
                'zen': np.deg2rad(self.raw_events[rows, 9]),
            }
            for name in required_marks:
                expected = raw_columns[name]
                tolerance = 1e-10 if name == 'time' else 5e-12
                if not np.allclose(events[name], expected, rtol=0, atol=tolerance):
                    raise ValueError(f'loaded event {name} values differ from the background mapping')
        return BoundPrecomputedBackground(
            spatial=np.asarray(self.table[rows, 2], dtype=np.float64),
            energy=np.asarray(self.table[rows, 3], dtype=np.float64),
            raw_row_indices=rows,
        )

    def metadata(self) -> dict[str, Any]:
        return {
            'path': str(self.config.background_path),
            'sha256': file_sha256(self.config.background_path),
            'n_rows': len(self.table),
            'event_paths': [str(path) for path in self.config.event_paths],
            'event_sha256': [file_sha256(path) for path in self.config.event_paths],
            'mapping': (
                'native (run,event,subevent) identity when retained by the loader; otherwise the complete immutable '
                'event-mark tuple; all marks checked against the public event rows'
            ),
            'density_columns': {'spatial': 2, 'energy': 3},
        }


class EventIndexedBackgroundPDF(PDF, IsBackgroundPDF):
    """A SkyLLH background PDF whose values remain attached to event IDs."""

    def __init__(
        self,
        values: Sequence[float],
        event_id_field: str = 'catalog_event_id',
        axes: Sequence[PDFAxis] = (),
        **kwargs,
    ):
        values = np.asarray(values, dtype=np.float64)
        if values.ndim != 1 or not len(values) or not np.all(np.isfinite(values)) or np.any(values <= 0):
            raise ValueError('event-indexed background values must be a finite positive vector')
        self._values = values
        self._event_id_field = event_id_field
        self._pd: np.ndarray | None = None
        super().__init__(pmm=None, **kwargs)
        for axis in axes:
            self.add_axis(PDFAxis(axis.name, axis.vmin, axis.vmax))

    @property
    def values(self) -> np.ndarray:
        return self._values

    def _event_ids(self, tdm: TrialDataManager) -> np.ndarray:
        if self._event_id_field not in tdm:
            raise KeyError(f'trial data is missing event ID field {self._event_id_field!r}')
        event_ids = np.asarray(tdm[self._event_id_field], dtype=np.int64)
        if np.any(event_ids < 0) or np.any(event_ids >= len(self._values)):
            raise ValueError('trial event ID lies outside the event-indexed background table')
        return event_ids

    def assert_is_valid_for_trial_data(
        self,
        tdm: TrialDataManager,
        tl: TimeLord | None = None,
        **kwargs,
    ) -> None:
        self._event_ids(tdm)

    def initialize_for_new_trial(self, tdm: TrialDataManager, tl: TimeLord | None = None, **kwargs):
        self._pd = self._values[self._event_ids(tdm)]

    def get_pd(
        self,
        tdm: TrialDataManager,
        params_recarray: np.ndarray | None = None,
        tl: TimeLord | None = None,
    ) -> tuple[np.ndarray, dict]:
        if self._pd is None:
            self.initialize_for_new_trial(tdm=tdm, tl=tl)
        assert self._pd is not None
        return self._pd, {}


class PrecomputedSignalEnergyPDFRatio(PDFRatio):
    """Evaluate supplied signal grids over event-indexed background energy PDFs."""

    def __init__(
        self,
        grid: PrecomputedSignalEnergyGrid,
        source_bin_indices: Sequence[int],
        background_energy: Sequence[float],
        event_id_field: str = 'catalog_event_id',
        **kwargs,
    ):
        source_bin_indices = np.asarray(source_bin_indices, dtype=np.int32)
        background_energy = np.asarray(background_energy, dtype=np.float64)
        if source_bin_indices.ndim != 1 or not len(source_bin_indices):
            raise ValueError('source_bin_indices must be a non-empty vector')
        if np.any(source_bin_indices < 0) or np.any(source_bin_indices >= len(grid.dec_bin_centers)):
            raise ValueError('source response bin lies outside the supplied signal grid')
        if (
            background_energy.ndim != 1
            or not len(background_energy)
            or not np.all(np.isfinite(background_energy))
            or np.any(background_energy <= 0)
        ):
            raise ValueError('background_energy must be a finite positive vector')
        self._grid = grid
        self._source_bin_indices = source_bin_indices
        self._background_energy = background_energy
        self._event_id_field = event_id_field
        super().__init__(sig_param_names=('gamma',), bkg_param_names=(), **kwargs)

    def initialize_for_new_trial(self, tdm: TrialDataManager, tl: TimeLord | None = None, **kwargs):
        if tdm.n_sources != len(self._source_bin_indices):
            raise ValueError('trial source count does not match supplied-grid source bins')
        if self._event_id_field not in tdm:
            raise KeyError(f'trial data is missing event ID field {self._event_id_field!r}')

    def _evaluate(
        self,
        tdm: TrialDataManager,
        src_params_recarray: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        if tdm.src_evt_idxs is None:
            raise ValueError('trial data has no source-event index mapping')
        src_idxs, evt_idxs = tdm.src_evt_idxs
        event_ids = np.asarray(tdm[self._event_id_field][evt_idxs], dtype=np.int64)
        if np.any(event_ids < 0) or np.any(event_ids >= len(self._background_energy)):
            raise ValueError('trial event ID lies outside the event-indexed background table')
        energies = np.asarray(tdm['log_energy'][evt_idxs], dtype=np.float64)
        gammas = np.asarray(src_params_recarray['gamma'][src_idxs], dtype=np.float64)
        response_bins = self._source_bin_indices[src_idxs]
        signal = np.empty(len(src_idxs), dtype=np.float64)
        signal_gradient = np.empty(len(src_idxs), dtype=np.float64)
        for gamma in np.unique(gammas):
            mask = gammas == gamma
            signal[mask], signal_gradient[mask] = self._grid.evaluate(response_bins[mask], energies[mask], float(gamma))
        background = self._background_energy[event_ids]
        return signal / background, signal_gradient / background, src_idxs

    def get_ratio(
        self,
        tdm: TrialDataManager,
        src_params_recarray: np.ndarray,
        tl: TimeLord | None = None,
    ) -> np.ndarray:
        ratio, _, _ = self._evaluate(tdm, src_params_recarray)
        return ratio

    def get_gradient(
        self,
        tdm: TrialDataManager,
        src_params_recarray: np.ndarray,
        fitparam_id: int,
        tl: TimeLord | None = None,
    ) -> np.ndarray:
        _, gradient, src_idxs = self._evaluate(tdm, src_params_recarray)
        source_mask = src_params_recarray['gamma:gpidx'] == fitparam_id + 1
        return np.where(source_mask[src_idxs], gradient, 0.0)

