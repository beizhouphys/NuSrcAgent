"""Primary-spectrum point-source flux estimates using the existing likelihood.

The TS gate controls reporting only. Intervals and joint contours are asymptotic
statistical estimates; neither coverage nor detector/PDF systematics are supplied.
"""
from __future__ import annotations

import math

import numpy as np
from scipy.optimize import brentq, minimize_scalar
from scipy.stats import chi2


def profile_flux(log_ratio, detector_yield, ns_hat, gamma_hat, ns_bounds,
                 gamma_bounds=None, ts_threshold=9.0, observed_ts=None,
                 gamma_profile=None, detector_yield_derivative=None):
    """Profile phi1TeV and Gamma without changing events, PDFs or fit bounds.

    log_ratio(ns, gamma) returns (ln L/L0, d ln L/d ns). detector_yield(gamma)
    is the expected count for unit differential flux at 1 TeV in GeV units.
    At fixed phi1TeV, ns = phi1TeV * detector_yield(gamma) on every evaluation.
    """
    ns_hat, gamma_hat = float(ns_hat), float(gamma_hat)
    ns_min, ns_max = map(float, ns_bounds)
    if ns_min != 0 or not 0 <= ns_hat <= ns_max:
        raise ValueError("Flux profile requires the recorded nonnegative ns bounds")
    yields, evaluations = {}, {}

    def yield_at(gamma):
        gamma = float(gamma)
        if gamma not in yields:
            value = float(detector_yield(gamma))
            if not math.isfinite(value) or value <= 0:
                raise ValueError("Invalid detector yield in flux profile")
            yields[gamma] = value
        return yields[gamma]

    def evaluate(ns, gamma):
        ns, gamma = float(ns), float(gamma)
        key = (ns, gamma)
        if key not in evaluations:
            values = gamma_profile.evaluate(ns, gamma)[:2] if gamma_profile is not None else log_ratio(ns, gamma)
            value, slope = map(float, values)
            if not math.isfinite(value) or not math.isfinite(slope):
                raise ValueError("Non-finite primary-spectrum likelihood profile")
            evaluations[key] = (value, slope)
        return evaluations[key]

    best, _ = evaluate(ns_hat, gamma_hat)
    null, _ = evaluate(0., gamma_hat)
    ts = 2 * (best-null)
    if observed_ts is not None:
        if not math.isclose(ts, observed_ts, rel_tol=1e-7, abs_tol=1e-6):
            raise ValueError("Flux profile does not reproduce the maximized TS")
        ts = float(observed_ts)
    phi_hat = ns_hat / yield_at(gamma_hat)
    result = dict(phi0_hat=phi_hat, gamma=gamma_hat, ns_hat=ns_hat,
        pivot_energy_gev=1e3, phi0_unit="GeV^-1 cm^-2 s^-1", flavor="nu_mu+anti_nu_mu",
        phi100_hat=phi_hat * 100.**(-gamma_hat), yield_at_best=yield_at(gamma_hat),
        ts_threshold=float(ts_threshold), threshold_operator=">", TS=ts,
        reported=ts > ts_threshold, gamma_mode="fixed" if gamma_bounds is None else "fitted",
        method="asymptotic_profile_likelihood", coverage_validated=False,
        systematic_uncertainties_included=False, warnings=[], intervals=[], contours=[], profiles=[])
    if not result["reported"]:
        return result
    if ns_hat <= 0 or ns_hat >= ns_max:
        raise ValueError("Cannot construct a flux measurement at the ns fit boundary")

    def q(value):
        delta = 2*(best-value)
        if delta < -1e-5:
            point = next((key for key, item in evaluations.items() if item[0] == value), None)
            raise ValueError(f"Flux profile exceeds the recorded primary maximum: 2 Delta ln L = {-delta:.12g}; (ns, Gamma) = {point}")
        return max(0., delta)

    gamma_lo, gamma_hi = (gamma_hat, gamma_hat) if gamma_bounds is None else map(float, gamma_bounds)
    if not gamma_lo <= gamma_hat <= gamma_hi:
        raise ValueError("Recorded Gamma is outside the profile bounds")
    profiles = {}

    def maximize_gamma(log_phi):
        phi = phi_hat * math.exp(float(log_phi))

        def objective(gamma):
            ns = phi * yield_at(gamma)
            return -evaluate(ns, gamma)[0] if ns <= ns_max else float("inf")

        if gamma_bounds is None:
            candidates = [(objective(gamma_hat), gamma_hat)]
        elif gamma_profile is not None:
            from analysis_backend.gamma_maximum import maximize_pieces
            if gamma_profile.maximum is None or detector_yield_derivative is None:
                raise ValueError("Flux profiling requires the recorded Gamma maximum and detector-yield derivative")
            def value_gradient(gamma):
                ns = phi*yield_at(gamma)
                if ns > ns_max:
                    raise ValueError("Flux profile reaches the recorded ns bound in a retained Gamma interval")
                value, grad_ns, grad_gamma = gamma_profile.evaluate(ns, gamma)
                return value, grad_gamma+grad_ns*phi*detector_yield_derivative(gamma)
            maximum = maximize_pieces(value_gradient, gamma_bounds, gamma_profile.switches,
                initial=gamma_hat, interval_maxima=gamma_profile.maximum["intervals"])
            candidates = [(-maximum["log_likelihood_ratio"], maximum["gamma"])]
        else:
            # Check the whole recorded range, then refine each resolved maximum.
            grid = sorted(set(np.linspace(gamma_lo, gamma_hi, 13).tolist()+[gamma_hat]))
            values = [objective(g) for g in grid]
            candidates = list(zip(values, grid))
            for i in range(1, len(grid)-1):
                if math.isfinite(values[i]) and values[i] <= values[i-1] and values[i] <= values[i+1]:
                    fit = minimize_scalar(objective, bounds=(grid[i-1], grid[i+1]),
                                          method="bounded", options={"xatol": 2e-6})
                    if not fit.success:
                        raise ValueError("Gamma optimization failed in the flux profile")
                    candidates.append((float(fit.fun), float(fit.x)))
        value, gamma = min(candidates)
        if not math.isfinite(value):
            return None
        ns = phi * yield_at(gamma)
        row = dict(parameter="phi0", value=phi, phi0=phi, gamma=gamma, ns=ns, q=q(-value))
        profiles[("phi0", float(log_phi))] = row
        return row

    def maximize_ns(gamma):
        gamma = float(gamma)
        if gamma_profile is not None:
            ns = gamma_profile.profile_ns(gamma)["ns"]
        elif evaluate(0., gamma)[1] <= 0:
            ns = 0.
        else:
            upper = min(ns_max, max(1., ns_hat))
            while evaluate(upper, gamma)[1] > 0 and upper < ns_max:
                upper = min(ns_max, 2*upper)
            ns = upper if evaluate(upper, gamma)[1] >= 0 else float(brentq(
                lambda n: evaluate(n, gamma)[1], 0., upper, xtol=1e-7))
        row = dict(parameter="gamma", value=gamma, phi0=ns/yield_at(gamma),
                   gamma=gamma, ns=ns, q=q(evaluate(ns, gamma)[0]))
        profiles[("gamma", gamma)] = row
        return row

    def endpoints(parameter, target):
        roots = []
        center = 0. if parameter == "phi0" else gamma_hat
        function = maximize_gamma if parameter == "phi0" else maximize_ns
        for sign in (-1, 1):
            step, previous = (0.25 if parameter == "phi0" else 0.1), center
            boundary = False
            for _ in range(80):
                trial = center+sign*step
                if parameter == "gamma":
                    trial = max(gamma_lo, min(gamma_hi, trial))
                    boundary = trial in (gamma_lo, gamma_hi)
                row = function(trial)
                if row is None:
                    raise ValueError("Flux confidence crossing unavailable inside the recorded ns bounds")
                if row["q"] >= target:
                    root = float(brentq(lambda x: function(x)["q"]-target,
                                         min(previous, trial), max(previous, trial), xtol=1e-7))
                    roots.append(dict(value=function(root)["value"], q=function(root)["q"], boundary=False))
                    break
                if boundary:
                    roots.append(dict(value=row["value"], q=row["q"], boundary=True))
                    result["warnings"].append(f"{parameter} confidence interval reaches a recorded fit bound")
                    break
                previous, step = trial, step*1.6
            else:
                raise ValueError("Cannot bracket a primary-spectrum confidence interval")
        return roots

    for parameter in (["phi0", "gamma"] if gamma_bounds is not None else ["phi0"]):
        for confidence in (0.6826894921370859, 0.95):
            threshold = float(chi2.ppf(confidence, 1))
            lower, upper = endpoints(parameter, threshold)
            result["intervals"].append(dict(parameter=parameter, confidence_level=confidence,
                dof=1, critical_q=threshold, lower=lower["value"], upper=upper["value"],
                q_lower=lower["q"], q_upper=upper["q"],
                lower_at_boundary=lower["boundary"], upper_at_boundary=upper["boundary"]))

    if gamma_bounds is not None:
        # At fixed Gamma the mixture likelihood is concave in ns. Trace its two
        # crossings across the Gamma profile, preserving normalization correlation.
        for confidence in (0.6826894921370859, 0.95):
            threshold = float(chi2.ppf(confidence, 2))
            lower_g, upper_g = endpoints("gamma", threshold)
            gamma_grid = sorted(set(np.linspace(lower_g["value"], upper_g["value"], 33).tolist()
                                    + [gamma_hat]))
            if gamma_profile is not None:
                epsilon = gamma_profile.maximum["one_sided_epsilon"]
                gamma_grid = sorted(set(gamma_grid+[point+offset for point in gamma_profile.switches
                    for offset in (-epsilon, 0., epsilon) if lower_g["value"] < point+offset < upper_g["value"]]))
            lower_branch, upper_branch = [], []
            for index, gamma in enumerate(gamma_grid):
                row = maximize_ns(gamma)
                if row["q"] > threshold+1e-5:
                    raise ValueError("Joint confidence contour crosses a disconnected Gamma region")
                peak = row["ns"]
                crossing = lambda ns: q(evaluate(ns, gamma)[0])-threshold
                if abs(row["q"]-threshold) < 1e-6:
                    low_ns, high_ns = peak, peak
                else:
                    if crossing(0.) <= 0:
                        raise ValueError("Joint flux contour reaches the zero-signal boundary")
                    low_ns = float(brentq(crossing, 0., peak, xtol=1e-7))
                    high = min(ns_max, peak+max(1., math.sqrt(peak+1)))
                    while crossing(high) < 0 and high < ns_max:
                        high = min(ns_max, peak+2*(high-peak))
                    if crossing(high) < 0:
                        raise ValueError("Joint flux contour unavailable inside the recorded ns bounds")
                    high_ns = float(brentq(crossing, peak, high, xtol=1e-7))
                for branch, ns in ((lower_branch, low_ns), (upper_branch, high_ns)):
                    branch.append(dict(gamma=gamma, phi0=ns/yield_at(gamma), ns=ns,
                                       q=q(evaluate(ns, gamma)[0])))
            closed = not (lower_g["boundary"] or upper_g["boundary"])
            result["contours"].append(dict(confidence_level=confidence, dof=2,
                critical_q=threshold, closed=closed, lower_branch=lower_branch, upper_branch=upper_branch))
    result["warnings"] = list(dict.fromkeys(result["warnings"]))
    result["profiles"] = list(profiles.values())
    result["likelihood_evaluations"] = len(evaluations)
    if gamma_profile is not None:
        result["gamma_search_procedure"] = gamma_profile.maximum["procedure"]
        result["likelihood_evaluations"] = len(gamma_profile.values)
    return result


