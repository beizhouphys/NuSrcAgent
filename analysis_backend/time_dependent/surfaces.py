"""Observed ``(n_s, Gamma)`` likelihood surfaces for fixed-profile analyses.

The production fit stores only the maximum.  This module reconstructs the
same immutable observed likelihood and evaluates it on a plotting grid without
performing another maximization or using background trials.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from .analysis import ConstructedCatalogAnalysis


SURFACE_SCHEMA = "td_likelihood_surface_v1"


@dataclass(frozen=True)
class SurfaceInputs:
    """Likelihood inputs for one source hypothesis or the catalog stack."""

    native_gamma: np.ndarray
    ratio_grid: np.ndarray
    phase_indices: np.ndarray
    selected_counts: np.ndarray
    phase_event_counts: np.ndarray
    yield_grid: np.ndarray


def _observed_surface_inputs(
    constructed: ConstructedCatalogAnalysis,
    source_index: int | None,
) -> SurfaceInputs:
    """Build the exact observed ratios used by the continuous profile fit."""

    from .optimized import OptimizedSharedScrambleEngine

    engine = OptimizedSharedScrambleEngine(constructed)
    events = []
    for data in constructed.data_list:
        if data.exp is None:
            raise RuntimeError("constructed phase has no experimental data")
        events.append(data.exp)
    event_counts = np.asarray([len(item) for item in events], dtype=np.int64)
    (
        native_gamma,
        ratio_grids,
        source_indices,
        event_indices,
        phase_yield_grid,
    ) = engine._evaluate_grid(events, event_counts, None)

    if source_index is not None:
        if not 0 <= source_index < engine.n_sources:
            raise IndexError(f"source index {source_index} is outside the catalog")
        grids = []
        phases = []
        for phase, (grid, indices) in enumerate(
            zip(ratio_grids, source_indices, strict=True)
        ):
            mask = indices == source_index
            grids.append(grid[:, mask])
            phases.append(np.full(np.count_nonzero(mask), phase, dtype=np.int32))
        phase_indices = np.concatenate(phases)
        return SurfaceInputs(
            native_gamma=native_gamma,
            ratio_grid=np.concatenate(grids, axis=1),
            phase_indices=phase_indices,
            selected_counts=np.bincount(
                phase_indices, minlength=len(event_counts)
            ).astype(np.int64),
            phase_event_counts=event_counts,
            yield_grid=phase_yield_grid[:, :, source_index],
        )

    stack_grids = []
    stack_phases = []
    for phase, (grid, sources, event_ids) in enumerate(
        zip(ratio_grids, source_indices, event_indices, strict=True)
    ):
        unique_events, inverse = np.unique(event_ids, return_inverse=True)
        stacked = np.zeros((len(native_gamma), len(unique_events)), dtype=np.float64)
        phase_yields = np.sum(phase_yield_grid[:, phase, :], axis=1)
        if np.any(phase_yields <= 0.0):
            raise ValueError("stack has a nonpositive detector yield")
        for gamma_index in range(len(native_gamma)):
            np.add.at(
                stacked[gamma_index],
                inverse,
                grid[gamma_index]
                * phase_yield_grid[gamma_index, phase, sources],
            )
            stacked[gamma_index] /= phase_yields[gamma_index]
        stack_grids.append(stacked)
        stack_phases.append(
            np.full(len(unique_events), phase, dtype=np.int32)
        )
    phase_indices = np.concatenate(stack_phases)
    return SurfaceInputs(
        native_gamma=native_gamma,
        ratio_grid=np.concatenate(stack_grids, axis=1),
        phase_indices=phase_indices,
        selected_counts=np.bincount(
            phase_indices, minlength=len(event_counts)
        ).astype(np.int64),
        phase_event_counts=event_counts,
        yield_grid=np.sum(phase_yield_grid, axis=2),
    )


def evaluate_log_lambda_surface(
    inputs: SurfaceInputs,
    gamma_values: np.ndarray,
    ns_values: np.ndarray,
    *,
    ns_chunk_size: int = 32,
) -> np.ndarray:
    """Evaluate log Lambda with the production linear-density interpolation."""

    gamma_values = np.asarray(gamma_values, dtype=np.float64)
    ns_values = np.asarray(ns_values, dtype=np.float64)
    if gamma_values.ndim != 1 or ns_values.ndim != 1:
        raise ValueError("Gamma and ns axes must be one-dimensional")
    if ns_chunk_size < 1:
        raise ValueError("ns_chunk_size must be positive")
    native = inputs.native_gamma
    if (
        native.ndim != 1
        or len(native) < 2
        or np.any(np.diff(native) <= 0.0)
        or np.min(gamma_values) < native[0]
        or np.max(gamma_values) > native[-1]
    ):
        raise ValueError("requested Gamma grid lies outside the native Gamma grid")

    pure_counts = inputs.phase_event_counts - inputs.selected_counts
    if np.any(pure_counts < 0):
        raise ValueError("selected event counts exceed phase event counts")
    surface = np.full((len(gamma_values), len(ns_values)), np.nan, dtype=np.float64)
    for gamma_index, gamma in enumerate(gamma_values):
        left = int(
            np.clip(
                np.searchsorted(native, gamma, side="right") - 1,
                0,
                len(native) - 2,
            )
        )
        weight = (gamma - native[left]) / (native[left + 1] - native[left])
        ratios = (
            (1.0 - weight) * inputs.ratio_grid[left]
            + weight * inputs.ratio_grid[left + 1]
        )
        yields = (
            (1.0 - weight) * inputs.yield_grid[left]
            + weight * inputs.yield_grid[left + 1]
        )
        if np.sum(yields) <= 0.0:
            continue
        fractions = yields / np.sum(yields)
        coefficients = (
            fractions[inputs.phase_indices]
            / inputs.phase_event_counts[inputs.phase_indices]
            * (ratios - 1.0)
        )
        phase_scale = fractions / inputs.phase_event_counts
        for start in range(0, len(ns_values), ns_chunk_size):
            stop = min(start + ns_chunk_size, len(ns_values))
            ns = ns_values[start:stop]
            selected_terms = 1.0 + ns[:, np.newaxis] * coefficients[np.newaxis, :]
            pure_terms = 1.0 - ns[:, np.newaxis] * phase_scale[np.newaxis, :]
            valid = np.all(selected_terms > 0.0, axis=1) & np.all(
                pure_terms > 0.0, axis=1
            )
            values = np.full(len(ns), np.nan, dtype=np.float64)
            values[valid] = np.sum(np.log(selected_terms[valid]), axis=1)
            values[valid] += np.sum(
                pure_counts[np.newaxis, :] * np.log(pure_terms[valid]), axis=1
            )
            surface[gamma_index, start:stop] = values
    return surface


def save_observed_likelihood_surface(
    constructed: ConstructedCatalogAnalysis,
    output: str | Path,
    fit: dict[str, Any],
    *,
    source_index: int | None,
    source_name: str = "",
    source_id: str = "",
    ns_points: int = 251,
    gamma_points: int = 121,
) -> dict[str, Any]:
    """Evaluate, validate, and atomically save one canonical surface NPZ."""

    if not constructed.config.spectrum.fit_gamma:
        raise ValueError("a two-dimensional ns-Gamma surface requires fitted Gamma")
    if ns_points < 2 or gamma_points < 2:
        raise ValueError("surface axes require at least two points")
    best_ns = float(fit["ns"])
    best_ts = float(fit["TS"])
    best_gamma = fit.get("gamma")
    if not np.isfinite(best_ns) or not np.isfinite(best_ts) or best_ns < 0.0:
        raise ValueError("saved fit has invalid ns or TS")
    if best_ns > 0.0 and (best_gamma is None or not np.isfinite(best_gamma)):
        raise ValueError("positive-ns free-Gamma fit has no finite Gamma")

    likelihood = constructed.config.likelihood
    spectrum = constructed.config.spectrum
    ns_max = min(float(likelihood.ns_max), max(25.0, 1.5 * best_ns))
    if ns_max < best_ns:
        raise ValueError("saved best-fit ns lies outside the likelihood bounds")
    ns_values = np.linspace(float(likelihood.ns_min), ns_max, ns_points)
    gamma_values = np.linspace(
        float(spectrum.gamma_min), float(spectrum.gamma_max), gamma_points
    )
    inputs = _observed_surface_inputs(constructed, source_index)
    log_lambda = evaluate_log_lambda_surface(inputs, gamma_values, ns_values)
    if not np.all(np.isfinite(log_lambda)):
        raise ValueError("likelihood surface contains nonfinite grid values")

    if best_gamma is None:
        if not np.isclose(best_ns, float(likelihood.ns_min), atol=1e-10, rtol=0.0):
            raise ValueError("unidentified Gamma is valid only on the ns boundary")
        maximum = 0.0
        if not np.allclose(log_lambda[:, 0], maximum, atol=1e-10, rtol=0.0):
            raise ValueError("ns-boundary likelihood is not Gamma independent")
    else:
        maximum = float(
            evaluate_log_lambda_surface(
                inputs,
                np.asarray([float(best_gamma)]),
                np.asarray([best_ns]),
            )[0, 0]
        )
        if not np.isfinite(maximum) or not np.isclose(
            2.0 * maximum, best_ts, rtol=2e-4, atol=3e-2
        ):
            raise ValueError(
                "evaluated likelihood surface does not reproduce the saved fitted TS"
            )
    delta = 2.0 * (maximum - log_lambda)
    finite_delta = delta[np.isfinite(delta)]
    if not finite_delta.size or float(np.min(finite_delta)) < -3e-2:
        raise ValueError("likelihood grid exceeds the saved maximum")

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    with temporary.open("wb") as stream:
        np.savez_compressed(
            stream,
            surface_schema=np.asarray(SURFACE_SCHEMA),
            ns=ns_values,
            gamma=gamma_values,
            log_lambda=log_lambda,
            minus_2_delta_log_likelihood=delta,
            native_gamma=inputs.native_gamma,
            selected_counts=inputs.selected_counts,
            phase_event_counts=inputs.phase_event_counts,
            source_index=np.asarray(-1 if source_index is None else source_index),
            source_name=np.asarray(source_name),
            source_id=np.asarray(source_id),
            best_fit_ns=np.asarray(best_ns),
            best_fit_gamma=np.asarray(
                np.nan if best_gamma is None else float(best_gamma)
            ),
            best_fit_ts=np.asarray(best_ts),
        )
    temporary.replace(output)
    return {
        "path": str(output),
        "schema": SURFACE_SCHEMA,
        "source_index": source_index,
        "source_name": source_name or None,
        "ns_points": int(ns_points),
        "gamma_points": int(gamma_points),
        "ns_min": float(ns_values[0]),
        "ns_max": float(ns_values[-1]),
        "gamma_min": float(gamma_values[0]),
        "gamma_max": float(gamma_values[-1]),
        "minimum_minus_2_delta_log_likelihood": float(np.min(finite_delta)),
    }
