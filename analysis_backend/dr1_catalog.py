#!/usr/bin/python
from __future__ import annotations

from agent_core.progress import track_progress

# The stacking likelihood core is a callable extraction of the corresponding
# blocks in legacy_codex_revised/likelihood_v4.py.  Agent-facing task and result handling
# that does not exist in the legacy script remains local to this module.

import builtins
import math
from statistics import NormalDist
from typing import Any

from numpy import *

from agent_core.schemas import NormalizedAnalysis
from analysis_backend.dr1_single_source import bounded_minimize, interp1d_linear, load_backend_data, run_single_source_time_integrated


FIG4_ASTRO_NS_REFERENCES = {-2.00: 3217.3, -2.53: 8845.7, -3.00: 49282.2}
REFERENCE_DIFFUSE_ALL_FLAVOR_FLUX100 = {-2.00: 5e-8, -2.53: 4.98e-8, -3.00: 5e-8}


def run_catalog_time_integrated(normalized: NormalizedAnalysis, repo_root='.') -> dict[str, object]:
    source_results, source_warnings = run_source_scan(normalized, repo_root)
    stacking_results: list[dict[str, object]] = []
    stacking_curves: list[dict[str, object]] = []
    stacking_warnings: list[str] = []
    schemes = build_weighting_schemes(normalized)
    for gamma in track_progress(normalized.spectral_indices, "DR1 stacking spectra"):
        data = load_backend_data(repo_root, gamma)
        for scheme_name, weights in schemes:
            result, curve = run_stacking_likelihood(normalized, weights, scheme_name, gamma, data)
            stacking_results.append(result)
            stacking_curves.append(curve)
            if not isfinite(float(result["flux_100tev_95"])):
                stacking_warnings.append(f"Flux conversion is unavailable for gamma={float(gamma):g}; flux_100tev_95 and fraction_of_diffuse_flux_95 are left blank.")
    stacking_warnings.append("Fig. 4 flux conversion uses the paper-calibrated astrophysical event-count references from legacy_codex_revised/likelihood_v4.py and legacy_codex_revised/ns2flux.py.")
    return {
        "backend": "likelihood_catalog_time_integrated_v1",
        "n_sources": len(normalized.sources),
        "source_scan_completed": len(source_results),
        "stacking_hypotheses": len(stacking_results),
        "source_results_file": "source_results.csv",
        "stacking_results_file": "stacking_results.csv",
        "excel_file": "analysis_results.xlsx",
        "figures": ["fig1_sky_distribution.pdf", "fig3_ts_distribution.pdf", "fig4_stacking.pdf"],
        "note": "catalog-wide single-source scan plus time-integrated stacking likelihood",
        "warnings": source_warnings + stacking_warnings,
        "_source_results": source_results,
        "_stacking_results": stacking_results,
        "_stacking_curves": stacking_curves,
    }


def run_source_scan(normalized: NormalizedAnalysis, repo_root='.') -> tuple[list[dict[str, object]], list[str]]:
    rows: list[dict[str, object]] = []
    warnings: list[str] = []
    n_tests = len(normalized.sources)
    for source in track_progress(normalized.sources, "DR1 catalog source fits"):
        result = run_single_source_time_integrated(source.ra_deg, source.dec_deg, repo_root=repo_root, gamma=normalized.spectral_indices[0])
        pre_trial_p = float(result["pre_trial_p"])
        post_trial_p = 1.-(1.-pre_trial_p)**n_tests
        ts = builtins.max(float(result["ts"]), 0.)
        ns_hat = float(result["best_fit_ns"])
        row: dict[str, object] = dict(source.metadata)
        row.update({
            "source_number": source.source_number,
            "source_name": source.name,
            "ra_deg": source.ra_deg,
            "dec_deg": source.dec_deg,
            "intrinsic_weight": source.weight,
            "ns_hat": ns_hat,
            "ts": ts,
            "signed_sqrt_ts": math.copysign(math.sqrt(ts), ns_hat),
            "pre_trial_p": pre_trial_p,
            "pre_trial_significance": normal_isf(pre_trial_p),
            "post_trial_p": post_trial_p,
            "post_trial_significance": builtins.max(normal_isf(post_trial_p), 0.),
            "n_events_in_roi": int(result["n_events_in_roi"]),
            "fit_status": "completed",
        })
        rows.append(row)
        warnings.extend(str(value) for value in result.get("warnings", []))
    ranked = sorted(rows, key=lambda row: float(row["signed_sqrt_ts"]), reverse=True)
    ranks = {int(row["source_number"]): rank for rank, row in enumerate(ranked, start=1)}
    for row in rows:
        row["significance_rank"] = ranks[int(row["source_number"])]
    return rows, list(dict.fromkeys(warnings))