def source_flux_measurement(analysis, result, ts_threshold, gamma_profile=None):
    if result["n_sources"] != 1 or result["likelihood_mode"] != "spatial_energy":
        raise ValueError("Flux measurements require a spatial+energy single-source fit")
    if result["minimizer_status"].get("warnflag") != 0:
        raise ValueError("Cannot measure flux from an unconverged primary fit")
    fitted = result["gamma_mode"] == "fitted"

    def parameters(ns, gamma):
        return np.asarray([ns, gamma] if fitted else [ns], dtype=np.float64)

    def log_ratio(ns, gamma):
        value, gradient = analysis.llhratio.evaluate(parameters(ns, gamma))
        return value, gradient[0]

    yield_cache = {}
    def yield_and_derivative(gamma):
        if gamma in yield_cache:
            return yield_cache[gamma]
        records = analysis.pmm.create_src_params_recarray(gflp_values=parameters(result["ns"], gamma))
        service = analysis.src_detsigyield_weights_service
        service.calculate(src_params_recarray=records)
        weights, derivatives = service.get_weights()
        derivative = float(np.sum(derivatives[analysis.pmm.get_gflp_idx("gamma")][:, 0])) if fitted else 0.
        yield_cache[gamma] = (float(np.sum(weights[:, 0])), derivative)
        return yield_cache[gamma]

    def detector_yield(gamma):
        return yield_and_derivative(gamma)[0]

    measurement = profile_flux(log_ratio, detector_yield, result["ns"], result["gamma"],
        result["fit_bounds"]["ns"], result["fit_bounds"]["gamma_skyllh"], ts_threshold,
        observed_ts=result["TS"], gamma_profile=gamma_profile,
        detector_yield_derivative=lambda g: yield_and_derivative(g)[1])
    if not math.isclose(measurement["TS"], result["TS"], rel_tol=1e-7, abs_tol=1e-6):
        raise ValueError("Flux profile does not reproduce the maximized TS")
    # The policy uses the original TS, including its strict equality boundary.
    if measurement["reported"] != (result["TS"] > ts_threshold):
        raise ValueError("Inconsistent TS reporting gate")
    measurement.update({key: result[key] for key in (
        "event_selection", "event_dec_min_deg", "event_dec_max_deg", "fit_bounds")})
    log_ratio(result["ns"], result["gamma"])
    return measurement
