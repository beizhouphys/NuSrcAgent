"""Backend-neutral likelihood kernels for optimized shared-scramble trials."""

from __future__ import annotations

import math
import multiprocessing as mp
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise

import numpy as np
from scipy.optimize import minimize_scalar

from skyllh.core.random import RandomStateService
from skyllh.core.storage import DataFieldRecordArray
from skyllh.core.timing import TimeLord

from .analysis import ConstructedCatalogAnalysis

_FORKED_ENGINE: OptimizedSharedScrambleEngine | None = None


def _run_forked_trial(
    arguments: tuple[int, int],
) -> tuple[int, int, OptimizedCatalogFit]:
    """Run one trial using the engine inherited by a forked worker."""

    if _FORKED_ENGINE is None:
        raise RuntimeError('forked trial worker was not initialized')
    return _FORKED_ENGINE._do_trial(*arguments)


@dataclass(frozen=True)
class ProfileFit:
    """Result of one likelihood profile."""

    ts: float
    ns: float
    gamma: float | None
    fit_ok: bool
    gamma_status: str


@dataclass(frozen=True)
class OptimizedCatalogFit:
    """Independent-source and stacked fits from one shared event realization."""

    source_ts: np.ndarray
    source_ns: np.ndarray
    source_gamma: np.ndarray
    source_fit_ok: np.ndarray
    source_gamma_status: np.ndarray
    stack: ProfileFit


@dataclass(frozen=True)
class OptimizedCatalogTrials:
    """Dense optimized trial output, including the shared stacked fit."""

    trial_index: np.ndarray
    seed: np.ndarray
    source_ts: np.ndarray
    source_ns: np.ndarray
    source_gamma: np.ndarray
    source_fit_ok: np.ndarray
    stack_ts: np.ndarray
    stack_ns: np.ndarray
    stack_gamma: np.ndarray
    stack_fit_ok: np.ndarray


