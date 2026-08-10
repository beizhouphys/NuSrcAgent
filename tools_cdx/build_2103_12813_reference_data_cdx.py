"""Create auditable paper-reference tables for the 2103.12813 comparison.

Fig. 3 values are recovered from the vector paths in PDF page 4.  The
logarithmic-axis transform and Poisson error-bar endpoints identify the
integer bin counts exactly.  Table I and Fig. 4 percentages are transcribed
from the paper text/table rather than estimated from pixels.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


PAPER = "Notes_and_papers/2103.12813 Search for High-Energy Neutrino Emission from Radio-Bright AGN.pdf"
DEFAULT_OUTPUT = "data_output/paper_reference_cdx/2103_12813"


FIG3_COUNTS = [322, 292, 253, 198, 177, 125, 88, 48, 38, 22, 12, 5, 1, 0, 0, 1, 1, 0, 0, 0]
TABLE_I = [
    ("1303-170", "J1306-1718", 0.208, 21.6, 16.6, 2.28e-5, 4.1, 0.074, 1.5),
    ("2245+029", "J2247+0310", 0.434, 50.8, 14.5, 7.14e-5, 3.8, 0.21, 0.8),
    ("0228-163", "J0231-1606", 0.162, 15.9, 9.8, 8.90e-4, 3.1, 0.95, 0.0),
    ("1424+240", "J1427+2348", 0.187, 38.1, 8.9, 1.42e-3, 3.0, 0.99, 0.0),
    ("0958+559", "J1001+5540", 0.180, 27.2, 8.3, 2.02e-3, 2.9, 1.0, 0.0),
]
FIG4_FRACTIONS_100TEV = {
    "equal": {-2.0: 0.278, -2.53: 0.103, -3.0: 0.017},
    "xband": {-2.0: 0.126, -2.53: 0.048, -3.0: 0.0084},
}
FIG4_FRACTIONS_INTEGRATED = {
    "equal": {-2.0: 0.306, -2.53: 0.103, -3.0: 0.023},
    "xband": {-2.0: 0.138, -2.53: 0.048, -3.0: 0.011},
}
DIFFUSE_REFERENCE_100TEV = {-2.0: 5.00e-8, -2.53: 4.98e-8, -3.0: 5.00e-8}


def _write_csv(path, fieldnames, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_reference_data(repo_root=".", output_dir=DEFAULT_OUTPUT):
    root = Path(repo_root).resolve()
    out = root / output_dir
    out.mkdir(parents=True, exist_ok=True)
    fig3 = [
        {"sqrt_TS_bin_min": 0.25 * idx, "sqrt_TS_bin_max": 0.25 * (idx + 1), "sqrt_TS_bin_center": 0.25 * idx + 0.125, "count": count}
        for idx, count in enumerate(FIG3_COUNTS)
    ]
    _write_csv(out / "paper_fig3_digitized_counts_cdx.csv", list(fig3[0]), fig3)
    fields = ["ivs_name", "j2000_name", "xband_flux_jy", "ns_hat", "TS", "pre_trial_p", "pre_trial_sigma", "post_trial_p", "post_trial_sigma"]
    table = [dict(zip(fields, row, strict=True)) for row in TABLE_I]
    _write_csv(out / "paper_table_I_transcribed_cdx.csv", fields, table)
    fig4 = []
    for scheme in ("equal", "xband"):
        for gamma in (-2.0, -2.53, -3.0):
            fraction = FIG4_FRACTIONS_100TEV[scheme][gamma]
            fig4.append(
                {
                    "weighting_scheme": scheme,
                    "spectral_index": gamma,
                    "fraction_diffuse_100TeV_95": fraction,
                    "allflavor_E2dFdE_100TeV_95_GeV_cm-2_s-1_sr-1": fraction * DIFFUSE_REFERENCE_100TEV[gamma],
                    "fraction_diffuse_16TeV_2p6PeV_95": FIG4_FRACTIONS_INTEGRATED[scheme][gamma],
                }
            )
    _write_csv(out / "paper_fig4_published_limits_cdx.csv", list(fig4[0]), fig4)
    provenance = {
        "paper": PAPER,
        "arxiv": "2103.12813",
        "fig3_method": "Exact integer counts inferred from PDF page-4 SVG vector coordinates. The common log-axis transform is D=122.023 SVG units/decade; Poisson endpoints n±sqrt(n) independently identify every nonzero n.",
        "fig3_nonnegative_fit_count": sum(FIG3_COUNTS),
        "table_I_method": "Manual transcription from Table I.",
        "fig4_method": "Exact percentages transcribed from the Results text; 100-TeV flux values multiply those percentages by the paper's displayed diffuse reference normalizations.",
        "not_digitized": "The Fig. 4 likelihood-profile line shapes are not used as numerical reference; published 95% limits are the comparison statistic.",
    }
    (out / "paper_reference_provenance_cdx.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    print(build_reference_data())