def build_weighting_schemes(normalized: NormalizedAnalysis) -> list[tuple[str, ndarray]]:
    n_sources = len(normalized.sources)
    input_weights = array([source.weight for source in normalized.sources], dtype=float)
    input_weights = input_weights/input_weights.sum()
    uniform = ones(n_sources, dtype=float)/float(n_sources)
    schemes: list[tuple[str, ndarray]] = []
    if normalized.include_uniform_baseline:
        schemes.append(("uniform", uniform))
    if not allclose(input_weights, uniform) or not normalized.include_uniform_baseline:
        schemes.append(("input_weight", input_weights))
    return schemes


def run_stacking_likelihood(normalized: NormalizedAnalysis, intrinsic_weights: ndarray, scheme_name: str, gamma: float, data: dict[str, Any]) -> tuple[dict[str, object], dict[str, object]]:
    # Names and calculation order below follow likelihood_v4.py:194-200 and
    # 615-630 so that the callable backend remains easy to compare to it.
    RAs_src = array([source.ra_rad for source in normalized.sources], dtype=float)
    Decs_src = array([source.dec_rad for source in normalized.sources], dtype=float)
    N_src = len(RAs_src)
    W_mdls_src = asarray(intrinsic_weights, dtype=float)
    W_accs_src = source_acceptance_matrix(Decs_src, data)

    W_facs, W_facs_normd, fks = legacy_stacking_weights(W_accs_src, W_mdls_src, scheme_name == "uniform")
    S_ki, B_ki, Nks1 = stacking_signal_background_pdfs(RAs_src, Decs_src, W_facs_normd, data)

    def ts_function(n_s):
        return TS_tot(n_s, fks, S_ki, B_ki, Nks1)

    # likelihood_v4.py first scans a logarithmic n_s grid to seed the fit.
    ns_seed_grid = legacy_ns_grid(float(Nks1.sum()))
    TS_seed_grid = array([ts_function(n_s) for n_s in ns_seed_grid])
    ns_s_hat = ns_seed_grid[argmax(TS_seed_grid)] if len(ns_seed_grid) else 0.
    ts, ns_hat = max_TS_tot(ns_s_hat, fks, S_ki, B_ki, Nks1)
    if ts <= 0.:
        ts = 0.
        ns_hat = 0.
    ns_95 = find_ns_95(ts_function, ns_hat, ts, float(Nks1.sum()))
    flux_100tev_95 = ns_to_fig4_flux100(ns_95, gamma)
    reference_flux = REFERENCE_DIFFUSE_ALL_FLAVOR_FLUX100.get(round(float(gamma), 2))
    fraction_diffuse = None if reference_flux is None else flux_100tev_95/reference_flux
    pre_trial_p = 0.5*math.erfc(math.sqrt(ts/2.))
    result = {
        "weighting_scheme": scheme_name,
        "spectral_index": float(gamma),
        "n_sources": len(normalized.sources),
        "ns_hat": float(ns_hat),
        "ts": ts,
        "pre_trial_p": pre_trial_p,
        "pre_trial_significance": normal_isf(pre_trial_p),
        "post_trial_p": None,
        "post_trial_significance": None,
        "ns_95": float(ns_95),
        "flux_100tev_95": float(flux_100tev_95),
        "fraction_of_diffuse_flux_95": None if fraction_diffuse is None else float(fraction_diffuse),
    }
    ns_curve = build_ns_curve(ns_hat, ns_95, float(Nks1.sum()))
    ts_curve = array([ts_function(value)-ts for value in ns_curve], dtype=float)
    flux_curve = array([ns_to_fig4_flux100(value, gamma) for value in ns_curve], dtype=float)
    curve = {"weighting_scheme": scheme_name, "spectral_index": float(gamma), "ns": ns_curve.tolist(), "delta_ts": ts_curve.tolist(), "flux_100tev": flux_curve.tolist(), "ns_95": float(ns_95), "flux_100tev_95": float(flux_100tev_95)}
    return result, curve


