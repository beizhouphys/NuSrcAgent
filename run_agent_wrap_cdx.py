from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent_core_cdx.agent_orchestrator_cdx import execute_task, resume_interrupted_task
from agent_core_cdx.catalog_inspector_cdx import inspect_catalog
from agent_core_cdx.planner_cdx import plan_catalog_task, plan_single_task, revalidate_task_plan
from agent_core_cdx.review_cdx import review_run
from agent_core_cdx.task_state_cdx import confirm_parameters, load_task, save_task


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root).expanduser().resolve()
    try:
        if args.command == "inspect-catalog":
            result = inspect_catalog(args.catalog, args.name_column, args.ra_column, args.dec_column, args.weight_column)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 2 if result.get("status") == "fail" else 0
        if args.command == "review-run":
            result = review_run(args.run_directory, repo_root, write_artifacts=not args.no_write)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 2 if result.get("status") == "fail" else 0
        if args.command == "create-single":
            task = plan_single_task(args.request, args.name, args.ra_deg, args.dec_deg, args.gamma)
            path = save_task(task, repo_root)
        elif args.command == "create-catalog":
            sources = None if args.source is None else [parse_source(value) for value in args.source]
            manual_weights = parse_weights(args.weights)
            task = plan_catalog_task(args.request, repo_root, args.catalog, sources, args.name_column, args.ra_column, args.dec_column, args.gamma, args.weight_mode, args.weight_column, args.weight_meaning, manual_weights, not args.no_uniform_baseline)
            path = save_task(task, repo_root)
        else:
            task, path = load_task(args.task, repo_root)
            if args.command == "confirm":
                values = confirmation_values(args)
                confirm_parameters(task, values)
                revalidate_task_plan(task, repo_root)
                save_task(task, repo_root, path)
            elif args.command == "run":
                task = execute_task(task, path, repo_root, backend=args.backend, max_safe_retries=args.max_safe_retries)
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Persistent, auditable wrapper for HE-neutrino analysis tasks.")
    parser.add_argument("--repo-root", default=".")
    subparsers = parser.add_subparsers(dest="command", required=True)

    single = subparsers.add_parser("create-single", help="Create a one-source task from a Codex-interpreted request.")
    single.add_argument("--request", required=True, help="Original natural-language request for the audit record.")
    single.add_argument("--name", default="source_0001")
    single.add_argument("--ra-deg", required=True, type=float)
    single.add_argument("--dec-deg", required=True, type=float)
    single.add_argument("--gamma", type=float, help="Omit when the user has not specified gamma.")

    catalog = subparsers.add_parser("create-catalog", help="Create a multi-source or catalog task from a Codex-interpreted request.")
    catalog.add_argument("--request", required=True, help="Original natural-language request for the audit record.")
    inputs = catalog.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--catalog")
    inputs.add_argument("--source", action="append", help="name,ra_deg,dec_deg; repeat for each source")
    catalog.add_argument("--name-column")
    catalog.add_argument("--ra-column")
    catalog.add_argument("--dec-column")
    catalog.add_argument("--gamma", type=float)
    catalog.add_argument("--weight-mode", choices=["uniform", "column", "manual"])
    catalog.add_argument("--weight-column")
    catalog.add_argument("--weight-meaning")
    catalog.add_argument("--weights", help="Comma-separated manual weights")
    catalog.add_argument("--no-uniform-baseline", action="store_true")

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
    run.add_argument("--backend", choices=["likelihood", "mock"], default="likelihood")
    run.add_argument("--max-safe-retries", type=int, choices=[0, 1], default=1)

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
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
