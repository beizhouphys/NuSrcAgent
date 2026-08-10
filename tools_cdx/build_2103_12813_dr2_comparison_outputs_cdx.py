"""Build Fig. 3/Table I/Fig. 4-style DR2 comparison artifacts."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from analysis_backend_cdx.dr2_flux_conversion_cdx import (
    diffuse_expected_events_per_phi0_mu,
    ns_to_allflavor_e2_intensity_100tev,
)


RUN_DIR = "data_output/2103_12813_dr2_spatial_only_cdx"
REFERENCE_DIR = "data_output/paper_reference_cdx/2103_12813"
FIGURE_DIR = "figures/2103_12813_dr2_spatial_only_cdx"
SENSITIVITY_DIR = "data_output/2103_12813_dr2_spatial_only_acceptance_gamma_2p5_sensitivity_cdx"


def _read_csv(path):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path, rows):
    if not rows:
        return
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _fig3(source_rows, reference_rows, figure_dir):
    paper_edges = np.asarray([float(row["sqrt_TS_bin_min"]) for row in reference_rows] + [float(reference_rows[-1]["sqrt_TS_bin_max"])])
    paper_counts = np.asarray([int(row["count"]) for row in reference_rows])
    signed_values = np.asarray(
        [np.sqrt(max(float(row["TS_signed_diagnostic"]), 0.0)) for row in source_rows if float(row["ns_hat_signed_diagnostic"]) >= 0.0]
    )
    dr2_counts, _ = np.histogram(signed_values, bins=paper_edges)
    centers = 0.5 * (paper_edges[:-1] + paper_edges[1:])
    width = np.diff(paper_edges)
    fig, ax = plt.subplots(figsize=(7.2, 5.4))
    ax.errorbar(centers, paper_counts, yerr=np.sqrt(paper_counts), xerr=0.5 * width, fmt="o", color="#2455ff", label="Paper: IceCube 10 yr")
    ax.errorbar(centers, dr2_counts, yerr=np.sqrt(dr2_counts), xerr=0.5 * width, fmt="s", color="#d62728", label="This work: IceTracks DR2 14 yr")
    x = np.linspace(0, paper_edges[-1], 400)
    for counts, color, style in ((paper_counts, "#2455ff", "--"), (dr2_counts, "#d62728", "-")):
        shape = np.exp(-0.5 * centers**2)
        amplitude = np.sum(counts * shape) / np.sum(shape**2)
        ax.plot(x, amplitude * np.exp(-0.5 * x**2), style, color=color, alpha=0.8)
    ax.set_yscale("log")
    ax.set_xlim(0, 5)
    ax.set_ylim(0.5, max(paper_counts.max(), dr2_counts.max()) * 1.7)
    ax.set_xlabel(r"$\sqrt{\mathrm{TS}}$")
    ax.set_ylabel("Number of sources in each bin")
    ax.set_title("Radio-bright AGN single-source scan: direct comparison")
    ax.legend()
    ax.grid(alpha=0.2)
    fig.tight_layout()
    for suffix in ("pdf", "png"):
        fig.savefig(figure_dir / f"fig3_10yr_paper_vs_14yr_dr2_cdx.{suffix}", dpi=220)
    plt.close(fig)
    comparison = [
        {
            "sqrt_TS_bin_min": paper_edges[idx],
            "sqrt_TS_bin_max": paper_edges[idx + 1],
            "paper_10yr_count": int(paper_counts[idx]),
            "dr2_14yr_count": int(dr2_counts[idx]),
            "signed_absolute_difference_dr2_minus_paper": int(dr2_counts[idx] - paper_counts[idx]),
            "signed_relative_difference_dr2_minus_paper": ((dr2_counts[idx] - paper_counts[idx]) / paper_counts[idx]) if paper_counts[idx] else None,
        }
        for idx in range(len(paper_counts))
    ]
    return comparison, len(signed_values)


def _table_i(source_rows, paper_rows, run_dir, figure_dir):
    by_ivs = {row["ivs_name"]: row for row in source_rows}
    ranked = sorted(source_rows, key=lambda row: float(row["TS"]), reverse=True)
    rank = {row["ivs_name"]: idx + 1 for idx, row in enumerate(ranked)}
    comparisons = []
    for paper in paper_rows:
        dr2 = by_ivs[paper["ivs_name"]]
        comparisons.append(
            {
                "ivs_name": paper["ivs_name"],
                "j2000_name": paper["j2000_name"],
                "paper_10yr_ns_hat": float(paper["ns_hat"]),
                "dr2_14yr_ns_hat": float(dr2["ns_hat"]),
                "ns_signed_absolute_difference_dr2_minus_paper": float(dr2["ns_hat"]) - float(paper["ns_hat"]),
                "ns_signed_relative_difference_dr2_minus_paper": (float(dr2["ns_hat"]) - float(paper["ns_hat"])) / float(paper["ns_hat"]),
                "paper_10yr_TS": float(paper["TS"]),
                "dr2_14yr_TS": float(dr2["TS"]),
                "TS_signed_absolute_difference_dr2_minus_paper": float(dr2["TS"]) - float(paper["TS"]),
                "TS_signed_relative_difference_dr2_minus_paper": (float(dr2["TS"]) - float(paper["TS"])) / float(paper["TS"]),
                "paper_10yr_pre_trial_p": float(paper["pre_trial_p"]),
                "dr2_14yr_pre_trial_p": float(dr2["pre_trial_p"]),
                "dr2_14yr_analytic_post_trial_p_uncalibrated": float(dr2["post_trial_p_catalog_analytic_uncalibrated"]),
                "dr2_14yr_rank": rank[paper["ivs_name"]],
            }
        )
    _write_csv(run_dir / "table_I_named_sources_10yr_vs_14yr_cdx.csv", comparisons)
    fig, ax = plt.subplots(figsize=(11.5, 3.4))
    ax.axis("off")
    comparison_labels = ["IVS", "J2000", r"paper $\hat n_s$", r"DR2 $\hat n_s$", "paper TS", "DR2 TS", "DR2 rank"]
    comparison_cells = [
        [row["ivs_name"], row["j2000_name"], f'{row["paper_10yr_ns_hat"]:.1f}', f'{row["dr2_14yr_ns_hat"]:.1f}', f'{row["paper_10yr_TS"]:.1f}', f'{row["dr2_14yr_TS"]:.2f}', row["dr2_14yr_rank"]]
        for row in comparisons
    ]
    table = ax.table(cellText=comparison_cells, colLabels=comparison_labels, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.55)
    ax.set_title("Sources in published Table I: IceCube 10-year paper versus IceTracks DR2 14-year", pad=18)
    fig.tight_layout()
    for suffix in ("pdf", "png"):
        fig.savefig(figure_dir / f"table_I_named_sources_10yr_vs_14yr_cdx.{suffix}", dpi=220)
    plt.close(fig)
    top = ranked[:5]
    top_rows = [
        {
            "rank": idx + 1,
            "ivs_name": row["ivs_name"],
            "j2000_name": row["j2000_name"],
            "xband_flux_jy": row["xband_flux_jy"],
            "ns_hat": row["ns_hat"],
            "TS": row["TS"],
            "pre_trial_p": row["pre_trial_p"],
            "analytic_post_trial_p_uncalibrated": row["post_trial_p_catalog_analytic_uncalibrated"],
        }
        for idx, row in enumerate(top)
    ]
    _write_csv(run_dir / "table_I_style_top5_dr2_14yr_cdx.csv", top_rows)
    fig, ax = plt.subplots(figsize=(11.5, 3.4))
    ax.axis("off")
    labels = ["Rank", "IVS", "J2000", "X-band [Jy]", r"$\hat n_s$", "TS", "pre-trial p", "analytic post-trial p*"]
    cells = [[r["rank"], r["ivs_name"], r["j2000_name"], f'{float(r["xband_flux_jy"]):.3f}', f'{float(r["ns_hat"]):.1f}', f'{float(r["TS"]):.2f}', f'{float(r["pre_trial_p"]):.3g}', f'{float(r["analytic_post_trial_p_uncalibrated"]):.3g}'] for r in top_rows]
    table = ax.table(cellText=cells, colLabels=labels, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.55)
    ax.set_title("IceTracks DR2 14-year spatial-only scan: Table I-style top five\n*catalog-size analytic correction; not trial-scramble calibrated", pad=18)
    fig.tight_layout()
    for suffix in ("pdf", "png"):
        fig.savefig(figure_dir / f"table_I_style_top5_dr2_14yr_cdx.{suffix}", dpi=220)
    plt.close(fig)
    return comparisons, top_rows


def _fig4(stack_rows, paper_rows, repo_root, run_dir, figure_dir):
    paper = {(row["weighting_scheme"], float(row["spectral_index"])): row for row in paper_rows}
    colors = {"equal": "#d62728", "xband": "#2455ff"}
    styles = {-2.0: "-", -2.53: "--", -3.0: ":"}
    comparisons = []
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 4.8))
    energies = np.geomspace(1e4, 1e7, 300)
    for row in stack_rows:
        scheme = row["weighting_scheme"]
        gamma_legacy = float(row["spectral_index_legacy"])
        gamma = abs(gamma_legacy)
        ns = np.asarray(row["ns_profile"], dtype=float)
        delta = np.asarray(row["delta_TS_profile"], dtype=float)
        flux = np.asarray([ns_to_allflavor_e2_intensity_100tev(value, repo_root, gamma) for value in ns])
        flux95 = float(row["allflavor_E2dFdE_100TeV_95_GeV_cm-2_s-1_sr-1"])
        p = paper[(scheme, gamma_legacy)]
        paper_flux = float(p["allflavor_E2dFdE_100TeV_95_GeV_cm-2_s-1_sr-1"])
        axes[0].plot(flux[flux > 0], delta[flux > 0], color=colors[scheme], linestyle=styles[gamma_legacy], label=f"14 yr {scheme}, Γ={gamma_legacy:g}")
        axes[0].plot([paper_flux], [-3.84], marker="x", ms=7, mew=2, color=colors[scheme])
        axes[1].plot(energies, flux95 * (energies / 1e5) ** (gamma_legacy + 2.0), color=colors[scheme], linestyle=styles[gamma_legacy])
        axes[1].plot(energies, paper_flux * (energies / 1e5) ** (gamma_legacy + 2.0), color=colors[scheme], linestyle=styles[gamma_legacy], alpha=0.35)
        comparisons.append(
            {
                "weighting_scheme": scheme,
                "spectral_index": gamma_legacy,
                "paper_10yr_flux_100TeV_95": paper_flux,
                "dr2_14yr_flux_100TeV_95": flux95,
                "flux_signed_absolute_difference_dr2_minus_paper": flux95 - paper_flux,
                "flux_signed_relative_difference_dr2_minus_paper": (flux95 - paper_flux) / paper_flux,
                "paper_10yr_fraction_diffuse_100TeV_95": float(p["fraction_diffuse_100TeV_95"]),
                "dr2_14yr_fraction_diffuse_100TeV_95": float(row["fraction_of_paper_diffuse_reference_100TeV_95"]),
                "dr2_14yr_ns_hat": float(row["ns_hat"]),
                "dr2_14yr_TS": float(row["TS"]),
                "dr2_14yr_ns_95": float(row["ns_95_deltaTS_minus3p84"]),
            }
        )
    axes[0].axhline(-3.84, color="black", lw=1, alpha=0.6)
    axes[0].set_xscale("log")
    axes[0].set_ylim(-10, 0.3)
    axes[0].set_xlabel(r"All-flavor $E^2dF/dE$ at 100 TeV [GeV cm$^{-2}$ s$^{-1}$ sr$^{-1}$]")
    axes[0].set_ylabel(r"$\mathrm{TS}-\mathrm{TS}_{\rm best}$")
    axes[0].set_title("14-year profiles; x = published 10-year limits")
    axes[0].legend(fontsize=7, ncol=2)
    axes[1].set_xscale("log")
    axes[1].set_yscale("log")
    axes[1].set_xlabel("Neutrino energy [GeV]")
    axes[1].set_ylabel(r"All-flavor $E^2dF/dE$ [GeV cm$^{-2}$ s$^{-1}$ sr$^{-1}$]")
    axes[1].set_title("95% UL: 14 yr opaque; paper 10 yr faint")
    for ax in axes:
        ax.grid(alpha=0.2)
    fig.tight_layout()
    for suffix in ("pdf", "png"):
        fig.savefig(figure_dir / f"fig4_10yr_paper_vs_14yr_dr2_cdx.{suffix}", dpi=220)
    plt.close(fig)
    _write_csv(run_dir / "fig4_limits_10yr_vs_14yr_cdx.csv", comparisons)
    return comparisons


def build(repo_root=".", run_dir=RUN_DIR, reference_dir=REFERENCE_DIR, figure_dir=FIGURE_DIR):
    root = Path(repo_root).resolve()
    run = root / run_dir
    reference = root / reference_dir
    figures = root / figure_dir
    figures.mkdir(parents=True, exist_ok=True)
    sources = json.loads((run / "source_scan_results_cdx.json").read_text(encoding="utf-8"))
    stacks = json.loads((run / "stacking_results_cdx.json").read_text(encoding="utf-8"))
    fig3_comparison, n_nonnegative = _fig3(sources, _read_csv(reference / "paper_fig3_digitized_counts_cdx.csv"), figures)
    _write_csv(run / "fig3_bins_10yr_vs_14yr_cdx.csv", fig3_comparison)
    table_comparison, top_rows = _table_i(sources, _read_csv(reference / "paper_table_I_transcribed_cdx.csv"), run, figures)
    fig4_comparison = _fig4(stacks, _read_csv(reference / "paper_fig4_published_limits_cdx.csv"), root, run, figures)
    summary = {
        "n_sources": len(sources),
        "paper_10yr_n_sources_with_ns_ge_0": sum(int(row["paper_10yr_count"]) for row in fig3_comparison),
        "dr2_14yr_n_sources_with_signed_ns_ge_0": n_nonnegative,
        "dr2_top_source": top_rows[0],
        "paper_table_I_named_source_comparisons": table_comparison,
        "fig4_limit_comparisons": fig4_comparison,
        "scientific_cautions": [
            "The datasets differ (IceCube 10-year public release versus IceTracks DR2 14-year), so differences are not attributable to exposure alone.",
            "The DR2 flux conversion directly integrates public DR2 effective areas and livetimes; the paper used its own 10-year calibration.",
            "Catalog post-trial p-values reported here are analytic catalog-size corrections and are not calibrated with scrambled trials.",
            "The signed-ns fit is a paper-compatibility diagnostic; constrained ns>=0 is the primary DR2 result.",
        ],
    }
    legacy_counts = {2.0: 3217.3, 2.53: 8845.7, 3.0: 49282.2}
    diffuse_refs = {2.0: 5.00e-8, 2.53: 4.98e-8, 3.0: 5.00e-8}
    summary["flux_conversion_reference_count_comparison"] = []
    for gamma in (2.0, 2.53, 3.0):
        per_phi0, by_configuration = diffuse_expected_events_per_phi0_mu(root, gamma)
        dr2_count = per_phi0 * diffuse_refs[gamma] / (3e10)
        legacy_count = legacy_counts[gamma]
        summary["flux_conversion_reference_count_comparison"].append(
            {
                "gamma_skyllh": gamma,
                "dr2_direct_count_at_displayed_diffuse_reference": dr2_count,
                "paper_10yr_calibrated_reference_count": legacy_count,
                "signed_relative_difference_dr2_minus_paper": (dr2_count - legacy_count) / legacy_count,
                "signed_absolute_difference_dr2_minus_paper": dr2_count - legacy_count,
                "dr2_count_by_configuration_per_unit_phi0_mu": by_configuration,
            }
        )
    sensitivity_path = root / SENSITIVITY_DIR / "source_scan_results_cdx.json"
    if sensitivity_path.exists():
        sensitivity = json.loads(sensitivity_path.read_text(encoding="utf-8"))
        sensitivity_by_name = {row["ivs_name"]: row for row in sensitivity}
        sensitivity_rows = []
        for main in sources:
            alt = sensitivity_by_name[main["ivs_name"]]
            main_ts = float(main["TS"])
            alt_ts = float(alt["TS"])
            main_ns = float(main["ns_hat"])
            alt_ns = float(alt["ns_hat"])
            sensitivity_rows.append(
                {
                    "ivs_name": main["ivs_name"],
                    "TS_acceptance_gamma_minus2p53": main_ts,
                    "TS_acceptance_gamma_minus2p5": alt_ts,
                    "TS_signed_absolute_difference_minus2p5_minus_minus2p53": alt_ts - main_ts,
                    "TS_signed_relative_difference_minus2p5_minus_minus2p53": (alt_ts - main_ts) / main_ts if main_ts else None,
                    "ns_acceptance_gamma_minus2p53": main_ns,
                    "ns_acceptance_gamma_minus2p5": alt_ns,
                    "ns_signed_absolute_difference_minus2p5_minus_minus2p53": alt_ns - main_ns,
                    "ns_signed_relative_difference_minus2p5_minus_minus2p53": (alt_ns - main_ns) / main_ns if main_ns else None,
                }
            )
        _write_csv(run / "acceptance_gamma_minus2p5_sensitivity_cdx.csv", sensitivity_rows)
        summary["acceptance_gamma_sensitivity"] = {
            "comparison": "legacy Gamma -2.5 minus -2.53",
            "maximum_absolute_TS_difference": max(abs(float(row["TS_signed_absolute_difference_minus2p5_minus_minus2p53"])) for row in sensitivity_rows),
            "maximum_absolute_ns_difference": max(abs(float(row["ns_signed_absolute_difference_minus2p5_minus_minus2p53"])) for row in sensitivity_rows),
        }
    (run / "comparison_summary_cdx.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    source_columns = [
        "catalog_index", "ivs_name", "j2000_name", "ra_deg", "dec_deg", "xband_flux_jy",
        "ns_hat", "TS", "sqrt_TS", "pre_trial_p", "post_trial_p_catalog_analytic_uncalibrated",
        "ns_hat_signed_diagnostic", "TS_signed_diagnostic", "acceptance_gamma_legacy",
        "raw_line_number", "source_name",
    ]
    stack_scalars = [
        {key: value for key, value in row.items() if key not in {"ns_profile", "delta_TS_profile", "dataset_fractions"}}
        for row in stacks
    ]
    stack_columns = [
        "weighting_scheme", "spectral_index_legacy", "ns_hat", "TS", "ns_95_deltaTS_minus3p84",
        "allflavor_E2dFdE_100TeV_95_GeV_cm-2_s-1_sr-1",
        "fraction_of_paper_diffuse_reference_100TeV_95", "acceptance_gamma_skyllh",
    ]
    workbook_payload = {
        "source_columns": source_columns,
        "source_rows": [[row.get(column) for column in source_columns] for row in sources],
        "stacking_columns": stack_columns,
        "stacking_rows": [[row.get(column) for column in stack_columns] for row in stack_scalars],
        "run_information": [
            ["field", "value"],
            ["analysis", "arXiv:2103.12813-style radio-bright AGN scan and stack"],
            ["sample", "IceCube IceTracks-DR2 14-year public data"],
            ["likelihood", "time-integrated spatial-only, all events, point sources"],
            ["catalog", "RFC 2019c; X-band >=0.15 Jy; |Dec|<87 deg; 3386 sources"],
            ["single-source acceptance Gamma", "-2.53 legacy convention"],
            ["stacking Gammas", "-2.0, -2.53, -3.0 legacy convention"],
            ["weights", "equal and X-band flux density"],
            ["primary ns bounds", "[0, 10000]"],
            ["signed diagnostic bounds", "physical lower bound clipped at -10; upper 10000"],
            ["upper limit", "Delta TS = -3.84 above best fit"],
            ["flux conversion", "Direct DR2 public effective-area and livetime integration; three-flavor factor"],
            ["post-trial warning", "Catalog-size analytic correction is uncalibrated; no scrambled trials"],
            ["paper reference", "arXiv:2103.12813"],
        ],
    }
    (run / "workbook_payload_cdx.json").write_text(json.dumps(workbook_payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return run, figures


if __name__ == "__main__":
    print(build())
