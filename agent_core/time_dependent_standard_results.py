"""Canonical saved-result bundle for reviewed fixed-window time-dependent trials.

This module is an output adapter only.  It never constructs or maximizes a
likelihood and it never starts trials.  It converts NuSrcAgent's reviewed
observed result and completed shared-trial shards into the artifact schema
consumed by ``agent_core/plot_time_dependent_standard_report.py``.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any

import numpy as np
from scipy.stats import norm

from agent_core.file_cache import sha256_file
from agent_core.simple_yaml import load_simple_yaml


PROFILE = "td_catalog_standard_v1"


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty table: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def _file_digest(path: Path) -> str:
    return sha256_file(path)


def _value_digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, allow_nan=False).encode("utf-8")
    ).hexdigest()


def _finite_significance(p_value: float) -> float | None:
    if not 0.0 < p_value < 1.0:
        return None
    return float(norm.isf(p_value))


def _fit_gamma(normalized: dict[str, Any]) -> bool:
    return normalized.get("gamma_mode") == "fitted"


def _fixed_gamma(normalized: dict[str, Any]) -> float | None:
    if _fit_gamma(normalized):
        return None
    values = normalized.get("spectral_indices", [])
    return -float(values[0]) if values else None


def _gamma_bounds(normalized: dict[str, Any]) -> tuple[float, float]:
    bounds = normalized.get("gamma_bounds")
    if bounds:
        return -float(bounds[1]), -float(bounds[0])
    return 1.0, 4.0


def _safe_name(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
    return normalized or "source"


def _source_components(normalized: dict[str, Any]) -> bool:
    return normalized.get("analysis_type") == "single_source" or normalized.get(
        "catalog_operation"
    ) in {"scan", "scan_and_stack"}


def _stack_component(normalized: dict[str, Any]) -> bool:
    return normalized.get("analysis_type") != "single_source" and normalized.get(
        "catalog_operation"
    ) in {"stack", "scan_and_stack"}


def _source_id(source: dict[str, Any], index: int) -> str:
    for key in ("source_id", "id"):
        if source.get(key) not in (None, ""):
            return str(source[key])
    return f"nusrcagent:{int(source.get('source_number', index + 1))}"


def _source_name(source: dict[str, Any], index: int) -> str:
    return str(source.get("name") or source.get("source_name") or f"source_{index + 1}")


def _observed_arrays(
    normalized: dict[str, Any], observed: dict[str, Any]
) -> dict[str, np.ndarray]:
    n_sources = len(normalized["sources"])
    records = observed.get("source_results", [])
    if len(records) != n_sources:
        raise ValueError("observed source result count does not match normalized catalog")
    fits = [item["fit"] for item in records]
    stack = observed.get("stack_result", {})
    return {
        "source_ts": np.asarray([fit["TS"] for fit in fits], dtype=float),
        "source_ns": np.asarray([fit["ns"] for fit in fits], dtype=float),
        "source_gamma": np.asarray(
            [np.nan if fit.get("gamma") is None else fit["gamma"] for fit in fits],
            dtype=float,
        ),
        "source_fit_ok": np.asarray([fit.get("fit_ok") is True for fit in fits], dtype=bool),
        "stack_ts": np.asarray(float(stack.get("TS", np.nan))),
        "stack_ns": np.asarray(float(stack.get("ns", np.nan))),
        "stack_gamma": np.asarray(
            np.nan if stack.get("gamma") is None else float(stack["gamma"])
        ),
        "stack_fit_ok": np.asarray(stack.get("fit_ok") is True, dtype=bool),
    }


def _merge_trials(chunks: list[dict[str, np.ndarray]]) -> dict[str, np.ndarray]:
    if not chunks:
        raise ValueError("completed trial ensemble contains no shards")
    keys = tuple(chunks[0])
    if any(set(chunk) != set(keys) for chunk in chunks):
        raise ValueError("trial shards have inconsistent fields")
    return {key: np.concatenate([np.asarray(chunk[key]) for chunk in chunks], axis=0) for key in keys}


def _baseline_configuration(
    root: Path, immutable: dict[str, Any]
) -> tuple[dict[str, Any], Path | None]:
    run = Path(immutable["baseline_run"])
    candidates = sorted(run.glob("config.original.*")) if run.is_dir() else []
    if len(candidates) != 1:
        return {}, None
    try:
        value = load_simple_yaml(candidates[0].read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}, candidates[0]
    return (value if isinstance(value, dict) else {}), candidates[0]


def _catalog_labels(
    normalized: dict[str, Any], observed: dict[str, Any], configuration: dict[str, Any]
) -> tuple[str, str, str | None]:
    temporal = observed.get("time_dependent_engine", {})
    catalog = configuration.get("catalog") or {}
    catalog_value = catalog.get("builtin") or catalog.get("file")
    label = normalized.get("catalog_label") or normalized.get("name")
    if not label and catalog_value:
        label = Path(str(catalog_value)).stem.replace("_", " ")
    if not label:
        sources = normalized.get("sources", [])
        label = (
            _source_name(sources[0], 0)
            if len(sources) == 1
            else f"NuSrcAgent catalog ({len(sources)} sources)"
        )
    weights = configuration.get("weights") or {}
    weight_mode = normalized.get("weight_mode") or weights.get("mode")
    weight_label = None
    if weight_mode and len(normalized.get("sources", [])) > 1:
        weight_label = str(weight_mode).replace("_", " ")
        if weights.get("column"):
            weight_label += f" from {weights['column']}"
        label = f"{label} ({weight_label} weighting)"
    datasets = temporal.get("dataset_names", [])
    dataset = "DR2 14 yr" if datasets else str(normalized.get("sample", "IceCube DR2"))
    return str(label), dataset, weight_label


def _resolved_input_path(root: Path, value: Any) -> Path | None:
    if value in (None, ""):
        return None
    path = Path(str(value)).expanduser()
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def _source_manifest(
    normalized: dict[str, Any], observed: dict[str, Any]
) -> dict[str, Any]:
    windows = observed["time_dependent_engine"]["windows"]
    if len(windows) != len(normalized["sources"]):
        raise ValueError("source window count does not match normalized catalog")
    selected = []
    for index, (source, window) in enumerate(zip(normalized["sources"], windows, strict=True)):
        start, stop = float(window["start_mjd"]), float(window["stop_mjd"])
        selected.append(
            {
                "source_index": index,
                "source_id": _source_id(source, index),
                "name": _source_name(source, index),
                "ra_deg": float(source["ra_deg"]),
                "dec_deg": float(source["dec_deg"]),
                "weight": float(source.get("weight", 1.0)),
                "time_start_mjd": start,
                "time_end_mjd": stop,
                "time_anchor_mjd": 0.5 * (start + stop),
                "time_anchor_definition": "fixed_window_midpoint",
            }
        )
    return {
        "selection_method": "NuSrcAgent reviewed fixed per-source catalog windows",
        "time_anchor_definition": "fixed_window_midpoint unless an explicit physical anchor is added to the recorded request",
        "selected": selected,
    }


def _source_statistics(
    normalized: dict[str, Any],
    observed_arrays: dict[str, np.ndarray],
    trials: dict[str, np.ndarray],
    manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    n_trials, n_sources = trials["source_ts"].shape
    if n_sources != len(manifest["selected"]):
        raise ValueError("trial source array does not match selected source count")
    observed_ts = observed_arrays["source_ts"]
    exceedances = np.count_nonzero(trials["source_ts"] >= observed_ts[np.newaxis, :], axis=0)
    local_p = (exceedances + 1.0) / (n_trials + 1.0)
    sidak_p = -np.expm1(n_sources * np.log1p(-local_p))
    maximum_ts = np.max(trials["source_ts"], axis=1)
    maximum_exceedances = np.count_nonzero(
        maximum_ts[:, np.newaxis] >= observed_ts[np.newaxis, :], axis=0
    )
    maximum_p = (maximum_exceedances + 1.0) / (n_trials + 1.0)
    rows = []
    for index, source in enumerate(manifest["selected"]):
        gamma = observed_arrays["source_gamma"][index]
        rows.append(
            {
                "source_index": index,
                "source_id": source["source_id"],
                "source_name": source["name"],
                "ra_deg": source["ra_deg"],
                "dec_deg": source["dec_deg"],
                "time_anchor_mjd": source["time_anchor_mjd"],
                "time_start_mjd": source["time_start_mjd"],
                "time_end_mjd": source["time_end_mjd"],
                "time_anchor_definition": source["time_anchor_definition"],
                "ts": float(observed_ts[index]),
                "ns": float(observed_arrays["source_ns"][index]),
                "gamma": None if not np.isfinite(gamma) else float(gamma),
                "n_exceedances": int(exceedances[index]),
                "p_pre": float(local_p[index]),
                "z_pre": _finite_significance(float(local_p[index])),
                "p_post_sidak": float(sidak_p[index]),
                "z_post_sidak": _finite_significance(float(sidak_p[index])),
                "n_max_ts_exceedances": int(maximum_exceedances[index]),
                "p_post_empirical_max_ts": float(maximum_p[index]),
                "z_post_empirical_max_ts": _finite_significance(float(maximum_p[index])),
            }
        )
    return rows


def _stack_summary(
    normalized: dict[str, Any],
    observed_arrays: dict[str, np.ndarray],
    trials: dict[str, np.ndarray],
) -> dict[str, Any]:
    n_trials = len(trials["stack_ts"])
    observed_ts = float(observed_arrays["stack_ts"])
    exceedances = int(np.count_nonzero(trials["stack_ts"] >= observed_ts))
    p_value = (exceedances + 1.0) / (n_trials + 1.0)
    observed_gamma = float(observed_arrays["stack_gamma"])
    summary = {
        "analysis": "time-dependent catalog stacking",
        "fit_gamma": _fit_gamma(normalized),
        "n_sources": len(normalized["sources"]),
        "observed_ts": observed_ts,
        "observed_ns": float(observed_arrays["stack_ns"]),
        "observed_gamma": observed_gamma if np.isfinite(observed_gamma) else None,
        "n_background_trials": n_trials,
        "n_background_ts_ge_observed": exceedances,
        "p_value": float(p_value),
        "significance_sigma_one_sided": _finite_significance(float(p_value)),
        "significance_display": "no excess" if p_value == 1.0 else None,
        "p_value_method": "(N(TS_bg >= TS_obs) + 1) / (N_trials + 1)",
        "empirical_zero_ts_fraction": float(np.count_nonzero(trials["stack_ts"] == 0.0) / n_trials),
        "minimum_resolvable_p_value": 1.0 / (n_trials + 1.0),
        "null_calibration": "matched shared seasonal background trials",
        "asymptotic_note": "NuSrcAgent does not apply time-integrated asymptotic significance formulas to time-dependent fits.",
    }
    if _fit_gamma(normalized) and summary["observed_ns"] == 0.0:
        summary["observed_gamma"] = None
        summary["gamma_status"] = "unidentified_at_ns_zero"
    return summary


def _validation(
    normalized: dict[str, Any],
    observed_arrays: dict[str, np.ndarray],
    trials: dict[str, np.ndarray],
    requested: int,
    baseline_review: dict[str, Any],
) -> dict[str, Any]:
    produced = len(trials["trial_index"])
    has_sources = _source_components(normalized)
    has_stack = _stack_component(normalized)
    checks = {
        "all_observed_source_fits_ok": bool(np.all(observed_arrays["source_fit_ok"])),
        "observed_stack_fit_ok": bool(observed_arrays["stack_fit_ok"]) if has_stack else True,
        "all_background_source_fits_ok": bool(np.all(trials["source_fit_ok"])),
        "all_background_stack_fits_ok": bool(np.all(trials["stack_fit_ok"])) if has_stack else True,
        "all_ts_and_ns_finite": bool(
            all(
                np.all(np.isfinite(values))
                for values in (
                    observed_arrays["source_ts"],
                    observed_arrays["source_ns"],
                    trials["source_ts"],
                    trials["source_ns"],
                    *(
                        (np.atleast_1d(observed_arrays["stack_ts"]), np.atleast_1d(observed_arrays["stack_ns"]), trials["stack_ts"], trials["stack_ns"])
                        if has_stack
                        else ()
                    ),
                )
            )
        ),
        "requested_trial_count": int(requested),
        "produced_trial_count": int(produced),
        "requested_trial_count_produced": produced == requested,
        "n_unique_seeds": int(len(np.unique(trials["seed"]))),
        "background_seeds_unique": len(np.unique(trials["seed"])) == produced,
        "trial_indices_contiguous": bool(
            np.array_equal(trials["trial_index"], np.arange(produced, dtype=trials["trial_index"].dtype))
        ),
        "baseline_review_passed": baseline_review.get("status") != "fail",
        "trial_arrays_validated": True,
    }
    required = [value for value in checks.values() if isinstance(value, bool)]
    checks["all_checks_passed"] = all(required)
    return checks


def _render(
    root: Path,
    bundle: Path,
    leading_source: str | None,
) -> dict[str, Any]:
    renderer = root / "agent_core" / "plot_time_dependent_standard_report.py"
    if not renderer.is_file():
        raise FileNotFoundError(f"missing standard renderer: {renderer}")
    uptime = root / "data_input/IceCube_data_released/2026_icecube_14_year_track_data_IceTracks_DR2/uptime"
    command = [sys.executable, str(renderer), str(bundle)]
    if uptime.is_dir():
        command.extend(["--uptime-dir", str(uptime)])
    if leading_source is not None:
        command.extend(["--single-source", leading_source])
    completed = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
    if completed.returncode:
        raise RuntimeError(
            "standard time-dependent renderer failed:\n"
            + completed.stdout
            + completed.stderr
        )
    manifest = bundle / "standardized_report/plot_manifest.json"
    if not manifest.is_file():
        raise ValueError("standard renderer did not create plot_manifest.json")
    return {
        "renderer": str(renderer),
        "renderer_sha256": _file_digest(renderer),
        "manifest": str(manifest),
        "manifest_sha256": _file_digest(manifest),
        "stdout": completed.stdout.strip(),
    }


def _publish_canonical_plots(bundle: Path) -> list[str]:
    """Mirror standard-renderer defaults into the canonical result locations."""

    relative_paths = (
        "single_src/source_pvalues_over_time.png",
        "single_src/source_pvalues_over_time.pdf",
        "single_src/source_pvalues_over_time_data.csv",
        "stacking/background_ts_histogram.png",
        "stacking/background_ts_histogram.pdf",
        "stacking/stacking_likelihood_contour.png",
        "stacking/stacking_likelihood_contour.pdf",
    )
    copied = []
    for relative in relative_paths:
        source = bundle / "standardized_report" / relative
        if not source.is_file():
            continue
        destination = bundle / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied.append(str(destination))
    for source in sorted((bundle / "standardized_report/single_src").glob("*_likelihood_contour.*")):
        if source.suffix not in {".png", ".pdf"}:
            continue
        destination = bundle / "single_src" / source.name
        shutil.copy2(source, destination)
        copied.append(str(destination))
    return copied


def _write_likelihood_surfaces(
    root: Path,
    bundle: Path,
    normalized: dict[str, Any],
    observed: dict[str, Any],
    leading: dict[str, Any] | None,
    stack_summary: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Save validated free-Gamma surfaces for the leading source and stack."""

    if not _fit_gamma(normalized):
        return []
    from agent_core.schemas import NormalizedAnalysis, NormalizedSource
    from analysis_backend.time_dependent.adapter import prepare_analysis
    from analysis_backend.time_dependent.surfaces import (
        save_observed_likelihood_surface,
    )

    payload = dict(normalized)
    payload["sources"] = [NormalizedSource(**source) for source in payload["sources"]]
    normalized_analysis = NormalizedAnalysis(**payload)
    prepared = prepare_analysis(
        normalized_analysis,
        root,
        workers=1,
        build_engine=False,
    )
    expected = observed["time_dependent_engine"]
    for key in (
        "engine",
        "spectrum",
        "likelihood",
        "dataset_names",
        "input_sha256",
        "windows",
    ):
        if prepared.metadata[key] != expected[key]:
            raise ValueError(
                "observed likelihood-surface reconstruction differs in " + key
            )

    saved = []
    if leading is not None:
        source_index = int(leading["source_index"])
        source_path = (
            bundle
            / "single_src"
            / f"{_safe_name(str(leading['source_name']))}_likelihood_contour.npz"
        )
        saved.append(
            save_observed_likelihood_surface(
                prepared.constructed,
                source_path,
                {
                    "TS": leading["ts"],
                    "ns": leading["ns"],
                    "gamma": leading["gamma"],
                },
                source_index=source_index,
                source_name=str(leading["source_name"]),
                source_id=str(leading["source_id"]),
            )
        )
    if stack_summary is not None:
        saved.append(
            save_observed_likelihood_surface(
                prepared.constructed,
                bundle / "stacking/stacking_likelihood_contour.npz",
                {
                    "TS": stack_summary["observed_ts"],
                    "ns": stack_summary["observed_ns"],
                    "gamma": stack_summary["observed_gamma"],
                },
                source_index=None,
            )
        )
    return saved


