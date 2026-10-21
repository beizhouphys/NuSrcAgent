from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent_core.cpu import configure_threads, positive_cpu_count

# Set numerical-library limits before importing analysis modules. Spawned scan
# workers keep the single-thread environment inherited from their parent.
if __name__ == "__main__" and "run" in sys.argv[1:]:
    _cpu_parser = argparse.ArgumentParser(add_help=False)
    _cpu_parser.add_argument("--cpus", type=positive_cpu_count, default=1)
    _cpu_options, _ = _cpu_parser.parse_known_args()
    configure_threads(_cpu_options.cpus)

from agent_core.progress import timed_command, print_result
from analysis_backend.sources import BUILTIN_CATALOG_NAMES
from agent_core.agent_orchestrator import execute_task, resume_interrupted_task
from agent_core.single_source_stages import configure_single_source_stages, execute_single_source_stage
from agent_core.catalog_inspector import inspect_catalog
from agent_core.environment import check_environment
from agent_core.planner import plan_catalog_task, plan_single_task, revalidate_task_plan
from agent_core.review import review_run
from agent_core.task_state import confirm_parameters, load_task, save_task


@timed_command
def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root).expanduser().resolve()
    try:
        if args.command == "install-inputs":
            from agent_core.input_install import install_inputs
            result = install_inputs(repo_root, args.data_sample, args.likelihood_mode,
                                    args.bundle_dir, args.base_url)
            print_result(result)
            return 0
        if args.command == "dr2-empirical-scramble":
            from agent_core.dr2_empirical_scramble import (
                aggregate_distributed_shards, launch_continuous, merge_host_shards, prepare,
                prepare_continuous, prepare_distributed_shard, prepare_versioned_continuous,
                report, request_stop, run, run_continuous, snapshot,
            )
            if args.action in ("prepare", "prepare-continuous", "prepare-versioned", "prepare-shard",
                               "run", "resume", "launch"):
                if check_environment(repo_root, "icecube_public_ps_14yr_dr2", "spatial_energy")["status"] == "fail":
                    raise ValueError("DR2 preflight failed")
            if args.action == "prepare":
                result = prepare(repo_root, args.output_directory, args.request, args.n_trials,
                                 args.n_sources, args.seed, args.workers)
            elif args.action == "prepare-continuous":
                result = prepare_continuous(repo_root, args.output_directory, args.parent_directory,
                                            args.request, args.workers)
            elif args.action == "prepare-versioned":
                result = prepare_versioned_continuous(
                    repo_root, args.output_directory, args.parent_directory, args.request,
                    args.background_pdf_version, args.analysis_alias, args.workers,
                    args.import_reference_fits,
                )
            elif args.action == "prepare-shard":
                result = prepare_distributed_shard(
                    repo_root, args.output_directory, args.parent_directory, args.request,
                    args.analysis_alias, args.shard_id, args.shard_number, args.workers,
                )
            elif args.action == "aggregate-shards":
                result = aggregate_distributed_shards(
                    repo_root, args.analysis_alias, args.output_directory,
                )
            elif args.action == "merge-shards":
                result = merge_host_shards(repo_root, args.output_directory, args.analysis_alias, args.shard_id,
                                           args.incoming_shard_id, args.request)
            elif args.action in ("launch", "resume"):
                task = json.loads((Path(args.output_directory)/"task.json").read_text())
                if task["parameters"]["experiment"]["value"].get("continuous"):
                    result = launch_continuous(repo_root, args.output_directory)
                else:
                    result = run(repo_root, args.output_directory, resume=args.action == "resume",
                                 max_hours=args.max_hours, max_fits=args.max_fits)
            elif args.action in ("run", "resume"):
                task = json.loads((Path(args.output_directory)/"task.json").read_text())
                result = (run_continuous(repo_root, args.output_directory)
                          if task["parameters"]["experiment"]["value"].get("continuous")
                          else run(repo_root, args.output_directory, resume=False,
                                   max_hours=args.max_hours, max_fits=args.max_fits))
            elif args.action == "stop":
                result = request_stop(args.output_directory)
            elif args.action in ("status", "snapshot"):
                result = snapshot(args.output_directory)
            else:
                result = report(args.output_directory)
            print_result(result)
            return 2 if result.get("status") == "FAILED" else 0
        if args.command == "environment-check":
            result = check_environment(repo_root, args.data_sample, args.likelihood_mode)
            print_result(result)
            return 2 if result.get("status") == "fail" else 0
        if args.command == "inspect-catalog":
            result = inspect_catalog(args.catalog, args.name_column, args.ra_column, args.dec_column, args.weight_column)
            print_result(result)
            return 2 if result.get("status") == "fail" else 0
        if args.command == "review-run":
            result = review_run(args.run_directory, repo_root, write_artifacts=not args.no_write)
            print_result(result)
            return 2 if result.get("status") == "fail" else 0
        if args.command == "dominance":
            from analysis_backend.skyllh_dr2_dominance import run_dominance_analysis
            result = run_dominance_analysis(repo_root, args.baseline_run_directory, args.output_directory, args.request, args.candidate_count, args.top_n)
            print_result(result)
            return 0 if result.get("status") == "COMPLETED" else 2
        if args.command == "review-dominance":
            from analysis_backend.skyllh_dr2_dominance import review_dominance_analysis
            result = review_dominance_analysis(repo_root, args.output_directory)
            print_result(result)
            return 2 if result.get("status") == "fail" else 0
        if args.command == "dr2-ra-scramble":
            from analysis_backend.skyllh_dr2_ra_scramble import run_dr2_ra_scramble_diagnostic
            seeds = [int(value.strip()) for value in args.seeds.split(",") if value.strip()]
            result = run_dr2_ra_scramble_diagnostic(repo_root, args.baseline_run_directory, args.output_directory, seeds)
            print_result(result)
            return 0 if result.get("status") == "COMPLETED_WITH_WARNINGS" else 2
        if args.command == "create-single":
            likelihood_mode = args.likelihood_mode or ("spatial_energy" if args.data_sample == "icecube_public_ps_14yr_dr2" else "spatial_only")
            gamma_mode = args.gamma_mode or ("fitted" if likelihood_mode == "spatial_energy" and args.data_sample == "icecube_public_ps_14yr_dr2" else "fixed")
            gamma = default_gamma(args.gamma, args.data_sample, likelihood_mode, gamma_mode)
            task = plan_single_task(args.request, args.name, args.ra_deg, args.dec_deg, gamma, args.data_sample, gamma_mode, likelihood_mode, args.event_abs_dec_max_deg, args.event_dec_min_deg, args.event_dec_max_deg)
            if args.gamma_mode is not None:
                task["parameters"]["gamma_mode"]["source"] = "user"
            set_mode_parameter_sources(task, args, likelihood_mode, gamma_mode)
            set_source_window(task, args)
            set_flux_upper_limits(task, args)
            set_flux_measurement(task, args)
            configure_single_source_stages(task)

            path = save_task(task, repo_root)
        elif args.command == "create-catalog":
            sources = None if args.source is None else [parse_source(value) for value in args.source]
            manual_weights = parse_weights(args.weights)
            likelihood_mode = args.likelihood_mode or ("spatial_energy" if args.data_sample == "icecube_public_ps_14yr_dr2" else "spatial_only")
            gamma_mode = args.gamma_mode or ("fitted" if likelihood_mode == "spatial_energy" and args.data_sample == "icecube_public_ps_14yr_dr2" else "fixed")
            gamma = default_gamma(args.gamma, args.data_sample, likelihood_mode, gamma_mode)
            include_uniform_baseline = False if args.data_sample == "icecube_public_ps_14yr_dr2" else not args.no_uniform_baseline
            task = plan_catalog_task(args.request, repo_root, args.catalog, sources, args.name_column, args.ra_column, args.dec_column, gamma, args.weight_mode, args.weight_column, args.weight_meaning, manual_weights, include_uniform_baseline, args.data_sample, gamma_mode, likelihood_mode, args.built_in_catalog, args.event_abs_dec_max_deg, args.event_dec_min_deg, args.event_dec_max_deg, args.catalog_operation)
            if args.gamma_mode is not None:
                task["parameters"]["gamma_mode"]["source"] = "user"
            set_mode_parameter_sources(task, args, likelihood_mode, gamma_mode)
            set_source_window(task, args)
            set_flux_upper_limits(task, args)
            set_flux_measurement(task, args)
            configure_single_source_stages(task)
            set_scan_fit_procedure(task, args)
            set_stacking_flux(task, args)

            path = save_task(task, repo_root)
        else:
            task, path = load_task(args.task, repo_root)
            if args.command == "confirm":
                values = confirmation_values(args)
                confirm_parameters(task, values)
                revalidate_task_plan(task, repo_root)
                save_task(task, repo_root, path)
            elif args.command == "run":
                if args.flux_user_reply is not None and args.stage != "flux":
                    raise ValueError("--flux-user-reply is only valid with --stage flux after the primary final answer")
                if args.stage == "flux" and task.get("execution_flow") == "single_source_two_stage_v1":
                    task = execute_single_source_stage(task, path, repo_root, "flux", args.max_safe_retries, user_reply=args.flux_user_reply, cpus=args.cpus)
                elif args.stage == "flux":
                    from agent_core.stacking_stages import execute_flux_stage
                    task = execute_flux_stage(task, path, repo_root, backend=args.backend, max_safe_retries=args.max_safe_retries, user_reply=args.flux_user_reply, cpus=args.cpus)
                else:
                    task = execute_task(task, path, repo_root, backend=args.backend, max_safe_retries=args.max_safe_retries, cpus=args.cpus)
            elif args.command == "resume":
                resume_interrupted_task(task)
                save_task(task, repo_root, path)
            elif args.command != "show":
                raise ValueError("unknown command")
        print_task(task, path)
        return 2 if task.get("status") == "FAILED" else 0
    except (ValueError, OSError, KeyError) as exc:
        print("AGENT WRAP ERROR: %s" % exc, file=sys.stderr)
        return 2


