"""Low-memory cached precomputed-PDF trials with a fitted spectral index."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numba import njit, prange

from .analysis import ConstructedCatalogAnalysis
from .cached import _scramble_coordinates
from .optimized import OptimizedCatalogFit, OptimizedCatalogTrials, ProfileFit
from .phase import source_phase_exposure_fractions
from .seeds import trial_seed


@dataclass(frozen=True)
class FreeGammaTrialCache:
    """Trial invariants without a dense candidate-pair-by-gamma table."""

    event_offsets: np.ndarray
    event_dec: np.ndarray
    event_azi: np.ndarray
    event_ang_err: np.ndarray
    event_energy_bin: np.ndarray
    event_energy_weight: np.ndarray
    event_inverse_background: np.ndarray
    grl_offsets: np.ndarray
    grl_start: np.ndarray
    grl_stop: np.ndarray
    grl_cdf: np.ndarray
    candidate_offsets: np.ndarray
    candidate_events: np.ndarray
    source_ra: np.ndarray
    source_dec: np.ndarray
    source_start: np.ndarray
    source_stop: np.ndarray
    source_dra_half: np.ndarray
    source_response_bin: np.ndarray
    source_time_factor: np.ndarray
    phase_event_counts: np.ndarray
    gamma_grid: np.ndarray
    gamma_pdf_bin: np.ndarray
    gamma_pdf_weight: np.ndarray
    phase_yield_grid: np.ndarray
    signal_densities: tuple[np.ndarray, ...]


@njit(cache=True)
def _fit_ns_newton(ratios, phases, n_selected, event_counts, yields, ns_min, ns_max):
    """Safeguarded Newton profile of the same conditional likelihood."""

    n_phases = len(event_counts)
    total_yield = np.sum(yields)
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

    def score_curvature(ns):
        score = 0.0
        curvature = 0.0
        for idx in range(len(ratios)):
            phase = phases[idx]
            coefficient = fractions[phase] / event_counts[phase] * (ratios[idx] - 1.0)
            denominator = 1.0 + ns * coefficient
            if denominator <= 0.0:
                return -np.inf, np.inf
            value = coefficient / denominator
            score += value
            curvature += value * value
        for phase in range(n_phases):
            if pure[phase] > 0 and fractions[phase] > 0.0:
                scale = fractions[phase] / event_counts[phase]
                denominator = 1.0 - ns * scale
                if denominator <= 0.0:
                    return -np.inf, np.inf
                value = scale / denominator
                score -= pure[phase] * value
                curvature += pure[phase] * value * value
        return score, curvature

    lower_score, _ = score_curvature(ns_min)
    if lower_score <= 0.0:
        ns_hat = ns_min
    else:
        upper_score, _ = score_curvature(upper)
        if upper_score >= 0.0:
            ns_hat = upper
        else:
            low = ns_min
            high = upper
            ns_hat = 0.5 * (low + high)
            for _ in range(80):
                score, curvature = score_curvature(ns_hat)
                if abs(score) <= 1e-12:
                    break
                if score > 0.0:
                    low = ns_hat
                else:
                    high = ns_hat
                if high - low <= 1e-10 * max(1.0, abs(ns_hat)):
                    ns_hat = 0.5 * (low + high)
                    break
                candidate = ns_hat + score / curvature
                ns_hat = candidate if low < candidate < high else 0.5 * (low + high)

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
def _signal_density_at_node(
    event,
    source,
    phase,
    gamma_node,
    event_energy_bin,
    event_energy_weight,
    source_response_bin,
    gamma_pdf_bin,
    gamma_pdf_weight,
    signal_densities,
):
    energy_bin = event_energy_bin[event]
    energy_weight = event_energy_weight[event]
    response_bin = source_response_bin[phase, source]
    density = signal_densities[phase]
    value = (1.0 - energy_weight) * density[response_bin, energy_bin, gamma_node]
    value += energy_weight * density[response_bin, energy_bin + 1, gamma_node]
    return value


@njit(cache=True)
def _fit_interpolated_gamma(
    ratio_grid,
    phases,
    selected_counts,
    event_counts,
    yield_grid,
    left,
    weight,
    ns_min,
    ns_max,
):
    ratios = (1.0 - weight) * ratio_grid[left] + weight * ratio_grid[left + 1]
    yields = (1.0 - weight) * yield_grid[left] + weight * yield_grid[left + 1]
    return _fit_ns_newton(
        ratios,
        phases,
        selected_counts,
        event_counts,
        yields,
        ns_min,
        ns_max,
    )


@njit(cache=True)
def _profile_gamma_cached(
    gamma_grid,
    ratio_grid,
    phases,
    selected_counts,
    event_counts,
    yield_grid,
    ns_min,
    ns_max,
    gamma_tolerance=1e-6,
):
    """Profile gamma nodes and continuously refine every candidate peak."""

    n_gamma = len(gamma_grid)
    best_ts = -1.0
    best_ns = np.nan
    best_gamma = np.nan
    all_nodes_background = True
    node_ts = np.empty(n_gamma, dtype=np.float64)
    for gamma_idx in range(n_gamma):
        ts, ns, ok = _fit_ns_newton(
            ratio_grid[gamma_idx],
            phases,
            selected_counts,
            event_counts,
            yield_grid[gamma_idx],
            ns_min,
            ns_max,
        )
        if not ok:
            return np.nan, np.nan, np.nan, False
        if ns > ns_min:
            all_nodes_background = False
        node_ts[gamma_idx] = ts
        if ts > best_ts:
            best_ts = ts
            best_ns = ns
            best_gamma = gamma_grid[gamma_idx]

    # With one phase, ratios and the score at ns=0 are linear within each
    # configured interval.  If every node chooses ns=0, no interval can hide a
    # positive solution.  This is the dominant background-trial fast path.
    if len(event_counts) == 1 and all_nodes_background:
        return 0.0, ns_min, np.nan, True

    golden = 0.5 * (np.sqrt(5.0) - 1.0)
    for left in range(n_gamma - 1):
        if len(event_counts) == 1:
            left_is_peak = node_ts[left] >= node_ts[left + 1]
            if left > 0:
                left_is_peak = left_is_peak and node_ts[left] >= node_ts[left - 1]
            right_is_peak = node_ts[left + 1] >= node_ts[left]
            if left + 2 < n_gamma:
                right_is_peak = right_is_peak and node_ts[left + 1] >= node_ts[left + 2]
            if not left_is_peak and not right_is_peak:
                continue
        lo = 0.0
        hi = 1.0
        x1 = hi - golden * (hi - lo)
        x2 = lo + golden * (hi - lo)
        result1 = _fit_interpolated_gamma(
            ratio_grid,
            phases,
            selected_counts,
            event_counts,
            yield_grid,
            left,
            x1,
            ns_min,
            ns_max,
        )
        result2 = _fit_interpolated_gamma(
            ratio_grid,
            phases,
            selected_counts,
            event_counts,
            yield_grid,
            left,
            x2,
            ns_min,
            ns_max,
        )
        while (hi - lo) * (gamma_grid[left + 1] - gamma_grid[left]) > gamma_tolerance:
            if result1[0] < result2[0]:
                lo = x1
                x1 = x2
                result1 = result2
                x2 = lo + golden * (hi - lo)
                result2 = _fit_interpolated_gamma(
                    ratio_grid,
                    phases,
                    selected_counts,
                    event_counts,
                    yield_grid,
                    left,
                    x2,
                    ns_min,
                    ns_max,
                )
            else:
                hi = x2
                x2 = x1
                result2 = result1
                x1 = hi - golden * (hi - lo)
                result1 = _fit_interpolated_gamma(
                    ratio_grid,
                    phases,
                    selected_counts,
                    event_counts,
                    yield_grid,
                    left,
                    x1,
                    ns_min,
                    ns_max,
                )
        if result1[0] >= result2[0]:
            weight = x1
            ts, ns, ok = result1
        else:
            weight = x2
            ts, ns, ok = result2
        if not ok:
            return np.nan, np.nan, np.nan, False
        if ts > best_ts:
            best_ts = ts
            best_ns = ns
            best_gamma = (1.0 - weight) * gamma_grid[left] + weight * gamma_grid[left + 1]

    if best_ns <= ns_min:
        best_gamma = np.nan
    return best_ts, best_ns, best_gamma, True


@njit(cache=True)
def _source_ratio_grid(
    events,
    scales,
    phases,
    source,
    n_gamma,
    event_energy_bin,
    event_energy_weight,
    source_response_bin,
    gamma_pdf_bin,
    gamma_pdf_weight,
    signal_densities,
):
    ratios = np.empty((n_gamma, len(events)), dtype=np.float64)
    for gamma_node in range(n_gamma):
        for pair in range(len(events)):
            ratios[gamma_node, pair] = scales[pair] * _signal_density_at_node(
                events[pair],
                source,
                phases[pair],
                gamma_node,
                event_energy_bin,
                event_energy_weight,
                source_response_bin,
                gamma_pdf_bin,
                gamma_pdf_weight,
                signal_densities,
            )
    return ratios


@njit(cache=True)
def _evaluate_coordinates_free(
    times,
    ras,
    event_dec,
    event_ang_err,
    event_energy_bin,
    event_energy_weight,
    event_inverse_background,
    candidate_offsets,
    candidate_events,
    source_ra,
    source_dec,
    source_start,
    source_stop,
    source_dra_half,
    source_response_bin,
    source_time_factor,
    event_offsets,
    event_counts,
    gamma_grid,
    gamma_pdf_bin,
    gamma_pdf_weight,
    phase_yield_grid,
    signal_densities,
    ns_min,
    ns_max,
):
    n_phases = len(event_counts)
    n_sources = len(source_ra)
    n_gamma = len(gamma_grid)
    source_ts = np.empty(n_sources, dtype=np.float64)
    source_ns = np.empty(n_sources, dtype=np.float64)
    source_gamma = np.empty(n_sources, dtype=np.float64)
    source_ok = np.empty(n_sources, dtype=np.bool_)

    contribution_events = []
    contribution_sources = []
    contribution_phases = []
    contribution_scales = []

    for source in range(n_sources):
        selected_events = []
        selected_scales = []
        selected_phases = []
        selected_counts = np.zeros(n_phases, dtype=np.int64)
        for phase in range(n_phases):
            if np.max(phase_yield_grid[:, phase, source]) <= 0.0:
                continue
            first = candidate_offsets[phase, source]
            last = candidate_offsets[phase, source + 1]
            for pair in range(first, last):
                event = candidate_events[pair]
                if times[event] < source_start[source] or times[event] > source_stop[source]:
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
                scale = (
                    spatial
                    * event_inverse_background[event]
                    * source_time_factor[phase, source]
                )
                selected_events.append(event)
                selected_scales.append(scale)
                selected_phases.append(phase)
                selected_counts[phase] += 1
                contribution_events.append(event)
                contribution_sources.append(source)
                contribution_phases.append(phase)
                contribution_scales.append(scale)

        events = np.asarray(selected_events, dtype=np.int64)
        scales = np.asarray(selected_scales, dtype=np.float64)
        phases = np.asarray(selected_phases, dtype=np.int32)
        ratio_grid = _source_ratio_grid(
            events,
            scales,
            phases,
            source,
            n_gamma,
            event_energy_bin,
            event_energy_weight,
            source_response_bin,
            gamma_pdf_bin,
            gamma_pdf_weight,
            signal_densities,
        )
        ts, ns, gamma, ok = _profile_gamma_cached(
            gamma_grid,
            ratio_grid,
            phases,
            selected_counts,
            event_counts,
            phase_yield_grid[:, :, source],
            ns_min,
            ns_max,
        )
        source_ts[source] = ts
        source_ns[source] = ns
        source_gamma[source] = gamma
        source_ok[source] = ok

    all_events = np.asarray(contribution_events, dtype=np.int64)
    all_sources = np.asarray(contribution_sources, dtype=np.int32)
    all_phases = np.asarray(contribution_phases, dtype=np.int32)
    all_scales = np.asarray(contribution_scales, dtype=np.float64)
    order = np.argsort(all_events)
    n_unique = 0
    previous = -1
    for position in range(len(order)):
        event = all_events[order[position]]
        if event != previous:
            n_unique += 1
            previous = event
    stack_ratios = np.zeros((n_gamma, n_unique), dtype=np.float64)
    stack_phases = np.empty(n_unique, dtype=np.int32)
    stack_counts = np.zeros(n_phases, dtype=np.int64)
    stack_yields = np.sum(phase_yield_grid, axis=2)
    unique_idx = -1
    previous = -1
    for position in range(len(order)):
        contribution = order[position]
        event = all_events[contribution]
        source = all_sources[contribution]
        phase = all_phases[contribution]
        if event != previous:
            unique_idx += 1
            previous = event
            stack_phases[unique_idx] = phase
            stack_counts[phase] += 1
        for gamma_node in range(n_gamma):
            signal = _signal_density_at_node(
                event,
                source,
                phase,
                gamma_node,
                event_energy_bin,
                event_energy_weight,
                source_response_bin,
                gamma_pdf_bin,
                gamma_pdf_weight,
                signal_densities,
            )
            stack_ratios[gamma_node, unique_idx] += (
                all_scales[contribution]
                * signal
                * phase_yield_grid[gamma_node, phase, source]
                / stack_yields[gamma_node, phase]
            )
    stack_ts, stack_ns, stack_gamma, stack_ok = _profile_gamma_cached(
        gamma_grid,
        stack_ratios,
        stack_phases,
        stack_counts,
        event_counts,
        stack_yields,
        ns_min,
        ns_max,
    )
    return (
        source_ts,
        source_ns,
        source_gamma,
        source_ok,
        stack_ts,
        stack_ns,
        stack_gamma,
        stack_ok,
    )


@njit(cache=True, parallel=True)
def _simulate_free_gamma_batch(
    seeds,
    event_offsets,
    event_dec,
    event_azi,
    event_ang_err,
    event_energy_bin,
    event_energy_weight,
    event_inverse_background,
    grl_offsets,
    grl_start,
    grl_stop,
    grl_cdf,
    candidate_offsets,
    candidate_events,
    source_ra,
    source_dec,
    source_start,
    source_stop,
    source_dra_half,
    source_response_bin,
    source_time_factor,
    event_counts,
    gamma_grid,
    gamma_pdf_bin,
    gamma_pdf_weight,
    phase_yield_grid,
    signal_densities,
    ns_min,
    ns_max,
):
    n_trials = len(seeds)
    n_sources = len(source_ra)
    source_ts = np.empty((n_trials, n_sources), dtype=np.float64)
    source_ns = np.empty((n_trials, n_sources), dtype=np.float64)
    source_gamma = np.empty((n_trials, n_sources), dtype=np.float64)
    source_ok = np.empty((n_trials, n_sources), dtype=np.bool_)
    stack_ts = np.empty(n_trials, dtype=np.float64)
    stack_ns = np.empty(n_trials, dtype=np.float64)
    stack_gamma = np.empty(n_trials, dtype=np.float64)
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
        result = _evaluate_coordinates_free(
            times,
            ras,
            event_dec,
            event_ang_err,
            event_energy_bin,
            event_energy_weight,
            event_inverse_background,
            candidate_offsets,
            candidate_events,
            source_ra,
            source_dec,
            source_start,
            source_stop,
            source_dra_half,
            source_response_bin,
            source_time_factor,
            event_offsets,
            event_counts,
            gamma_grid,
            gamma_pdf_bin,
            gamma_pdf_weight,
            phase_yield_grid,
            signal_densities,
            ns_min,
            ns_max,
        )
        source_ts[trial] = result[0]
        source_ns[trial] = result[1]
        source_gamma[trial] = result[2]
        source_ok[trial] = result[3]
        stack_ts[trial] = result[4]
        stack_ns[trial] = result[5]
        stack_gamma[trial] = result[6]
        stack_ok[trial] = result[7]
    return (
        source_ts,
        source_ns,
        source_gamma,
        source_ok,
        stack_ts,
        stack_ns,
        stack_gamma,
        stack_ok,
    )


def _linear_coordinates(axis: np.ndarray, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    lower = np.searchsorted(axis, values, side='right') - 1
    lower = np.clip(lower, 0, len(axis) - 2)
    weight = (values - axis[lower]) / (axis[lower + 1] - axis[lower])
    return lower.astype(np.int32), np.asarray(weight, dtype=np.float64)


def build_free_gamma_trial_cache(constructed: ConstructedCatalogAnalysis) -> FreeGammaTrialCache:
    """Precompute geometry and interpolation coordinates for free-gamma trials."""

    config = constructed.config
    if config.pdfs.backend != 'precomputed' or not config.spectrum.fit_gamma:
        raise ValueError('free-gamma cache requires the precomputed backend and fit_gamma=true')
    sources = constructed.model.sources
    n_sources = len(sources)
    n_phases = len(constructed.datasets)
    source_ra = np.asarray([source.ra for source in sources], dtype=np.float64)
    source_dec = np.asarray([source.dec for source in sources], dtype=np.float64)
    source_start = np.asarray(
        [item.source.time_start_mjd for item in constructed.selection.selected], dtype=np.float64
    )
    source_stop = np.asarray(
        [item.source.time_end_mjd for item in constructed.selection.selected], dtype=np.float64
    )
    angle = np.deg2rad(config.likelihood.event_selection_angle_deg)
    dec_minus = np.maximum(-np.pi / 2.0, source_dec - angle)
    dec_plus = np.minimum(np.pi / 2.0, source_dec + angle)
    source_dra_half = np.minimum(
        2.0 * np.pi,
        np.abs(angle / np.minimum(np.cos(dec_minus), np.cos(dec_plus))),
    )
    gamma_grid = np.asarray(constructed.model.gamma_grid.grid, dtype=np.float64)

    analysis = constructed.analysis
    gamma_gflp_idx = analysis.pmm.get_gflp_idx('gamma')
    phase_yield_grid = np.empty((len(gamma_grid), n_phases, n_sources), dtype=np.float64)
    for gamma_idx, gamma in enumerate(gamma_grid):
        values = np.zeros(analysis.pmm.n_global_floating_params, dtype=np.float64)
        values[gamma_gflp_idx] = gamma
        src_params = analysis.pmm.create_src_params_recarray(gflp_values=values)
        analysis.src_detsigyield_weights_service.calculate(src_params_recarray=src_params)
        weights, _ = analysis.src_detsigyield_weights_service.get_weights()
        if weights is None:
            raise RuntimeError('detector signal yield service did not calculate gamma-grid weights')
        phase_yield_grid[gamma_idx] = weights

    event_offsets = [0]
    event_dec_parts = []
    event_azi_parts = []
    event_ang_err_parts = []
    event_energy_bin_parts = []
    event_energy_weight_parts = []
    event_inverse_background_parts = []
    grl_offsets = [0]
    grl_start_parts = []
    grl_stop_parts = []
    grl_cdf_parts = []
    candidate_offsets = np.zeros((n_phases, n_sources + 1), dtype=np.int64)
    candidate_events_parts = []
    source_response_bin = np.empty((n_phases, n_sources), dtype=np.int32)
    source_time_factor = np.zeros((n_phases, n_sources), dtype=np.float64)
    gamma_pdf_bin = np.empty((n_phases, len(gamma_grid)), dtype=np.int32)
    gamma_pdf_weight = np.empty((n_phases, len(gamma_grid)), dtype=np.float64)
    signal_densities = []
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
            raise RuntimeError('precomputed cache requires experimental events, GRL, and PDF products')
        events = data.exp
        event_base = event_offsets[-1]
        event_offsets.append(event_base + len(events))
        event_dec_parts.append(np.asarray(events['dec'], dtype=np.float64))
        event_azi_parts.append(np.asarray(events['azi'], dtype=np.float64))
        event_ang_err_parts.append(np.asarray(events['ang_err'], dtype=np.float64))
        energy_bin, energy_weight = _linear_coordinates(
            grid.log_energy,
            np.asarray(events['log_energy'], dtype=np.float64),
        )
        event_energy_bin_parts.append(energy_bin)
        event_energy_weight_parts.append(energy_weight)
        event_inverse_background_parts.append(1.0 / (background.energy * background.spatial))
        gamma_pdf_bin[phase], gamma_pdf_weight[phase] = _linear_coordinates(
            grid.gamma,
            gamma_grid,
        )
        node_density = np.empty(
            (len(grid.dec_bin_centers), len(grid.log_energy), len(gamma_grid)),
            dtype=np.float64,
        )
        for gamma_idx in range(len(gamma_grid)):
            raw_idx = gamma_pdf_bin[phase, gamma_idx]
            raw_weight = gamma_pdf_weight[phase, gamma_idx]
            node_density[:, :, gamma_idx] = (
                (1.0 - raw_weight) * grid.density[:, :, raw_idx]
                + raw_weight * grid.density[:, :, raw_idx + 1]
            )
        signal_densities.append(np.ascontiguousarray(node_density))

        starts = np.asarray(data.grl['start'], dtype=np.float64)
        stops = np.asarray(data.grl['stop'], dtype=np.float64)
        counts = np.asarray(
            [
                np.count_nonzero((events['time'] >= start) & (events['time'] < stop))
                for start, stop in zip(starts, stops, strict=True)
            ],
            dtype=np.float64,
        )
        grl_start_parts.append(starts)
        grl_stop_parts.append(stops)
        grl_cdf_parts.append(np.cumsum(counts / np.sum(counts)))
        grl_offsets.append(grl_offsets[-1] + len(starts))

        source_response_bin[phase] = grid.declination_bins(source_dec)
        overlaps = source_phase_exposure_fractions(
            livetime,
            0.5 * (source_start + source_stop),
            source_stop - source_start,
        ) * float(livetime.livetime)
        active = overlaps > 0.0
        source_time_factor[phase, active] = float(livetime.livetime) / overlaps[active]
        for source in range(n_sources):
            candidate_offsets[phase, source] = pair_offset
            if not active[source] or np.max(phase_yield_grid[:, phase, source]) <= 0.0:
                continue
            mask = (events['dec'] > dec_minus[source]) & (events['dec'] < dec_plus[source])
            local_events = np.flatnonzero(mask).astype(np.int64)
            candidate_events_parts.append(local_events + event_base)
            pair_offset += len(local_events)
        candidate_offsets[phase, n_sources] = pair_offset

    return FreeGammaTrialCache(
        event_offsets=np.asarray(event_offsets, dtype=np.int64),
        event_dec=np.concatenate(event_dec_parts),
        event_azi=np.concatenate(event_azi_parts),
        event_ang_err=np.concatenate(event_ang_err_parts),
        event_energy_bin=np.concatenate(event_energy_bin_parts),
        event_energy_weight=np.concatenate(event_energy_weight_parts),
        event_inverse_background=np.concatenate(event_inverse_background_parts),
        grl_offsets=np.asarray(grl_offsets, dtype=np.int64),
        grl_start=np.concatenate(grl_start_parts),
        grl_stop=np.concatenate(grl_stop_parts),
        grl_cdf=np.concatenate(grl_cdf_parts),
        candidate_offsets=candidate_offsets,
        candidate_events=np.concatenate(candidate_events_parts),
        source_ra=source_ra,
        source_dec=source_dec,
        source_start=source_start,
        source_stop=source_stop,
        source_dra_half=source_dra_half,
        source_response_bin=source_response_bin,
        source_time_factor=source_time_factor,
        phase_event_counts=np.diff(event_offsets).astype(np.int64),
        gamma_grid=gamma_grid,
        gamma_pdf_bin=gamma_pdf_bin,
        gamma_pdf_weight=gamma_pdf_weight,
        phase_yield_grid=phase_yield_grid,
        signal_densities=tuple(signal_densities),
    )


class CachedPrecomputedFreeGammaEngine:
    """Shared seasonal trials with on-demand cached gamma interpolation."""

    def __init__(self, constructed: ConstructedCatalogAnalysis):
        self.constructed = constructed
        self.cache = build_free_gamma_trial_cache(constructed)

    def _fit_coordinates(self, times: np.ndarray, ras: np.ndarray) -> OptimizedCatalogFit:
        likelihood = self.constructed.config.likelihood
        result = _evaluate_coordinates_free(
            np.asarray(times, dtype=np.float64),
            np.asarray(ras, dtype=np.float64),
            self.cache.event_dec,
            self.cache.event_ang_err,
            self.cache.event_energy_bin,
            self.cache.event_energy_weight,
            self.cache.event_inverse_background,
            self.cache.candidate_offsets,
            self.cache.candidate_events,
            self.cache.source_ra,
            self.cache.source_dec,
            self.cache.source_start,
            self.cache.source_stop,
            self.cache.source_dra_half,
            self.cache.source_response_bin,
            self.cache.source_time_factor,
            self.cache.event_offsets,
            self.cache.phase_event_counts,
            self.cache.gamma_grid,
            self.cache.gamma_pdf_bin,
            self.cache.gamma_pdf_weight,
            self.cache.phase_yield_grid,
            self.cache.signal_densities,
            likelihood.ns_min,
            likelihood.ns_max,
        )
        source_ts, source_ns, source_gamma, source_ok = result[:4]
        stack_ts, stack_ns, stack_gamma, stack_ok = result[4:]
        lo = self.constructed.config.spectrum.gamma_min
        hi = self.constructed.config.spectrum.gamma_max
        source_status = np.full(len(source_ts), 'interior', dtype='<U12')
        source_status[np.isnan(source_gamma)] = 'unidentified'
        source_status[np.isclose(source_gamma, lo) | np.isclose(source_gamma, hi)] = 'boundary'
        if np.isnan(stack_gamma):
            stack_status = 'unidentified'
            stack_value = None
        else:
            stack_value = float(stack_gamma)
            stack_status = 'boundary' if np.isclose(stack_gamma, lo) or np.isclose(stack_gamma, hi) else 'interior'
        return OptimizedCatalogFit(
            source_ts=source_ts,
            source_ns=source_ns,
            source_gamma=source_gamma,
            source_fit_ok=source_ok,
            source_gamma_status=source_status,
            stack=ProfileFit(
                float(stack_ts),
                float(stack_ns),
                stack_value,
                bool(stack_ok),
                stack_status,
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
        result = _simulate_free_gamma_batch(
            seeds,
            self.cache.event_offsets,
            self.cache.event_dec,
            self.cache.event_azi,
            self.cache.event_ang_err,
            self.cache.event_energy_bin,
            self.cache.event_energy_weight,
            self.cache.event_inverse_background,
            self.cache.grl_offsets,
            self.cache.grl_start,
            self.cache.grl_stop,
            self.cache.grl_cdf,
            self.cache.candidate_offsets,
            self.cache.candidate_events,
            self.cache.source_ra,
            self.cache.source_dec,
            self.cache.source_start,
            self.cache.source_stop,
            self.cache.source_dra_half,
            self.cache.source_response_bin,
            self.cache.source_time_factor,
            self.cache.phase_event_counts,
            self.cache.gamma_grid,
            self.cache.gamma_pdf_bin,
            self.cache.gamma_pdf_weight,
            self.cache.phase_yield_grid,
            self.cache.signal_densities,
            likelihood.ns_min,
            likelihood.ns_max,
        )
        return OptimizedCatalogTrials(
            trial_index=indices,
            seed=seeds.astype(np.uint64),
            source_ts=result[0],
            source_ns=result[1],
            source_gamma=result[2],
            source_fit_ok=result[3],
            stack_ts=result[4],
            stack_ns=result[5],
            stack_gamma=result[6],
            stack_fit_ok=result[7],
        )
