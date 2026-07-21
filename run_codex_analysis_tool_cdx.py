from __future__ import annotations # cdx

import argparse # cdx
import json # cdx
from pathlib import Path # cdx

from agent_core_cdx.catalog_inspector_cdx import inspect_catalog # cdx
from agent_core_cdx.review_cdx import review_run # cdx


def main(argv=None) -> int: # cdx
    parser = build_parser() # cdx
    args = parser.parse_args(argv) # cdx
    if args.command == "inspect-catalog": # cdx
        result = inspect_catalog(args.catalog, args.name_column, args.ra_column, args.dec_column, args.weight_column) # cdx
    else: # cdx
        result = review_run(args.run_directory, args.repo_root, write_artifacts=not args.no_write) # cdx
    print(json.dumps(result, indent=2, sort_keys=True)) # cdx
    return 2 if result["status"] == "fail" else 0 # cdx


def build_parser() -> argparse.ArgumentParser: # cdx
    parser = argparse.ArgumentParser(description="Deterministic tools for the Codex-native HE-neutrino analysis agent.") # cdx
    subparsers = parser.add_subparsers(dest="command", required=True) # cdx
    inspect_parser = subparsers.add_parser("inspect-catalog", help="Inspect catalog schema, coordinates, and weight candidates.") # cdx
    inspect_parser.add_argument("--catalog", required=True) # cdx
    inspect_parser.add_argument("--name-column") # cdx
    inspect_parser.add_argument("--ra-column") # cdx
    inspect_parser.add_argument("--dec-column") # cdx
    inspect_parser.add_argument("--weight-column") # cdx
    review_parser = subparsers.add_parser("review-run", help="Review a completed analysis run and write review artifacts.") # cdx
    review_parser.add_argument("--run-directory", required=True) # cdx
    review_parser.add_argument("--repo-root", default=".") # cdx
    review_parser.add_argument("--no-write", action="store_true") # cdx
    return parser # cdx


if __name__ == "__main__": # cdx
    raise SystemExit(main()) # cdx