def set_scan_fit_procedure(task, args):
    """Pin new individual catalog fits independently of single/stack defaults."""
    from agent_core.task_state import parameter
    operation = task["parameters"].get("catalog_operation", {}).get("value")
    if (args.data_sample == "icecube_public_ps_14yr_dr2"
            and task["workflow"] != "single_source" and operation in {"scan", "scan_and_stack"}):
        task["parameters"]["scan_fit_procedure"] = parameter("skyllh_lbfgs_v1", "system_default", True)
        task["parameters"]["scan_fit_procedure"]["basis"] = (
            "Owner restored the original SkyLLH optimizer for individual catalog fits on 2026-10-19; "
            "omit the additional Gamma interval/stencil-switch search. The joint stack retains its own procedure.")


def set_stacking_flux(task, args):
    from agent_core.task_state import parameter
    if (args.data_sample == "icecube_public_ps_14yr_dr2" and task["workflow"] != "single_source"
            and task["parameters"]["likelihood_mode"]["value"] == "spatial_energy"
            and task["parameters"].get("catalog_operation", {}).get("value") in {"stack", "scan_and_stack"}):
        enabled = args.flux_upper_limits is not False
        settings = dict(upper_limit_cl=0.95 if enabled else None,
            upper_limit_gammas=[-2., -2.5, -3.] if enabled else [],
            measurement_ts_threshold=9., reporting="two_stage",
            display_quantity="full_sky_average_intensity")
        task["parameters"]["stacking_flux"] = parameter(settings, "system_default", True)
        task["parameters"]["stacking_flux"]["basis"] = "Owner-approved separate primary chat output, then fixed-spectrum 95% limits and strict TS > 9 intensity measurement; catalog total flux / (4*pi sr)."


