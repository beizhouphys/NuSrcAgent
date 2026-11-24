"""Batched fixed-gamma trials with cross-trial precomputed PDF invariants."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numba import njit, prange

from .analysis import ConstructedCatalogAnalysis
from .optimized import OptimizedCatalogFit, OptimizedCatalogTrials, ProfileFit
from .phase import source_phase_profile_integrals
from .seeds import trial_seed


@dataclass(frozen=True)
class FixedGammaTrialCache:
    """Contiguous immutable arrays shared by all fixed-gamma trials."""

    event_offsets: np.ndarray
    event_dec: np.ndarray
    event_azi: np.ndarray
    event_ang_err: np.ndarray
    grl_offsets: np.ndarray
    grl_start: np.ndarray
    grl_stop: np.ndarray
    grl_cdf: np.ndarray
    candidate_offsets: np.ndarray
    candidate_events: np.ndarray
    candidate_base_ratio: np.ndarray
    source_ra: np.ndarray
    source_dec: np.ndarray
    source_start: np.ndarray
    source_stop: np.ndarray
    source_sigma: np.ndarray
    gaussian_profile: bool
    source_dra_half: np.ndarray
    phase_event_counts: np.ndarray
    phase_yields: np.ndarray


@njit(cache=True)
def _fit_ns_cached(ratios, phases, n_selected, event_counts, yields, ns_min, ns_max):
    n_phases = len(event_counts)
    total_yield = 0.0
    for phase in range(n_phases):
        total_yield += yields[phase]
    if total_yield <= 0.0:
        return np.nan, np.nan, False

    fractions = yields / total_yield
    pure = event_counts - n_selected
    upper = ns_max
    for phase in range(n_phases):
        if pure[phase] > 0 and fractions[phase] > 0.0:
            upper = min(upper, np.nextafter(event_counts[phase] / fractions[phase], -np.inf))
    if upper < ns_min:
        return np.nan, np.nan, False

    def score(ns):
        value = 0.0
        for idx in range(len(ratios)):
            phase = phases[idx]
            coefficient = fractions[phase] / event_counts[phase] * (ratios[idx] - 1.0)
            denominator = 1.0 + ns * coefficient
            if denominator <= 0.0:
                return -np.inf
            value += coefficient / denominator
        for phase in range(n_phases):
            if pure[phase] > 0 and fractions[phase] > 0.0:
                scale = fractions[phase] / event_counts[phase]
                denominator = 1.0 - ns * scale
                if denominator <= 0.0:
                    return -np.inf
                value -= pure[phase] * scale / denominator
        return value

    if score(ns_min) <= 0.0:
        ns_hat = ns_min
    elif score(upper) >= 0.0:
        ns_hat = upper
    else:
        low = ns_min
        high = upper
        for _ in range(100):
            middle = 0.5 * (low + high)
            if score(middle) > 0.0:
                low = middle
            else:
                high = middle
            if high - low <= 1e-10 * max(1.0, abs(middle)):
                break
        ns_hat = 0.5 * (low + high)

    log_lambda = 0.0
    for idx in range(len(ratios)):
        phase = phases[idx]
        coefficient = fractions[phase] / event_counts[phase] * (ratios[idx] - 1.0)
        log_lambda += np.log1p(ns_hat * coefficient)
    for phase in range(n_phases):
        if pure[phase] > 0 and fractions[phase] > 0.0:
            log_lambda += pure[phase] * np.log1p(
                -ns_hat * fractions[phase] / event_counts[phase]
            )
    ts = max(0.0, 2.0 * log_lambda)
    return ts, ns_hat, np.isfinite(ts) and np.isfinite(ns_hat)


@njit(cache=True)
def _scramble_coordinates(
    seed,
    event_offsets,
    event_azi,
    grl_offsets,
    grl_start,
    grl_stop,
    grl_cdf,
):
    """Reproduce SkyLLH's phase-ordered seasonal RandomState scramble."""

    np.random.seed(seed)
    n_events = event_offsets[-1]
    times = np.empty(n_events, dtype=np.float64)
    ras = np.empty(n_events, dtype=np.float64)
    run_indices = np.empty(n_events, dtype=np.int32)
    for phase in range(len(event_offsets) - 1):
        event_start = event_offsets[phase]
        event_stop = event_offsets[phase + 1]
        run_start = grl_offsets[phase]
        run_stop = grl_offsets[phase + 1]
        for event in range(event_start, event_stop):
            value = np.random.random()
            run_indices[event] = run_start + np.searchsorted(
                grl_cdf[run_start:run_stop], value, side='right'
            )
        for event in range(event_start, event_stop):
            run = run_indices[event]
            time = grl_start[run] + np.random.random() * (grl_stop[run] - grl_start[run])
            times[event] = time
            residual = (time / 0.997269566) % 1.0
            ras[event] = (2.54199002505 + 2.0 * np.pi * residual - event_azi[event]) % (
                2.0 * np.pi
            )
    return times, ras


