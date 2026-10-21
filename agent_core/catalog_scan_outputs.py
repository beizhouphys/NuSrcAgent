"""Analytic catalog correction, compact top five and the observed sqrt(TS) histogram."""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from scipy.special import log_ndtr, ndtri_exp

from agent_core.analysis_outputs import write_csv
from agent_core.file_cache import sha256_file
from agent_core.p_value import background_trial_note, local_p_value_estimate


METHOD = "analytic_independent_source_catalog_correction_estimate"
NOTE = ("Local p values and significances are analytic half-chi-square estimates "
        "(dof=2 for fitted Gamma, dof=1 for fixed Gamma). Global estimates use "
        "p_global = 1 - (1 - p_local)^N_sources, following arXiv:2103.12813 Sec. IV A. "
        "This assumes independent source tests; overlapping source hypotheses can be correlated. "
        "It covers the selected source catalog only, not additional catalog selections, spectra "
        "or stacking hypotheses. No empirical calibration is implied. Global significance "
        "is the signed one-sided Gaussian Z; the table displays max(0, Z), following paper "
        "Table I, while the CSV retains both values. sqrt(TS) is the figure coordinate, "
        "not a significance conversion for fitted Gamma. At ns=0, Gamma is not a spectral measurement.")
GLOBAL_COLUMNS = ("post_trial_p_approx", "post_trial_significance",
                  "post_trial_excess_significance", "post_trial_method", "post_trial_n_sources")


def catalog_p_value_estimate(ts, gamma_mode, n_sources):
    """Evaluate the paper's correction in log space, including very small tails."""
    if isinstance(n_sources, bool) or int(n_sources) != n_sources or n_sources < 1:
        raise ValueError("Catalog trial count must be a positive integer")
    local = local_p_value_estimate(ts, gamma_mode)
    log_p = (-math.log(2.) - max(float(ts), 0.) / 2. if gamma_mode == "fitted"
             else float(log_ndtr(-math.sqrt(max(float(ts), 0.)))))
    # exp(log_p) may underflow; N*p is the accurate small-p limit in that case.
    log_global = math.log(n_sources) + log_p
    if log_global < -36.:
        p_global = math.exp(log_global)
        z_global = float(-ndtri_exp(log_global))
    else:
        log_survival = n_sources * math.log1p(-local["pre_trial_p"])
        p_global = -math.expm1(log_survival)
        z_global = (float(ndtri_exp(log_survival)) if p_global > .5
                    else float(-ndtri_exp(math.log(p_global))))
    return {"post_trial_p_approx": p_global, "post_trial_significance": z_global,
            "post_trial_excess_significance": max(0., z_global),
            "post_trial_method": METHOD, "post_trial_n_sources": int(n_sources)}


def ranked_sources(records):
    # TS breaks ties when a floating-point p value has underflowed to zero.
    return sorted(records, key=lambda item: (item["fit"]["pre_trial_p"],
                  -item["fit"]["pre_trial_significance"], item["source_number"]))


def compact_scan_table(records):
    """Separate p value/significance columns, with grouped local/global headings."""
    headers = ["Source", "ns", "Γ", "TS", "p value", "significance", "p value", "significance"]
    rows = [[str(item["source_name"]).replace("\n", " ").replace("\r", " ").replace("\t", " "),
             f"{item['fit']['ns']:.2f}", f"{item['fit']['gamma']:.3f}", f"{item['fit']['TS']:.3f}",
             f"{item['fit']['pre_trial_p']:.4g}", f"{item['fit']['pre_trial_significance']:.3f}σ",
             f"{item['fit']['post_trial_p_approx']:.4g}",
             (f"{item['fit']['post_trial_excess_significance']:.3f}σ"
              if item['fit']['post_trial_excess_significance'] > 0 else "0σ")]
            for item in ranked_sources(records)[:5]]
    widths = [max(len(row[i]) for row in [headers, *rows]) for i in range(len(headers))]
    prefix = sum(widths[:4]) + 4
    group_width = widths[4] + 1 + widths[5]
    lines = [" " * prefix + "Local".center(group_width) + " " + "Global".center(group_width),
             " ".join(h.ljust(w) if i == 0 else h.rjust(w) for i, (h, w) in enumerate(zip(headers, widths))) ]
    lines.extend(" ".join(v.ljust(w) if i == 0 else v.rjust(w)
                          for i, (v, w) in enumerate(zip(row, widths))) for row in rows)
    return "\n".join(lines)


