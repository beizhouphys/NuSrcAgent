#!/usr/bin/python
from __future__ import annotations # Codex

# The stacking likelihood core is a callable extraction of the corresponding
# blocks in legacy_codex_revised/likelihood_v4.py.  Agent-facing task and result handling
# that does not exist in the legacy script remains local to this module.

import builtins # Codex
import math # Codex
from statistics import NormalDist # Codex
from typing import Any # Codex

from numpy import * # Codex

from agent_core_cdx.schemas_cdx import NormalizedAnalysis # Codex
from analysis_backend_cdx.single_source_cdx import bounded_minimize, interp1d_linear, load_backend_data, run_single_source_time_integrated # Codex


FIG4_ASTRO_NS_REFERENCES = {-2.00: 3217.3, -2.53: 8845.7, -3.00: 49282.2} # Codex
REFERENCE_DIFFUSE_ALL_FLAVOR_FLUX100 = {-2.00: 5e-8, -2.53: 4.98e-8, -3.00: 5e-8} # Codex


def run_catalog_time_integrated(normalized: NormalizedAnalysis, repo_root='.') -> dict[str, object]: # Codex
    source_results, source_warnings = run_source_scan(normalized, repo_root) # Codex
    stacking_results: list[dict[str, object]] = [] # Codex
    stacking_curves: list[dict[str, object]] = [] # Codex
    stacking_warnings: list[str] = [] # Codex
    schemes = build_weighting_schemes(normalized) # Codex
    for gamma in normalized.spectral_indices: # Codex
        data = load_backend_data(repo_root, gamma) # Codex
        for scheme_name, weights in schemes: # Codex
            result, curve = run_stacking_likelihood(normalized, weights, scheme_name, gamma, data) # Codex
            stacking_results.append(result) # Codex
            stacking_curves.append(curve) # Codex
            if not isfinite(float(result["flux_100tev_95"])): # Codex
                stacking_warnings.append(f"Flux conversion is unavailable for gamma={float(gamma):g}; flux_100tev_95 and fraction_of_diffuse_flux_95 are left blank.") # Codex
    stacking_warnings.append("Stacking post-trial p-value is not reported until background trials include the full weighting/spectral-index scan.") # Codex
    stacking_warnings.append("Fig. 4 flux conversion uses the paper-calibrated astrophysical event-count references from legacy_codex_revised/likelihood_v4.py and legacy_codex_revised/ns2flux.py.") # Codex
    return { # Codex
        "backend": "likelihood_catalog_time_integrated_v1", # Codex
        "n_sources": len(normalized.sources), # Codex
        "source_scan_completed": len(source_results), # Codex
        "stacking_hypotheses": len(stacking_results), # Codex
        "source_results_file": "source_results_cdx.csv", # Codex
        "stacking_results_file": "stacking_results_cdx.csv", # Codex
        "excel_file": "analysis_results_cdx.xlsx", # Codex
        "figures": ["fig1_sky_distribution_cdx.pdf", "fig3_ts_distribution_cdx.pdf", "fig4_stacking_cdx.pdf"], # Codex
        "note": "catalog-wide single-source scan plus time-integrated stacking likelihood", # Codex
        "warnings": source_warnings + stacking_warnings, # Codex
        "_source_results": source_results, # Codex
        "_stacking_results": stacking_results, # Codex
        "_stacking_curves": stacking_curves, # Codex
    } # Codex


def run_source_scan(normalized: NormalizedAnalysis, repo_root='.') -> tuple[list[dict[str, object]], list[str]]: # Codex
    rows: list[dict[str, object]] = [] # Codex
    warnings: list[str] = [] # Codex
    n_tests = len(normalized.sources) # Codex
    for source in normalized.sources: # Codex
        result = run_single_source_time_integrated(source.ra_deg, source.dec_deg, repo_root=repo_root, gamma=normalized.spectral_indices[0]) # Codex
        pre_trial_p = float(result["pre_trial_p"]) # Codex
        post_trial_p = 1.-(1.-pre_trial_p)**n_tests # Codex
        ts = builtins.max(float(result["ts"]), 0.) # Codex
        ns_hat = float(result["best_fit_ns"]) # Codex
        row: dict[str, object] = dict(source.metadata) # Codex
        row.update({ # Codex
            "source_number": source.source_number, # Codex
            "source_name": source.name, # Codex
            "ra_deg": source.ra_deg, # Codex
            "dec_deg": source.dec_deg, # Codex
            "intrinsic_weight": source.weight, # Codex
            "ns_hat": ns_hat, # Codex
            "ts": ts, # Codex
            "signed_sqrt_ts": math.copysign(math.sqrt(ts), ns_hat), # Codex
            "pre_trial_p": pre_trial_p, # Codex
            "pre_trial_significance": normal_isf(pre_trial_p), # Codex
            "post_trial_p": post_trial_p, # Codex
            "post_trial_significance": builtins.max(normal_isf(post_trial_p), 0.), # Codex
            "n_events_in_roi": int(result["n_events_in_roi"]), # Codex
            "fit_status": "completed", # Codex
        }) # Codex
        rows.append(row) # Codex
        warnings.extend(str(value) for value in result.get("warnings", [])) # Codex
    ranked = sorted(rows, key=lambda row: float(row["signed_sqrt_ts"]), reverse=True) # Codex
    ranks = {int(row["source_number"]): rank for rank, row in enumerate(ranked, start=1)} # Codex
    for row in rows: # Codex
        row["significance_rank"] = ranks[int(row["source_number"])] # Codex
    return rows, list(dict.fromkeys(warnings)) # Codex