@njit(cache=True)
def _evaluate_coordinates(
    times,
    ras,
    event_dec,
    event_ang_err,
    candidate_offsets,
    candidate_events,
    candidate_base_ratio,
    source_ra,
    source_dec,
    source_start,
    source_stop,
    source_sigma,
    gaussian_profile,
    source_dra_half,
    event_offsets,
    event_counts,
    phase_yields,
    ns_min,
    ns_max,
):
    n_phases = len(event_counts)
    n_sources = len(source_ra)
    source_ts = np.empty(n_sources, dtype=np.float64)
    source_ns = np.empty(n_sources, dtype=np.float64)
    source_ok = np.empty(n_sources, dtype=np.bool_)
    stack_ratio = np.zeros(len(times), dtype=np.float64)
    stack_yields = np.zeros(n_phases, dtype=np.float64)
    for phase in range(n_phases):
        for source in range(n_sources):
            stack_yields[phase] += phase_yields[phase, source]

    for source in range(n_sources):
        capacity = 0
        for phase in range(n_phases):
            capacity += candidate_offsets[phase, source + 1] - candidate_offsets[phase, source]
        ratios = np.empty(capacity, dtype=np.float64)
        phases = np.empty(capacity, dtype=np.int32)
        selected_counts = np.zeros(n_phases, dtype=np.int64)
        used = 0
        for phase in range(n_phases):
            if phase_yields[phase, source] <= 0.0:
                continue
            first = candidate_offsets[phase, source]
            last = candidate_offsets[phase, source + 1]
            stack_weight = phase_yields[phase, source] / stack_yields[phase]
            for pair in range(first, last):
                event = candidate_events[pair]
                if times[event] < source_start[source] or times[event] > source_stop[source]:
                    continue
                if gaussian_profile and times[event] >= source_stop[source]:
                    continue
                dra = abs(ras[event] - source_ra[source])
                dra = min(dra, 2.0 * np.pi - dra)
                if dra >= source_dra_half[source]:
                    continue
                delta_dec = abs(event_dec[event] - source_dec[source])
                separation_term = np.sin(delta_dec / 2.0) ** 2
                separation_term += (
                    np.cos(event_dec[event])
                    * np.cos(source_dec[source])
                    * np.sin(dra / 2.0) ** 2
                )
                separation_term = min(1.0, max(0.0, separation_term))
                psi = 2.0 * np.arcsin(np.sqrt(separation_term))
                sigma_sq = event_ang_err[event] ** 2
                spatial = (
                    0.5
                    / (np.pi * np.sin(psi))
                    * (psi / sigma_sq)
                    * np.exp(-0.5 * psi**2 / sigma_sq)
                )
                time_shape = 1.0
                if gaussian_profile:
                    center = 0.5 * (source_start[source] + source_stop[source])
                    delta_time = times[event] - center
                    time_shape = np.exp(-0.5 * (delta_time / source_sigma[source]) ** 2)
                ratio = candidate_base_ratio[pair] * spatial * time_shape
                ratios[used] = ratio
                phases[used] = phase
                used += 1
                selected_counts[phase] += 1
                stack_ratio[event] += ratio * stack_weight
        ts, ns, ok = _fit_ns_cached(
            ratios[:used],
            phases[:used],
            selected_counts,
            event_counts,
            phase_yields[:, source],
            ns_min,
            ns_max,
        )
        source_ts[source] = ts
        source_ns[source] = ns
        source_ok[source] = ok

    stack_capacity = 0
    for event in range(len(stack_ratio)):
        if stack_ratio[event] != 0.0:
            stack_capacity += 1
    stack_ratios = np.empty(stack_capacity, dtype=np.float64)
    stack_phases = np.empty(stack_capacity, dtype=np.int32)
    stack_counts = np.zeros(n_phases, dtype=np.int64)
    used = 0
    for phase in range(n_phases):
        for event in range(event_offsets[phase], event_offsets[phase + 1]):
            if stack_ratio[event] != 0.0:
                stack_ratios[used] = stack_ratio[event]
                stack_phases[used] = phase
                stack_counts[phase] += 1
                used += 1
    stack_ts, stack_ns, stack_ok = _fit_ns_cached(
        stack_ratios,
        stack_phases,
        stack_counts,
        event_counts,
        stack_yields,
        ns_min,
        ns_max,
    )
    return source_ts, source_ns, source_ok, stack_ts, stack_ns, stack_ok


