"""Resumable all-event spatial-only DR2 scan for large source catalogs.

The spatial PDF is deliberately identical to
``ChunkedSpatialOnlySourceWeightedPDFRatio``.  The implementation batches
sources only to avoid reloading 1.64 million events for every source; it does
not apply an ROI or event cut.
"""

from __future__ import annotations

import csv
import json
from math import erf, sqrt
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

from analysis_backend_cdx.dr2_flux_conversion_cdx import ns_to_allflavor_e2_intensity_100tev
from analysis_backend_cdx.skyllh_dr2_pdfs_cdx import BACKGROUND_SPATIAL_FIELD
from analysis_backend_cdx.skyllh_dr2_stacking_cdx import create_dr2_stacking_analysis


DATASET_NAMES = ("IC40", "IC59", "IC79", "IC86_I-XI")
STACK_GAMMAS = (2.0, 2.53, 3.0)
STACK_SCHEMES = ("equal", "xband")


def _normal_sf(z):
    return 0.5 * (1.0 - erf(float(z) / sqrt(2.0)))


def _ratio_parts(ratio):
    if isinstance(ratio, tuple):
        nonzero, zero_count, n_events = ratio
        return nonzero, int(zero_count), int(n_events)
    return ratio, 0, len(ratio)


def _logl(ns, ratios, fractions, event_counts):
    total = 0.0
    for ratio, fraction, n_events in zip(ratios, fractions, event_counts, strict=True):
        nonzero, zero_count, _ = _ratio_parts(ratio)
        scale = float(fraction) / float(n_events)
        zero_term = 1.0 - float(ns) * scale
        if zero_count and zero_term <= 0.0:
            return -np.inf
        if zero_count:
            total += zero_count * float(np.log(zero_term))
        q = scale * (nonzero - 1.0)
        terms = 1.0 + float(ns) * q
        if np.any(terms <= 0.0):
            return -np.inf
        total += float(np.log(terms).sum(dtype=np.float64))
    return total


def _score(ns, ratios, fractions, event_counts):
    total = 0.0
    for ratio, fraction, n_events in zip(ratios, fractions, event_counts, strict=True):
        nonzero, zero_count, _ = _ratio_parts(ratio)
        scale = float(fraction) / float(n_events)
        zero_term = 1.0 - float(ns) * scale
        if zero_count and zero_term <= 0.0:
            return np.inf
        if zero_count:
            total += zero_count * (-scale / zero_term)
        q = scale * (nonzero - 1.0)
        terms = 1.0 + float(ns) * q
        if np.any(terms <= 0.0):
            return np.inf
        total += float(np.sum(q / terms, dtype=np.float64))
    return total


def fit_ns(ratios, fractions, ns_min=0.0, ns_max=1e4):
    event_counts = [_ratio_parts(ratio)[2] for ratio in ratios]
    lo, hi = float(ns_min), float(ns_max)
    if lo < 0.0:
        max_q = max(
            float(np.max(float(fraction) / float(n_events) * (_ratio_parts(ratio)[0] - 1.0)))
            for ratio, fraction, n_events in zip(ratios, fractions, event_counts, strict=True)
        )
        if max_q > 0.0:
            lo = max(lo, float(np.nextafter(-1.0 / max_q, np.inf)))
    lo_score = _score(lo, ratios, fractions, event_counts)
    hi_score = _score(hi, ratios, fractions, event_counts)
    if not np.isfinite(lo_score) or lo_score <= 0.0:
        best = lo
    elif np.isfinite(hi_score) and hi_score >= 0.0:
        best = hi
    else:
        valid_hi = hi
        while not np.isfinite(_logl(valid_hi, ratios, fractions, event_counts)) and valid_hi > lo + 1e-8:
            valid_hi = 0.5 * (lo + valid_hi)
        if _score(valid_hi, ratios, fractions, event_counts) >= 0.0:
            best = valid_hi
        else:
            best = brentq(lambda x: _score(x, ratios, fractions, event_counts), lo, valid_hi, xtol=1e-7)
    logl_best = _logl(best, ratios, fractions, event_counts)
    return float(best), float(2.0 * logl_best), float(logl_best)


