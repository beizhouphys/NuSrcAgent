from __future__ import annotations # Codex

import argparse # Codex
import csv # Codex
from pathlib import Path # Codex


def main() -> int: # Codex
    parser = argparse.ArgumentParser(description="Build a reproducible RFC radio-source smoke-test catalog.") # Codex
    parser.add_argument("--input", default="data_input/VLBI_rfc_2019c_cat_BZ.dat") # Codex
    parser.add_argument("--output", default="configs_cdx/examples_cdx/catalog_sources_rfc100_cdx.csv") # Codex
    parser.add_argument("--count", type=int, default=100) # Codex
    parser.add_argument("--min-xband-flux-jy", type=float, default=0.15) # Codex
    args = parser.parse_args() # Codex
    rows = select_rows(Path(args.input), args.count, args.min_xband_flux_jy) # Codex
    output = Path(args.output) # Codex
    output.parent.mkdir(parents=True, exist_ok=True) # Codex
    fields = ["source_name", "ivs_name", "j2000_name", "ra_deg", "dec_deg", "xband_flux_jy", "source_catalog"] # Codex
    with output.open("w", encoding="utf-8", newline="") as handle: # Codex
        writer = csv.DictWriter(handle, fieldnames=fields) # Codex
        writer.writeheader() # Codex
        writer.writerows(rows) # Codex
    print(f"Wrote {len(rows)} RFC sources to {output}") # Codex
    return 0 # Codex


def select_rows(path: Path, count: int, min_xband_flux_jy: float) -> list[dict[str, object]]: # Codex
    eligible: list[dict[str, object]] = [] # Codex
    with path.open("r", encoding="utf-8") as handle: # Codex
        for line in handle: # Codex
            if not line.strip() or line.startswith("#"): # Codex
                continue # Codex
            fields = line.split() # Codex
            xband_flux = float(fields[17]) # Codex
            dec_deg = signed_angle(fields[6], fields[7], fields[8]) # Codex
            if xband_flux < min_xband_flux_jy or not -87.0 < dec_deg < 87.0: # Codex
                continue # Codex
            ra_deg = (float(fields[3]) + float(fields[4]) / 60.0 + float(fields[5]) / 3600.0) * 15.0 # Codex
            eligible.append({"source_name": fields[1], "ivs_name": fields[1], "j2000_name": fields[2], "ra_deg": f"{ra_deg:.8f}", "dec_deg": f"{dec_deg:.8f}", "xband_flux_jy": f"{xband_flux:.6g}", "source_catalog": fields[-1]}) # Codex
    if len(eligible) < count: # Codex
        raise ValueError(f"requested {count} sources but only found {len(eligible)}") # Codex
    if count == 1: # Codex
        return [eligible[0]] # Codex
    indices = [round(index * (len(eligible) - 1) / (count - 1)) for index in range(count)] # Codex
    return [eligible[index] for index in indices] # Codex


def signed_angle(degrees: str, minutes: str, seconds: str) -> float: # Codex
    sign = -1.0 if degrees.startswith("-") else 1.0 # Codex
    return sign * (abs(float(degrees)) + float(minutes) / 60.0 + float(seconds) / 3600.0) # Codex


if __name__ == "__main__": # Codex
    raise SystemExit(main()) # Codex
