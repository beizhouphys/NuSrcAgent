"""Explicit time-search settings shared by planning, validation and runtime."""
from __future__ import annotations

import math
import json
from pathlib import Path


def temporal_errors(settings):
    if not isinstance(settings, dict) or not settings:
        return ["Time-dependent analysis requires explicit temporal settings"]
    if settings.get("scope") == "per_source_catalog_windows":
        return catalog_window_errors(settings)
    errors = []
    allowed = {"scope", "profile", "time_format", "time_scale", "background_time_model",
               "t0", "width", "search"}
    if settings.get("scope") not in (None, "legacy_time_profile"):
        errors.append("Unknown temporal scope")
    if set(settings) - allowed:
        errors.append("Unknown temporal settings: " + ", ".join(sorted(set(settings)-allowed)))
    if settings.get("profile") not in {"gaussian", "box"}:
        errors.append("temporal.profile must be gaussian or box")
    if settings.get("time_format") != "mjd" or settings.get("time_scale") != "ut1":
        errors.append("Temporal times must explicitly use MJD in the public-data UT1 convention")
    if settings.get("background_time_model") != "uniform_livetime":
        errors.append("Explicit temporal.background_time_model=uniform_livetime is required")
    fitted = False
    for name in ("t0", "width"):
        value = settings.get(name, {})
        if not isinstance(value, dict):
            errors.append("temporal." + name + " must be a mapping")
            continue
        # A supplied value is fixed unless fitting is explicitly requested.
        mode = value.get("mode", "fixed" if "value" in value else "fitted")
        if mode not in {"fixed", "fitted"}:
            errors.append("temporal." + name + ".mode must be fixed or fitted")
            continue
        if set(value) - {"mode", "value", "bounds", "seeds"}:
            errors.append("Unknown temporal." + name + " fields")
        if mode == "fixed":
            if not finite(value.get("value")) or (name == "width" and value["value"] <= 0):
                errors.append("Fixed temporal." + name + " requires a finite " + ("positive " if name == "width" else "") + "value")
            if "bounds" in value or "seeds" in value:
                errors.append("Fixed temporal." + name + " cannot have fit bounds or seeds")
        else:
            fitted = True
            bounds = value.get("bounds")
            valid_bounds = (isinstance(bounds, list) and len(bounds) == 2
                and all(finite(x) for x in bounds) and bounds[0] < bounds[1]
                and (name != "width" or bounds[0] > 0))
            if not valid_bounds:
                errors.append("Fitted temporal." + name + " requires explicit ordered finite bounds (positive width)")
            seeds = value.get("seeds")
            if not isinstance(seeds, list) or not seeds or not all(finite(x) for x in seeds):
                errors.append("Fitted temporal." + name + " requires explicit nonempty search seeds")
            elif valid_bounds and any(not bounds[0] <= x <= bounds[1] for x in seeds):
                errors.append("Temporal search seeds must be inside the corresponding bounds")
            if "value" in value:
                errors.append("For a fitted temporal parameter put the supplied initial value in seeds")
    search = settings.get("search", {})
    if fitted:
        if not isinstance(search, dict) or search.get("method") != "grid_powell_v1":
            errors.append("Fitted temporal parameters require explicit search.method=grid_powell_v1")
        elif (set(search) - {"method", "maxiter", "xtol", "ftol"}
              or isinstance(search.get("maxiter"), bool)
              or not isinstance(search.get("maxiter"), int) or search["maxiter"] < 1
              or not finite(search.get("xtol")) or search["xtol"] <= 0
              or not finite(search.get("ftol")) or search["ftol"] <= 0):
            errors.append("Temporal search requires positive maxiter, xtol and ftol; unknown settings are rejected")
    elif search:
        errors.append("A fixed temporal profile must not request a time search")
    return errors


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def catalog_window_errors(settings):
    """Validate the donor's fixed-box contract independently of time searches."""
    errors = []
    allowed = {"scope", "profile", "time_format", "time_scale", "background_time_model",
               "windows", "window_columns", "datasets", "engine", "gamma_grid_step",
               "event_selection_angle_deg", "ns_max", "pdf_backend", "tail_tolerance"}
    if set(settings) - allowed:
        errors.append("Unknown catalog temporal settings: " + ", ".join(sorted(set(settings)-allowed)))
    if settings.get("profile") not in {"box", "gaussian"}:
        errors.append("Catalog time profiles require explicit profile=box or gaussian")
    for key, value in {"time_format": "mjd", "time_scale": "ut1",
                       "background_time_model": "uniform_livetime"}.items():
        if settings.get(key) != value:
            errors.append(f"Catalog windows require explicit {key}={value}")
    datasets = settings.get("datasets")
    if not isinstance(datasets, list) or not datasets or not all(isinstance(x, str) and x for x in datasets) or len(set(datasets)) != len(datasets):
        errors.append("Catalog windows require unique explicit dataset names")
    else:
        seasons = {"IC86_" + x for x in ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI")}
        if set(datasets) - (seasons | {"IC40", "IC59", "IC79", "IC86_I-XI"}):
            errors.append("Unsupported DR2 dataset name")
        if "IC86_I-XI" in datasets and seasons.intersection(datasets):
            errors.append("Pooled IC86 and individual seasons overlap; select one representation")
    if settings.get("engine", "auto") not in {"auto", "reference", "cached-fixed", "cached-free"}:
        errors.append("Unknown time-dependent engine")
    if settings.get("pdf_backend", "precomputed") not in {"precomputed", "skyllh"}:
        errors.append("pdf_backend must be precomputed or skyllh")
    if settings.get("pdf_backend", "precomputed") == "skyllh" and settings.get("engine", "auto") in ("cached-fixed", "cached-free"):
        errors.append("Cached engines require precomputed PDFs")
    for key, default in (("gamma_grid_step", .1), ("event_selection_angle_deg", 10.), ("ns_max", 1000.)):
        if not finite(settings.get(key, default)) or settings.get(key, default) <= 0:
            errors.append(key + " must be finite and positive")
    if finite(settings.get("ns_max", 1000.)) and settings.get("ns_max", 1000.) < 1:
        errors.append("ns_max must include the preserved ns_seed=1")
    if finite(settings.get("event_selection_angle_deg", 10.)) and settings.get("event_selection_angle_deg", 10.) > 180:
        errors.append("event_selection_angle_deg must not exceed 180")
    tolerance = settings.get("tail_tolerance", 1e-12)
    if not finite(tolerance) or not 0 < tolerance < 1:
        errors.append("tail_tolerance must be finite and strictly between zero and one")
    if settings.get("profile") == "box" and "tail_tolerance" in settings:
        errors.append("tail_tolerance is only valid for Gaussian time profiles")
    windows, columns = settings.get("windows"), settings.get("window_columns")
    if (windows is None) == (columns is None):
        errors.append("Supply exactly one of windows or window_columns")
    elif columns is not None:
        expected_columns = {"start", "stop"} if settings.get("profile") == "box" else {"center", "sigma"}
        if not isinstance(columns, dict) or set(columns) != expected_columns or not all(isinstance(x, str) and x for x in columns.values()):
            errors.append("window_columns must map " + " and ".join(sorted(expected_columns)) + " to catalog column names")
    else:
        if not isinstance(windows, list) or not windows:
            errors.append("windows must be a nonempty list in source input order")
        else:
            for row in windows:
                if settings.get("profile") == "box":
                    invalid = (not isinstance(row, dict) or set(row) != {"name", "start_mjd", "stop_mjd"}
                        or not isinstance(row.get("name"), str) or not row["name"]
                        or not finite(row.get("start_mjd")) or not finite(row.get("stop_mjd"))
                        or row["stop_mjd"] <= row["start_mjd"])
                    message = "Each box window requires a source name and finite start_mjd < stop_mjd"
                else:
                    invalid = (not isinstance(row, dict) or set(row) != {"name", "center_mjd", "sigma_days"}
                        or not isinstance(row.get("name"), str) or not row["name"]
                        or not finite(row.get("center_mjd")) or not finite(row.get("sigma_days"))
                        or row["sigma_days"] <= 0)
                    message = "Each Gaussian profile requires a source name, finite center_mjd and positive sigma_days"
                if invalid:
                    errors.append(message)
    return errors


def parameter_mode(value):
    return value.get("mode", "fixed" if "value" in value else "fitted")


def unavailable_significance():
    return dict(pre_trial_p=None, pre_trial_significance=None, p_value_dof=None,
                p_value_is_estimate=False, p_value_method="unavailable_time_dependent_calibration",
                significance_convention="one_sided_gaussian", significance_calibration="unavailable",
                post_trial_calibration="unavailable")


def apply_catalog_window_defaults(task, root):
    """Resolve new-task defaults without changing explicit or historical settings."""
    from agent_core.agent_orchestrator import build_analysis_payload
    from agent_core.schemas import AnalysisConfig
    from agent_core.normalize import normalize_config
    from analysis_backend.time_dependent.adapter import resolve_windows
    from agent_core.time_dependent_phase_correction import response_uptime, IC86_SEASONS
    from agent_core.file_cache import sha256_file

    settings = task["parameters"]["temporal"]["value"]
    provenance = task.setdefault("temporal_defaults", {})
    if "background_time_model" not in settings:
        settings["background_time_model"] = "uniform_livetime"
        provenance["background_time_model"] = dict(value="uniform_livetime", source="system_default")
    if "datasets" in settings:
        return []
    candidates = ["IC40", "IC59", "IC79", "IC86_I-XI"]
    # Incomplete/invalid profiles remain pending; do not derive phases from them.
    if catalog_window_errors(dict(settings, datasets=candidates)):
        return []
    try:
        normalized = normalize_config(AnalysisConfig.from_dict(build_analysis_payload(task, Path(root))), root)
        windows = resolve_windows(normalized)
        directory = Path(root)/"data_input/IceCube_data_released/2026_icecube_14_year_track_data_IceTracks_DR2/uptime"
        uptime = response_uptime(directory, candidates)
        overlaps = {
            phase: [row["name"] for row in windows if any(
                max(row["start_mjd"], start) < min(row["stop_mjd"], stop)
                for start, stop in uptime[phase])]
            for phase in candidates
        }
        selected = [phase for phase in candidates if overlaps[phase]]
        if not selected:
            return ["No supported detector phase overlaps the supplied fixed profiles"]
        seasons = ["IC40", "IC59", "IC79", *("IC86_" + season for season in IC86_SEASONS)]
        hashes = {str((directory/(season + "_exp.csv")).relative_to(root)):
                  sha256_file(directory/(season + "_exp.csv")) for season in seasons}
        settings["datasets"] = selected
        provenance["datasets"] = dict(value=selected, source="detector_uptime_overlap",
            candidates=candidates, overlapping_sources=overlaps,
            profile_supports=windows, uptime_sha256=hashes)
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        return ["Cannot derive detector phases from fixed profiles: " + str(exc)]
    return []


def configure_temporal_task(task, args, root):
    from agent_core.task_state import parameter, refresh_readiness
    from agent_core.planner import combined_questions
    params = task["parameters"]
    mode = getattr(args, "time_mode", None) or params.get("time_mode", {}).get("value") or (
        "time_dependent" if getattr(args, "temporal_file", None) else "time_integrated")
    params["time_mode"] = parameter(mode, "user" if mode == "time_dependent" else "system_default", True)
    if mode != "time_dependent":
        if getattr(args, "temporal_file", None):
            raise ValueError("--temporal-file requires time-dependent analysis")
        return
    old_errors = task.get("temporal_planning_errors", [])
    task["planning_errors"] = [error for error in task["planning_errors"] if error not in old_errors]
    previous_settings = params.get("temporal", {}).get("value")
    # New requests default to the merged engine. Existing tasks without a scope
    # retain their historical interpretation when confirmed or resumed.
    default_scope = ("per_source_catalog_windows"
        if getattr(args, "command", "").startswith("create-") or previous_settings is None
        else previous_settings.get("scope") if isinstance(previous_settings, dict) else None)
    if getattr(args, "temporal_file", None):
        path = Path(args.temporal_file).expanduser()
        path = path if path.is_absolute() else Path(root)/path
        settings = json.loads(path.read_text())
        if isinstance(settings, dict) and settings.get("scope") is None and default_scope:
            settings["scope"] = default_scope
        params["temporal"] = parameter(settings, "user", True)
        from agent_core.file_cache import sha256_file
        task["temporal_input"] = dict(file=str(path.resolve()), sha256=sha256_file(path))
    elif previous_settings is None and default_scope:
        params["temporal"] = parameter({"scope": default_scope}, "system_default", True)
    settings = params.get("temporal", {}).get("value")
    default_errors = []
    if isinstance(settings, dict) and settings.get("scope") == "per_source_catalog_windows":
        if getattr(args, "command", "").startswith("create-"):
            task["temporal_defaults_policy"] = "overlapping_response_phases_v1"
        if task.get("temporal_defaults_policy") == "overlapping_response_phases_v1":
            if getattr(args, "temporal_file", None):
                task.pop("temporal_defaults", None)
            # Request construction needs the scope-specific procedure even during planning.
            params["fit_procedure"] = parameter("catalog_continuous_profile_v1", "catalog_window_engine", True)
            default_errors = apply_catalog_window_defaults(task, root)
    errors = temporal_errors(settings) + default_errors
    if params.get("data_sample", {}).get("value") != "icecube_public_ps_14yr_dr2":
        errors.append("Time-dependent analysis currently requires DR2")
    catalog_windows = isinstance(settings, dict) and settings.get("scope") == "per_source_catalog_windows"
    if catalog_windows:
        params["fit_procedure"] = parameter("catalog_continuous_profile_v1", "catalog_window_engine", True)
        params["signal_energy_gamma_interpolation"] = parameter("linear_v1", "catalog_window_engine", True)
        if task["workflow"] != "single_source" and params["catalog_operation"]["value"] in {"scan", "scan_and_stack"}:
            params["scan_fit_procedure"] = parameter("catalog_continuous_profile_v1", "catalog_window_engine", True)
        if params.get("likelihood_mode", {}).get("value") != "spatial_energy" or params.get("spectrum", {}).get("value"):
            errors.append("Catalog-window engine currently requires spatial+energy with a power-law spectrum")
        if any(getattr(args, key, None) is not None for key in ("source_dec_window_deg", "event_abs_dec_max_deg", "event_dec_min_deg", "event_dec_max_deg")):
            errors.append("Catalog-window event selection is set by temporal.event_selection_angle_deg; additional declination cuts are unsupported")
        params["source_dec_window_deg"] = parameter(None, "catalog_window_selection", True)
    if not catalog_windows and task["workflow"] != "single_source" and params["catalog_operation"]["value"] != "scan":
        errors.append("Legacy Gaussian/box time searches support catalog_operation=scan only; use per_source_catalog_windows for stacking and shared trials")
    if not catalog_windows:
        for name in ("fit_procedure", "scan_fit_procedure"):
            if params.get(name, {}).get("value") == "catalog_continuous_profile_v1":
                params[name] = parameter("skyllh_lbfgs_v1", "global_profile_engine", True)
    if getattr(args, "flux_upper_limits", None) is True:
        errors.append("Time-dependent flux products are not supported")
    for name, value in (("flux_upper_limit_cl", None), ("flux_upper_limit_gammas", []),
                        ("flux_measurement_ts_threshold", None), ("stacking_flux", {})):
        params[name] = parameter(value, "not_applicable_to_time_dependent", True)
    task["temporal_planning_errors"] = errors
    task["planning_errors"].extend(errors)
    task["questions"] = combined_questions(task, task["planning_errors"])
    task["planned_tools"] = ["run_agent_wrap.py run", "run_agent_wrap.py review-run"]
    refresh_readiness(task)
    if catalog_windows and task.get("status") == "READY":
        # Resolve catalog columns, weights, and window identity before execution.
        from agent_core.agent_orchestrator import build_analysis_payload
        from agent_core.schemas import AnalysisConfig
        from agent_core.validate import validate_config
        validation = validate_config(AnalysisConfig.from_dict(build_analysis_payload(task, Path(root))), root)
        if validation.errors:
            task["temporal_planning_errors"].extend(validation.errors)
            task["planning_errors"].extend(validation.errors)
            task["questions"] = combined_questions(task, task["planning_errors"])
            refresh_readiness(task)