def legacy_stacking_weights(W_accs_src: ndarray, W_mdls_src: ndarray, IF_equal_weighting: bool) -> tuple[ndarray, ndarray, ndarray]:
    """likelihood_v4.py:615-630, with legacy globals passed as arguments."""
    N_src = W_accs_src.shape[1]
    if IF_equal_weighting:
        W_facs = W_accs_src
    else:
        W_facs = W_accs_src * W_mdls_src.reshape(1,-1)
    W_facs_normd = W_facs/(W_facs.sum(axis=1).reshape(-1,1))

    W_facs_sum = W_facs.sum(axis=1)/N_src
    fks = W_facs_sum/W_facs_sum.sum()
    return W_facs, W_facs_normd, fks


def source_acceptance_matrix(decs: ndarray, data: dict[str, Any]) -> ndarray:
    acceptance = zeros((len(data["W_accs"]), len(decs)), dtype=float)
    for k, (coszeniths, values) in enumerate(data["W_accs"]):
        acceptance[k] = array([interp1d_linear(coszeniths, values, -sin(dec))*data["uptimes"][k] for dec in decs])
    return acceptance


def stacking_signal_background_pdfs(RAs_src: ndarray, Decs_src: ndarray, W_facs_normd: ndarray, data: dict[str, Any], chunk_size: int = 512) -> tuple[list[ndarray], list[ndarray], ndarray]:
    """likelihood_v4.py:675-700 plus its B>0 loading filter at 763-844."""
    Nks = data["Nks"]
    RAs_nu = data["RAs_nu"]
    Decs_nu = data["Decs_nu"]
    sgms_nu = data["sgms_nu"]
    bkgd_pdfs_nu = data["bkgd_pdfs_nu"]

    S_ki = []; B_ki = []; Nks1 = []
    cos_Decs_src = cos(Decs_src)
    sin_Decs_src = sin(Decs_src)
    for k in range(len(Nks)):
        RAs_nu1D = RAs_nu[k]
        Decs_nu1D = Decs_nu[k]
        sgms_nu1D = sgms_nu[k]

        S_ki1D = zeros(Nks[k])
        B_ki1D = asarray(bkgd_pdfs_nu[k], dtype=float)
        for i0 in range(0, Nks[k], chunk_size):
            i1 = builtins.min(i0+chunk_size, Nks[k])
            RAs_nu2D = RAs_nu1D[i0:i1].reshape(-1,1)
            Decs_nu2D = Decs_nu1D[i0:i1].reshape(-1,1)
            sgms_nu2D = sgms_nu1D[i0:i1].reshape(-1,1)
            cos_ang_dis = cos(RAs_src.reshape(1,-1)-RAs_nu2D)*cos_Decs_src.reshape(1,-1)*cos(Decs_nu2D) + sin_Decs_src.reshape(1,-1)*sin(Decs_nu2D)
            cos_ang_dis = clip(cos_ang_dis, -1., 1.)
            ang_dis2 = arccos(cos_ang_dis)**2.
            spatial_facs = 1./(2.*pi*sgms_nu2D**2.)*exp(-ang_dis2/(2.*sgms_nu2D**2.))
            S_ki1D[i0:i1] = dot(spatial_facs, W_facs_normd[k])

        idx = where(B_ki1D > 0.)
        S_ki += [S_ki1D[idx]]
        B_ki += [B_ki1D[idx]]
        Nks1 += [len(idx[0])]
    return S_ki, B_ki, array(Nks1)


