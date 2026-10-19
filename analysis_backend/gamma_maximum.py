"""Maximize the unchanged DR2 likelihood across its Gamma interpolation pieces."""
from __future__ import annotations

import math

import numpy as np
from scipy.optimize import brentq, minimize, minimize_scalar


LEGACY_FIT = "skyllh_lbfgs_v1"
PIECEWISE_FIT = "gamma_piecewise_v1"


def maximize_pieces(value_gradient, bounds, switches, initial=None, interval_maxima=None):
    """Check each smooth piece, exact switch and one-sided switch values.

    Optional interval maxima are the previously computed maxima over free ns.
    They bound the corresponding fixed-flux likelihood and permit eliminating
    pieces that cannot improve a candidate. No interpolation value is changed.
    """
    lower, upper = map(float, bounds)
    breaks = sorted(set(float(g) for g in switches if lower < g < upper))
    knots = [lower, *breaks, upper]
    epsilon = min(1e-9, min(np.diff(knots))*1e-7)
    cache = {}

    def evaluate(gamma):
        gamma = float(gamma)
        if gamma not in cache:
            value, gradient = map(float, value_gradient(gamma))
            if not math.isfinite(value) or not math.isfinite(gradient):
                raise ValueError("Non-finite likelihood or derivative in Gamma maximum search")
            cache[gamma] = (value, gradient)
        return cache[gamma]

    candidates = []
    if initial is not None and lower <= initial <= upper:
        candidates.append((evaluate(initial)[0], float(initial)))
    records, fallbacks = [], 0
    limits = {(r["lower"], r["upper"]): r["log_likelihood_ratio"] for r in interval_maxima or []}
    intervals = list(zip(knots[:-1], knots[1:]))
    if limits:
        intervals.sort(key=lambda pair: limits[pair], reverse=True)
    for left, right in intervals:
        if limits and candidates and limits[(left, right)] < max(candidates)[0]-1e-7:
            continue
        lo = left if left == lower else left+epsilon
        hi = right if right == upper else right-epsilon
        middle = (lo+hi)/2
        samples = [left, lo, middle, hi, right]
        local = [(evaluate(g)[0], g) for g in samples]

        def objective(array):
            value, derivative = evaluate(float(array[0]))
            return -value, np.asarray([-derivative])

        fit = minimize(objective, [middle], jac=True, bounds=[(lo, hi)], method="L-BFGS-B",
                       options={"ftol": 1e-13, "gtol": 1e-7, "maxiter": 100})
        if not fit.success:
            # A derivative-free search remains within the same recorded piece.
            fit = minimize_scalar(lambda g: -evaluate(g)[0], bounds=(lo, hi), method="bounded",
                                  options={"xatol": 2e-8, "maxiter": 150})
            fallbacks += 1
            gamma = float(fit.x)
        else:
            gamma = float(fit.x[0])
        if not fit.success:
            raise ValueError("Gamma optimization failed inside an interpolation interval")
        local.append((evaluate(gamma)[0], gamma))
        value, gamma = max(local)
        candidates.append((value, gamma))
        records.append(dict(lower=left, upper=right, gamma=gamma, log_likelihood_ratio=value))
    # Retain the original candidate in exact likelihood ties (notably ns=0).
    value, gamma = candidates[0]
    for other, point in candidates[1:]:
        if other > value+1e-12:
            value, gamma = other, point
    return dict(gamma=gamma, log_likelihood_ratio=value, intervals=records,
                evaluations=len(cache), derivative_free_fallbacks=fallbacks,
                switch_points=breaks, one_sided_epsilon=epsilon,
                at_switch=any(abs(gamma-point) <= 2*epsilon for point in breaks))