@njit(cache=True, parallel=True)
def _simulate_cached_batch(
    seeds,
    event_offsets,
    event_dec,
    event_azi,
    event_ang_err,
    grl_offsets,
    grl_start,
    grl_stop,
    grl_cdf,
    candidate_offsets,
    candidate_events,
    candidate_base_ratio,
    source_ra,
    source_dec,
    source_start,
    source_stop,
    source_sigma,
    gaussian_profile,
    source_dra_half,
    event_counts,
    phase_yields,
    ns_min,
    ns_max,
):
    n_trials = len(seeds)
    n_sources = len(source_ra)
    source_ts = np.empty((n_trials, n_sources), dtype=np.float64)
    source_ns = np.empty((n_trials, n_sources), dtype=np.float64)
    source_ok = np.empty((n_trials, n_sources), dtype=np.bool_)
    stack_ts = np.empty(n_trials, dtype=np.float64)
    stack_ns = np.empty(n_trials, dtype=np.float64)
    stack_ok = np.empty(n_trials, dtype=np.bool_)
    for trial in prange(n_trials):
        times, ras = _scramble_coordinates(
            seeds[trial],
            event_offsets,
            event_azi,
            grl_offsets,
            grl_start,
            grl_stop,
            grl_cdf,
        )
        result = _evaluate_coordinates(
            times,
            ras,
            event_dec,
            event_ang_err,
            candidate_offsets,
            candidate_events,
            candidate_base_ratio,
            source_ra,
            source_dec,
            source_start,
            source_stop,
            source_sigma,
            gaussian_profile,
            source_dra_half,
            event_offsets,
            event_counts,
            phase_yields,
            ns_min,
            ns_max,
        )
        source_ts[trial], source_ns[trial], source_ok[trial] = result[:3]
        stack_ts[trial], stack_ns[trial], stack_ok[trial] = result[3:]
    return source_ts, source_ns, source_ok, stack_ts, stack_ns, stack_ok