def TS_tot(n_s: float, fks: ndarray, S_ki: list[ndarray], B_ki: list[ndarray], Nks1: ndarray) -> float:
    """likelihood_v4.py:707-720, with legacy globals passed as arguments."""
    TS_total = 0.
    n_s = float(n_s)
    for k in range(len(Nks1)):
        L_k = n_s*fks[k]/float(Nks1[k])*S_ki[k] + (1.-n_s*fks[k]/float(Nks1[k]))*B_ki[k]
        L_k0 = B_ki[k]
        if any(L_k <= 0.) or any(L_k0 <= 0.): # callable optimizer guard; legacy inputs are positive # Codex
            return -1e99
        TS_k = 2.*sum(log(L_k) - log(L_k0))
        TS_total = TS_total + TS_k
    return float(TS_total)


def max_TS_tot(ns0: float, fks: ndarray, S_ki: list[ndarray], B_ki: list[ndarray], Nks1: ndarray) -> tuple[float, float]:
    """likelihood_v4.py:722-728 using the repository's NumPy optimizer."""
    def TS_tot1(n_s):
        return -1.*TS_tot(n_s, fks, S_ki, B_ki, Nks1)
    max_ns, minimum = bounded_minimize(TS_tot1, 0., float(Nks1.sum()))
    seed_minimum = TS_tot1(ns0)
    if seed_minimum < minimum: # retain the legacy pre-scan seed as a fit candidate # Codex
        max_ns = float(ns0)
        minimum = seed_minimum
    max_TS = -1.*minimum
    return float(max_TS), float(max_ns)


def legacy_ns_grid(upper_bound: float) -> ndarray:
    """Callable equivalent of use.ebs(1., 2000., 200) in likelihood_v4.py."""
    if upper_bound <= 0.:
        return array([], dtype=float)
    upper = builtins.min(2000., upper_bound)
    if upper < 1.:
        return array([upper], dtype=float)
    return logspace(log10(1.), log10(upper), 201)


def find_ns_95(ts_function, ns_hat: float, ts: float, upper_bound: float) -> float:
    target = ts-3.84
    lo = builtins.max(float(ns_hat), 0.)
    hi = builtins.min(builtins.max(lo+10., 10.), upper_bound)
    while ts_function(hi) > target and hi < upper_bound:
        hi = builtins.min(hi*2., upper_bound)
    if ts_function(hi) > target:
        return float("nan")
    for _ in range(100):
        mid = (lo+hi)/2.
        if ts_function(mid) > target:
            lo = mid
        else:
            hi = mid
    return (lo+hi)/2.


def build_ns_curve(ns_hat: float, ns_95: float, upper_bound: float) -> ndarray:
    # The legacy result curve uses use.ebs(1., 2000., 200). Extend it only when
    # needed to display a catalog's fitted value or upper limit.
    curve_max = 2000.
    if isfinite(ns_95):
        curve_max = builtins.max(curve_max, ns_95*1.35)
    curve_max = builtins.max(curve_max, ns_hat*1.35, 1.)
    curve_max = builtins.min(curve_max, upper_bound)
    if curve_max < 1.:
        return unique(array([0., ns_hat, curve_max]))
    return unique(concatenate(([ns_hat], logspace(log10(1.), log10(curve_max), 201))))


def ns_to_fig4_flux100(ns: float, gamma: float) -> float:
    if not isfinite(ns):
        return float("nan")
    gamma_key = round(float(gamma), 2)
    if gamma_key not in FIG4_ASTRO_NS_REFERENCES:
        return float("nan")
    return float(ns)/FIG4_ASTRO_NS_REFERENCES[gamma_key]*REFERENCE_DIFFUSE_ALL_FLAVOR_FLUX100[gamma_key]


def normal_isf(p_value: float) -> float:
    p_value = builtins.min(builtins.max(float(p_value), 1e-16), 1.-1e-16)
    return NormalDist().inv_cdf(1.-p_value)
