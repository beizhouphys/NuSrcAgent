"""Scientific/artifact review for the dedicated 2103.12813 DR2 benchmark."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def review(repo_root=".", run_dir="data_output/2103_12813_dr2_spatial_only_cdx", write=True):
    root = Path(repo_root).resolve()
    run = root / run_dir
    checks = []

    def check(name, passed, detail):
        checks.append({"name": name, "status": "pass" if passed else "fail", "detail": detail})

    sources = json.loads((run / "source_scan_results_cdx.json").read_text(encoding="utf-8"))
    stacks = json.loads((run / "stacking_results_cdx.json").read_text(encoding="utf-8"))
    provenance = json.loads((run / "provenance_cdx.json").read_text(encoding="utf-8"))
    check("source_count", len(sources) == 3386, f"found {len(sources)}; expected 3386")
    check("catalog_order", [int(row["catalog_index"]) for row in sources] == list(range(3386)), "catalog_index must be contiguous and input ordered")
    check("unique_sources", len({row["ivs_name"] for row in sources}) == 3386, "IVS identifiers must be unique")
    check("coordinates", all(0.0 <= float(row["ra_deg"]) < 360.0 and -87.0 < float(row["dec_deg"]) < 87.0 for row in sources), "selected coordinate bounds")
    check("source_fit_values", all(math.isfinite(float(row["ns_hat"])) and float(row["ns_hat"]) >= 0.0 and math.isfinite(float(row["TS"])) and float(row["TS"]) >= -1e-8 for row in sources), "primary fits must be finite with ns>=0 and TS>=0")
    check("source_probabilities", all(0.0 <= float(row["pre_trial_p"]) <= 1.0 and 0.0 <= float(row["post_trial_p_catalog_analytic_uncalibrated"]) <= 1.0 for row in sources), "probabilities must lie in [0,1]")
    expected_hypotheses = {(scheme, gamma) for scheme in ("equal", "xband") for gamma in (2.0, 2.53, 3.0)}
    actual_hypotheses = {(row["weighting_scheme"], float(row["acceptance_gamma_skyllh"])) for row in stacks}
    check("stacking_hypotheses", actual_hypotheses == expected_hypotheses, f"found {sorted(actual_hypotheses)}")
    check("stacking_values", all(math.isfinite(float(row["TS"])) and math.isfinite(float(row["ns_95_deltaTS_minus3p84"])) and math.isfinite(float(row["allflavor_E2dFdE_100TeV_95_GeV_cm-2_s-1_sr-1"])) for row in stacks), "six stack fits and conversions must be finite")
    check("all_events", provenance.get("event_selection") == "all_events" and int(provenance.get("n_events", 0)) == 1643355, str(provenance.get("n_events")))
    check("likelihood_mode", provenance.get("likelihood_mode") == "spatial_only", str(provenance.get("likelihood_mode")))
    expected_artifacts = [
        run / "comparison_summary_cdx.json",
        run / "table_I_style_top5_dr2_14yr_cdx.csv",
        run / "table_I_named_sources_10yr_vs_14yr_cdx.csv",
        run / "fig3_bins_10yr_vs_14yr_cdx.csv",
        run / "fig4_limits_10yr_vs_14yr_cdx.csv",
        run / "workbook_payload_cdx.json",
        root / "outputs/2103_12813_dr2_spatial_only_cdx/analysis_results_cdx.xlsx",
        root / "data_output/paper_reference_cdx/2103_12813/paper_reference_provenance_cdx.json",
        root / "figures/2103_12813_dr2_spatial_only_cdx/fig3_10yr_paper_vs_14yr_dr2_cdx.pdf",
        root / "figures/2103_12813_dr2_spatial_only_cdx/table_I_style_top5_dr2_14yr_cdx.pdf",
        root / "figures/2103_12813_dr2_spatial_only_cdx/table_I_named_sources_10yr_vs_14yr_cdx.pdf",
        root / "figures/2103_12813_dr2_spatial_only_cdx/fig4_10yr_paper_vs_14yr_dr2_cdx.pdf",
    ]
    check("comparison_artifacts", all(path.exists() and path.stat().st_size > 0 for path in expected_artifacts), "all tables and PDFs must exist and be nonempty")
    failures = [item for item in checks if item["status"] == "fail"]
    result = {
        "status": "fail" if failures else "warning",
        "checks": checks,
        "warnings": [
            "Catalog-size post-trial probabilities are analytic and uncalibrated; right-ascension-scrambled trials were not run.",
            "The 14-year DR2 result and 10-year paper result use different releases and response calibrations.",
            "The DR2 flux conversion directly integrates public effective areas/livetimes and is not identical to the paper's 10-year calibration.",
            "Signed-ns values are a paper-compatibility diagnostic; constrained ns>=0 values are primary.",
        ],
        "publication_ready": False,
    }
    if write:
        (run / "review_cdx.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        lines = ["# Scientific Review", "", f"Status: `{result['status']}`", "", "## Checks", ""]
        lines.extend(f"- {item['status'].upper()}: {item['name']} — {item['detail']}" for item in checks)
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in result["warnings"])
        (run / "review_cdx.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--run-dir", default="data_output/2103_12813_dr2_spatial_only_cdx")
    args = parser.parse_args()
    print(json.dumps(review(args.repo_root, args.run_dir), indent=2))