def build_fixed_gamma_trial_cache(constructed: ConstructedCatalogAnalysis) -> FixedGammaTrialCache:
    """Precompute every trial-invariant term used by fixed-gamma trials."""

    config = constructed.config
    if config.pdfs.backend != 'precomputed' or config.spectrum.fit_gamma:
        raise ValueError('fixed-gamma cache requires the precomputed backend and fit_gamma=false')
    sources = constructed.model.sources
    n_sources = len(sources)
    source_ra = np.asarray([source.ra for source in sources], dtype=np.float64)
    source_dec = np.asarray([source.dec for source in sources], dtype=np.float64)
    source_start = np.asarray(
        [item.source.time_start_mjd for item in constructed.selection.selected], dtype=np.float64
    )
    source_stop = np.asarray(
        [item.source.time_end_mjd for item in constructed.selection.selected], dtype=np.float64
    )
    gaussian_profile = config.catalog.time_profile.type == 'gaussian'
    source_sigma = np.asarray(
        [0.0 if item.source.time_sigma_days is None else item.source.time_sigma_days for item in constructed.selection.selected],
        dtype=np.float64,
    )
    angle = np.deg2rad(config.likelihood.event_selection_angle_deg)
    dec_minus = np.maximum(-np.pi / 2.0, source_dec - angle)
    dec_plus = np.minimum(np.pi / 2.0, source_dec + angle)
    source_dra_half = np.minimum(
        2.0 * np.pi,
        np.abs(angle / np.minimum(np.cos(dec_minus), np.cos(dec_plus))),
    )

    analysis = constructed.analysis
    src_params = analysis.pmm.create_src_params_recarray(
        gflp_values=np.zeros(analysis.pmm.n_global_floating_params, dtype=np.float64)
    )
    analysis.src_detsigyield_weights_service.calculate(src_params_recarray=src_params)
    phase_yields, _ = analysis.src_detsigyield_weights_service.get_weights()
    if phase_yields is None:
        raise RuntimeError('detector signal yield service did not calculate fixed-gamma weights')
    phase_yields = np.asarray(phase_yields, dtype=np.float64)

    event_offsets = [0]
    event_dec_parts = []
    event_azi_parts = []
    event_ang_err_parts = []
    grl_offsets = [0]
    grl_start_parts = []
    grl_stop_parts = []
    grl_cdf_parts = []
    candidate_offsets = np.zeros((len(constructed.datasets), n_sources + 1), dtype=np.int64)
    candidate_events_parts = []
    candidate_base_parts = []
    pair_offset = 0
    for phase, (data, livetime, background, grid) in enumerate(
        zip(
            constructed.data_list,
            constructed.livetimes,
            constructed.precomputed_backgrounds,
            constructed.precomputed_signal_grids,
            strict=True,
        )
    ):
        if data.exp is None or data.grl is None or background is None or grid is None:
            raise RuntimeError('precomputed cache requires experimental events, GRL, and bound PDF products')
        events = data.exp
        event_base = event_offsets[-1]
        event_offsets.append(event_base + len(events))
        event_dec_parts.append(np.asarray(events['dec'], dtype=np.float64))
        event_azi_parts.append(np.asarray(events['azi'], dtype=np.float64))
        event_ang_err_parts.append(np.asarray(events['ang_err'], dtype=np.float64))

        starts = np.asarray(data.grl['start'], dtype=np.float64)
        stops = np.asarray(data.grl['stop'], dtype=np.float64)
        counts = np.asarray(
            [np.count_nonzero((events['time'] >= start) & (events['time'] < stop)) for start, stop in zip(starts, stops, strict=True)],
            dtype=np.float64,
        )
        weights = counts / np.sum(counts)
        grl_start_parts.append(starts)
        grl_stop_parts.append(stops)
        grl_cdf_parts.append(np.cumsum(weights))
        grl_offsets.append(grl_offsets[-1] + len(starts))

        response_bins = grid.declination_bins(source_dec)
        overlaps = source_phase_profile_integrals(
            livetime,
            0.5 * (source_start + source_stop),
            source_stop - source_start,
            profile_type=config.catalog.time_profile.type,
            gaussian_sigmas_days=(source_sigma if gaussian_profile else None),
            gaussian_tail_tolerance=config.catalog.time_profile.tail_tolerance,
        )
        for source in range(n_sources):
            candidate_offsets[phase, source] = pair_offset
            if overlaps[source] <= 0.0 or phase_yields[phase, source] <= 0.0:
                continue
            mask = (events['dec'] > dec_minus[source]) & (events['dec'] < dec_plus[source])
            local_events = np.flatnonzero(mask).astype(np.int64)
            signal, _ = grid.evaluate(
                np.full(len(local_events), response_bins[source], dtype=np.int32),
                np.asarray(events['log_energy'][local_events], dtype=np.float64),
                config.spectrum.gamma,
            )
            base = signal / background.energy[local_events] / background.spatial[local_events]
            base *= float(livetime.livetime) / overlaps[source]
            candidate_events_parts.append(local_events + event_base)
            candidate_base_parts.append(base)
            pair_offset += len(local_events)
        candidate_offsets[phase, n_sources] = pair_offset

    return FixedGammaTrialCache(
        event_offsets=np.asarray(event_offsets, dtype=np.int64),
        event_dec=np.concatenate(event_dec_parts),
        event_azi=np.concatenate(event_azi_parts),
        event_ang_err=np.concatenate(event_ang_err_parts),
        grl_offsets=np.asarray(grl_offsets, dtype=np.int64),
        grl_start=np.concatenate(grl_start_parts),
        grl_stop=np.concatenate(grl_stop_parts),
        grl_cdf=np.concatenate(grl_cdf_parts),
        candidate_offsets=candidate_offsets,
        candidate_events=np.concatenate(candidate_events_parts),
        candidate_base_ratio=np.concatenate(candidate_base_parts),
        source_ra=source_ra,
        source_dec=source_dec,
        source_start=source_start,
        source_stop=source_stop,
        source_sigma=source_sigma,
        gaussian_profile=gaussian_profile,
        source_dra_half=source_dra_half,
        phase_event_counts=np.diff(event_offsets).astype(np.int64),
        phase_yields=phase_yields,
    )


