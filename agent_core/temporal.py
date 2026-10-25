"""Explicit time-search settings shared by planning, validation and runtime."""
from __future__ import annotations

import math
import json
from pathlib import Path


def temporal_errors(settings):
    if not isinstance(settings, dict) or not settings:
        return ["Time-dependent analysis requires explicit temporal settings"]
    errors = []
    allowed = {"profile", "time_format", "time_scale", "background_time_model",
               "t0", "width", "search"}
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


def parameter_mode(value):
    return value.get("mode", "fixed" if "value" in value else "fitted")


def unavailable_significance():
    return dict(pre_trial_p=None, pre_trial_significance=None, p_value_dof=None,
                p_value_is_estimate=False, p_value_method="unavailable_time_dependent_calibration",
                significance_convention="one_sided_gaussian", significance_calibration="unavailable",
                post_trial_calibration="unavailable")


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
    if getattr(args, "temporal_file", None):
        path = Path(args.temporal_file).expanduser()
        path = path if path.is_absolute() else Path(root)/path
        settings = json.loads(path.read_text())
        params["temporal"] = parameter(settings, "user", True)
        from agent_core.file_cache import sha256_file
        task["temporal_input"] = dict(file=str(path.resolve()), sha256=sha256_file(path))
    settings = params.get("temporal", {}).get("value")
    errors = temporal_errors(settings)
    if params.get("data_sample", {}).get("value") != "icecube_public_ps_14yr_dr2":
        errors.append("Time-dependent analysis currently requires DR2")
    if task["workflow"] != "single_source" and params["catalog_operation"]["value"] != "scan":
        errors.append("Time-dependent stacking awaits collaborator code; select catalog_operation=scan")
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