def set_flux_upper_limits(task, args):
    from agent_core.task_state import parameter
    enabled = args.flux_upper_limits
    applicable = (args.data_sample == "icecube_public_ps_14yr_dr2"
                  and task["parameters"]["likelihood_mode"]["value"] == "spatial_energy"
                  and (task["workflow"] == "single_source"
                       or task["parameters"].get("catalog_operation", {}).get("value") in {"scan", "scan_and_stack"}))
    stack_only = (task["workflow"] != "single_source"
                  and task["parameters"].get("catalog_operation", {}).get("value") == "stack"
                  and args.data_sample == "icecube_public_ps_14yr_dr2"
                  and task["parameters"]["likelihood_mode"]["value"] == "spatial_energy")
    if stack_only:
        enabled = False
    if enabled is True and not applicable:
        raise ValueError("Flux upper limits require DR2 spatial+energy single-source or catalog-scan analysis")
    if enabled is None:
        enabled = applicable and task["workflow"] == "single_source"
    source = "user" if args.flux_upper_limits is not None else "system_default"
    task["parameters"]["flux_upper_limit_cl"] = parameter(0.95 if enabled else None, source, True)
    task["parameters"]["flux_upper_limit_gammas"] = parameter([-2.0, -2.5, -3.0] if enabled else [], source, True)
    if enabled:
        task["parameters"]["flux_upper_limit_gammas"]["basis"] = "Owner-approved separate fixed E^-2, E^-2.5 and E^-3 spectra; one-sided asymptotic 95% limits and reference-spectrum plot."


