"""Internal production runner for the 14-year reproduction/comparison study."""

from __future__ import annotations

import argparse
from pathlib import Path

from analysis_backend_cdx.skyllh_dr2_catalog_scan_cdx import run_catalog_scan
from tools_cdx.build_radio_bright_agn_catalog_cdx import DEFAULT_OUTPUT, build_catalog


DEFAULT_RUN_DIR = "data_output/2103_12813_dr2_spatial_only_cdx"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--catalog", default=DEFAULT_OUTPUT)
    parser.add_argument("--output-dir", default=DEFAULT_RUN_DIR)
    parser.add_argument("--source-chunk", type=int, default=8)
    parser.add_argument("--event-chunk", type=int, default=16384)
    parser.add_argument("--checkpoint-every", type=int, default=256)
    parser.add_argument("--acceptance-gamma", type=float, default=2.53)
    parser.add_argument("--no-stacking", action="store_true", help="Run only the source-scan sensitivity fit")
    parser.add_argument("--limit-sources", type=int)
    args = parser.parse_args()
    root = Path(args.repo_root).resolve()
    catalog = root / args.catalog
    if not catalog.exists():
        catalog, _ = build_catalog(root, args.catalog)
    if args.limit_sources is not None:
        import csv

        with catalog.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))[: args.limit_sources]
        limited = root / args.output_dir / f"catalog_first_{args.limit_sources}_cdx.csv"
        limited.parent.mkdir(parents=True, exist_ok=True)
        with limited.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        catalog = limited
    run_catalog_scan(
        root,
        catalog,
        args.output_dir,
        acceptance_gamma=args.acceptance_gamma,
        stack_gammas=() if args.no_stacking else (2.0, 2.53, 3.0),
        source_chunk=args.source_chunk,
        event_chunk=args.event_chunk,
        checkpoint_every=args.checkpoint_every,
    )


if __name__ == "__main__":
    main()