def add_catalog_scan_estimates(result):
    records = result.get("source_results", [])
    if not records:
        return
    for item in records:
        fit = item["fit"]
        fit.update(catalog_p_value_estimate(fit["TS"], fit["gamma_mode"], len(records)))
    for rank, item in enumerate(ranked_sources(records), 1):
        item["significance_rank"] = rank
    best = ranked_sources(records)[0]["fit"]
    result.update(catalog_post_trial_p=best["post_trial_p_approx"],
                  catalog_post_trial_significance=best["post_trial_significance"],
                  catalog_post_trial_excess_significance=best["post_trial_excess_significance"],
                  catalog_post_trial_method=METHOD)
    result.setdefault("catalog_scan_summary", {}).update({
        "schema_version": 1, "n_sources": len(records), "method": METHOD,
        "scope": "selected_catalog_individual_source_scan", "note": NOTE,
        "background_trial_note": background_trial_note(best["pre_trial_significance"], best["post_trial_significance"]),
        "top_five_source_numbers": [item["source_number"] for item in ranked_sources(records)[:5]]})
    result["catalog_post_trial_note"] = NOTE


def sqrt_ts_histogram(records):
    values = np.sqrt([max(0., float(item["fit"]["TS"])) for item in records])
    # Include TS=0 and the rightmost source; empty bins stay in the numeric table.
    edges = np.arange(max(1, math.ceil(float(values.max()) / .25)) + 1) * .25
    counts, _ = np.histogram(values, bins=edges)
    return [dict(bin_left=float(left), bin_right=float(right),
                 sqrt_ts_center=float((left + right) / 2.), count=int(count),
                 poisson_error=float(math.sqrt(count)))
            for left, right, count in zip(edges[:-1], edges[1:], counts)]


def write_catalog_scan_outputs(run_dir, result, root):
    records = result.get("source_results", [])
    if not records or not all(math.isfinite(item["fit"]["TS"]) and item["fit"]["TS"] >= 0 for item in records):
        return  # The fit review rejects invalid TS; never create a misleading plot.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    run_dir, root = Path(run_dir), Path(root)
    summary = result["catalog_scan_summary"]
    rows = sqrt_ts_histogram(records)
    table = run_dir / "sqrt_ts_distribution_bins.csv"
    write_csv(table, list(rows[0]), rows)
    figure_dir = root / "figures" / run_dir.name
    figure_dir.mkdir(parents=True, exist_ok=True)
    stem = figure_dir / "sqrt_ts_distribution"
    settings = {"font.family": "serif", "mathtext.fontset": "stix", "font.size": 12,
                "pdf.fonttype": 42, "axes.linewidth": 1.}
    with plt.rc_context(settings):
        fig, ax = plt.subplots(figsize=(6.6, 4.5), layout="constrained")
        nonempty = [row for row in rows if row["count"] > 0]
        # A lower error endpoint of zero is outside a log axis; keep the full sqrt(N)
        # values in the CSV and clip only the drawn endpoint to the plot's lower limit.
        counts = np.array([row["count"] for row in nonempty])
        errors = np.sqrt(counts)
        ax.errorbar([row["sqrt_ts_center"] for row in nonempty], counts,
                    yerr=[np.minimum(errors, counts - .6), errors],
                    fmt="o", color="#2458a6", ms=4, capsize=2, lw=1.)
        ax.set(xlabel=r"$\sqrt{\mathrm{TS}}$", ylabel="Number of sources in each bin",
               yscale="log", xlim=(0., rows[-1]["bin_right"] + .125),
               ylim=(.6, max(counts + errors) * 2.5))
        ax.tick_params(which="both", direction="in", top=True, right=True)
        zero = sum(item["fit"]["TS"] == 0 for item in records)
        ax.text(.97, .96, f"{len(records)} sources; {zero} with TS = 0\nBin width = 0.25",
                transform=ax.transAxes, ha="right", va="top", fontsize=10)
        for extension in ("pdf", "png"):
            fig.savefig(stem.with_suffix("." + extension), dpi=180)
        plt.close(fig)
    files = {"sqrt_ts_bins": str(table), "sqrt_ts_pdf": str(stem.with_suffix(".pdf")),
             "sqrt_ts_png": str(stem.with_suffix(".png"))}
    result.setdefault("generated_files", {}).update(files)
    result.setdefault("figures", []).extend([files["sqrt_ts_pdf"], files["sqrt_ts_png"]])
    summary.update(files, bin_width=.25, zero_ts_sources=zero,
                   histogram_sources=sum(row["count"] for row in rows), normal_distribution_fit=False)
    summary["output_sha256"] = {name: sha256_file(path) for name, path in files.items()}