def _validate_phase_inputs(
    ratios: np.ndarray,
    pair_phase_indices: np.ndarray,
    phase_event_counts: np.ndarray,
    phase_yields: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    ratios = np.asarray(ratios, dtype=np.float64)
    pair_phase_indices = np.asarray(pair_phase_indices, dtype=np.int32)
    phase_event_counts = np.asarray(phase_event_counts, dtype=np.int64)
    phase_yields = np.asarray(phase_yields, dtype=np.float64)
    if ratios.ndim != 1 or pair_phase_indices.shape != ratios.shape:
        raise ValueError('ratios and pair_phase_indices must be same-length vectors')
    if phase_event_counts.ndim != 1 or phase_yields.shape != phase_event_counts.shape:
        raise ValueError('phase event counts and yields must be same-length vectors')
    if not len(phase_event_counts) or np.any(phase_event_counts <= 0):
        raise ValueError('phase event counts must be positive')
    if np.any(pair_phase_indices < 0) or np.any(pair_phase_indices >= len(phase_event_counts)):
        raise ValueError('pair phase index lies outside the configured phases')
    if not np.all(np.isfinite(ratios)) or np.any(ratios < 0):
        raise ValueError('signal-to-background ratios must be finite and nonnegative')
    if not np.all(np.isfinite(phase_yields)) or np.any(phase_yields < 0) or np.sum(phase_yields) <= 0:
        raise ValueError('phase yields must be finite, nonnegative and have a positive sum')
    selected_counts = np.bincount(pair_phase_indices, minlength=len(phase_event_counts))
    if np.any(selected_counts > phase_event_counts):
        raise ValueError('a phase contains more selected ratios than events')
    return ratios, pair_phase_indices, phase_event_counts, phase_yields


def fit_ns_multiphase(
    ratios: Sequence[float],
    pair_phase_indices: Sequence[int],
    phase_event_counts: Sequence[int],
    phase_yields: Sequence[float],
    *,
    ns_min: float = 0.0,
    ns_max: float = 1000.0,
    tolerance: float = 1e-10,
) -> tuple[float, float, bool]:
    """Profile one global ``ns`` across arbitrary detector phases.

    ``phase_yields`` are unnormalized expected signal yields.  Their normalized
    values are the SkyLLH dataset signal fractions, so phase ``j`` receives
    ``ns * f_j`` signal events.  ``ratios`` contains only events with nonzero
    signal support; omitted events contribute the analytic pure-background
    term.
    """

    ratios, pair_phase_indices, event_counts, yields = _validate_phase_inputs(
        np.asarray(ratios),
        np.asarray(pair_phase_indices),
        np.asarray(phase_event_counts),
        np.asarray(phase_yields),
    )
    if ns_min < 0 or ns_max < ns_min:
        raise ValueError('optimized conditional fits require 0 <= ns_min <= ns_max')
    fractions = yields / np.sum(yields)
    selected_counts = np.bincount(pair_phase_indices, minlength=len(event_counts))
    pure_background = event_counts - selected_counts
    pair_scale = fractions[pair_phase_indices] / event_counts[pair_phase_indices]
    coefficients = pair_scale * (ratios - 1.0)
    phase_scale = fractions / event_counts

    upper = float(ns_max)
    active_background = (pure_background > 0) & (fractions > 0)
    if np.any(active_background):
        upper = min(upper, float(np.min(event_counts[active_background] / fractions[active_background])))
        upper = float(np.nextafter(upper, -np.inf))
    lower = float(ns_min)
    if upper < lower:
        return np.nan, np.nan, False

    def score(ns: float) -> float:
        pair_denominator = 1.0 + ns * coefficients
        phase_denominator = 1.0 - ns * phase_scale
        if np.any(pair_denominator <= 0) or np.any(phase_denominator[active_background] <= 0):
            return -np.inf
        value = float(np.sum(coefficients / pair_denominator))
        value -= float(
            np.sum(pure_background[active_background] * phase_scale[active_background] / phase_denominator[active_background])
        )
        return value

    try:
        lower_score = score(lower)
        upper_score = score(upper)
        if lower_score <= 0:
            ns_hat = lower
        elif upper_score >= 0:
            ns_hat = upper
        else:
            lo, hi = lower, upper
            for _ in range(100):
                mid = 0.5 * (lo + hi)
                if score(mid) > 0:
                    lo = mid
                else:
                    hi = mid
                if hi - lo <= tolerance * max(1.0, abs(mid)):
                    break
            ns_hat = 0.5 * (lo + hi)
        log_lambda = float(np.sum(np.log1p(ns_hat * coefficients)))
        if np.any(active_background):
            log_lambda += float(
                np.sum(pure_background[active_background] * np.log1p(-ns_hat * phase_scale[active_background]))
            )
        ts = max(0.0, 2.0 * log_lambda)
        return ts, ns_hat, math.isfinite(ts) and math.isfinite(ns_hat)
    except (FloatingPointError, ValueError, ZeroDivisionError):
        return np.nan, np.nan, False


def profile_gamma_multiphase(
    gamma_grid: Sequence[float],
    ratio_grid: np.ndarray,
    pair_phase_indices: Sequence[int],
    phase_event_counts: Sequence[int],
    phase_yield_grid: np.ndarray,
    *,
    gamma_min: float | None = None,
    gamma_max: float | None = None,
    ns_min: float = 0.0,
    ns_max: float = 1000.0,
    refine_all_intervals: bool = True,
    gamma_tolerance: float = 1e-5,
) -> ProfileFit:
    """Reference global gamma profile using linear-density interpolation.

    This implementation deliberately favors auditability over production
    speed.  The compiled engine uses the same fixed-gamma kernel and is tested
    against this exhaustive interval search.
    """

    gamma_grid = np.asarray(gamma_grid, dtype=np.float64)
    ratio_grid = np.asarray(ratio_grid, dtype=np.float64)
    yield_grid = np.asarray(phase_yield_grid, dtype=np.float64)
    pair_phase_indices = np.asarray(pair_phase_indices, dtype=np.int32)
    event_counts = np.asarray(phase_event_counts, dtype=np.int64)
    if gamma_grid.ndim != 1 or len(gamma_grid) < 2 or np.any(np.diff(gamma_grid) <= 0):
        raise ValueError('gamma_grid must be a strictly increasing vector')
    if ratio_grid.shape != (len(gamma_grid), len(pair_phase_indices)):
        raise ValueError('ratio_grid must have shape (n_gamma, n_selected_pairs)')
    if yield_grid.shape != (len(gamma_grid), len(event_counts)):
        raise ValueError('phase_yield_grid must have shape (n_gamma, n_phases)')
    lo_bound = gamma_grid[0] if gamma_min is None else float(gamma_min)
    hi_bound = gamma_grid[-1] if gamma_max is None else float(gamma_max)
    if lo_bound < gamma_grid[0] or hi_bound > gamma_grid[-1] or lo_bound >= hi_bound:
        raise ValueError('requested gamma bounds lie outside gamma_grid')

    def interpolate(values: np.ndarray, gamma: float) -> np.ndarray:
        idx = int(np.clip(np.searchsorted(gamma_grid, gamma, side='right') - 1, 0, len(gamma_grid) - 2))
        weight = (gamma - gamma_grid[idx]) / (gamma_grid[idx + 1] - gamma_grid[idx])
        return (1.0 - weight) * values[idx] + weight * values[idx + 1]

    def evaluate(gamma: float) -> tuple[float, float, bool]:
        return fit_ns_multiphase(
            interpolate(ratio_grid, gamma),
            pair_phase_indices,
            event_counts,
            interpolate(yield_grid, gamma),
            ns_min=ns_min,
            ns_max=ns_max,
        )

    candidates = [lo_bound, hi_bound]
    interior = gamma_grid[(gamma_grid > lo_bound) & (gamma_grid < hi_bound)]
    candidates.extend(interior.tolist())
    node_results = {gamma: evaluate(gamma) for gamma in candidates}
    if refine_all_intervals:
        bounded_nodes = np.unique(np.r_[lo_bound, interior, hi_bound])
        for left, right in pairwise(bounded_nodes):
            result = minimize_scalar(
                lambda value: -evaluate(float(value))[0],
                bounds=(float(left), float(right)),
                method='bounded',
                options={'xatol': gamma_tolerance},
            )
            gamma = float(result.x)
            node_results[gamma] = evaluate(gamma)
    gamma_hat, (ts, ns_hat, fit_ok) = max(node_results.items(), key=lambda item: item[1][0])
    if not fit_ok:
        return ProfileFit(np.nan, np.nan, None, False, 'failed')
    if ns_hat == 0:
        return ProfileFit(ts, ns_hat, None, True, 'unidentified')
    at_boundary = np.isclose(gamma_hat, lo_bound, atol=gamma_tolerance) or np.isclose(
        gamma_hat, hi_bound, atol=gamma_tolerance
    )
    return ProfileFit(ts, ns_hat, gamma_hat, True, 'boundary' if at_boundary else 'interior')


class OptimizedSharedScrambleEngine:
    """Reuse each phase scramble and PDF evaluation for all sources and stack.

    The engine is backend-neutral: ratios come from the constructed SkyLLH
    graph, so both cached SkyLLH PDFs and strict precomputed PDFs use this same
    likelihood path.  s is evaluated on the configured grid and profiled
    with the same linear-density interpolation used by the precomputed backend.
    """

    def __init__(self, constructed: ConstructedCatalogAnalysis):
        if constructed.config.likelihood.ns_min < 0:
            raise ValueError('optimized shared-scramble analysis requires likelihood.ns_min >= 0')
        self.constructed = constructed
        if any(data.exp is None or len(data.exp) == 0 for data in constructed.data_list):
            raise ValueError('each detector phase must contain events for likelihood evaluation')

    @property
    def n_sources(self) -> int:
        return len(self.constructed.model.sources)

    def _gamma_grid(self) -> np.ndarray:
        spectrum = self.constructed.config.spectrum
        if spectrum.fit_gamma:
            return np.asarray(self.constructed.model.gamma_grid.grid, dtype=np.float64)
        return np.asarray([spectrum.gamma], dtype=np.float64)

    def _evaluate_grid(
        self,
        events_list: Sequence[DataFieldRecordArray],
        n_events_list: Sequence[int],
        tl: TimeLord | None,
    ) -> tuple[
        np.ndarray,
        list[np.ndarray],
        list[np.ndarray],
        list[np.ndarray],
        np.ndarray,
    ]:
        analysis = self.constructed.analysis
        analysis.initialize_trial(events_list=list(events_list), n_events_list=list(n_events_list), tl=tl)
        for ratio, tdm in zip(self.constructed.pdfratios, self.constructed.tdms, strict=True):
            ratio.initialize_for_new_trial(tdm=tdm, tl=tl)

        gamma_grid = self._gamma_grid()
        n_gamma = len(gamma_grid)
        phase_yield_grid = np.empty((n_gamma, len(events_list), self.n_sources), dtype=np.float64)
        phase_ratio_grids: list[np.ndarray] = []
        phase_src_indices: list[np.ndarray] = []
        phase_event_indices: list[np.ndarray] = []
        gamma_gflp_idx = (
            analysis.pmm.get_gflp_idx('gamma') if self.constructed.config.spectrum.fit_gamma else None
        )
        for tdm in self.constructed.tdms:
            if tdm.src_evt_idxs is None:
                raise RuntimeError('trial initialization did not create source-event indices')
            phase_src_indices.append(np.asarray(tdm.src_evt_idxs[0], dtype=np.int32))
            phase_event_indices.append(np.asarray(tdm.src_evt_idxs[1], dtype=np.int64))
            phase_ratio_grids.append(np.empty((n_gamma, len(tdm.src_evt_idxs[0])), dtype=np.float64))

        for gamma_idx, gamma in enumerate(gamma_grid):
            gflp_values = np.zeros(analysis.pmm.n_global_floating_params, dtype=np.float64)
            if gamma_gflp_idx is not None:
                gflp_values[gamma_gflp_idx] = gamma
            src_params = analysis.pmm.create_src_params_recarray(gflp_values=gflp_values)
            analysis.src_detsigyield_weights_service.calculate(src_params_recarray=src_params)
            weights, _ = analysis.src_detsigyield_weights_service.get_weights()
            if weights is None:
                raise RuntimeError('detector signal yield service did not calculate weights')
            phase_yield_grid[gamma_idx] = weights
            for phase_idx, (ratio, tdm) in enumerate(
                zip(self.constructed.pdfratios, self.constructed.tdms, strict=True)
            ):
                phase_ratio_grids[phase_idx][gamma_idx] = ratio.get_ratio(
                    tdm=tdm,
                    src_params_recarray=src_params,
                    tl=tl,
                )
        return (
            gamma_grid,
            phase_ratio_grids,
            phase_src_indices,
            phase_event_indices,
            phase_yield_grid,
        )

    def _profile(
        self,
        gamma_grid: np.ndarray,
        ratio_grid: np.ndarray,
        pair_phase_indices: np.ndarray,
        event_counts: np.ndarray,
        yield_grid: np.ndarray,
    ) -> ProfileFit:
        likelihood = self.constructed.config.likelihood
        spectrum = self.constructed.config.spectrum
        if spectrum.fit_gamma:
            return profile_gamma_multiphase(
                gamma_grid,
                ratio_grid,
                pair_phase_indices,
                event_counts,
                yield_grid,
                gamma_min=spectrum.gamma_min,
                gamma_max=spectrum.gamma_max,
                ns_min=likelihood.ns_min,
                ns_max=likelihood.ns_max,
            )
        ts, ns, ok = fit_ns_multiphase(
            ratio_grid[0],
            pair_phase_indices,
            event_counts,
            yield_grid[0],
            ns_min=likelihood.ns_min,
            ns_max=likelihood.ns_max,
        )
        return ProfileFit(ts, ns, spectrum.gamma if ns > 0 else None, ok, 'fixed')

    def fit_events(
        self,
        events_list: Sequence[DataFieldRecordArray],
        n_events_list: Sequence[int] | None = None,
        tl: TimeLord | None = None,
    ) -> OptimizedCatalogFit:
        """Fit every source independently and the stack to shared phase events."""

        if len(events_list) != len(self.constructed.datasets):
            raise ValueError('events_list must contain one event array per configured phase')
        if n_events_list is None:
            n_events_list = [len(events) for events in events_list]
        event_counts = np.asarray(n_events_list, dtype=np.int64)
        (
            gamma_grid,
            ratio_grids,
            src_indices,
            event_indices,
            yield_grid,
        ) = self._evaluate_grid(events_list, event_counts, tl)
        source_fits = []
        for source_idx in range(self.n_sources):
            grids = []
            phase_idxs = []
            for phase_idx, (grid, indices) in enumerate(zip(ratio_grids, src_indices, strict=True)):
                mask = indices == source_idx
                grids.append(grid[:, mask])
                phase_idxs.append(np.full(np.count_nonzero(mask), phase_idx, dtype=np.int32))
            source_fits.append(
                self._profile(
                    gamma_grid,
                    np.concatenate(grids, axis=1),
                    np.concatenate(phase_idxs),
                    event_counts,
                    yield_grid[:, :, source_idx],
                )
            )

        stack_grids = []
        stack_phase_idxs = []
        for phase_idx, (grid, sources, events) in enumerate(
            zip(ratio_grids, src_indices, event_indices, strict=True)
        ):
            unique_events, inverse = np.unique(events, return_inverse=True)
            stacked = np.zeros((len(gamma_grid), len(unique_events)), dtype=np.float64)
            for gamma_idx in range(len(gamma_grid)):
                np.add.at(
                    stacked[gamma_idx],
                    inverse,
                    grid[gamma_idx] * yield_grid[gamma_idx, phase_idx, sources],
                )
                stacked[gamma_idx] /= np.sum(yield_grid[gamma_idx, phase_idx])
            stack_grids.append(stacked)
            stack_phase_idxs.append(np.full(len(unique_events), phase_idx, dtype=np.int32))
        stack_fit = self._profile(
            gamma_grid,
            np.concatenate(stack_grids, axis=1),
            np.concatenate(stack_phase_idxs),
            event_counts,
            np.sum(yield_grid, axis=2),
        )
        return OptimizedCatalogFit(
            source_ts=np.asarray([fit.ts for fit in source_fits]),
            source_ns=np.asarray([fit.ns for fit in source_fits]),
            source_gamma=np.asarray([np.nan if fit.gamma is None else fit.gamma for fit in source_fits]),
            source_fit_ok=np.asarray([fit.fit_ok for fit in source_fits]),
            source_gamma_status=np.asarray([fit.gamma_status for fit in source_fits]),
            stack=stack_fit,
        )

    def fit_observed(self, tl: TimeLord | None = None) -> OptimizedCatalogFit:
        events = []
        for data in self.constructed.data_list:
            if data.exp is None:
                raise RuntimeError('constructed phase has no experimental data')
            events.append(data.exp)
        return self.fit_events(events, tl=tl)

    def _do_trial(
        self, trial_index: int, base_seed: int
    ) -> tuple[int, int, OptimizedCatalogFit]:
        from .seeds import trial_seed

        seed = trial_seed(base_seed, trial_index)
        counts, events = self.constructed.analysis.generate_background_events(
            rss=RandomStateService(seed=seed),
        )
        return trial_index, seed, self.fit_events(events, counts)

    def run_trials(
        self,
        *,
        n_trials: int,
        base_seed: int,
        trial_index_start: int = 0,
        n_workers: int = 1,
    ) -> OptimizedCatalogTrials:
        """Run deterministic trials serially or in forked shared-memory workers."""

        if n_trials <= 0 or trial_index_start < 0 or n_workers <= 0:
            raise ValueError('n_trials and n_workers must be positive and trial_index_start nonnegative')
        arguments = [
            (index, base_seed) for index in range(trial_index_start, trial_index_start + n_trials)
        ]
        if n_workers == 1:
            results = [self._do_trial(*item) for item in arguments]
        else:
            global _FORKED_ENGINE
            if 'fork' not in mp.get_all_start_methods():
                raise RuntimeError('parallel shared-memory trials require the multiprocessing fork method')
            _FORKED_ENGINE = self
            try:
                with mp.get_context('fork').Pool(processes=min(n_workers, n_trials)) as pool:
                    results = pool.map(_run_forked_trial, arguments, chunksize=1)
            finally:
                _FORKED_ENGINE = None
        fits = [item[2] for item in results]
        result_fields = {
            'trial_index': np.asarray([item[0] for item in results], dtype=np.int64),
            'seed': np.asarray([item[1] for item in results], dtype=np.uint64),
            'source_ts': np.stack([fit.source_ts for fit in fits]),
            'source_ns': np.stack([fit.source_ns for fit in fits]),
            'source_gamma': np.stack([fit.source_gamma for fit in fits]),
            'source_fit_ok': np.stack([fit.source_fit_ok for fit in fits]),
            'stack_ts': np.asarray([fit.stack.ts for fit in fits]),
            'stack_ns': np.asarray([fit.stack.ns for fit in fits]),
            'stack_gamma': np.asarray(
                [np.nan if fit.stack.gamma is None else fit.stack.gamma for fit in fits]
            ),
            'stack_fit_ok': np.asarray([fit.stack.fit_ok for fit in fits]),
        }
        return OptimizedCatalogTrials(**result_fields)
