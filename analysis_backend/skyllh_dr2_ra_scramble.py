"""Checkpointed source/event right-ascension null tests for a fitted DR2 stack."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from agent_core.simple_yaml import load_simple_yaml
from analysis_backend.skyllh_dr2_dominance import _source_specs
from analysis_backend.skyllh_dr2_stacking import run_dr2_stacking


SCRAMBLE_MODES = ("sources_only", "events_only", "sources_and_events")


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _summary(result, mode, trial_seed, source_seed, event_seed):
    return {
        "mode": mode,
        "trial_seed": int(trial_seed),
        "source_ra_scramble_seed": source_seed,
        "event_ra_scramble_seed": event_seed,
        "TS": float(result["TS"]),
        "ns": float(result["ns"]),
        "gamma_skyllh": float(result["gamma"]),
        "gamma_legacy": float(result["gamma_legacy"]),
        "n_sources": int(result["n_sources"]),
        "n_events_total": int(result["n_events_total"]),
        "minimizer_status": result["minimizer_status"],
        "ra_scramble": result["ra_scramble"],
    }


def _mode_seeds(mode, seed):
    if mode == "sources_only":
        return int(seed), None
    if mode == "events_only":
        return None, int(seed)
    if mode == "sources_and_events":
        return int(seed), int(seed) + 10_000_000
    raise ValueError(f"Unknown RA-scramble mode {mode!r}")


def _mode_statistics(rows, baseline_ts):
    values = np.asarray([float(row["TS"]) for row in rows], dtype=np.float64)
    median = float(np.median(values))
    return {
        "n_trials": int(len(values)),
        "TS_min": float(np.min(values)),
        "TS_median": median,
        "TS_max": float(np.max(values)),
        "TS_mean": float(np.mean(values)),
        "n_TS_at_least_baseline": int(np.count_nonzero(values >= float(baseline_ts))),
        "fraction_TS_at_least_baseline": float(np.mean(values >= float(baseline_ts))),
        "TS_median_signed_relative_difference_from_baseline": (median - float(baseline_ts)) / float(baseline_ts),
        "TS_median_signed_absolute_difference_from_baseline": median - float(baseline_ts),
    }


def _write_markdown(path, state):
    lines = [
        "# DR2 SMBHB right-ascension scramble diagnostic",
        "",
        "Status: **WARNING — fixed-Gamma smoke-test null trials, not a calibrated empirical p-value.**",
        "",
        f"Baseline: TS={state['baseline']['TS']:.6g}, ns={state['baseline']['ns']:.6g}, "
        f"Gamma={state['baseline']['gamma_legacy']:.6g}, sources={state['baseline']['n_sources']}, "
        f"events={state['baseline']['n_events_total']}.",
        "",
        "Each selected RA is replaced independently by a uniform value in [0, 2pi). All declinations, "
        "event energies, angular errors, source weights, event rows, and sky cuts are preserved. "
        "The source and event streams in the combined mode are independent.",
        f"Gamma is fixed to the unscrambled best fit ({state['baseline']['gamma_legacy']:.6g}); only ns is re-maximized. "
        "This gives a conservative lower bound on the corresponding fitted-Gamma TS.",
        "",
        "| Mode | Trial seed | Source seed | Event seed | TS | ns | Gamma |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    rows = sorted(state["trials"].values(), key=lambda item: (SCRAMBLE_MODES.index(item["mode"]), item["trial_seed"]))
    for row in rows:
        source_seed = "—" if row["source_ra_scramble_seed"] is None else row["source_ra_scramble_seed"]
        event_seed = "—" if row["event_ra_scramble_seed"] is None else row["event_ra_scramble_seed"]
        lines.append(
            f"| {row['mode']} | {row['trial_seed']} | {source_seed} | {event_seed} | "
            f"{row['TS']:.6g} | {row['ns']:.6g} | {row['gamma_legacy']:.6g} |"
        )
    lines.extend(["", "## Per-mode summary", ""])
    for mode in SCRAMBLE_MODES:
        stats = state["statistics"][mode]
        lines.append(
            f"- `{mode}`: TS min/median/max = {stats['TS_min']:.4g}/{stats['TS_median']:.4g}/"
            f"{stats['TS_max']:.4g}; {stats['n_TS_at_least_baseline']}/{stats['n_trials']} trials reached "
            "or exceeded the unscrambled baseline; median signed relative/absolute differences = "
            f"{100.0 * stats['TS_median_signed_relative_difference_from_baseline']:+.2f}%/"
            f"{stats['TS_median_signed_absolute_difference_from_baseline']:+.4g}."
        )
    lines.extend([
        "",
        "These trials test whether the large raw TS survives destruction of RA associations. They are too few "
        "to estimate a tail probability. A publication-level empirical p-value requires a predeclared, much larger "
        "trial ensemble and optimizer-stability checks.",
        "",
    ])
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def run_dr2_ra_scramble_diagnostic(repo_root, baseline_run_directory, output_directory, seeds):
    root = Path(repo_root).resolve()
    baseline_dir = Path(baseline_run_directory).expanduser().resolve()
    out = Path(output_directory)
    if not out.is_absolute():
        out = root / out
    out.mkdir(parents=True, exist_ok=True)
    seeds = [int(seed) for seed in seeds]
    if not seeds or len(set(seeds)) != len(seeds) or any(seed < 0 for seed in seeds):
        raise ValueError("RA-scramble seeds must be a non-empty list of unique non-negative integers")

    normalized = load_simple_yaml((baseline_dir / "config.normalized.yaml").read_text(encoding="utf-8"))
    baseline_report = load_simple_yaml((baseline_dir / "report.yaml").read_text(encoding="utf-8"))["result"]
    baseline_review = _read_json(baseline_dir / "review.json")
    if baseline_review.get("status") not in {"pass", "warning"}:
        raise ValueError("Baseline run must have a passing or warning review")
    if baseline_report.get("likelihood_mode") != "spatial_energy" or baseline_report.get("gamma_mode") != "fitted":
        raise ValueError("RA-scramble diagnostic requires a fitted-Gamma DR2 spatial-energy baseline")
    specs = _source_specs(normalized)
    state_path = out / "dr2_ra_scramble_diagnostic.json"
    state = _read_json(state_path) if state_path.exists() else {
        "status": "RUNNING",
        "review_status": "warning",
        "baseline_run_directory": str(baseline_dir),
        "baseline": {
            "TS": float(baseline_report["TS"]),
            "ns": float(baseline_report["ns"]),
            "gamma_skyllh": float(baseline_report["gamma"]),
            "gamma_legacy": float(baseline_report["gamma_legacy"]),
            "n_sources": int(baseline_report["n_sources"]),
            "n_events_total": int(baseline_report["n_events_total"]),
        },
        "trial_definition": {
            "modes": list(SCRAMBLE_MODES),
            "seeds": seeds,
            "ra_distribution": "independent_uniform_[0,2pi)",
            "preserved": ["source_dec", "source_weight", "event_dec", "event_energy", "event_ang_err", "event_row_order", "sky_cuts"],
            "combined_streams_independent": True,
            "gamma_mode": "fixed_at_unscrambled_best_fit",
        },
        "trials": {},
    }
    if state["trial_definition"]["seeds"] != seeds:
        raise ValueError("Existing checkpoint uses different RA-scramble seeds")

    common = {
        "repo_root": root,
        "likelihood_mode": "spatial_energy",
        "gamma_mode": "fixed",
        "gamma": float(baseline_report["gamma"]),
        "ns_seed": 10.0,
        "event_abs_dec_max_deg": normalized.get("event_abs_dec_max_deg"),
        "event_dec_min_deg": normalized.get("event_dec_min_deg"),
        "event_dec_max_deg": normalized.get("event_dec_max_deg"),
        "data_selection": baseline_report.get("data_selection", "full14"),
        "signal_energy_declination_mode": baseline_report.get("signal_energy_declination_mode", "source"),
    }
    for mode in SCRAMBLE_MODES:
        for seed in seeds:
            label = f"{mode}_seed_{seed}"
            if label in state["trials"]:
                continue
            source_seed, event_seed = _mode_seeds(mode, seed)
            result = run_dr2_stacking(
                specs,
                source_ra_scramble_seed=source_seed,
                event_ra_scramble_seed=event_seed,
                random_seed=seed,
                **common,
            )
            state["trials"][label] = _summary(result, mode, seed, source_seed, event_seed)
            _write_json(state_path, state)

    by_mode = {mode: [row for row in state["trials"].values() if row["mode"] == mode] for mode in SCRAMBLE_MODES}
    state["statistics"] = {mode: _mode_statistics(rows, state["baseline"]["TS"]) for mode, rows in by_mode.items()}
    all_rows = list(state["trials"].values())
    state["checks"] = {
        "expected_trial_count": len(all_rows) == len(SCRAMBLE_MODES) * len(seeds),
        "all_finite_nonnegative_TS": all(np.isfinite(row["TS"]) and row["TS"] >= 0.0 for row in all_rows),
        "all_finite_fit_parameters": all(np.isfinite(row["ns"]) and np.isfinite(row["gamma_skyllh"]) for row in all_rows),
        "all_optimizer_warnflags_zero": all(int(row["minimizer_status"].get("warnflag", -1)) == 0 for row in all_rows),
        "source_and_event_streams_independent_in_combined_mode": all(
            row["source_ra_scramble_seed"] != row["event_ra_scramble_seed"] for row in by_mode["sources_and_events"]
        ),
    }
    state["status"] = "COMPLETED_WITH_WARNINGS" if all(state["checks"].values()) else "FAILED"
    state["scientific_cautions"] = [
        "This small trial ensemble is a diagnostic smoke test, not an empirical p-value calibration.",
        "Gamma is fixed at the unscrambled best fit; each TS is a lower bound on a stable fitted-Gamma result.",
        "The fitted-Gamma energy-PDF discrepancy identified in the baseline review remains unresolved.",
        "A raw TS from different analyses cannot be converted to a universal sigma using sqrt(TS).",
    ]
    _write_json(state_path, state)
    _write_markdown(out / "dr2_ra_scramble_review.md", state)
    return state
