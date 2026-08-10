"""Build the 3386-source RFC 2019c catalog used by arXiv:2103.12813."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np


RAW_CATALOG = "data_input/VLBI_rfc_2019c_cat_BZ.dat"
DEFAULT_OUTPUT = "data_output/catalogs_cdx/radio_bright_agn_rfc2019c_xband_ge_0p15_dec_lt87_3386_enriched.csv"


def _sexagesimal_ra_deg(hour, minute, second):
    return 15.0 * (float(hour) + float(minute) / 60.0 + float(second) / 3600.0)


def _sexagesimal_dec_deg(degree_token, minute, second):
    sign = -1.0 if str(degree_token).startswith("-") else 1.0
    return sign * (abs(float(degree_token)) + float(minute) / 60.0 + float(second) / 3600.0)


def build_catalog(repo_root=".", output_path=None):
    root = Path(repo_root).resolve()
    raw_path = root / RAW_CATALOG
    output = root / (output_path or DEFAULT_OUTPUT)
    rows = []
    with raw_path.open(encoding="utf-8", errors="replace") as handle:
        for raw_line_number, line in enumerate(handle, start=1):
            fields = line.split()
            if len(fields) < 25 or fields[0].startswith("#"):
                continue
            try:
                xband_flux_jy = float(fields[17])
                ra_deg = _sexagesimal_ra_deg(fields[3], fields[4], fields[5])
                dec_deg = _sexagesimal_dec_deg(fields[6], fields[7], fields[8])
            except ValueError:
                continue
            if xband_flux_jy < 0.15 or abs(dec_deg) >= 87.0:
                continue
            rows.append(
                {
                    "catalog_index": len(rows),
                    "raw_line_number": raw_line_number,
                    "ivs_name": fields[1],
                    "j2000_name": fields[2],
                    "source_name": fields[1],
                    "ra_deg": ra_deg,
                    "dec_deg": dec_deg,
                    "xband_flux_jy": xband_flux_jy,
                }
            )
    if len(rows) != 3386:
        raise RuntimeError(f"Expected 3386 selected sources, found {len(rows)}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return output, rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output")
    args = parser.parse_args()
    output, rows = build_catalog(args.repo_root, args.output)
    flux = np.asarray([row["xband_flux_jy"] for row in rows])
    print(f"Wrote {len(rows)} sources to {output}")
    print(f"X-band flux range: {flux.min():.6g}--{flux.max():.6g} Jy")


if __name__ == "__main__":
    main()
