"""One-sided asymptotic upper limits for a fixed-spectrum scalar signal fit.

This inverts the existing likelihood without changing PDFs or fit bounds.
The normal critical value is an approximation, not a coverage calibration.
"""
from __future__ import annotations

import math
from statistics import NormalDist

from scipy.optimize import brentq
from agent_core.profile_progress import ProfileProgress


def invert_upper_profile(log_likelihood_ratio, ns_hat, ns_max, confidence):
    progress=ProfileProgress()
    with progress.work('fixed-spectrum upper-limit inversion',1):
        with progress.unit():
            return _invert_upper_profile(lambda ns: progress.evaluate(
                lambda n,g: log_likelihood_ratio(n),ns,0.), ns_hat,ns_max,confidence)


def _invert_upper_profile(log_likelihood_ratio, ns_hat, ns_max, confidence):
    """Find the upper crossing above the constrained scalar maximum.

    ``log_likelihood_ratio`` returns ln(L(ns)/L(0)). The fixed-spectrum
    mixture likelihood is concave in ns; no Gamma optimization occurs here.
    Failure to cross inside the recorded bounds is an error, never a limit.
    """
    ns_hat, ns_max, confidence = map(float, (ns_hat, ns_max, confidence))
    if not all(map(math.isfinite, (ns_hat, ns_max, confidence))) or not 0 <= ns_hat < ns_max or not 0.5 < confidence < 1:
        raise ValueError("Invalid scalar upper-limit bounds or confidence")
    threshold = NormalDist().inv_cdf(confidence) ** 2
    evaluations = {}

    def evaluate(ns):
        ns = float(ns)
        if ns not in evaluations:
            value = float(log_likelihood_ratio(ns))
            if not math.isfinite(value):
                raise ValueError("Non-finite likelihood during upper-limit inversion")
            evaluations[ns] = value
        return evaluations[ns]

    best = evaluate(ns_hat)
    if evaluate(0.0) > best + 1e-6:
        raise ValueError("Recorded best fit is worse than the null likelihood")

    def crossing(ns):
        value = evaluate(ns)
        if value > best + 1e-6:
            raise ValueError("Profile evaluation exceeds the recorded maximum")
        return 2.0 * (best - value) - threshold

    upper = min(ns_max, ns_hat + max(1.0, math.sqrt(ns_hat + 1.0)))
    while crossing(upper) < 0 and upper < ns_max:
        upper = min(ns_max, ns_hat + 2.0 * (upper - ns_hat))
    if crossing(upper) < 0:
        raise ValueError("Upper limit does not cross the threshold inside the recorded ns bounds")
    root = float(brentq(crossing, ns_hat, upper, xtol=1e-9, rtol=1e-12))
    q_root = 2.0 * (best - evaluate(root))
    return {
        "confidence_level": confidence,
        "sidedness": "one_sided_upper",
        "method": "asymptotic_fixed_gamma_profile_likelihood",
        "critical_q": threshold,
        "q_at_upper_limit": q_root,
        "ns_upper_limit": root,
        "ns_hat": ns_hat,
        "ns_bound_max": ns_max,
        "log_likelihood_ratio_at_best": best,
        "coverage_validated": False,
        "systematic_uncertainties_included": False,
        "profile": [{"ns": ns, "log_likelihood_ratio": value,
                     "q": 2.0 * (best - value)}
                    for ns, value in sorted(evaluations.items())],
    }


def fixed_gamma_flux_upper_limit(analysis, result, confidence):
    """Use exactly the fit's public-effective-area yield and interpolation.

    The analysis flux model has Phi0=1 at 1 TeV, in GeV^-1 cm^-2 s^-1.
    A point-source flux has no sr^-1 and no all-flavor factor is introduced.
    """
    import numpy as np

    if result["gamma_mode"] != "fixed" or result["likelihood_mode"] != "spatial_energy":
        raise ValueError("Flux upper limits require a fixed-Gamma spatial+energy fit")
    if int(result["minimizer_status"].get("warnflag", -1)) != 0:
        raise ValueError("Cannot invert an unconverged fit")

    def log_ratio(ns):
        value, _ = analysis.llhratio.evaluate(np.asarray([ns], dtype=np.float64))
        return value

    limit = invert_upper_profile(log_ratio, result["ns"], result["fit_bounds"]["ns"][1], confidence)
    if not math.isclose(2 * limit["log_likelihood_ratio_at_best"], result["TS"], abs_tol=1e-6, rel_tol=1e-7):
        raise ValueError("Upper-limit likelihood does not reproduce the maximized TS")
    # With sum_j w_model[j] = 1, phi0 is the sum of the source fluxes.
    # Each source has phi0_j = w_model[j] * phi0; acceptance is applied once.
    weights = result.get("w_model", [1.] if result["n_sources"] == 1 else [])
    if len(weights) != result["n_sources"] or not math.isclose(sum(weights), 1., abs_tol=1e-12):
        raise ValueError("Flux conversion requires normalized intrinsic source weights")
    yield_by_dataset = {name: sum(float(w)*float(y) for w, y in zip(weights, values, strict=True) if w > 0)
                        for name, values in result["w_acc_by_dataset"].items()}
    yield_at_1tev = sum(yield_by_dataset.values())
    if not math.isfinite(yield_at_1tev) or yield_at_1tev <= 0:
        raise ValueError("Invalid detector yield for point-source flux conversion")
    gamma = float(result["gamma"])
    yield_at_100tev = yield_at_1tev * 100.0 ** gamma
    phi_upper = limit["ns_upper_limit"] / yield_at_100tev
    limit.update({
        "gamma": gamma, "gamma_mode": "fixed",
        "flux_definition": "dPhi/dE = phi0 * (E / 100 TeV)^(-Gamma)",
        "flavor": "nu_mu+anti_nu_mu", "pivot_energy_gev": 1e5,
        "phi0_unit": "GeV^-1 cm^-2 s^-1", "phi0_upper_limit": phi_upper,
        "e2_dphi_de_upper_limit_gev_cm2_s": 1e10 * phi_upper,
        "e2_dphi_de_upper_limit_tev_cm2_s": 1e7 * phi_upper,
        "flux_conversion": "same SkyLLH public-effective-area/livetime detector yield and declination interpolation as the fit; no DR1 paper calibration",
        "yield_per_phi0_at_100tev": yield_at_100tev,
        "yield_per_phi0_at_1tev_by_dataset": yield_by_dataset,
        "event_selection": result["event_selection"],
        "event_dec_min_deg": result["event_dec_min_deg"],
        "event_dec_max_deg": result["event_dec_max_deg"],
    })
    if result["n_sources"] > 1:
        limit.update(intensity0_upper_limit=limit["phi0_upper_limit"]/(4*math.pi),
                     intensity0_unit="GeV^-1 cm^-2 s^-1 sr^-1", solid_angle_sr=4*math.pi,
                     e2_intensity_upper_limit_gev_cm2_s_sr=limit["e2_dphi_de_upper_limit_gev_cm2_s"]/(4*math.pi))
        limit.update(flux_scope="sum_of_source_fluxes", n_sources=result["n_sources"],
                     source_flux_definition="dPhi_j/dE = w_model_j * phi0_total * (E / 100 TeV)^(-Gamma); sum_j w_model_j = 1")
    return limit