def profile_and_upper_limit(ratios, fractions, ns_hat, logl_best, ns_max=1e4, delta_ts=-3.84):
    event_counts = [_ratio_parts(ratio)[2] for ratio in ratios]
    target_logl = logl_best + 0.5 * float(delta_ts)
    lower = max(float(ns_hat), 0.0)
    upper = max(1.0, 1.25 * lower + 1.0)
    while upper < ns_max and _logl(upper, ratios, fractions, event_counts) > target_logl:
        upper = min(float(ns_max), 2.0 * upper)
    if _logl(upper, ratios, fractions, event_counts) > target_logl:
        ns_95 = np.nan
    else:
        ns_95 = brentq(
            lambda value: _logl(value, ratios, fractions, event_counts) - target_logl,
            lower,
            upper,
            xtol=1e-7,
        )
    positive_max = max(1.0, float(ns_hat), float(ns_95) if np.isfinite(ns_95) else upper)
    positive = np.geomspace(max(1e-3, positive_max / 1e4), positive_max * 1.35, 100)
    grid = np.unique(np.concatenate(([0.0, float(ns_hat)], positive)))
    delta = [2.0 * (_logl(value, ratios, fractions, event_counts) - logl_best) for value in grid]
    return grid, np.asarray(delta), float(ns_95)


def _source_specs(rows):
    return [
        {
            "name": row["source_name"],
            "ra_rad": np.deg2rad(float(row["ra_deg"])),
            "dec_rad": np.deg2rad(float(row["dec_deg"])),
            "w_model": 1.0,
        }
        for row in rows
    ]


def _load_catalog(path):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _acceptance_and_data(repo_root, rows, gammas):
    specs = _source_specs(rows)
    acceptances = {}
    event_data = backgrounds = None
    for gamma in gammas:
        analysis = create_dr2_stacking_analysis(
            repo_root, specs, likelihood_mode="spatial_only", gamma_mode="fixed", gamma=float(gamma)
        )
        src_params = analysis._pmm.create_src_params_recarray(gflp_values=[0.0])
        analysis.src_detsigyield_weights_service.calculate(src_params)
        acceptances[float(gamma)] = np.asarray(
            analysis.src_detsigyield_weights_service.get_weights()[0], dtype=np.float64
        )
        if event_data is None:
            event_data = [
                {
                    "ra": np.asarray(data.exp["ra"], dtype=np.float64),
                    "dec": np.asarray(data.exp["dec"], dtype=np.float64),
                    "sigma": np.asarray(data.exp["ang_err"], dtype=np.float64),
                }
                for data in analysis.data_list
            ]
            backgrounds = [
                np.asarray(data.exp[BACKGROUND_SPATIAL_FIELD], dtype=np.float64) for data in analysis.data_list
            ]
        del analysis
    return event_data, backgrounds, acceptances


def _spatial_matrix(events, source_ra, source_dec, event_chunk=16384):
    n_events, n_sources = len(events["ra"]), len(source_ra)
    result = np.empty((n_events, n_sources), dtype=np.float64)
    sin_sdec = np.sin(source_dec)
    cos_sdec = np.cos(source_dec)
    for e0 in range(0, n_events, int(event_chunk)):
        e1 = min(e0 + int(event_chunk), n_events)
        era = events["ra"][e0:e1, np.newaxis]
        edec = events["dec"][e0:e1, np.newaxis]
        sigma_sq = events["sigma"][e0:e1, np.newaxis] ** 2
        cospsi = np.sin(edec) * sin_sdec + np.cos(edec) * cos_sdec * np.cos(era - source_ra)
        psi = np.arccos(np.clip(cospsi, -1.0, 1.0))
        with np.errstate(divide="ignore", invalid="ignore", under="ignore"):
            spatial = 0.5 / (np.pi * np.sin(psi)) * (psi / sigma_sq) * np.exp(-0.5 * psi**2 / sigma_sq)
        spatial = np.where(psi == 0.0, 0.5 / (np.pi * sigma_sq), spatial)
        result[e0:e1] = spatial
    return result