def set_flux_measurement(task, args):
    """Record the approved single-source procedure only for newly created tasks."""
    from agent_core.task_state import parameter
    if (task["workflow"] != "single_source" or args.data_sample != "icecube_public_ps_14yr_dr2"
            or task["parameters"]["likelihood_mode"]["value"] != "spatial_energy"
            or task.get("intent") == "gaussian_score_diagnostic"):
        return
    task["parameters"]["fit_procedure"] = parameter("skyllh_lbfgs_v1", "system_default", True)
    task["parameters"]["fit_procedure"]["basis"] = "Owner requested the original SkyLLH optimizer for all fits; likelihood, PDFs and bounds retained. Corresponding trials must use the same recorded procedure."
    task["parameters"]["signal_energy_gamma_interpolation"] = parameter("linear_v1", "system_default", True)
    task["parameters"]["signal_energy_gamma_interpolation"]["basis"] = "Owner-approved two-node linear Gamma interpolation for standalone single-source primary and flux fits; catalog scans and joint stacks retain their existing procedure."
    task["parameters"]["flux_measurement_ts_threshold"] = parameter(9.0, "system_default", True)
    task["parameters"]["flux_measurement_ts_threshold"]["basis"] = "Owner-approved strict TS > 9 criterion for reporting primary-spectrum flux measurement, profile intervals and free-Gamma joint contours."


