#!/usr/bin/python
from __future__ import annotations # Codex

# Stacking likelihood blocks are copied from likelihood_v4.py with minimal callable-backend edits.

import builtins # Codex
import math # Codex
from statistics import NormalDist # Codex
from typing import Any # Codex

from numpy import * # Codex

from agent_core_cdx.schemas_cdx import NormalizedAnalysis # Codex
from likelihood_backend_single_source_cdx import bounded_minimize, interp1d_linear, load_backend_data, run_single_source_time_integrated # Codex


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
    stacking_warnings.append("Stacking post-trial p-value is not reported until background trials include the full weighting/spectral-index scan.") # Codex
    stacking_warnings.append("Fig. 4 flux conversion uses the paper-calibrated astrophysical event-count references from likelihood_v4.py/ns2flux.py.") # Codex
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
    decs = array([source.dec_rad for source in normalized.sources], dtype=float) # Codex
    ras = array([source.ra_rad for source in normalized.sources], dtype=float) # Codex
    acceptance = source_acceptance_matrix(decs, data) # Codex
    weighted_acceptance = acceptance*intrinsic_weights.reshape(1, -1) # Codex
    normalized_source_weights = weighted_acceptance/weighted_acceptance.sum(axis=1).reshape(-1, 1) # Codex
    fks = weighted_acceptance.sum(axis=1) # Codex
    fks = fks/fks.sum() # Codex
    signal_pdfs, background_pdfs = stacking_signal_background_pdfs(ras, decs, normalized_source_weights, data) # Codex
    sb_ratios = [signal_pdfs[k]/background_pdfs[k] for k in range(len(signal_pdfs))] # Codex
    n_events = array([len(values) for values in sb_ratios], dtype=int) # Codex
    def ts_function(ns): # Codex
        return stacking_ts(float(ns), fks, sb_ratios, n_events) # Codex
    ns_hat, min_negative_ts = bounded_minimize(lambda ns: -ts_function(ns), 0., float(n_events.sum())) # Codex
    ts = builtins.max(-float(min_negative_ts), 0.) # Codex
    if ts == 0.: # Codex
        ns_hat = 0. # Codex
    ns_95 = find_ns_95(ts_function, ns_hat, ts, float(n_events.sum())) # Codex
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
    ns_curve = build_ns_curve(ns_hat, ns_95, float(n_events.sum())) # Codex
    ts_curve = array([ts_function(value)-ts for value in ns_curve], dtype=float) # Codex
    flux_curve = array([ns_to_fig4_flux100(value, gamma) for value in ns_curve], dtype=float) # Codex
    curve = {"weighting_scheme": scheme_name, "spectral_index": float(gamma), "ns": ns_curve.tolist(), "delta_ts": ts_curve.tolist(), "flux_100tev": flux_curve.tolist(), "ns_95": float(ns_95), "flux_100tev_95": float(flux_100tev_95)} # Codex
    return result, curve # Codex


def source_acceptance_matrix(decs: ndarray, data: dict[str, Any]) -> ndarray: # Codex
    acceptance = zeros((len(data["W_accs"]), len(decs)), dtype=float) # Codex
    for k, (coszeniths, values) in enumerate(data["W_accs"]): # Codex
        acceptance[k] = array([interp1d_linear(coszeniths, values, -sin(dec))*data["uptimes"][k] for dec in decs]) # Codex
    return acceptance # Codex


def stacking_signal_background_pdfs(ras: ndarray, decs: ndarray, normalized_source_weights: ndarray, data: dict[str, Any], chunk_size: int = 4096) -> tuple[list[ndarray], list[ndarray]]: # Codex
    signal_pdfs: list[ndarray] = [] # Codex
    background_pdfs: list[ndarray] = [] # Codex
    cos_decs = cos(decs).reshape(1, -1) # Codex
    sin_decs = sin(decs).reshape(1, -1) # Codex
    for k in range(len(data["Nks"])): # Codex
        event_ras = data["RAs_nu"][k] # Codex
        event_decs = data["Decs_nu"][k] # Codex
        event_sigmas = data["sgms_nu"][k] # Codex
        signal = zeros(len(event_ras), dtype=float) # Codex
        for start in range(0, len(event_ras), chunk_size): # Codex
            stop = builtins.min(start+chunk_size, len(event_ras)) # Codex
            ra_chunk = event_ras[start:stop].reshape(-1, 1) # Codex
            dec_chunk = event_decs[start:stop].reshape(-1, 1) # Codex
            sigma_chunk = event_sigmas[start:stop].reshape(-1, 1) # Codex
            cos_distance = cos(ras.reshape(1, -1)-ra_chunk)*cos_decs*cos(dec_chunk)+sin_decs*sin(dec_chunk) # Codex
            distance2 = arccos(clip(cos_distance, -1., 1.))**2. # Codex
            spatial = exp(-distance2/(2.*sigma_chunk**2.))/(2.*pi*sigma_chunk**2.) # Codex
            signal[start:stop] = dot(spatial, normalized_source_weights[k]) # Codex
        background = asarray(data["bkgd_pdfs_nu"][k], dtype=float) # Codex
        valid = background > 0. # Codex
        signal_pdfs.append(signal[valid]) # Codex
        background_pdfs.append(background[valid]) # Codex
    return signal_pdfs, background_pdfs # Codex


def stacking_ts(ns: float, fks: ndarray, sb_ratios: list[ndarray], n_events: ndarray) -> float: # Codex
    total = 0. # Codex
    for k in range(len(n_events)): # Codex
        factors = 1.+ns*fks[k]/float(n_events[k])*(sb_ratios[k]-1.) # Codex
        if factors.min() <= 0.: # Codex
            return -1e99 # Codex
        total += 2.*log(factors).sum() # Codex
    return float(total) # Codex


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
    curve_max = ns_95*1.35 if isfinite(ns_95) else builtins.max(ns_hat*3., 100.) # Codex
    curve_max = builtins.min(builtins.max(curve_max, 10.), upper_bound) # Codex
    positive = geomspace(1e-3, curve_max, 140) # Codex
    return unique(concatenate(([0., ns_hat], positive))) # Codex


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
