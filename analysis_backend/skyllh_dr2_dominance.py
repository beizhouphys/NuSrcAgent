"""Checkpointed source-dominance diagnostics for completed DR2 stacks."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from agent_core.p_value import local_p_value_estimate
from agent_core.simple_yaml import load_simple_yaml
from analysis_backend.skyllh_dr2_pdfs import BACKGROUND_ENERGY_FIELD, BACKGROUND_SPATIAL_FIELD
from analysis_backend.skyllh_dr2_stacking import create_dr2_stacking_analysis, run_dr2_stacking


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _source_hash(specs):
    payload = json.dumps(
        [[str(item["name"]), float(item["ra_rad"]), float(item["dec_rad"]), float(item["w_model"])] for item in specs],
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _source_specs(normalized):
    sources = normalized["sources"]
    weight = 1.0 / len(sources)
    return [
        {
            "source_number": int(source["source_number"]),
            "name": str(source["name"]),
            "ra_deg": float(source["ra_deg"]),
            "dec_deg": float(source["dec_deg"]),
            "ra_rad": float(source["ra_rad"]),
            "dec_rad": float(source["dec_rad"]),
            "w_model": weight,
        }
        for source in sources
    ]


def _initialize_ratio(ratio, data_exp):
    ratio.event_ra = np.asarray(data_exp["ra"], dtype=np.float64)
    ratio.event_dec = np.asarray(data_exp["dec"], dtype=np.float64)
    ratio.event_sigma = np.asarray(data_exp["ang_err"], dtype=np.float64)
    ratio.event_log_energy = np.asarray(data_exp["log_energy"], dtype=np.float64)
    ratio.background = np.asarray(data_exp[BACKGROUND_SPATIAL_FIELD], dtype=np.float64) * np.asarray(
        data_exp[BACKGROUND_ENERGY_FIELD], dtype=np.float64
    )


def _delete_one_dataset_logl(ratio, weights, full_ratio, fractions_minus, ns):
    weights = np.asarray(weights, dtype=np.float64)
    total_weight = float(weights.sum())
    n_events = len(ratio.event_ra)
    result = np.zeros(len(weights), dtype=np.float64)
    for e0 in range(0, n_events, ratio.event_chunk):
        e1 = min(e0 + ratio.event_chunk, n_events)
        era = ratio.event_ra[e0:e1]
        edec = ratio.event_dec[e0:e1]
        sigma_sq = ratio.event_sigma[e0:e1] ** 2
        loge = ratio.event_log_energy[e0:e1]
        sin_edec = np.sin(edec)[:, np.newaxis]
        cos_edec = np.cos(edec)[:, np.newaxis]
        full_numerator_over_background = full_ratio[e0:e1] * total_weight
        for s0 in range(0, len(weights), ratio.source_chunk):
            s1 = min(s0 + ratio.source_chunk, len(weights))
            sra = ratio.source_ras[s0:s1]
            sdec = ratio.source_decs[s0:s1]
            cospsi = sin_edec * np.sin(sdec) + cos_edec * np.cos(sdec) * np.cos(era[:, np.newaxis] - sra)
            psi = np.arccos(np.clip(cospsi, -1.0, 1.0))
            with np.errstate(divide="ignore", invalid="ignore", under="ignore"):
                spatial = 0.5 / (np.pi * np.sin(psi)) * (psi / sigma_sq[:, np.newaxis]) * np.exp(
                    -0.5 * psi**2 / sigma_sq[:, np.newaxis]
                )
            spatial = np.where(psi == 0.0, 0.5 / (np.pi * sigma_sq[:, np.newaxis]), spatial)
            signal = np.zeros_like(spatial)
            dec_indices = ratio.source_dec_indices[s0:s1]
            x1, dx, energy_grid = ratio._gamma_slices(ratio._dominance_gamma)
            offset = ratio._dominance_gamma - x1
            for dec_idx in np.unique(dec_indices):
                source_mask = dec_indices == dec_idx
                m0 = ratio._interpolate_energy(loge, energy_grid[dec_idx, :, 0])
                m1 = ratio._interpolate_energy(loge, energy_grid[dec_idx, :, 1])
                m2 = ratio._interpolate_energy(loge, energy_grid[dec_idx, :, 2])
                parabola_a = 0.5 * (m0 - 2.0 * m1 + m2) / dx**2
                parabola_b = 0.5 * (m2 - m0) / dx
                energy = parabola_a * offset**2 + parabola_b * offset + m1
                signal[:, source_mask] = spatial[:, source_mask] * energy[:, np.newaxis]
            component_over_background = signal * weights[s0:s1][np.newaxis, :] / ratio.background[e0:e1, np.newaxis]
            reduced_ratio = (
                full_numerator_over_background[:, np.newaxis] - component_over_background
            ) / (total_weight - weights[s0:s1])[np.newaxis, :]
            alpha = float(ns) * fractions_minus[s0:s1] / float(n_events)
            terms = 1.0 + alpha[np.newaxis, :] * (reduced_ratio - 1.0)
            if np.any(terms <= 0.0):
                raise ValueError("Delete-one fixed-fit likelihood entered an invalid logarithm region")
            result[s0:s1] += np.log(terms).sum(axis=0, dtype=np.float64)
    return result


def screen_delete_one(repo_root, normalized, baseline_result):
    specs = _source_specs(normalized)
    gamma = float(baseline_result["gamma"])
    ns = float(baseline_result["ns"])
    analysis = create_dr2_stacking_analysis(
        repo_root,
        specs,
        likelihood_mode="spatial_energy",
        gamma_mode="fixed",
        gamma=gamma,
        event_abs_dec_max_deg=normalized.get("event_abs_dec_max_deg"),
        event_dec_min_deg=normalized.get("event_dec_min_deg"),
        event_dec_max_deg=normalized.get("event_dec_max_deg"),
    )
    src_params = analysis._pmm.create_src_params_recarray(gflp_values=[0.0])
    analysis.src_detsigyield_weights_service.calculate(src_params)
    a_jk = np.asarray(analysis.src_detsigyield_weights_service.get_weights()[0], dtype=np.float64)
    dataset_totals = a_jk.sum(axis=1)
    total_yield = float(dataset_totals.sum())
    removed_yield = a_jk.sum(axis=0)
    fractions_minus = (dataset_totals[:, np.newaxis] - a_jk) / (total_yield - removed_yield)[np.newaxis, :]
    delete_logl = np.zeros(len(specs), dtype=np.float64)
    reconstructed_full_logl = 0.0
    full_fractions = dataset_totals / total_yield
    for dataset_idx, (ratio, data) in enumerate(zip(analysis.chunked_ratios, analysis.data_list, strict=True)):
        _initialize_ratio(ratio, data.exp)
        ratio._dominance_gamma = gamma
        full_ratio, _ = ratio._calculate(gamma, a_jk[dataset_idx], np.zeros(len(specs), dtype=np.float64))
        full_terms = 1.0 + ns * float(full_fractions[dataset_idx]) / len(full_ratio) * (full_ratio - 1.0)
        reconstructed_full_logl += float(np.log(full_terms).sum(dtype=np.float64))
        delete_logl += _delete_one_dataset_logl(
            ratio, a_jk[dataset_idx], full_ratio, fractions_minus[dataset_idx], ns
        )
    reconstructed_ts = 2.0 * reconstructed_full_logl
    baseline_ts = float(baseline_result["TS"])
    rows = []
    for idx, spec in enumerate(specs):
        fixed_ts = 2.0 * float(delete_logl[idx])
        rows.append(
            {
                "source_number": spec["source_number"],
                "source_name": spec["name"],
                "ra_deg": spec["ra_deg"],
                "dec_deg": spec["dec_deg"],
                "fixed_delete_ts": fixed_ts,
                "delta_ts_fixed": baseline_ts - fixed_ts,
            }
        )
    rows.sort(key=lambda row: (-float(row["delta_ts_fixed"]), int(row["source_number"])))
    for rank, row in enumerate(rows, start=1):
        row["screening_rank"] = rank
    return {
        "baseline_ts": baseline_ts,
        "reconstructed_baseline_ts": reconstructed_ts,
        "signed_relative_difference": (reconstructed_ts - baseline_ts) / baseline_ts,
        "signed_absolute_difference": reconstructed_ts - baseline_ts,
        "rows": rows,
    }


def _fit_summary(result, removed_numbers, label):
    estimate = local_p_value_estimate(result["TS"], result.get("gamma_mode", "fitted"))
    return {
        "label": label,
        "removed_source_numbers": list(removed_numbers),
        "n_removed": len(removed_numbers),
        "n_sources": int(result["n_sources"]),
        "TS": float(result["TS"]),
        "ns": float(result["ns"]),
        "gamma_skyllh": float(result["gamma"]),
        "gamma_legacy": float(result["gamma_legacy"]),
        "pre_trial_p_analytic": estimate["pre_trial_p"],
        "pre_trial_significance_estimate": estimate["pre_trial_significance"],
        "p_value_method": estimate["p_value_method"],
        "p_value_dof": estimate["p_value_dof"],
        "p_value_is_estimate": True,
        "minimizer_warnflag": int(result["minimizer_status"].get("warnflag", -1)),
        "minimizer_iterations": int(result["minimizer_status"].get("nit", -1)),
        "source_hash": None,
    }


def _run_reduced(specs, removed_numbers, repo_root, normalized, gamma_seed, ns_seed):
    removed = set(int(value) for value in removed_numbers)
    selected = [dict(spec) for spec in specs if int(spec["source_number"]) not in removed]
    uniform = 1.0 / len(selected)
    for spec in selected:
        spec["w_model"] = uniform
    result = run_dr2_stacking(
        selected,
        repo_root=repo_root,
        likelihood_mode="spatial_energy",
        gamma_mode="fitted",
        gamma=float(gamma_seed),
        ns_seed=float(ns_seed),
        event_abs_dec_max_deg=normalized.get("event_abs_dec_max_deg"),
        event_dec_min_deg=normalized.get("event_dec_min_deg"),
        event_dec_max_deg=normalized.get("event_dec_max_deg"),
    )
    result.update(local_p_value_estimate(result["TS"], "fitted"))
    return result, _source_hash(selected)


def run_dominance_analysis(repo_root, baseline_run_directory, output_directory, request, candidate_count=15, top_n=10):
    root = Path(repo_root).resolve()
    baseline_dir = Path(baseline_run_directory).expanduser().resolve()
    out = Path(output_directory)
    if not out.is_absolute():
        out = root / out
    out.mkdir(parents=True, exist_ok=True)
    report = load_simple_yaml((baseline_dir / "report.yaml").read_text(encoding="utf-8"))
    normalized = load_simple_yaml((baseline_dir / "config.normalized.yaml").read_text(encoding="utf-8"))
    review = _json(baseline_dir / "review.json")
    if review.get("status") != "pass":
        raise ValueError("Baseline run review must pass before dominance analysis")
    baseline = report["result"]
    if baseline.get("likelihood_mode") != "spatial_energy" or baseline.get("gamma_mode") != "fitted":
        raise ValueError("Dominance workflow requires a fitted-Gamma DR2 spatial+energy baseline")
    specs = _source_specs(normalized)
    if not 1 <= int(top_n) <= int(candidate_count) <= len(specs):
        raise ValueError("Dominance counts must satisfy 1 <= top_n <= candidate_count <= normalized source count")
    state_path = out / "dominance_task.json"
    state = _json(state_path) if state_path.exists() else {
        "status": "RUNNING",
        "request": str(request),
        "baseline_run_directory": str(baseline_dir),
        "baseline": {"TS": baseline["TS"], "ns": baseline["ns"], "gamma": baseline["gamma"], "n_sources": baseline["n_sources"]},
        "candidate_count": int(candidate_count),
        "top_n": int(top_n),
        "individual_refits": [],
        "cumulative_refits": [],
    }
    state["candidate_count"] = int(candidate_count)
    state["top_n"] = int(top_n)
    _write_json(state_path, state)
    screening_path = out / "delete_one_screening.json"
    if screening_path.exists():
        screening = _json(screening_path)
    else:
        screening = screen_delete_one(root, normalized, baseline)
        _write_json(screening_path, screening)
        _write_csv(out / "delete_one_screening.csv", screening["rows"])
    tolerance = 1e-3
    if abs(float(screening["signed_relative_difference"])) > tolerance:
        raise ValueError("Fixed-fit screening does not reproduce the baseline TS within tolerance")
    completed_individual = {int(item["removed_source_numbers"][0]): item for item in state["individual_refits"]}
    candidates = screening["rows"][: int(candidate_count)]
    for candidate in candidates:
        number = int(candidate["source_number"])
        if number in completed_individual:
            continue
        result, source_hash = _run_reduced(specs, [number], root, normalized, baseline["gamma"], baseline["ns"])
        summary = _fit_summary(result, [number], "delete_one")
        summary["source_hash"] = source_hash
        summary.update({"source_name": candidate["source_name"], "ra_deg": candidate["ra_deg"], "dec_deg": candidate["dec_deg"], "delta_ts": float(baseline["TS"]) - summary["TS"], "delta_ts_fixed": candidate["delta_ts_fixed"], "screening_rank": candidate["screening_rank"]})
        state["individual_refits"].append(summary)
        _write_json(state_path, state)
    individual = sorted(state["individual_refits"], key=lambda item: (-float(item["delta_ts"]), int(item["removed_source_numbers"][0])))
    top = individual[: int(top_n)]
    for rank, item in enumerate(top, start=1):
        item["dominance_rank"] = rank
    _write_csv(out / "top_candidates_refit.csv", individual)
    completed_cumulative = {int(item["n_removed"]): item for item in state["cumulative_refits"]}
    previous_ts = float(baseline["TS"])
    gamma_seed = float(baseline["gamma"])
    ns_seed = float(baseline["ns"])
    removed = []
    for rank, candidate in enumerate(top, start=1):
        removed.append(int(candidate["removed_source_numbers"][0]))
        if rank in completed_cumulative:
            existing = completed_cumulative[rank]
            if [int(value) for value in existing["removed_source_numbers"]] != removed:
                raise ValueError("The verified Top-N order changed; remove stale cumulative checkpoints and rerun")
            previous_ts = float(existing["TS"])
            gamma_seed = float(existing["gamma_skyllh"])
            ns_seed = float(existing["ns"])
            continue
        result, source_hash = _run_reduced(specs, removed, root, normalized, gamma_seed, ns_seed)
        summary = _fit_summary(result, removed, "cumulative_top_%d" % rank)
        summary["source_hash"] = source_hash
        summary.update({"last_removed_source_number": removed[-1], "last_removed_source_name": candidate["source_name"], "marginal_ts_drop": previous_ts - summary["TS"], "cumulative_ts_drop": float(baseline["TS"]) - summary["TS"]})
        state["cumulative_refits"].append(summary)
        _write_json(state_path, state)
        previous_ts = summary["TS"]
        gamma_seed = summary["gamma_skyllh"]
        ns_seed = summary["ns"]
    top_rows = []
    cumulative_by_rank = {int(item["n_removed"]): item for item in state["cumulative_refits"]}
    for item in top:
        row = dict(item)
        cumulative = cumulative_by_rank[int(item["dominance_rank"])]
        row.update({"cumulative_TS": cumulative["TS"], "marginal_ts_drop": cumulative["marginal_ts_drop"], "cumulative_ts_drop": cumulative["cumulative_ts_drop"], "cumulative_ns": cumulative["ns"], "cumulative_gamma_skyllh": cumulative["gamma_skyllh"], "cumulative_gamma_legacy": cumulative["gamma_legacy"]})
        top_rows.append(row)
    _write_csv(out / "top10_dominance.csv", top_rows)
    _write_csv(out / "cumulative_removal.csv", sorted(state["cumulative_refits"], key=lambda item: int(item["n_removed"])))
    state["status"] = "COMPLETED"
    state["screening_baseline_check"] = {key: screening[key] for key in ["baseline_ts", "reconstructed_baseline_ts", "signed_relative_difference", "signed_absolute_difference"]}
    state["artifacts"] = {
        "screening_json": str(screening_path),
        "screening_csv": str(out / "delete_one_screening.csv"),
        "candidate_refits_csv": str(out / "top_candidates_refit.csv"),
        "top10_csv": str(out / "top10_dominance.csv"),
        "cumulative_csv": str(out / "cumulative_removal.csv"),
    }
    _write_json(state_path, state)
    return state


def review_dominance_analysis(repo_root, output_directory):
    import os
    root = Path(repo_root).resolve()
    matplotlib_config = root / "data_output/.matplotlib"
    matplotlib_config.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(matplotlib_config))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out = Path(output_directory)
    if not out.is_absolute():
        out = root / out
    state = _json(out / "dominance_task.json")
    screening = _json(out / "delete_one_screening.json")
    checks = []
    def check(check_id, ok, message, status_if_bad="fail"):
        checks.append({"id": check_id, "status": "pass" if ok else status_if_bad, "message": message})
    rows = screening.get("rows", [])
    check("completion", state.get("status") in {"COMPLETED", "COMPLETED_WITH_WARNINGS"}, "dominance task reached a completed state")
    check("screening_count", len(rows) == int(state["baseline"]["n_sources"]), "screening covers all %d normalized sources" % int(state["baseline"]["n_sources"]))
    check("screening_ranks", sorted(int(row["screening_rank"]) for row in rows) == list(range(1, len(rows) + 1)), "screening ranks form a complete permutation")
    rel = float(screening["signed_relative_difference"])
    check("baseline_reconstruction", abs(rel) <= 1e-3, "fixed-fit baseline reconstruction is within relative tolerance 1e-3")
    individual = state.get("individual_refits", [])
    candidate_count = int(state["candidate_count"])
    valid_individual = len(individual) == candidate_count and all(
        np.isfinite(float(item[key])) for item in individual for key in ["TS", "ns", "gamma_skyllh", "delta_ts"]
    ) and all(float(item["TS"]) >= 0.0 and float(item["ns"]) >= 0.0 and 1.0 <= float(item["gamma_skyllh"]) <= 6.0 and int(item["minimizer_warnflag"]) == 0 for item in individual)
    check("individual_refits", valid_individual, "%d candidate leave-one-out fits are finite and converged" % candidate_count)
    ranked = sorted(individual, key=lambda item: (-float(item["delta_ts"]), int(item["removed_source_numbers"][0])))
    top_n = int(state["top_n"])
    top = ranked[:top_n]
    screening_order = [int(item["removed_source_numbers"][0]) for item in sorted(individual, key=lambda item: int(item["screening_rank"]))]
    refit_order = [int(item["removed_source_numbers"][0]) for item in ranked]
    check("candidate_rank_stability", screening_order == refit_order, "screening and full-refit order agree for all verified candidates", "warning")
    check("candidate_cutoff", float(ranked[top_n - 1]["delta_ts"]) > float(ranked[-1]["delta_ts"]), "rank-10 refit impact exceeds rank-%d impact" % candidate_count)
    cumulative = sorted(state.get("cumulative_refits", []), key=lambda item: int(item["n_removed"]))
    baseline_ts = float(state["baseline"]["TS"])
    expected_removed = []
    previous_ts = baseline_ts
    cumulative_ok = len(cumulative) == top_n
    for idx, item in enumerate(cumulative, start=1):
        expected_removed.append(int(top[idx - 1]["removed_source_numbers"][0]))
        cumulative_ok = cumulative_ok and int(item["n_removed"]) == idx and int(item["n_sources"]) == int(state["baseline"]["n_sources"]) - idx
        cumulative_ok = cumulative_ok and [int(value) for value in item["removed_source_numbers"]] == expected_removed
        cumulative_ok = cumulative_ok and np.isfinite(float(item["TS"])) and float(item["TS"]) >= 0.0 and int(item["minimizer_warnflag"]) == 0
        cumulative_ok = cumulative_ok and abs(float(item["cumulative_ts_drop"]) - (baseline_ts - float(item["TS"]))) < 1e-9
        cumulative_ok = cumulative_ok and abs(float(item["marginal_ts_drop"]) - (previous_ts - float(item["TS"]))) < 1e-9
        cumulative_ok = cumulative_ok and float(item["TS"]) <= previous_ts + 1e-9
        previous_ts = float(item["TS"])
    check("cumulative_refits", cumulative_ok, "Top-1 through Top-10 cumulative refits are ordered, converged, and internally consistent")
    artifacts = list(state.get("artifacts", {}).values())
    check("numeric_artifacts", all(Path(value).exists() and Path(value).stat().st_size > 0 for value in artifacts), "all declared numeric artifacts are readable")
    figure_dir = root / "figures/dominance" / out.name
    figure_dir.mkdir(parents=True, exist_ok=True)
    names = [item["source_name"] for item in top][::-1]
    impacts = [float(item["delta_ts"]) for item in top][::-1]
    fig, ax = plt.subplots(figsize=(8.2, 5.2))
    ax.barh(names, impacts, color="#2563eb")
    ax.set_xlabel("Individual leave-one-out ΔTS")
    ax.set_title(f"Top-{top_n} source dominance in the {state['baseline']['n_sources']}-source DR2 stack")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    for suffix in ["pdf", "png"]:
        fig.savefig(figure_dir / ("top10_individual_delta_ts." + suffix), dpi=180)
    plt.close(fig)
    steps = [0] + [int(item["n_removed"]) for item in cumulative]
    ts_values = [baseline_ts] + [float(item["TS"]) for item in cumulative]
    fig, ax = plt.subplots(figsize=(7.4, 4.8))
    ax.plot(steps, ts_values, marker="o", color="#0f766e")
    ax.set_xlabel("Number of top-ranked sources removed")
    ax.set_ylabel("Refitted TS")
    ax.set_title("Cumulative source removal lowers the stack TS")
    ax.set_xticks(steps)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    for suffix in ["pdf", "png"]:
        fig.savefig(figure_dir / ("cumulative_ts_removal." + suffix), dpi=180)
    plt.close(fig)
    statuses = [item["status"] for item in checks]
    status = "fail" if "fail" in statuses else ("warning" if "warning" in statuses else "pass")
    if status != "fail":
        state["status"] = "COMPLETED_WITH_WARNINGS" if status == "warning" else "COMPLETED"
        _write_json(out / "dominance_task.json", state)
    review = {
        "status": status,
        "checks": checks,
        "metrics": {
            "baseline_TS": baseline_ts,
            "top1_source": top[0]["source_name"],
            "top1_individual_delta_TS": float(top[0]["delta_ts"]),
            "top10_cumulative_TS": float(cumulative[-1]["TS"]),
            "top10_cumulative_delta_TS": float(cumulative[-1]["cumulative_ts_drop"]),
            "screening_signed_relative_difference": rel,
            "screening_signed_absolute_difference": float(screening["signed_absolute_difference"]),
            "max_screening_to_refit_absolute_correction": max(abs(float(item["delta_ts"]) - float(item["delta_ts_fixed"])) for item in individual),
        },
        "figures": [str(figure_dir / "top10_individual_delta_ts.pdf"), str(figure_dir / "cumulative_ts_removal.pdf")],
    }
    _write_json(out / "dominance_review.json", review)
    lines = ["# DR2 Source-Dominance Review", "", "Status: `%s`" % status, "", "## Checks", ""]
    lines.extend("- `%s` %s: %s" % (item["status"], item["id"], item["message"]) for item in checks)
    lines.extend(["", "## Metrics", ""])
    lines.extend("- %s: `%s`" % (key, value) for key, value in review["metrics"].items())
    (out / "dominance_review.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return review