def set_source_window(task, args):
    """Record the owner-approved default only on newly created individual fits."""
    from agent_core.task_state import parameter
    import math
    explicit = args.source_dec_window_deg
    cuts = any(value is not None for value in (args.event_abs_dec_max_deg, args.event_dec_min_deg, args.event_dec_max_deg))
    operation = task["parameters"].get("catalog_operation", {}).get("value", "stack")
    applicable = args.data_sample == "icecube_public_ps_14yr_dr2" and (task["workflow"] == "single_source" or operation in ("scan", "scan_and_stack"))
    if explicit is not None and (not applicable or cuts or not math.isfinite(explicit) or not 20.0 <= explicit <= 180.0):
        raise ValueError("--source-dec-window-deg requires an individual DR2 fit, no explicit cuts, and a finite half-width in [20, 180]")
    if args.full_sky_events and cuts:
        raise ValueError("--full-sky-events cannot be combined with event declination cuts")
    value = (20.0 if explicit is None else explicit) if applicable and not cuts and not args.full_sky_events else None
    task["parameters"]["source_dec_window_deg"] = parameter(value, "user" if explicit is not None or args.full_sky_events else "system_default", True)
    if value is not None:
        task["parameters"]["source_dec_window_deg"]["basis"] = "Owner-approved source-centered Dec window: minimum half-width >=20 deg, retaining >=20% of each dataset; background spatial PDF integral normalization."


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Persistent, auditable wrapper for HE-neutrino analysis tasks.")
    parser.add_argument("--repo-root", default=".")
    subparsers = parser.add_subparsers(dest="command", required=True)

    install = subparsers.add_parser("install-inputs", help="Download/extract the fixed project-provided IceCube and frozen PDF bundles and verify hashes.")
    install.add_argument("--data-sample", choices=["icecube_public_ps_14yr_dr2", "icecube_public_ps_10yr"], default="icecube_public_ps_14yr_dr2")
    install.add_argument("--likelihood-mode", choices=["spatial_energy", "spatial_only"])
    source = install.add_mutually_exclusive_group()
    source.add_argument("--bundle-dir", help="Use local asset files instead of downloading")
    source.add_argument("--base-url", help="Explicit HTTPS mirror for the same hash-pinned bundle filenames")

    empirical = subparsers.add_parser("dr2-empirical-scramble", help="Conditional event-RA calibration with fitted ns and Gamma; checkpointed fixed-N or continuous ensemble.")
    empirical.add_argument("--action", choices=["prepare", "prepare-continuous", "prepare-versioned",
                                                "prepare-shard", "aggregate-shards", "merge-shards", "run", "launch",
                                                "resume", "report", "status", "snapshot", "stop"], required=True)
    empirical.add_argument("--output-directory", required=True)
    empirical.add_argument("--parent-directory", help="Paused timing-pilot directory imported by prepare-continuous.")
    empirical.add_argument("--background-pdf-version", choices=["v3"], default="v3")
    empirical.add_argument("--analysis-alias", default="")
    empirical.add_argument("--shard-id", default="")
    empirical.add_argument("--incoming-shard-id", default="")
    empirical.add_argument("--shard-number", type=int)
    empirical.add_argument("--import-reference-fits", action="store_true")
    empirical.add_argument("--request", default="")
    empirical.add_argument("--n-trials", type=int, default=100)
    empirical.add_argument("--n-sources", type=int, default=1000)
    empirical.add_argument("--seed", type=int, default=2026091501)
    empirical.add_argument("--workers", type=int, default=2)
    empirical.add_argument("--max-hours", type=float, default=2.)
    empirical.add_argument("--max-fits", type=int, help="Operational fit limit for timing pilot; no partial-ensemble p-value is reported.")










    environment = subparsers.add_parser("environment-check", help="Check the pinned runtime and selected sample data.")
    environment.add_argument("--data-sample", choices=["icecube_public_ps_14yr_dr2", "icecube_public_ps_10yr"], default="icecube_public_ps_14yr_dr2")
    environment.add_argument("--likelihood-mode", choices=["spatial_energy", "spatial_only"])

    single = subparsers.add_parser("create-single", help="Create a one-source task from a Codex-interpreted request.")
    single.add_argument("--request", required=True, help="Original natural-language request for the audit record.")
    single.add_argument("--name", default="source_0001")
    single.add_argument("--ra-deg", required=True, type=float)
    single.add_argument("--dec-deg", required=True, type=float)
    single.add_argument("--gamma", type=float, help="Omit when the user has not specified gamma.")
    single.add_argument("--gamma-mode", choices=["fitted", "fixed"])
    single.add_argument("--interpretation-note", action="append", default=[], metavar="PARAMETER=EXPLANATION", help="Record an agent interpretation under the approved clarification policy; metadata only.")
    single.add_argument("--likelihood-mode", choices=["spatial_energy", "spatial_only"])
    single.add_argument("--data-sample", choices=["icecube_public_ps_14yr_dr2", "icecube_public_ps_10yr"], default="icecube_public_ps_14yr_dr2")
    single_limits = single.add_mutually_exclusive_group()
    single_limits.add_argument("--flux-upper-limits", dest="flux_upper_limits", action="store_true", default=None, help="Compute 95%% limits for E^-2, E^-2.5, E^-3 and plot reference spectra; default for DR2 spatial+energy single sources, opt-in for scans.")
    single_limits.add_argument("--no-flux-upper-limits", dest="flux_upper_limits", action="store_false", help="Skip the additional fixed-spectrum upper-limit fits and plots.")
    single_window = single.add_mutually_exclusive_group()
    single_window.add_argument("--source-dec-window-deg", type=float, help="Minimum source-centered Dec half-width >=20 deg; expands to retain >=20%% of every DR2 dataset.")
    single_window.add_argument("--full-sky-events", action="store_true", help="Use all events for individual DR2 fits instead of the default adaptive source window.")
    single.add_argument("--event-abs-dec-max-deg", type=float, help="Keep events with |Dec| below this value and condition the background spatial PDF to that region.")
    single.add_argument("--event-dec-min-deg", type=float, help="Inclusive lower event-declination bound in degrees; conditions the background spatial PDF to the selected region.")
    single.add_argument("--event-dec-max-deg", type=float, help="Inclusive upper event-declination bound in degrees; conditions the background spatial PDF to the selected region.")

    catalog = subparsers.add_parser("create-catalog", help="Create a multi-source or catalog task from a Codex-interpreted request.")
    catalog.add_argument("--catalog-operation", choices=["stack", "scan", "scan_and_stack"], help="DR2: stacking, independent single-source fits, or both. Default: stack. DR1 retains scan_and_stack.")
    catalog.add_argument("--request", required=True, help="Original natural-language request for the audit record.")
    inputs = catalog.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--catalog")
    inputs.add_argument("--built-in-catalog", choices=BUILTIN_CATALOG_NAMES)
    inputs.add_argument("--source", action="append", help="name,ra_deg,dec_deg; repeat for each source")
    catalog.add_argument("--name-column")
    catalog.add_argument("--ra-column")
    catalog.add_argument("--dec-column")
    catalog.add_argument("--gamma", type=float)
    catalog.add_argument("--gamma-mode", choices=["fitted", "fixed"])
    catalog.add_argument("--interpretation-note", action="append", default=[], metavar="PARAMETER=EXPLANATION", help="Record an agent interpretation under the approved clarification policy; metadata only.")
    catalog.add_argument("--likelihood-mode", choices=["spatial_energy", "spatial_only"])
    catalog.add_argument("--data-sample", choices=["icecube_public_ps_14yr_dr2", "icecube_public_ps_10yr"], default="icecube_public_ps_14yr_dr2")
    catalog_limits = catalog.add_mutually_exclusive_group()
    catalog_limits.add_argument("--flux-upper-limits", dest="flux_upper_limits", action="store_true", default=None, help="Compute 95%% limits for E^-2, E^-2.5, E^-3 and plot reference spectra; default for DR2 spatial+energy single sources, opt-in for scans.")
    catalog_limits.add_argument("--no-flux-upper-limits", dest="flux_upper_limits", action="store_false", help="Skip the additional fixed-spectrum upper-limit fits and plots.")
    catalog.add_argument("--weight-mode", choices=["uniform", "column", "manual"])
    catalog.add_argument("--weight-column")
    catalog.add_argument("--weight-meaning")
    catalog.add_argument("--weights", help="Comma-separated manual weights")
    catalog.add_argument("--no-uniform-baseline", action="store_true")
    catalog_window = catalog.add_mutually_exclusive_group()
    catalog_window.add_argument("--source-dec-window-deg", type=float, help="Minimum source-centered Dec half-width >=20 deg; expands to retain >=20%% of every DR2 dataset.")
    catalog_window.add_argument("--full-sky-events", action="store_true", help="Use all events for individual DR2 fits instead of the default adaptive source window.")
    catalog.add_argument("--event-abs-dec-max-deg", type=float, help="Keep events with |Dec| below this value and condition the background spatial PDF to that region.")
    catalog.add_argument("--event-dec-min-deg", type=float, help="Inclusive lower event-declination bound in degrees; conditions the background spatial PDF to the selected region.")
    catalog.add_argument("--event-dec-max-deg", type=float, help="Inclusive upper event-declination bound in degrees; conditions the background spatial PDF to the selected region.")

    confirm = subparsers.add_parser("confirm", help="Record user-confirmed scientific parameters.")
    confirm.add_argument("--task", required=True)
    confirm.add_argument("--gamma", type=float)
    confirm.add_argument("--weight-mode", choices=["uniform", "column", "manual"])
    confirm.add_argument("--weight-column")
    confirm.add_argument("--weight-meaning")
    confirm.add_argument("--weights")
    confirm.add_argument("--name-column")
    confirm.add_argument("--ra-column")
    confirm.add_argument("--dec-column")
    baseline = confirm.add_mutually_exclusive_group()
    baseline.add_argument("--uniform-baseline", action="store_true")
    baseline.add_argument("--no-uniform-baseline", action="store_true")

    run = subparsers.add_parser("run", help="Execute a READY task and enforce its completion gate.")
    run.add_argument("--task", required=True)
    run.add_argument("--stage", choices=["primary", "flux"], help="New single-source tasks and DR2 stacks return the primary fit first; report it in a final answer and wait for the user reply before --stage flux.")
    run.add_argument("--flux-user-reply", help="Actual user reply authorizing flux continuation after the primary final answer; required for --stage flux.")
    run.add_argument("--backend", choices=["likelihood"], default="likelihood")
    run.add_argument("--max-safe-retries", type=int, choices=[0, 1], default=1)
    run.add_argument("--cpus", type=positive_cpu_count, default=1,
                     help="CPU budget: DR2 source scans use single-thread workers; single-source and joint stacking fits use numerical thread limits. Default: 1.")

    show = subparsers.add_parser("show", help="Show the persisted task state.")
    show.add_argument("--task", required=True)
    resume = subparsers.add_parser("resume", help="Explicitly resume an interrupted RUNNING/REVIEWING task.")
    resume.add_argument("--task", required=True)

    inspect_parser = subparsers.add_parser("inspect-catalog", help="Inspect catalog columns, coordinates, and candidate weights.")
    inspect_parser.add_argument("--catalog", required=True)
    inspect_parser.add_argument("--name-column")
    inspect_parser.add_argument("--ra-column")
    inspect_parser.add_argument("--dec-column")
    inspect_parser.add_argument("--weight-column")

    review_parser = subparsers.add_parser("review-run", help="Review a completed analysis run and write review artifacts.")
    review_parser.add_argument("--run-directory", required=True)
    review_parser.add_argument("--no-write", action="store_true")
    dominance = subparsers.add_parser("dominance", help="Run checkpointed delete-one and cumulative source-dominance diagnostics for a completed DR2 stack.")
    dominance.add_argument("--request", required=True)
    dominance.add_argument("--baseline-run-directory", required=True)
    dominance.add_argument("--output-directory", required=True)
    dominance.add_argument("--candidate-count", type=int, default=15)
    dominance.add_argument("--top-n", type=int, default=10)
    dominance_review = subparsers.add_parser("review-dominance", help="Review a completed DR2 source-dominance analysis.")
    dominance_review.add_argument("--output-directory", required=True)
    ra_scramble = subparsers.add_parser("dr2-ra-scramble", help="Run checkpointed source/event RA-scramble diagnostics for a completed fitted-Gamma DR2 stack.")
    ra_scramble.add_argument("--baseline-run-directory", required=True)
    ra_scramble.add_argument("--output-directory", required=True)
    ra_scramble.add_argument("--seeds", default="104729,130363,155921", help="Comma-separated unique non-negative integer trial seeds.")
    return parser