def build_weighting_schemes(normalized: NormalizedAnalysis) -> list[tuple[str, ndarray]]: # Codex
    n_sources = len(normalized.sources) # Codex
    input_weights = array([source.weight for source in normalized.sources], dtype=float) # Codex
    input_weights = input_weights/input_weights.sum() # Codex
    uniform = ones(n_sources, dtype=float)/float(n_sources) # Codex
    schemes: list[tuple[str, ndarray]] = [] # Codex
    if normalized.include_uniform_baseline: # Codex
        schemes.append(("uniform", uniform)) # Codex
    if not allclose(input_weights, uniform) or not normalized.include_uniform_baseline: # Codex
        schemes.append(("input_weight", input_weights)) # Codex
    return schemes # Codex


def run_stacking_likelihood(normalized: NormalizedAnalysis, intrinsic_weights: ndarray, scheme_name: str, gamma: float, data: dict[str, Any]) -> tuple[dict[str, object], dict[str, object]]: # Codex
    # Names and calculation order below follow likelihood_v4.py:194-200 and
    # 615-630 so that the callable backend remains easy to compare to it.
    RAs_src = array([source.ra_rad for source in normalized.sources], dtype=float) # Codex
    Decs_src = array([source.dec_rad for source in normalized.sources], dtype=float) # Codex
    N_src = len(RAs_src) # Codex
    W_mdls_src = asarray(intrinsic_weights, dtype=float) # Codex
    W_accs_src = source_acceptance_matrix(Decs_src, data) # Codex

    W_facs, W_facs_normd, fks = legacy_stacking_weights(W_accs_src, W_mdls_src, scheme_name == "uniform") # Codex
    S_ki, B_ki, Nks1 = stacking_signal_background_pdfs(RAs_src, Decs_src, W_facs_normd, data) # Codex

    def ts_function(n_s): # Codex
        return TS_tot(n_s, fks, S_ki, B_ki, Nks1) # Codex

    # likelihood_v4.py first scans a logarithmic n_s grid to seed the fit.
    ns_seed_grid = legacy_ns_grid(float(Nks1.sum())) # Codex
    TS_seed_grid = array([ts_function(n_s) for n_s in ns_seed_grid]) # Codex
    ns_s_hat = ns_seed_grid[argmax(TS_seed_grid)] if len(ns_seed_grid) else 0. # Codex
    ts, ns_hat = max_TS_tot(ns_s_hat, fks, S_ki, B_ki, Nks1) # Codex
    if ts <= 0.: # Codex
        ts = 0. # Codex
        ns_hat = 0. # Codex
    ns_95 = find_ns_95(ts_function, ns_hat, ts, float(Nks1.sum())) # Codex
    flux_100tev_95 = ns_to_fig4_flux100(ns_95, gamma) # Codex
    reference_flux = REFERENCE_DIFFUSE_ALL_FLAVOR_FLUX100.get(round(float(gamma), 2)) # Codex
    fraction_diffuse = None if reference_flux is None else flux_100tev_95/reference_flux # Codex
    pre_trial_p = 0.5*math.erfc(math.sqrt(ts/2.)) # Codex
    result = { # Codex
        "weighting_scheme": scheme_name, # Codex
        "spectral_index": float(gamma), # Codex
        "n_sources": len(normalized.sources), # Codex
        "ns_hat": float(ns_hat), # Codex
        "ts": ts, # Codex
        "pre_trial_p": pre_trial_p, # Codex
        "pre_trial_significance": normal_isf(pre_trial_p), # Codex
        "post_trial_p": None, # Codex
        "post_trial_significance": None, # Codex
        "ns_95": float(ns_95), # Codex
        "flux_100tev_95": float(flux_100tev_95), # Codex
        "fraction_of_diffuse_flux_95": None if fraction_diffuse is None else float(fraction_diffuse), # Codex
    } # Codex
    ns_curve = build_ns_curve(ns_hat, ns_95, float(Nks1.sum())) # Codex
    ts_curve = array([ts_function(value)-ts for value in ns_curve], dtype=float) # Codex
    flux_curve = array([ns_to_fig4_flux100(value, gamma) for value in ns_curve], dtype=float) # Codex
    curve = {"weighting_scheme": scheme_name, "spectral_index": float(gamma), "ns": ns_curve.tolist(), "delta_ts": ts_curve.tolist(), "flux_100tev": flux_curve.tolist(), "ns_95": float(ns_95), "flux_100tev_95": float(flux_100tev_95)} # Codex
    return result, curve # Codex