def finalize_time_dependent_results(
    repo_root: str | Path,
    trial_directory: str | Path,
    task: dict[str, Any],
    chunks: list[dict[str, np.ndarray]],
) -> dict[str, Any]:
    """Write and render the standard bundle for one completed trial ensemble."""

    root = Path(repo_root).resolve()
    directory = Path(trial_directory).resolve()
    immutable = task["immutable"]
    normalized = immutable["normalized"]
    observed = immutable["observed"]
    requested = int(immutable["n_trials"])
    receipt = directory / "standard_results.json"
    if receipt.is_file():
        saved = json.loads(receipt.read_text(encoding="utf-8"))
        if saved.get("request_sha256") != task.get("request_sha256"):
            raise ValueError("saved standard result belongs to a different trial request")
        for key in ("result_directory", "report", "analysis_summary", "validation", "plot_manifest"):
            if not Path(saved[key]).is_file() and key != "result_directory":
                raise ValueError(f"saved standard result artifact is missing: {saved[key]}")
        if not Path(saved["result_directory"]).is_dir():
            raise ValueError("saved standard result directory is missing")
        for surface in saved.get("likelihood_surfaces", []):
            path = Path(surface["path"])
            if not path.is_file() or _file_digest(path) != surface.get("sha256"):
                raise ValueError(f"saved likelihood surface is missing or changed: {path}")
        return saved
    if task.get("completed") != requested:
        raise ValueError("standard results require the complete requested trial ensemble")
    if normalized.get("temporal", {}).get("scope") != "per_source_catalog_windows":
        raise ValueError("standard results apply only to fixed per-source catalog windows")

    trials = _merge_trials(chunks)
    observed_arrays = _observed_arrays(normalized, observed)
    validation = _validation(
        normalized, observed_arrays, trials, requested, task.get("baseline_review", {})
    )
    if not validation["all_checks_passed"]:
        failure = directory / "standard_results_validation_failed.json"
        _write_json(failure, validation)
        raise ValueError(f"standard result validation failed; inspect {failure}")

    bundle = directory / "standard_results"
    if bundle.exists():
        raise FileExistsError(
            f"standard result directory already exists: {bundle}; do not overwrite reviewed artifacts"
        )
    bundle.mkdir(parents=True)
    (bundle / "single_src").mkdir()
    (bundle / "stacking").mkdir()

    configuration, configuration_path = _baseline_configuration(root, immutable)
    catalog_label, dataset_label, weight_label = _catalog_labels(
        normalized, observed, configuration
    )
    manifest = _source_manifest(normalized, observed)
    source_rows = _source_statistics(normalized, observed_arrays, trials, manifest)
    leading = min(source_rows, key=lambda row: row["p_pre"]) if _source_components(normalized) else None
    stack_summary = _stack_summary(normalized, observed_arrays, trials) if _stack_component(normalized) else None
    fit_gamma = _fit_gamma(normalized)
    gamma_min, gamma_max = _gamma_bounds(normalized)

    spectrum = {
        "fit_gamma": fit_gamma,
        **(
            {"gamma_min": gamma_min, "gamma_max": gamma_max}
            if fit_gamma
            else {"fixed_gamma": _fixed_gamma(normalized)}
        ),
    }
    summary = {
        "analysis": "time-dependent catalog analysis",
        "catalog_label": catalog_label,
        "dataset_label": dataset_label,
        "engine": observed["time_dependent_engine"]["engine"],
        "likelihood_family": observed["time_dependent_engine"]["likelihood_family"],
        **spectrum,
        "n_sources": len(normalized["sources"]),
        "n_background_trials": requested,
        "has_source_component": _source_components(normalized),
        "has_stacking_component": _stack_component(normalized),
        "single_source": leading,
        "stacking": stack_summary,
    }

    catalog_value = (configuration.get("catalog") or {}).get("file")
    catalog_path = _resolved_input_path(root, catalog_value)
    inputs = {
        "baseline_task": immutable["baseline_task"],
        "baseline_run": immutable["baseline_run"],
        "baseline_files": immutable["baseline_files"],
        "normalized_request_sha256": _value_digest(normalized),
        "resolved_configuration_path": (
            str(configuration_path.resolve()) if configuration_path is not None else None
        ),
        "configuration_sha256": (
            _file_digest(configuration_path) if configuration_path is not None else None
        ),
        "resolved_catalog_path": str(catalog_path) if catalog_path is not None else None,
        "catalog_sha256": (
            _file_digest(catalog_path) if catalog_path is not None and catalog_path.is_file() else None
        ),
        "catalog_sources": manifest["selected"],
        "dataset_names": observed["time_dependent_engine"]["dataset_names"],
        "input_sha256": observed["time_dependent_engine"]["input_sha256"],
        "spectral_model": spectrum,
        "time_window_definition": "fixed per-source box windows",
        "source_weight_prescription": weight_label,
        "scrambling_method": immutable["method"],
        "engine": observed["time_dependent_engine"]["engine"],
        "backend": observed.get("backend"),
        "base_seed": immutable["base_seed"],
        "trial_range": [0, requested],
        "software_and_code": immutable["code"],
        "report_profile": PROFILE,
    }

    _write_json(bundle / "inputs.json", inputs)
    _write_json(bundle / "validation.json", validation)
    _write_json(bundle / "analysis_summary.json", summary)
    _write_json(bundle / "observed.sources.json", manifest)
    _write_json(
        bundle / "observed.json",
        {
            "kind": "reviewed_observed_fit",
            "baseline_run": immutable["baseline_run"],
            "precomputed_pdf_inputs": {},
            "time_dependent_engine": observed["time_dependent_engine"],
        },
    )
    np.savez(bundle / "observed.npz", **observed_arrays)

    background_stem = f"background_trials_{0:06d}_{requested:06d}"
    np.savez(bundle / f"{background_stem}.npz", **trials)
    background_metadata = {
        "kind": "completed shared seasonal background trials",
        "n_trials": requested,
        "trial_start": 0,
        "trial_stop": requested,
        "base_seed": immutable["base_seed"],
        "method": immutable["method"],
        "request_sha256": task["request_sha256"],
        "source_count": len(normalized["sources"]),
    }
    _write_json(bundle / f"{background_stem}.json", background_metadata)
    _write_json(bundle / f"{background_stem}.sources.json", manifest)

    if _source_components(normalized):
        _write_csv(bundle / "single_src/source_results.csv", source_rows)
        _write_csv(bundle / "single_src/source_pvalues_over_time_data.csv", source_rows)
        _write_json(
            bundle / "single_src/source_results.json",
            {
                "method": "empirical local survival fraction with add-one correction",
                "empirical_post_trial_method": "shared-trial maximum single-source TS survival fraction with add-one correction",
                "sidak_post_trial_formula": "1 - (1 - p_pre)**n_sources",
                "n_trials": requested,
                "minimum_empirical_p": 1.0 / (requested + 1.0),
                "results": source_rows,
            },
        )
        _write_json(bundle / "single_src/summary.json", summary["single_source"] or {})
        _write_json(bundle / "single_src/observed.json", {"fit_ok": True, "n_sources": len(source_rows)})
        _write_json(bundle / "single_src/background_trials.json", background_metadata)

    if stack_summary is not None:
        stack_rows = [
            {
                "seed": int(trials["seed"][index]),
                "ts": float(trials["stack_ts"][index]),
                "ns": float(trials["stack_ns"][index]),
                "gamma": None
                if not np.isfinite(trials["stack_gamma"][index])
                else float(trials["stack_gamma"][index]),
                "trial_index": int(trials["trial_index"][index]),
                "fit_ok": bool(trials["stack_fit_ok"][index]),
            }
            for index in range(requested)
        ]
        _write_csv(bundle / "stacking/background_trials.csv", stack_rows)
        _write_json(bundle / "stacking/summary.json", stack_summary)
        _write_json(
            bundle / "stacking/observed.json",
            {
                "ts": stack_summary["observed_ts"],
                "parameters": {
                    "ns": stack_summary["observed_ns"],
                    "gamma": stack_summary["observed_gamma"],
                },
                "fit_ok": True,
            },
        )
        _write_json(bundle / "stacking/background_trials.json", background_metadata)

    expected_surface_count = int(fit_gamma) * (
        int(leading is not None) + int(stack_summary is not None)
    )
    validation["likelihood_surfaces_required"] = fit_gamma
    try:
        likelihood_surfaces = _write_likelihood_surfaces(
            root,
            bundle,
            normalized,
            observed,
            leading,
            stack_summary,
        )
        for surface in likelihood_surfaces:
            surface["sha256"] = _file_digest(Path(surface["path"]))
        surfaces_valid = len(likelihood_surfaces) == expected_surface_count
        validation["likelihood_surface_count"] = len(likelihood_surfaces)
        validation["likelihood_surfaces_valid"] = surfaces_valid
        validation["all_checks_passed"] = bool(
            validation["all_checks_passed"] and surfaces_valid
        )
        if not surfaces_valid:
            raise ValueError(
                "free-Gamma standard results did not produce every required likelihood surface"
            )
    except Exception as error:
        validation["likelihood_surface_count"] = 0
        validation["likelihood_surfaces_valid"] = False
        validation["likelihood_surface_error"] = str(error)
        validation["all_checks_passed"] = False
        _write_json(bundle / "validation.json", validation)
        _write_json(
            directory / "standard_results_validation_failed.json", validation
        )
        raise
    summary["likelihood_surfaces"] = likelihood_surfaces
    inputs["likelihood_surfaces"] = likelihood_surfaces
    _write_json(bundle / "validation.json", validation)
    _write_json(bundle / "analysis_summary.json", summary)
    _write_json(bundle / "inputs.json", inputs)

    lines = [
        f"# {catalog_label} time-dependent results",
        "",
        f"Dataset: {dataset_label}. Background ensemble: {requested:,} matched shared seasonal trials.",
        "",
    ]
    if leading is not None:
        lines.extend(
            [
                "## Single-source scan",
                "",
                f"- Leading source: {leading['source_name']}",
                f"- Best fit: TS={leading['ts']:.6g}, ns={leading['ns']:.6g}"
                + ("; Gamma unidentified" if leading["gamma"] is None else f", Gamma={leading['gamma']:.6g}"),
                f"- Local p-value: {leading['p_pre']:.6g} ({leading['n_exceedances']}/{requested} exceedances)",
                f"- Sidak post-trial p-value: {leading['p_post_sidak']:.6g}",
                f"- Empirical max-TS post-trial p-value: {leading['p_post_empirical_max_ts']:.6g}",
                "",
            ]
        )
    if stack_summary is not None:
        significance = (
            "no excess"
            if stack_summary["p_value"] == 1.0
            else f"{stack_summary['significance_sigma_one_sided']:.4g} sigma, one-sided"
        )
        gamma_display = (
            "Gamma unidentified"
            if stack_summary["observed_gamma"] is None and fit_gamma
            else (
                "fixed Gamma"
                if stack_summary["observed_gamma"] is None
                else f"Gamma={stack_summary['observed_gamma']:.6g}"
            )
        )
        lines.extend(
            [
                "## Stacking",
                "",
                f"- Best fit: TS={stack_summary['observed_ts']:.6g}, ns={stack_summary['observed_ns']:.6g}, {gamma_display}",
                f"- Empirical p-value: {stack_summary['p_value']:.6g} ({stack_summary['n_background_ts_ge_observed']}/{requested} exceedances; {significance})",
                "",
            ]
        )
    lines.extend(
        [
            "All validation checks passed. Trial seeds are unique and trial indices are contiguous.",
            (
                "Validated numerical ns-Gamma likelihood surfaces were saved for the applicable leading-source and stacking fits."
                if fit_gamma
                else "The fixed-Gamma fit has no two-dimensional ns-Gamma likelihood surface."
            ),
            "NuSrcAgent uses the matched scrambled distribution as the time-dependent null calibration; no time-integrated asymptotic significance formula is applied.",
            "",
        ]
    )
    (bundle / "report.md").write_text("\n".join(lines), encoding="utf-8")

    render = _render(root, bundle, leading["source_name"] if leading else None)
    canonical_plots = _publish_canonical_plots(bundle)
    output = {
        "request_sha256": task["request_sha256"],
        "result_directory": str(bundle),
        "report": str(bundle / "report.md"),
        "analysis_summary": str(bundle / "analysis_summary.json"),
        "validation": str(bundle / "validation.json"),
        "plot_manifest": render["manifest"],
        "report_profile": PROFILE,
        "leading_source": leading,
        "stacking": stack_summary,
        "validation_summary": validation,
        "renderer": render,
        "canonical_plot_files": canonical_plots,
        "likelihood_surfaces": likelihood_surfaces,
    }
    _write_json(receipt, output)
    return output