def confirmation_values(args: argparse.Namespace) -> Dict[str, Any]:
    values = {
        "gamma": args.gamma,
        "weight_mode": args.weight_mode,
        "weight_column": args.weight_column,
        "weight_meaning": args.weight_meaning,
        "manual_weights": parse_weights(args.weights),
        "name_column": args.name_column,
        "ra_column": args.ra_column,
        "dec_column": args.dec_column,
    }
    if args.uniform_baseline:
        values["include_uniform_baseline"] = True
    elif args.no_uniform_baseline:
        values["include_uniform_baseline"] = False
    return {key: value for key, value in values.items() if value is not None}


def parse_source(value: str) -> Dict[str, Any]:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 3:
        raise ValueError("--source must have the form name,ra_deg,dec_deg")
    return {"name": parts[0], "ra_deg": float(parts[1]), "dec_deg": float(parts[2])}


def parse_weights(value: Optional[str]) -> Optional[List[float]]:
    return None if value is None else [float(item.strip()) for item in value.split(",")]


def default_gamma(value: Optional[float], data_sample: str, likelihood_mode: str, gamma_mode: str) -> Optional[float]:
    if value is not None:
        return value
    if data_sample == "icecube_public_ps_14yr_dr2" and likelihood_mode == "spatial_only":
        return -2.5
    if data_sample == "icecube_public_ps_14yr_dr2" and gamma_mode == "fitted":
        return -3.0
    return None


