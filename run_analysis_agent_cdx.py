from __future__ import annotations # Codex

import argparse # Codex
import sys # Codex
from datetime import datetime, timezone # Codex
from pathlib import Path # Codex

from agent_core_cdx.analysis_agent_cdx import AnalysisAgent, build_catalog_request, build_single_source_request # Codex
from agent_core_cdx.schemas_cdx import ConfigError # Codex


def main(argv: list[str] | None = None) -> int: # Codex
    parser = build_parser() # Codex
    args = parser.parse_args(argv) # Codex
    repo_root = Path(args.repo_root).resolve() # Codex
    agent = AnalysisAgent(repo_root) # Codex
    try: # Codex
        payload = request_from_args(args) # Codex
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") # Codex
        request_path = agent.prepare_request(payload, f"data_output/agent_requests_cdx/request_{stamp}_cdx.yaml") # Codex
        run = agent.run(request_path, backend=args.backend, prepare_only=args.prepare_only) # Codex
        print(f"Validated request: {request_path}") # Codex
        print(f"Analysis: {run.normalized.analysis_type}; sources: {len(run.normalized.sources)}") # Codex
        if run.run_dir is None: # Codex
            print("Preparation completed; likelihood backend was not run.") # Codex
            return 0 # Codex
        print_summary(run.result) # Codex
        if run.review is not None: # cdx
            print(f"Review status: {run.review['status']}; checks: {len(run.review['checks'])}") # cdx
        print(f"Output directory: {run.run_dir}") # Codex
        workbook = run.run_dir / "analysis_results_cdx.xlsx" # Codex
        if workbook.exists(): # Codex
            print(f"Excel workbook: {workbook}") # Codex
        return 2 if run.review is not None and run.review.get("status") == "fail" else 0 # cdx
    except (ConfigError, ValueError) as exc: # Codex
        print(f"AGENT ERROR: {exc}", file=sys.stderr) # Codex
        return 2 # Codex


def build_parser() -> argparse.ArgumentParser: # Codex
    parser = argparse.ArgumentParser(description="Single-source and catalog-stacking HE-neutrino analysis agent.") # Codex
    parser.add_argument("--repo-root", default=".", help="Repository root.") # Codex
    parser.add_argument("--backend", choices=["likelihood", "mock"], default="likelihood", help="Analysis backend.") # Codex
    parser.add_argument("--prepare-only", action="store_true", help="Generate and validate the request without running the likelihood.") # Codex
    subparsers = parser.add_subparsers(dest="command", required=True) # Codex
    single = subparsers.add_parser("single", help="Analyze one sky coordinate.") # Codex
    single.add_argument("--name", default="source_0001") # Codex
    single.add_argument("--ra-deg", required=True, type=float) # Codex
    single.add_argument("--dec-deg", required=True, type=float) # Codex
    single.add_argument("--gamma", type=float, default=-2.53, help="Negative source spectral index.") # cdx
    catalog = subparsers.add_parser("catalog", help="Scan and stack a catalog or an inline coordinate list.") # Codex
    inputs = catalog.add_mutually_exclusive_group(required=True) # Codex
    inputs.add_argument("--catalog", help="CSV or TSV catalog path containing coordinate columns.") # Codex
    inputs.add_argument("--source", action="append", help="Inline source as name,ra_deg,dec_deg; repeat for each source.") # Codex
    catalog.add_argument("--name-column", default="source_name") # Codex
    catalog.add_argument("--ra-column", default="ra_deg") # Codex
    catalog.add_argument("--dec-column", default="dec_deg") # Codex
    weights = catalog.add_mutually_exclusive_group() # Codex
    weights.add_argument("--weight-column", help="Catalog column used for intrinsic stacking weights.") # Codex
    weights.add_argument("--weights", help="Comma-separated manual weights in source order.") # Codex
    catalog.add_argument("--gamma", action="append", type=float, default=None, help="Negative spectral index; repeat to scan multiple values.") # Codex
    catalog.add_argument("--no-uniform-baseline", action="store_true", help="Do not add a uniform-weight stacking baseline.") # Codex
    return parser # Codex


def request_from_args(args: argparse.Namespace) -> dict[str, object]: # Codex
    if args.command == "single": # Codex
        return build_single_source_request(args.name, args.ra_deg, args.dec_deg, args.gamma, "data_output/runs_cdx") # cdx
    sources = None if args.source is None else [parse_source(value) for value in args.source] # Codex
    manual_weights = None if args.weights is None else [float(value.strip()) for value in args.weights.split(",")] # Codex
    gammas = args.gamma or [-2.53] # Codex
    return build_catalog_request(args.catalog, sources, args.name_column, args.ra_column, args.dec_column, args.weight_column, manual_weights, gammas, not args.no_uniform_baseline, "data_output/runs_cdx") # Codex


def parse_source(value: str) -> dict[str, object]: # Codex
    parts = [part.strip() for part in value.split(",")] # Codex
    if len(parts) != 3: # Codex
        raise ValueError("--source must have the form name,ra_deg,dec_deg") # Codex
    return {"name": parts[0], "ra_deg": float(parts[1]), "dec_deg": float(parts[2])} # Codex


def print_summary(result: dict[str, object]) -> None: # Codex
    if "best_fit_ns" in result: # Codex
        print(f"Single source: ns_hat={float(result['best_fit_ns']):.6g}; TS={float(result['ts']):.6g}; pre-trial p={float(result['pre_trial_p']):.6g}") # Codex
    source_rows = result.get("_source_results") # Codex
    if isinstance(source_rows, list) and source_rows: # Codex
        best = max(source_rows, key=lambda row: float(row.get("ts", 0.0))) # Codex
        print(f"Highest-TS source: #{best['source_number']} {best['source_name']}; TS={float(best['ts']):.6g}; pre-trial p={float(best['pre_trial_p']):.6g}; post-trial p={float(best['post_trial_p']):.6g}") # Codex
    stacking_rows = result.get("_stacking_results") # Codex
    if isinstance(stacking_rows, list): # Codex
        for row in stacking_rows: # Codex
            print(f"Stacking {row['weighting_scheme']} gamma={float(row['spectral_index']):.3g}: ns_hat={float(row['ns_hat']):.6g}; TS={float(row['ts']):.6g}; p={float(row['pre_trial_p']):.6g}; significance={float(row['pre_trial_significance']):.6g} sigma") # Codex


if __name__ == "__main__": # Codex
    raise SystemExit(main()) # Codex