def legacy_stacking_weights(W_accs_src: ndarray, W_mdls_src: ndarray, IF_equal_weighting: bool) -> tuple[ndarray, ndarray, ndarray]: # Codex
    """likelihood_v4.py:615-630, with legacy globals passed as arguments.""" # Codex
    N_src = W_accs_src.shape[1] # Codex
    if IF_equal_weighting: # Codex
        W_facs = W_accs_src # Codex
    else: # Codex
        W_facs = W_accs_src * W_mdls_src.reshape(1,-1) # Codex
    W_facs_normd = W_facs/(W_facs.sum(axis=1).reshape(-1,1)) # Codex

    W_facs_sum = W_facs.sum(axis=1)/N_src # Codex
    fks = W_facs_sum/W_facs_sum.sum() # Codex
    return W_facs, W_facs_normd, fks # Codex


def source_acceptance_matrix(decs: ndarray, data: dict[str, Any]) -> ndarray: # Codex
    acceptance = zeros((len(data["W_accs"]), len(decs)), dtype=float) # Codex
    for k, (coszeniths, values) in enumerate(data["W_accs"]): # Codex
        acceptance[k] = array([interp1d_linear(coszeniths, values, -sin(dec))*data["uptimes"][k] for dec in decs]) # Codex
    return acceptance # Codex


def stacking_signal_background_pdfs(RAs_src: ndarray, Decs_src: ndarray, W_facs_normd: ndarray, data: dict[str, Any], chunk_size: int = 512) -> tuple[list[ndarray], list[ndarray], ndarray]: # Codex
    """likelihood_v4.py:675-700 plus its B>0 loading filter at 763-844.""" # Codex
    Nks = data["Nks"] # Codex
    RAs_nu = data["RAs_nu"] # Codex
    Decs_nu = data["Decs_nu"] # Codex
    sgms_nu = data["sgms_nu"] # Codex
    bkgd_pdfs_nu = data["bkgd_pdfs_nu"] # Codex

    S_ki = []; B_ki = []; Nks1 = [] # Codex
    cos_Decs_src = cos(Decs_src) # Codex
    sin_Decs_src = sin(Decs_src) # Codex
    for k in range(len(Nks)): # Codex
        RAs_nu1D = RAs_nu[k] # Codex
        Decs_nu1D = Decs_nu[k] # Codex
        sgms_nu1D = sgms_nu[k] # Codex

        S_ki1D = zeros(Nks[k]) # Codex
        B_ki1D = asarray(bkgd_pdfs_nu[k], dtype=float) # Codex
        for i0 in range(0, Nks[k], chunk_size): # Codex
            i1 = builtins.min(i0+chunk_size, Nks[k]) # Codex
            RAs_nu2D = RAs_nu1D[i0:i1].reshape(-1,1) # Codex
            Decs_nu2D = Decs_nu1D[i0:i1].reshape(-1,1) # Codex
            sgms_nu2D = sgms_nu1D[i0:i1].reshape(-1,1) # Codex
            cos_ang_dis = cos(RAs_src.reshape(1,-1)-RAs_nu2D)*cos_Decs_src.reshape(1,-1)*cos(Decs_nu2D) + sin_Decs_src.reshape(1,-1)*sin(Decs_nu2D) # Codex
            cos_ang_dis = clip(cos_ang_dis, -1., 1.) # Codex
            ang_dis2 = arccos(cos_ang_dis)**2. # Codex
            spatial_facs = 1./(2.*pi*sgms_nu2D**2.)*exp(-ang_dis2/(2.*sgms_nu2D**2.)) # Codex
            S_ki1D[i0:i1] = dot(spatial_facs, W_facs_normd[k]) # Codex

        idx = where(B_ki1D > 0.) # Codex
        S_ki += [S_ki1D[idx]] # Codex
        B_ki += [B_ki1D[idx]] # Codex
        Nks1 += [len(idx[0])] # Codex
    return S_ki, B_ki, array(Nks1) # Codex