def set_mode_parameter_sources(task: Dict[str, Any], args: argparse.Namespace, likelihood_mode: str, gamma_mode: str) -> None:
    if args.likelihood_mode is not None:
        task["parameters"]["likelihood_mode"]["source"] = "user"
    if args.gamma is None and likelihood_mode == "spatial_only" and args.data_sample == "icecube_public_ps_14yr_dr2":
        task["parameters"]["gamma"]["source"] = "system_default_acceptance_gamma"
    elif args.gamma is None and gamma_mode == "fitted":
        task["parameters"]["gamma"]["source"] = "system_default_fit_seed"
    for note in getattr(args, "interpretation_note", []) or []:
        name, separator, explanation = note.partition("=")
        if not separator or name not in {"gamma", "gamma_mode", "weight_column", "weight_meaning"} or name not in task["parameters"] or not explanation.strip():
            raise ValueError("interpretation note must be an available gamma, gamma_mode, weight_column or weight_meaning followed by =EXPLANATION")
        task["parameters"][name]["source"] = "agent_interpreted"
        task["parameters"][name]["interpretation"] = explanation.strip()


def print_task(task: Dict[str, Any], path: Path) -> None:
    summary = {
        "task_file": str(path),
        "task_id": task.get("task_id"),
        "status": task.get("status"),
        "workflow": task.get("workflow"),
        "selection_reason": task.get("selection_reason"),
        "missing_parameters": task.get("missing_parameters", []),
        "questions": task.get("questions", []),
        "planning_errors": task.get("planning_errors", []),
        "completion": task.get("completion", {}),
        "artifacts": task.get("artifacts", {}),
    }
    if task.get("status") in {"COMPLETED", "COMPLETED_WITH_WARNINGS"}:
        run_directory = task.get("artifacts", {}).get("run_directory")
        if run_directory:
            from agent_core.simple_yaml import load_simple_yaml
            report_path = Path(run_directory) / "report.yaml"
            if report_path.is_file():
                report_result = load_simple_yaml(report_path.read_text()).get("result", {})
                scan_summary = report_result.get("catalog_scan_summary")
                if scan_summary:
                    from agent_core.catalog_scan_outputs import compact_scan_table
                    summary["catalog_scan_summary"] = dict(scan_summary, chat_table=compact_scan_table(report_result["source_results"]))
    if task.get("stacking_stages"):
        from agent_core.stacking_stages import chat_stages
        summary["stacking_stages"] = chat_stages(task)
    if task.get("execution_flow") == "single_source_two_stage_v1":
        from agent_core.single_source_stages import chat_stages as single_chat_stages
        summary.update(single_chat_stages(task))
    print_result(summary)


if __name__ == "__main__":
    raise SystemExit(main())