class CachedPrecomputedFixedGammaEngine:
    """v1-style invariant cache plus batched Numba seasonal trials."""

    def __init__(self, constructed: ConstructedCatalogAnalysis):
        self.constructed = constructed
        self.cache = build_fixed_gamma_trial_cache(constructed)

    def _fit_coordinates(self, times: np.ndarray, ras: np.ndarray) -> OptimizedCatalogFit:
        likelihood = self.constructed.config.likelihood
        result = _evaluate_coordinates(
            np.asarray(times, dtype=np.float64),
            np.asarray(ras, dtype=np.float64),
            self.cache.event_dec,
            self.cache.event_ang_err,
            self.cache.candidate_offsets,
            self.cache.candidate_events,
            self.cache.candidate_base_ratio,
            self.cache.source_ra,
            self.cache.source_dec,
            self.cache.source_start,
            self.cache.source_stop,
            self.cache.source_sigma,
            self.cache.gaussian_profile,
            self.cache.source_dra_half,
            self.cache.event_offsets,
            self.cache.phase_event_counts,
            self.cache.phase_yields,
            likelihood.ns_min,
            likelihood.ns_max,
        )
        source_ts, source_ns, source_ok, stack_ts, stack_ns, stack_ok = result
        gamma = self.constructed.config.spectrum.gamma
        source_gamma = np.where(source_ns > 0.0, gamma, np.nan)
        return OptimizedCatalogFit(
            source_ts=source_ts,
            source_ns=source_ns,
            source_gamma=source_gamma,
            source_fit_ok=source_ok,
            source_gamma_status=np.full(len(source_ts), 'fixed'),
            stack=ProfileFit(
                ts=stack_ts,
                ns=stack_ns,
                gamma=gamma if stack_ns > 0.0 else None,
                fit_ok=bool(stack_ok),
                gamma_status='fixed',
            ),
        )

    def fit_observed(self) -> OptimizedCatalogFit:
        times = []
        ras = []
        for data in self.constructed.data_list:
            if data.exp is None:
                raise RuntimeError('constructed phase has no experimental data')
            times.append(np.asarray(data.exp['time'], dtype=np.float64))
            ras.append(np.asarray(data.exp['ra'], dtype=np.float64))
        return self._fit_coordinates(np.concatenate(times), np.concatenate(ras))

    def fit_seed(self, seed: int) -> OptimizedCatalogFit:
        times, ras = _scramble_coordinates(
            seed,
            self.cache.event_offsets,
            self.cache.event_azi,
            self.cache.grl_offsets,
            self.cache.grl_start,
            self.cache.grl_stop,
            self.cache.grl_cdf,
        )
        return self._fit_coordinates(times, ras)

    def run_trials(
        self,
        *,
        n_trials: int,
        base_seed: int,
        trial_index_start: int = 0,
    ) -> OptimizedCatalogTrials:
        if n_trials <= 0 or trial_index_start < 0:
            raise ValueError('n_trials must be positive and trial_index_start nonnegative')
        indices = np.arange(trial_index_start, trial_index_start + n_trials, dtype=np.int64)
        seeds = np.asarray([trial_seed(base_seed, int(index)) for index in indices], dtype=np.uint32)
        likelihood = self.constructed.config.likelihood
        source_ts, source_ns, source_ok, stack_ts, stack_ns, stack_ok = _simulate_cached_batch(
            seeds,
            self.cache.event_offsets,
            self.cache.event_dec,
            self.cache.event_azi,
            self.cache.event_ang_err,
            self.cache.grl_offsets,
            self.cache.grl_start,
            self.cache.grl_stop,
            self.cache.grl_cdf,
            self.cache.candidate_offsets,
            self.cache.candidate_events,
            self.cache.candidate_base_ratio,
            self.cache.source_ra,
            self.cache.source_dec,
            self.cache.source_start,
            self.cache.source_stop,
            self.cache.source_sigma,
            self.cache.gaussian_profile,
            self.cache.source_dra_half,
            self.cache.phase_event_counts,
            self.cache.phase_yields,
            likelihood.ns_min,
            likelihood.ns_max,
        )
        gamma = self.constructed.config.spectrum.gamma
        return OptimizedCatalogTrials(
            trial_index=indices,
            seed=seeds.astype(np.uint64),
            source_ts=source_ts,
            source_ns=source_ns,
            source_gamma=np.where(source_ns > 0.0, gamma, np.nan),
            source_fit_ok=source_ok,
            stack_ts=stack_ts,
            stack_ns=stack_ns,
            stack_gamma=np.where(stack_ns > 0.0, gamma, np.nan),
            stack_fit_ok=stack_ok,
        )