def _write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_catalog_scan(
    repo_root,
    catalog_path,
    output_dir,
    acceptance_gamma=2.53,
    stack_gammas=STACK_GAMMAS,
    source_chunk=8,
    event_chunk=16384,
    checkpoint_every=256,
    ns_max=1e4,
):
    """Run/resume the 3386-source scan and the six Fig. 4 stack hypotheses."""
    root = Path(repo_root).resolve()
    catalog = Path(catalog_path)
    if not catalog.is_absolute():
        catalog = root / catalog
    out = Path(output_dir)
    if not out.is_absolute():
        out = root / out
    out.mkdir(parents=True, exist_ok=True)
    rows = _load_catalog(catalog)
    gammas = tuple(sorted(set(float(g) for g in (*stack_gammas, acceptance_gamma))))
    events, backgrounds, acceptances = _acceptance_and_data(root, rows, gammas)
    event_counts = [len(item["ra"]) for item in events]
    hypotheses = [(scheme, float(gamma)) for scheme in STACK_SCHEMES for gamma in stack_gammas]
    stack_numerators = [np.zeros((len(hypotheses), n), dtype=np.float64) for n in event_counts]
    progress_path = out / "checkpoint_progress_cdx.json"
    partial_path = out / "source_scan_partial_cdx.jsonl"
    start = 0
    if progress_path.exists():
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
        start = int(progress["next_source_index"])
        for dataset_idx, name in enumerate(DATASET_NAMES):
            stack_numerators[dataset_idx] = np.load(out / f"checkpoint_stack_{name}_cdx.npy")
        if partial_path.exists():
            committed_lines = []
            for line in partial_path.read_text(encoding="utf-8").splitlines():
                if line and int(json.loads(line)["catalog_index"]) < start:
                    committed_lines.append(line)
            partial_path.write_text("\n".join(committed_lines) + ("\n" if committed_lines else ""), encoding="utf-8")
    mode = "a" if start else "w"
    source_ra_all = np.deg2rad(np.asarray([float(row["ra_deg"]) for row in rows]))
    source_dec_all = np.deg2rad(np.asarray([float(row["dec_deg"]) for row in rows]))
    xband = np.asarray([float(row["xband_flux_jy"]) for row in rows])
    with partial_path.open(mode, encoding="utf-8") as partial:
        for s0 in range(start, len(rows), int(source_chunk)):
            s1 = min(s0 + int(source_chunk), len(rows))
            matrices = [
                _spatial_matrix(data, source_ra_all[s0:s1], source_dec_all[s0:s1], event_chunk)
                for data in events
            ]
            for dataset_idx, matrix in enumerate(matrices):
                weights = np.empty((s1 - s0, len(hypotheses)), dtype=np.float64)
                for hidx, (scheme, gamma) in enumerate(hypotheses):
                    model = np.ones(s1 - s0) if scheme == "equal" else xband[s0:s1]
                    weights[:, hidx] = acceptances[gamma][dataset_idx, s0:s1] * model
                stack_numerators[dataset_idx] += (matrix @ weights).T
            acc = acceptances[float(acceptance_gamma)][:, s0:s1]
            for local_idx, source_idx in enumerate(range(s0, s1)):
                fractions = acc[:, local_idx] / np.sum(acc[:, local_idx])
                ratios = [matrices[k][:, local_idx] / backgrounds[k] for k in range(len(events))]
                ratios = [(ratio[ratio != 0.0], int(np.count_nonzero(ratio == 0.0)), len(ratio)) for ratio in ratios]
                ns_signed, ts_signed_raw, _ = fit_ns(ratios, fractions, ns_min=-10.0, ns_max=ns_max)
                ts_signed = np.sign(ns_signed) * abs(ts_signed_raw)
                if ns_signed > 0.0:
                    ns_hat, ts = ns_signed, abs(ts_signed_raw)
                else:
                    ns_hat, ts = 0.0, 0.0
                p_pre = _normal_sf(np.sqrt(max(ts, 0.0)))
                result = dict(rows[source_idx])
                result.update(
                    {
                        "ns_hat": ns_hat,
                        "TS": ts,
                        "sqrt_TS": np.sqrt(max(ts, 0.0)),
                        "pre_trial_p": p_pre,
                        "post_trial_p_catalog_analytic_uncalibrated": 1.0 - (1.0 - p_pre) ** len(rows),
                        "ns_hat_signed_diagnostic": ns_signed,
                        "TS_signed_diagnostic": ts_signed,
                        "acceptance_gamma_legacy": -float(acceptance_gamma),
                    }
                )
                partial.write(json.dumps(result, sort_keys=True) + "\n")
            partial.flush()
            if s1 == len(rows) or s1 % int(checkpoint_every) < int(source_chunk):
                for dataset_idx, name in enumerate(DATASET_NAMES):
                    np.save(out / f"checkpoint_stack_{name}_cdx.npy", stack_numerators[dataset_idx])
                _write_json(progress_path, {"next_source_index": s1, "n_sources": len(rows)})
            print(f"Completed sources {s0}:{s1} / {len(rows)}", flush=True)

    source_results = [json.loads(line) for line in partial_path.read_text(encoding="utf-8").splitlines() if line]
    source_results.sort(key=lambda row: int(row["catalog_index"]))
    _write_json(out / "source_scan_results_cdx.json", source_results)
    stack_results = []
    for hidx, (scheme, gamma) in enumerate(hypotheses):
        model = np.ones(len(rows)) if scheme == "equal" else xband
        total_weights = np.asarray(
            [np.sum(acceptances[gamma][k] * model) for k in range(len(events))], dtype=np.float64
        )
        fractions = total_weights / total_weights.sum()
        ratios = [
            stack_numerators[k][hidx] / (total_weights[k] * backgrounds[k]) for k in range(len(events))
        ]
        ns_hat, ts, logl_best = fit_ns(ratios, fractions, ns_min=0.0, ns_max=ns_max)
        grid, delta, ns_95 = profile_and_upper_limit(ratios, fractions, ns_hat, logl_best, ns_max=ns_max)
        flux_95 = ns_to_allflavor_e2_intensity_100tev(ns_95, root, gamma) if np.isfinite(ns_95) else np.nan
        reference_flux = {2.0: 5.00e-8, 2.53: 4.98e-8, 3.0: 5.00e-8}[gamma]
        stack_results.append(
            {
                "weighting_scheme": scheme,
                "spectral_index_legacy": -gamma,
                "acceptance_gamma_skyllh": gamma,
                "ns_hat": ns_hat,
                "TS": ts,
                "ns_95_deltaTS_minus3p84": ns_95,
                "allflavor_E2dFdE_100TeV_95_GeV_cm-2_s-1_sr-1": flux_95,
                "fraction_of_paper_diffuse_reference_100TeV_95": flux_95 / reference_flux,
                "ns_profile": grid.tolist(),
                "delta_TS_profile": delta.tolist(),
                "dataset_fractions": dict(zip(DATASET_NAMES, fractions.tolist(), strict=True)),
            }
        )
    _write_json(out / "stacking_results_cdx.json", stack_results)
    provenance = {
        "sample": "icecube_public_ps_14yr_dr2",
        "likelihood_mode": "spatial_only",
        "event_selection": "all_events",
        "n_events": int(sum(event_counts)),
        "n_sources": len(rows),
        "source_chunk": int(source_chunk),
        "event_chunk": int(event_chunk),
        "acceptance_gamma_legacy": -float(acceptance_gamma),
        "stack_gammas_legacy": [-float(value) for value in stack_gammas],
        "ns_bounds_primary": [0.0, float(ns_max)],
        "ns_bounds_signed_diagnostic": [-10.0, float(ns_max)],
        "upper_limit_definition": "Delta TS = -3.84 above best fit",
        "post_trial_note": "Catalog-size analytic correction is uncalibrated and is not a trial-scrambled p-value.",
    }
    _write_json(out / "provenance_cdx.json", provenance)
    return {"sources": source_results, "stacking": stack_results, "provenance": provenance}