def TS_tot(n_s: float, fks: ndarray, S_ki: list[ndarray], B_ki: list[ndarray], Nks1: ndarray) -> float: # Codex
    """likelihood_v4.py:707-720, with legacy globals passed as arguments.""" # Codex
    TS_total = 0. # Codex
    n_s = float(n_s) # Codex
    for k in range(len(Nks1)): # Codex
        L_k = n_s*fks[k]/float(Nks1[k])*S_ki[k] + (1.-n_s*fks[k]/float(Nks1[k]))*B_ki[k] # Codex
        L_k0 = B_ki[k] # Codex
        if any(L_k <= 0.) or any(L_k0 <= 0.): # callable optimizer guard; legacy inputs are positive # Codex
            return -1e99 # Codex
        TS_k = 2.*sum(log(L_k) - log(L_k0)) # Codex
        TS_total = TS_total + TS_k # Codex
    return float(TS_total) # Codex


def max_TS_tot(ns0: float, fks: ndarray, S_ki: list[ndarray], B_ki: list[ndarray], Nks1: ndarray) -> tuple[float, float]: # Codex
    """likelihood_v4.py:722-728 using the repository's NumPy optimizer.""" # Codex
    def TS_tot1(n_s): # Codex
        return -1.*TS_tot(n_s, fks, S_ki, B_ki, Nks1) # Codex
    max_ns, minimum = bounded_minimize(TS_tot1, 0., float(Nks1.sum())) # Codex
    seed_minimum = TS_tot1(ns0) # Codex
    if seed_minimum < minimum: # retain the legacy pre-scan seed as a fit candidate # Codex
        max_ns = float(ns0) # Codex
        minimum = seed_minimum # Codex
    max_TS = -1.*minimum # Codex
    return float(max_TS), float(max_ns) # Codex


def legacy_ns_grid(upper_bound: float) -> ndarray: # Codex
    """Callable equivalent of use.ebs(1., 2000., 200) in likelihood_v4.py.""" # Codex
    if upper_bound <= 0.: # Codex
        return array([], dtype=float) # Codex
    upper = builtins.min(2000., upper_bound) # Codex
    if upper < 1.: # Codex
        return array([upper], dtype=float) # Codex
    return logspace(log10(1.), log10(upper), 201) # Codex


def find_ns_95(ts_function, ns_hat: float, ts: float, upper_bound: float) -> float: # Codex
    target = ts-3.84 # Codex
    lo = builtins.max(float(ns_hat), 0.) # Codex
    hi = builtins.min(builtins.max(lo+10., 10.), upper_bound) # Codex
    while ts_function(hi) > target and hi < upper_bound: # Codex
        hi = builtins.min(hi*2., upper_bound) # Codex
    if ts_function(hi) > target: # Codex
        return float("nan") # Codex
    for _ in range(100): # Codex
        mid = (lo+hi)/2. # Codex
        if ts_function(mid) > target: # Codex
            lo = mid # Codex
        else: # Codex
            hi = mid # Codex
    return (lo+hi)/2. # Codex


def build_ns_curve(ns_hat: float, ns_95: float, upper_bound: float) -> ndarray: # Codex
    # The legacy result curve uses use.ebs(1., 2000., 200). Extend it only when
    # needed to display a catalog's fitted value or upper limit.
    curve_max = 2000. # Codex
    if isfinite(ns_95): # Codex
        curve_max = builtins.max(curve_max, ns_95*1.35) # Codex
    curve_max = builtins.max(curve_max, ns_hat*1.35, 1.) # Codex
    curve_max = builtins.min(curve_max, upper_bound) # Codex
    if curve_max < 1.: # Codex
        return unique(array([0., ns_hat, curve_max])) # Codex
    return unique(concatenate(([ns_hat], logspace(log10(1.), log10(curve_max), 201)))) # Codex


def ns_to_fig4_flux100(ns: float, gamma: float) -> float: # Codex
    if not isfinite(ns): # Codex
        return float("nan") # Codex
    gamma_key = round(float(gamma), 2) # Codex
    if gamma_key not in FIG4_ASTRO_NS_REFERENCES: # Codex
        return float("nan") # Codex
    return float(ns)/FIG4_ASTRO_NS_REFERENCES[gamma_key]*REFERENCE_DIFFUSE_ALL_FLAVOR_FLUX100[gamma_key] # Codex


def normal_isf(p_value: float) -> float: # Codex
    p_value = builtins.min(builtins.max(float(p_value), 1e-16), 1.-1e-16) # Codex
    return NormalDist().inv_cdf(1.-p_value) # Codex