class GammaProfile:
    """Concave ns maximization and cached likelihood evaluations at each Gamma."""

    def __init__(self, log_ratio_gradient, ns_bounds, gamma_bounds, switches, ns_seed):
        self.log_ratio_gradient = log_ratio_gradient
        self.ns_bounds = tuple(map(float, ns_bounds))
        self.gamma_bounds = tuple(map(float, gamma_bounds))
        self.switches = list(switches)
        self.ns_seed = float(ns_seed)
        self.values, self.profiles = {}, {}
        self.maximum = None
        if self.ns_bounds[0] != 0 or self.ns_bounds[1] <= 0:
            raise ValueError("Gamma search requires the recorded nonnegative ns bounds")

    def evaluate(self, ns, gamma):
        key = (float(ns), float(gamma))
        if key not in self.values:
            value, gradients = self.log_ratio_gradient(*key)
            row = tuple(map(float, (value, *gradients)))
            if len(row) != 3 or not all(map(math.isfinite, row)):
                raise ValueError("Invalid likelihood evaluation during Gamma search")
            self.values[key] = row
        return self.values[key]

    def profile_ns(self, gamma):
        gamma = float(gamma)
        if gamma not in self.profiles:
            if self.evaluate(0., gamma)[1] <= 0:
                ns = 0.
            else:
                upper = min(self.ns_bounds[1], max(1., self.ns_seed))
                while self.evaluate(upper, gamma)[1] > 0 and upper < self.ns_bounds[1]:
                    upper = min(self.ns_bounds[1], 2*upper)
                ns = upper if self.evaluate(upper, gamma)[1] >= 0 else float(brentq(
                    lambda n: self.evaluate(n, gamma)[1], 0., upper, xtol=1e-7))
            value, derivative_ns, derivative_gamma = self.evaluate(ns, gamma)
            self.profiles[gamma] = dict(ns=ns, gamma=gamma, log_likelihood_ratio=value,
                                        derivative_ns=derivative_ns, derivative_gamma=derivative_gamma)
        return self.profiles[gamma]

    def maximize(self, original_ns, original_gamma):
        original_value = self.evaluate(original_ns, original_gamma)[0]
        def value_gradient(gamma):
            row = self.profile_ns(gamma)
            return row["log_likelihood_ratio"], row["derivative_gamma"]
        maximum = maximize_pieces(value_gradient, self.gamma_bounds, self.switches, initial=original_gamma)
        row = self.profile_ns(maximum["gamma"])
        if maximum["log_likelihood_ratio"] < original_value-1e-7:
            raise ValueError("Gamma search lost the original fit maximum")
        maximum.update(ns=row["ns"], procedure=PIECEWISE_FIT,
            original_ns=float(original_ns), original_gamma=float(original_gamma),
            original_log_likelihood_ratio=original_value,
            improvement_in_TS=2*(maximum["log_likelihood_ratio"]-original_value),
            ns_bounds=list(self.ns_bounds), gamma_bounds=list(self.gamma_bounds),
            likelihood_evaluations=len(self.values))
        self.maximum = maximum
        return maximum


def runtime_gamma_profile(analysis, ns_bounds, gamma_bounds, ns_seed):
    """Use the actual runtime Gamma grid; do not replace its interpolation."""
    grids = [ratio.gamma_grid for ratio in analysis.chunked_ratios]
    delta, origin = float(grids[0].delta), float(grids[0].lower_bound)
    if any(float(grid.delta) != delta or float(grid.lower_bound) != origin for grid in grids):
        raise ValueError("DR2 datasets have inconsistent Gamma interpolation grids")
    lower, upper = map(float, gamma_bounds)
    first = math.floor((lower-origin)/delta)-1
    last = math.ceil((upper-origin)/delta)+1
    switches = [float(round(origin+(index+.5)*delta, 12)) for index in range(first, last+1)]
    switches = [point for point in switches if lower < point < upper]
    def evaluate(ns, gamma):
        return analysis.llhratio.evaluate(np.asarray([ns, gamma], dtype=np.float64))
    return GammaProfile(evaluate, ns_bounds, gamma_bounds, switches, ns_seed)