def review_catalog_scan_outputs(result, table):
    """Historical scans without this declared output schema keep their original review."""
    import csv
    summary = result.get("catalog_scan_summary")
    if summary is None:
        if any("post_trial_method" in item.get("fit", {}) for item in result.get("source_results", [])):
            return {"dr2_scan_reporting": False}
        return {}
    records = result.get("source_results", [])
    try:
        count = len(records)
        statistics_ok = (summary["schema_version"] == 1 and summary["method"] == METHOD
                         and summary["n_sources"] == count and len(table) == count)
        best = ranked_sources(records)[0]["fit"]
        statistics_ok = (statistics_ok and result["catalog_post_trial_p"] == best["post_trial_p_approx"]
                         and result["catalog_post_trial_significance"] == best["post_trial_significance"]
                         and result["catalog_post_trial_excess_significance"] == best["post_trial_excess_significance"]
                         and result["catalog_post_trial_method"] == METHOD)
        for item, row in zip(records, table):
            fit = item["fit"]
            expected = catalog_p_value_estimate(fit["TS"], fit["gamma_mode"], count)
            for key, value in expected.items():
                if isinstance(value, str):
                    statistics_ok = statistics_ok and fit[key] == value and row[key] == value
                else:
                    statistics_ok = (statistics_ok and fit[key] == value
                                     and math.isclose(float(row[key]), value, rel_tol=1e-12, abs_tol=1e-12))
            statistics_ok = statistics_ok and int(row["significance_rank"]) == item["significance_rank"]
        for rank, item in enumerate(ranked_sources(records), 1):
            statistics_ok = statistics_ok and item["significance_rank"] == rank
        statistics_ok = (statistics_ok and summary["top_five_source_numbers"] == [i["source_number"] for i in ranked_sources(records)[:5]])
        with Path(summary["sqrt_ts_bins"]).open(newline="") as handle:
            bins = list(csv.DictReader(handle))
        expected_bins = sqrt_ts_histogram(records)
        histogram_ok = len(bins) == len(expected_bins)
        for row, expected in zip(bins, expected_bins):
            histogram_ok = histogram_ok and all(math.isclose(float(row[k]), v, rel_tol=1e-12, abs_tol=1e-12)
                                                for k, v in expected.items())
        histogram_ok = (histogram_ok and summary["histogram_sources"] == count
                        and summary["zero_ts_sources"] == sum(i["fit"]["TS"] == 0 for i in records)
                        and summary["bin_width"] == .25 and summary["normal_distribution_fit"] is False)
        artifacts_ok = all(Path(summary[key]).is_file() and
                           sha256_file(summary[key]) == summary["output_sha256"][key]
                           for key in ("sqrt_ts_bins", "sqrt_ts_pdf", "sqrt_ts_png"))
        return {"dr2_scan_global_estimates": statistics_ok,
                "dr2_scan_histogram": histogram_ok, "dr2_scan_artifacts": artifacts_ok}
    except (KeyError, ValueError, TypeError, OSError, OverflowError):
        return {"dr2_scan_reporting": False}
