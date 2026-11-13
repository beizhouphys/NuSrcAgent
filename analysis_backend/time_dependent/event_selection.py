"""Sparse event selection for catalog sources with fixed time windows."""

from __future__ import annotations

from typing import Literal, overload

import numpy as np

from skyllh.core.event_selection import SpatialEventSelectionMethod
from skyllh.core.source_hypo_grouping import SourceHypoGroupManager
from skyllh.core.storage import DataFieldRecordArray
from skyllh.core.timing import TaskTimer, TimeLord

_SelectEventsReturn2 = tuple[DataFieldRecordArray, tuple[np.ndarray, np.ndarray]]
_SelectEventsReturn3 = tuple[DataFieldRecordArray, tuple[np.ndarray, np.ndarray], np.ndarray]
_SelectEventsReturn = _SelectEventsReturn2 | _SelectEventsReturn3


class SourceTimeSpatialBoxEventSelectionMethod(SpatialEventSelectionMethod):
    """Select only source-event pairs inside fixed time and spatial boxes.

    Unlike SkyLLH's dense spatial-box selector, this implementation sorts the
    event times once and processes each source's much smaller time slice.  A
    pair outside its source time window has exactly zero signal probability,
    so removing it does not approximate or otherwise alter the likelihood.
    """

    def __init__(
        self,
        shg_mgr: SourceHypoGroupManager,
        time_centers_mjd: np.ndarray,
        time_widths_days: np.ndarray,
        delta_angle: float,
    ):
        self._time_centers_mjd = np.asarray(time_centers_mjd, dtype=np.float64)
        self._time_widths_days = np.asarray(time_widths_days, dtype=np.float64)
        self._delta_angle = float(delta_angle)
        if self._time_centers_mjd.ndim != 1 or self._time_widths_days.ndim != 1:
            raise ValueError('source time center and width arrays must be one-dimensional')
        if self._time_centers_mjd.shape != self._time_widths_days.shape:
            raise ValueError('source time center and width arrays must have the same shape')
        if not np.all(np.isfinite(self._time_centers_mjd)):
            raise ValueError('source time centers must be finite')
        if not np.all(np.isfinite(self._time_widths_days)) or np.any(self._time_widths_days <= 0):
            raise ValueError('source time widths must be finite and positive')
        if not np.isfinite(self._delta_angle) or self._delta_angle <= 0:
            raise ValueError('delta_angle must be finite and positive')
        super().__init__(shg_mgr=shg_mgr)
        self._validate_source_count()

    def _validate_source_count(self) -> None:
        if self._src_arr is not None and len(self._src_arr) != len(self._time_centers_mjd):
            raise ValueError('source time arrays must contain exactly one entry per source')

    def change_shg_mgr(self, shg_mgr: SourceHypoGroupManager | None):
        super().change_shg_mgr(shg_mgr=shg_mgr)
        self._validate_source_count()

    @overload
    def select_events(
        self,
        events: DataFieldRecordArray,
        src_evt_idxs: tuple | None = None,
        ret_original_evt_idxs: Literal[False] = False,
        tl: TimeLord | None = None,
    ) -> _SelectEventsReturn2: ...

    @overload
    def select_events(
        self,
        events: DataFieldRecordArray,
        src_evt_idxs: tuple | None = None,
        *,
        ret_original_evt_idxs: Literal[True],
        tl: TimeLord | None = None,
    ) -> _SelectEventsReturn3: ...

    def select_events(
        self,
        events: DataFieldRecordArray,
        src_evt_idxs: tuple | None = None,
        ret_original_evt_idxs: bool = False,
        tl: TimeLord | None = None,
    ) -> _SelectEventsReturn:
        if src_evt_idxs is not None:
            raise ValueError('source-time spatial selection must be the first event-selection method')
        for field in ('time', 'ra', 'dec'):
            if field not in events:
                raise KeyError(f'event data is missing required field {field!r}')
        assert self._src_arr is not None

        with TaskTimer(tl, 'ESM-SourceTimeSpatialBox: Sort event times.'):
            time_order = np.argsort(events['time'], kind='stable')
            sorted_times = events['time'][time_order]

        src_ra = self._src_arr['ra']
        src_dec = self._src_arr['dec']
        starts = self._time_centers_mjd - 0.5 * self._time_widths_days
        stops = self._time_centers_mjd + 0.5 * self._time_widths_days
        dec_minus = np.maximum(-np.pi / 2, src_dec - self._delta_angle)
        dec_plus = np.minimum(np.pi / 2, src_dec + self._delta_angle)
        cosfact = np.minimum(np.cos(dec_minus), np.cos(dec_plus))
        dra_half = np.minimum(2 * np.pi, np.abs(self._delta_angle / cosfact))

        pair_sources = []
        pair_events = []
        with TaskTimer(tl, 'ESM-SourceTimeSpatialBox: Select sparse source-event pairs.'):
            for source_idx in range(len(src_ra)):
                first = np.searchsorted(sorted_times, starts[source_idx], side='left')
                last = np.searchsorted(sorted_times, stops[source_idx], side='right')
                candidate_idxs = time_order[first:last]
                if len(candidate_idxs) == 0:
                    continue

                candidate_dec = events['dec'][candidate_idxs]
                candidate_idxs = candidate_idxs[
                    (candidate_dec > dec_minus[source_idx]) & (candidate_dec < dec_plus[source_idx])
                ]
                if len(candidate_idxs) == 0:
                    continue

                ra_diff = np.abs(events['ra'][candidate_idxs] - src_ra[source_idx])
                ra_diff = np.minimum(ra_diff, 2 * np.pi - ra_diff)
                candidate_idxs = candidate_idxs[ra_diff < dra_half[source_idx]]
                if len(candidate_idxs) == 0:
                    continue

                pair_sources.append(np.full(len(candidate_idxs), source_idx, dtype=np.int32))
                pair_events.append(candidate_idxs.astype(np.int32, copy=False))

        if pair_events:
            src_idxs = np.concatenate(pair_sources)
            original_pair_evt_idxs = np.concatenate(pair_events)
            selected_positions = np.unique(original_pair_evt_idxs)
            evt_idxs = np.searchsorted(selected_positions, original_pair_evt_idxs).astype(np.int32, copy=False)
        else:
            src_idxs = np.empty(0, dtype=np.int32)
            evt_idxs = np.empty(0, dtype=np.int32)
            selected_positions = np.empty(0, dtype=np.int32)

        original_evt_idxs = events.indices[selected_positions]
        selected_events = events[original_evt_idxs]
        result = (selected_events, (src_idxs, evt_idxs))
        if ret_original_evt_idxs:
            return (*result, original_evt_idxs)
        return result

