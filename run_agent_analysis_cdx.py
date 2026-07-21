from __future__ import annotations # Codex

import argparse # Codex
import sys # Codex
from pathlib import Path # Codex

from agent_core_cdx.config_io_cdx import load_config_file # cdx
from agent_core_cdx.likelihood_backend_cdx import run_likelihood_backend # cdx
from agent_core_cdx.mock_backend_cdx import run_mock_backend # cdx
from agent_core_cdx.normalize_cdx import normalize_config # cdx
from agent_core_cdx.report_cdx import write_run_artifacts # cdx
from agent_core_cdx.schemas_cdx import ConfigError, to_clean_dict # cdx
from agent_core_cdx.simple_yaml_cdx import dump_simple_yaml # cdx
from agent_core_cdx.validate_cdx import validate_config # cdx


def main(argv: list[str] | None = None) -> int: # Codex
    parser = argparse.ArgumentParser(description="Run the HE-neutrino single-source or catalog-stacking analysis pipeline.") # Codex
    parser.add_argument("config", help="Analysis config path. Use YAML for now; JSON is accepted by code for later API use.") # Codex
    parser.add_argument("--repo-root", default=".", help="Repository root for relative paths.") # Codex
    parser.add_argument("--backend", choices=["mock", "likelihood"], default="mock", help="Backend to run after validation.") # Codex
    parser.add_argument("--validate-only", action="store_true", help="Validate and normalize without running a backend.") # Codex
    parser.add_argument("--print-normalized", action="store_true", help="Print normalized config as YAML.") # Codex
    args = parser.parse_args(argv) # Codex
    repo_root = Path(args.repo_root).resolve() # Codex
    try: # Codex
        config = load_config_file(args.config) # Codex
        validation = validate_config(config, repo_root) # Codex
        for warning in validation.warnings: # Codex
            print(f"WARNING: {warning}", file=sys.stderr) # Codex
        for error in validation.errors: # Codex
            print(f"ERROR: {error}", file=sys.stderr) # Codex
        if not validation.ok: # Codex
            return 2 # Codex
        normalized = normalize_config(config, repo_root, validation.warnings) # Codex
        if args.print_normalized: # Codex
            print(dump_simple_yaml(to_clean_dict(normalized)), end="") # Codex
        if args.validate_only: # Codex
            print("Config validation completed successfully.") # Codex
            return 0 # Codex
        if args.backend == "mock": # Codex
            result = run_mock_backend(normalized) # Codex
        else: # Codex
            result = run_likelihood_backend(normalized, repo_root) # Codex
        run_dir = write_run_artifacts(args.config, config, normalized, result, repo_root) # Codex
        print(f"Run completed with {args.backend} backend: {run_dir}") # Codex
        print(f"Report: {run_dir / 'report_cdx.md'}") # cdx
        return 0 # Codex
    except ConfigError as exc: # Codex
        print(f"CONFIG ERROR: {exc}", file=sys.stderr) # Codex
        return 2 # Codex


if __name__ == "__main__": # Codex
    raise SystemExit(main()) # Codex
