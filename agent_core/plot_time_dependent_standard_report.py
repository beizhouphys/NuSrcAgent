#!/usr/bin/env python3
"""Render the standard time-dependent catalog figures from saved results.

This script is deliberately analysis-free: it consumes the machine-readable
products of a completed catalog run and never refits the data.  By default it
writes a separate ``standardized_report/`` directory below the run directory.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import textwrap
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import chi2, norm

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent_core.time_dependent_phase_correction import (
    assign_sources_to_response,
    response_uptime,
    sidak_by_response,
)


PROFILE = "td_catalog_standard_v1"
MJD_EPOCH = datetime(1858, 11, 17)
SIGMA_LEVELS = np.asarray([1.0, 2.0, 3.0])
SIGMA_P_VALUES = norm.sf(SIGMA_LEVELS)
CONTOUR_LEVELS = (2.30, 5.99)
CONTOUR_LABELS = {2.30: "68%", 5.99: "95%"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result_dir", type=Path, help="completed analysis result directory")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="output directory (default: RESULT_DIR/standardized_report)",
    )
    parser.add_argument(
        "--uptime-dir",
        type=Path,
        help="directory containing phase *_exp.csv files; inferred from metadata by default",
    )
    parser.add_argument(
        "--post-trial",
        choices=("empirical", "sidak", "phase-sidak"),
        default="phase-sidak",
        help="post-trial series shown in the lower timeline panel; phase-sidak groups by detector response at the box stop or Gaussian center",
    )
    parser.add_argument("--catalog-label", help="optional presentation-label override")
    parser.add_argument("--dataset-label", help="optional presentation-label override")
    parser.add_argument(
        "--single-source",
        help="exact source name, source ID, or zero-based source index to plot individually",
    )
    parser.add_argument(
        "--source-surface",
        type=Path,
        help=(
            "saved likelihood-surface NPZ for --single-source; by default use "
            "single_src/<normalized-name>_likelihood_contour.npz when present"
        ),
    )
    parser.add_argument(
        "--allow-unvalidated",
        action="store_true",
        help="render diagnostic plots even when validation.json is absent or fails",
    )
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return value


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty table {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def mjd_to_datetime(mjd: float) -> datetime:
    return MJD_EPOCH + timedelta(days=float(mjd))


def safe_name(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
    return normalized or "source"


def apply_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["STIXGeneral", "DejaVu Serif"],
            "mathtext.fontset": "stix",
            "font.size": 13,
            "axes.labelsize": 13,
            "axes.titlesize": 16,
            "axes.linewidth": 1.05,
            "xtick.labelsize": 12,
            "ytick.labelsize": 12,
            "axes.facecolor": "white",
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )


def style_ticks(ax: plt.Axes) -> None:
    """Match the major/minor tick hierarchy used by the flux figures."""

    ax.tick_params(which="both", direction="in", top=True, right=True)
    ax.tick_params(which="major", length=7, width=1)
    ax.tick_params(which="minor", length=3.5, width=0.8)


def validate_run(root: Path, summary: dict[str, Any], allow_unvalidated: bool) -> dict[str, Any]:
    path = root / "validation.json"
    if not path.is_file():
        if allow_unvalidated:
            return {"validation_file_present": False}
        raise ValueError(f"missing validation file: {path}")
    validation = read_json(path)
    failed = [key for key, value in validation.items() if isinstance(value, bool) and not value]
    n_trials = int(summary["n_background_trials"])
    unique_seeds = validation.get("n_unique_seeds")
    if unique_seeds is not None and int(unique_seeds) != n_trials:
        failed.append("n_unique_seeds")
    if failed and not allow_unvalidated:
        raise ValueError(f"run did not pass validation: {', '.join(sorted(set(failed)))}")
    return validation


def infer_uptime_paths(observed: dict[str, Any], explicit_dir: Path | None) -> list[Path]:
    if explicit_dir is not None:
        paths = sorted(explicit_dir.glob("*_exp.csv"))
    else:
        paths = []
        for phase in observed.get("precomputed_pdf_inputs", {}).values():
            for event_path in phase.get("event_paths", []):
                event = Path(event_path)
                if event.parent.name == "events":
                    candidate = event.parent.parent / "uptime" / event.name
                    if candidate.is_file():
                        paths.append(candidate)
        paths = sorted(set(paths))
    if not paths:
        raise ValueError(
            "could not resolve detector-phase uptime files; pass --uptime-dir explicitly"
        )
    return paths


def read_phases(paths: list[Path]) -> list[tuple[str, float, float]]:
    phases = []
    for path in paths:
        uptime = np.atleast_2d(np.loadtxt(path))
        if uptime.shape[1] < 2:
            raise ValueError(f"uptime file has fewer than two columns: {path}")
        label = path.stem.removesuffix("_exp").replace("_", "-")
        phases.append((label, float(np.min(uptime[:, 0])), float(np.max(uptime[:, 1]))))
    return sorted(phases, key=lambda item: item[1])


def read_source_windows(manifest_path: Path) -> list[tuple[float, float]]:
    """Read and validate selected-source time windows from the run manifest."""

    manifest = read_json(manifest_path)
    selected = manifest.get("selected")
    if not isinstance(selected, list) or not selected:
        raise ValueError(f"no selected sources found in {manifest_path}")
    windows = []
    for index, source in enumerate(selected):
        try:
            start = float(source["time_start_mjd"])
            stop = float(source["time_end_mjd"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(
                f"selected source {index} in {manifest_path} has no valid time window"
            ) from error
        if not np.isfinite(start) or not np.isfinite(stop) or stop < start:
            raise ValueError(
                f"selected source {index} in {manifest_path} has invalid window "
                f"[{start}, {stop}]"
            )
        windows.append((start, stop))
    return windows


def phases_overlapping_source_windows(
    phases: list[tuple[str, float, float]],
    windows: list[tuple[float, float]],
) -> list[tuple[str, float, float]]:
    """Keep phases intersecting at least one interval in the source-window union."""

    selected = [
        phase
        for phase in phases
        if any(phase[1] <= window_stop and phase[2] >= window_start for window_start, window_stop in windows)
    ]
    if not selected:
        raise ValueError("no detector phase overlaps any selected-source time window")
    return selected


def spectral_label(summary: dict[str, Any]) -> str:
    if summary.get("fit_gamma"):
        return (
            rf"$s$ fitted over "
            rf"[{float(summary['gamma_min']):.1f}, {float(summary['gamma_max']):.1f}]"
        )
    return rf"$s = {float(summary['fixed_gamma']):.1f}$"


def single_source_catalog_label(label: str) -> str:
    """Drop a stack-weight suffix from a single-source title when identifiable."""

    return re.sub(r"\s*\([^)]*stack[^)]*\)\s*$", "", label, flags=re.IGNORECASE)


def select_source(rows: list[dict[str, str]], selector: str) -> dict[str, str]:
    """Resolve one source by exact name, ID, or zero-based index."""

    folded = selector.casefold()
    matches = [
        row
        for row in rows
        if folded
        in {
            row["source_name"].casefold(),
            row["source_id"].casefold(),
            row["source_index"].casefold(),
        }
    ]
    if len(matches) != 1:
        raise ValueError(
            f"single-source selector {selector!r} matched {len(matches)} sources; "
            "use an exact source name, source ID, or source index"
        )
    return matches[0]


def resolve_background_npz(root: Path) -> Path:
    candidates = sorted(root.glob("background_trials_*.npz"))
    if len(candidates) != 1:
        raise ValueError(
            f"expected exactly one merged background_trials_*.npz in {root}, "
            f"found {[path.name for path in candidates]}"
        )
    return candidates[0]


def read_source_ts_trials(
    root: Path,
    source_index: int,
    n_trials: int,
) -> tuple[np.ndarray, float, Path, Path]:
    """Read one source's observed and shared-background TS arrays."""

    observed_path = root / "observed.npz"
    trials_path = resolve_background_npz(root)
    with np.load(observed_path, allow_pickle=False) as archive:
        observed_source_ts = np.asarray(archive["source_ts"], dtype=float)
    with np.load(trials_path, allow_pickle=False) as archive:
        trial_source_ts = np.asarray(archive["source_ts"], dtype=float)
    if trial_source_ts.ndim != 2 or trial_source_ts.shape[0] != n_trials:
        raise ValueError(
            f"source_ts in {trials_path} has shape {trial_source_ts.shape}; "
            f"expected ({n_trials}, n_sources)"
        )
    if source_index >= len(observed_source_ts) or source_index >= trial_source_ts.shape[1]:
        raise IndexError(f"source index {source_index} is outside the saved TS arrays")
    return (
        trial_source_ts[:, source_index],
        float(observed_source_ts[source_index]),
        observed_path,
        trials_path,
    )


def validate_source_surface(path: Path, source: dict[str, str]) -> None:
    """Reject an explicitly mismatched source likelihood surface."""

    with np.load(path, allow_pickle=False) as archive:
        required = {"ns", "gamma", "minus_2_delta_log_likelihood"}
        missing = required.difference(archive.files)
        if missing:
            raise ValueError(f"likelihood surface {path} is missing {sorted(missing)}")
        if "source_name" in archive:
            stored_name = str(np.asarray(archive["source_name"]).item())
            if stored_name and stored_name.casefold() != source["source_name"].casefold():
                raise ValueError(
                    f"likelihood surface {path} is for {stored_name!r}, not "
                    f"{source['source_name']!r}"
                )


def add_phase_context(
    ax: plt.Axes,
    phases: list[tuple[str, float, float]],
    *,
    label_phases: bool,
    visible_start_mjd: float,
    visible_stop_mjd: float,
) -> None:
    for index, (name, start, stop) in enumerate(phases):
        if index % 2 == 0:
            ax.axvspan(
                mjd_to_datetime(start),
                mjd_to_datetime(stop),
                color="#5b78b2",
                alpha=0.055,
                linewidth=0,
                zorder=0,
            )
        if index:
            ax.axvline(
                mjd_to_datetime(start), color="#526aa0", lw=0.7, alpha=0.55, zorder=1
            )
        if label_phases:
            visible_start = max(start, visible_start_mjd)
            visible_stop = min(stop, visible_stop_mjd)
            ax.text(
                mjd_to_datetime(0.5 * (visible_start + visible_stop)),
                1.23,
                name,
                color="#2f4781",
                fontsize=8.2,
                ha="center",
                va="center",
            )
def plot_source_timeline(
    output_stem: Path,
    rows: list[dict[str, str]],
    phases: list[tuple[str, float, float]],
    source_windows: list[tuple[float, float]],
    dataset_end_mjd: float,
    n_trials: int,
    title: str,
    post_trial: str,
) -> Path:
    rows = sorted(rows, key=lambda row: float(row["time_anchor_mjd"]))
    time_column = "phase_assignment_mjd" if post_trial == "phase-sidak" else "time_anchor_mjd"
    dates = np.asarray([mjd_to_datetime(float(row[time_column])) for row in rows])
    local_p = np.asarray([float(row["p_pre"]) for row in rows])
    post_field = {
        "empirical": "p_post_empirical_max_ts",
        "sidak": "p_post_sidak",
        "phase-sidak": "p_post_phase_sidak",
    }[post_trial]
    post_p = np.asarray([float(row[post_field]) for row in rows])
    ts = np.asarray([float(row["ts"]) for row in rows])
    floor = 1.0 / (n_trials + 1.0)
    best = int(np.argmin(local_p))

    apply_style()
    fig, axes = plt.subplots(2, 1, figsize=(16, 9), sharex=True, constrained_layout=True)
    labels = (
        "Pre-trial",
        {
            "empirical": "Post-trial (empirical max-TS)",
            "sidak": "Post-trial (Šidák, full catalog)",
            "phase-sidak": "Post-trial (response-group Šidák; joint-fit local $p$)",
        }[post_trial],
    )
    colors = ("#7752a5", "#d17c12")
    y_min = floor / 1.8
    anchor_min = min(float(row[time_column]) for row in rows)
    anchor_max = max(float(row[time_column]) for row in rows)
    coverage_start = min(start for start, _ in source_windows)
    coverage_stop = max(stop for _, stop in source_windows)
    display_start = min(coverage_start, anchor_min)
    display_stop = max(coverage_stop, anchor_max)
    padding = float(np.clip(0.02 * max(display_stop - display_start, 1.0), 5.0, 45.0))
    x_min_mjd = display_start - padding
    x_max_mjd = display_stop + padding

    for panel, (ax, values, label, color) in enumerate(
        zip(axes, (local_p, post_p), labels, colors)
    ):
        add_phase_context(
            ax,
            phases,
            label_phases=panel == 0,
            visible_start_mjd=x_min_mjd,
            visible_stop_mjd=x_max_mjd,
        )
        for probability in SIGMA_P_VALUES:
            ax.axhline(probability, color="#159b78", ls=":", lw=1.4, alpha=0.9, zorder=1)
        if panel == 0 or post_trial != "phase-sidak":
            ax.axhline(floor, color="#6b6b6b", ls="--", lw=0.9, alpha=0.7, zorder=1)
        ax.scatter(
            dates,
            values,
            s=27,
            color=color,
            edgecolors="white",
            linewidths=0.3,
            alpha=0.78,
            zorder=3,
        )
        ax.scatter(
            dates[best],
            values[best],
            marker="*",
            s=165,
            color="#f0b323",
            edgecolors="#40320a",
            linewidths=0.8,
            zorder=4,
        )
        ax.set_yscale("log")
        ax.set_ylim(y_min, 1.55)
        ax.set_xlim(mjd_to_datetime(x_min_mjd), mjd_to_datetime(x_max_mjd))
        ax.set_ylabel(f"{label} $p$-value")
        ax.grid(axis="y", which="major", color="0.86", lw=0.6)
        style_ticks(ax)

        right = ax.twinx()
        right.set_yscale("log")
        right.set_ylim(ax.get_ylim())
        right.set_yticks(SIGMA_P_VALUES, [rf"${int(value)}\sigma$" for value in SIGMA_LEVELS])
        right.set_ylabel("One-sided significance")
        style_ticks(right)

    axes[0].set_title(title)
    if x_min_mjd <= dataset_end_mjd <= x_max_mjd:
        for ax in axes:
            ax.axvline(
                mjd_to_datetime(dataset_end_mjd),
                color="#26364f",
                lw=1.1,
                ls="--",
                alpha=0.8,
                zorder=1,
            )
        axes[0].text(
            mjd_to_datetime(dataset_end_mjd),
            y_min * 1.15,
            "Data end",
            rotation=90,
            ha="right",
            va="bottom",
            fontsize=8,
            color="#26364f",
        )
    axes[0].annotate(
        f'{rows[best]["source_name"]}\nTS={ts[best]:.2f}',
        xy=(dates[best], local_p[best]),
        xytext=(16, 18),
        textcoords="offset points",
        fontsize=9,
        ha="left",
        va="bottom",
        arrowprops={"arrowstyle": "-", "color": "0.35", "lw": 0.8},
    )
    axes[1].xaxis.set_major_locator(mdates.YearLocator())
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axes[1].xaxis.set_minor_locator(mdates.MonthLocator(bymonth=(4, 7, 10)))
    axes[1].set_xlabel(
        ("Box end time" if rows[0]["time_profile"] == "box" else "Gaussian center time")
        if post_trial == "phase-sidak" else "Source time anchor"
    )
    axes[1].text(
        0.008,
        0.035,
        (
            "Analytic response-group correction of saved joint-fit local $p$; "
            "gray line in upper panel: local Monte Carlo floor"
            if post_trial == "phase-sidak" else
            r"Dashed gray: Monte Carlo floor $1/(N_\mathrm{trials}+1)$"
        ),
        transform=axes[1].transAxes,
        fontsize=8.5,
        color="0.35",
    )

    output_stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_stem.with_suffix(".png"), dpi=220, facecolor="white", metadata={"Creator": "NuSrcAgent"})
    fig.savefig(output_stem.with_suffix(".pdf"), facecolor="white", metadata={"Creator": "NuSrcAgent"})
    plt.close(fig)

    data_path = output_stem.with_name(f"{output_stem.name}_data.csv")
    plot_rows: list[dict[str, Any]] = []
    for row in rows:
        plot_rows.append(
            {
                **row,
                "source_date_iso": mjd_to_datetime(float(row[time_column])).date().isoformat(),
                "displayed_post_trial_method": post_trial,
                "displayed_post_trial_p": row[post_field],
            }
        )
    write_csv(data_path, plot_rows)
    return data_path


def plot_stacking_histogram(
    output_stem: Path,
    rows: list[dict[str, str]],
    summary: dict[str, Any],
    title: str,
) -> None:
    background_ts = np.asarray([float(row["ts"]) for row in rows], dtype=float)
    observed_ts = float(summary["observed_ts"])
    maximum = max(float(np.max(background_ts)), observed_ts, 1.0)
    bins = np.linspace(0.0, maximum * 1.025, 61)

    apply_style()
    fig, ax = plt.subplots(figsize=(9.2, 6.0), constrained_layout=True)
    _, edges, _ = ax.hist(
        background_ts,
        bins=bins,
        color="#7752a5",
        edgecolor="#4c3569",
        linewidth=0.45,
        alpha=0.82,
        label=f"Background ({len(background_ts):,} trials)",
    )
    show_asymptotic = bool(summary.get("asymptotic_null_distribution"))
    if show_asymptotic:
        expected = 0.5 * len(background_ts) * np.diff(chi2.cdf(edges, df=1))
        expected[0] += 0.5 * len(background_ts)
        ax.stairs(
            expected,
            edges,
            color="#404040",
            linewidth=2.0,
            linestyle="--",
            label=r"Asymptotic $\frac{1}{2}\delta(0)+\frac{1}{2}\chi^2_1$",
        )
    ax.axvline(
        observed_ts,
        color="#d17c12",
        linewidth=2.4,
        label=rf"Observed TS = {observed_ts:.3f}",
    )
    ax.set_yscale("log")
    ax.set_ylim(bottom=0.08)
    ax.set_xlabel("Stacking test statistic (TS)")
    ax.set_ylabel("Trials per bin")
    ax.set_title(textwrap.fill(title, width=68))
    ax.grid(axis="y", which="major", color="0.86", linewidth=0.65)
    style_ticks(ax)
    ax.legend(frameon=False, loc="upper right")
    annotation = (
        rf"$N_{{\rm bg}}(\mathrm{{TS}}\geq\mathrm{{TS}}_{{\rm obs}})"
        rf"={int(summary['n_background_ts_ge_observed'])}$"
        "\n"
        rf"$p_{{\rm scramble}}={float(summary['p_value']):.5f}$"
    )
    if show_asymptotic and "asymptotic_p_value" in summary:
        annotation += "\n" + rf"$p_{{\rm asymptotic}}={float(summary['asymptotic_p_value']):.5f}$"
    ax.text(0.96, 0.62, annotation, transform=ax.transAxes, ha="right", va="top", fontsize=11)

    output_stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_stem.with_suffix(".png"), dpi=220, facecolor="white", metadata={"Creator": "NuSrcAgent"})
    fig.savefig(output_stem.with_suffix(".pdf"), facecolor="white", metadata={"Creator": "NuSrcAgent"})
    plt.close(fig)


def plot_single_source_histogram(
    output_stem: Path,
    background_ts: np.ndarray,
    source: dict[str, str],
    show_asymptotic: bool,
    title: str,
) -> Path:
    """Plot one source's TS distribution from the shared background trials."""

    observed_ts = float(source["ts"])
    n_trials = len(background_ts)
    exceedances = int(source["n_exceedances"])
    p_value = float(source["p_pre"])
    computed_exceedances = int(np.count_nonzero(background_ts >= observed_ts))
    computed_p = (computed_exceedances + 1.0) / (n_trials + 1.0)
    if computed_exceedances != exceedances or not np.isclose(computed_p, p_value):
        raise ValueError(
            f"saved p-value fields for {source['source_name']} disagree with the trial TS array"
        )
    maximum = max(float(np.max(background_ts)), observed_ts, 1.0)
    bins = np.linspace(0.0, maximum * 1.025, 61)

    apply_style()
    fig, ax = plt.subplots(figsize=(9.2, 6.0), constrained_layout=True)
    _, edges, _ = ax.hist(
        background_ts,
        bins=bins,
        color="#7752a5",
        edgecolor="#4c3569",
        linewidth=0.45,
        alpha=0.82,
        label=f"Background ({n_trials:,} trials)",
    )
    asymptotic_p = None
    if show_asymptotic:
        expected = 0.5 * n_trials * np.diff(chi2.cdf(edges, df=1))
        expected[0] += 0.5 * n_trials
        asymptotic_p = 0.5 * float(chi2.sf(observed_ts, df=1))
        ax.stairs(
            expected,
            edges,
            color="#404040",
            linewidth=2.0,
            linestyle="--",
            label=r"Asymptotic $\frac{1}{2}\delta(0)+\frac{1}{2}\chi^2_1$",
        )
    ax.axvline(
        observed_ts,
        color="#d17c12",
        linewidth=2.4,
        label=rf"Observed TS = {observed_ts:.3f}",
    )
    ax.set_yscale("log")
    ax.set_ylim(bottom=0.08)
    ax.set_xlabel("Single-source test statistic (TS)")
    ax.set_ylabel("Trials per bin")
    ax.set_title(textwrap.fill(title, width=68))
    ax.grid(axis="y", which="major", color="0.86", linewidth=0.65)
    style_ticks(ax)
    ax.legend(frameon=False, loc="upper right")
    annotation = (
        rf"$N_{{\rm bg}}(\mathrm{{TS}}\geq\mathrm{{TS}}_{{\rm obs}})={exceedances}$"
        "\n"
        rf"$p_{{\rm local}}={p_value:.5g}$"
    )
    if asymptotic_p is not None:
        annotation += "\n" + rf"$p_{{\rm asymptotic}}={asymptotic_p:.5g}$"
    ax.text(0.96, 0.62, annotation, transform=ax.transAxes, ha="right", va="top", fontsize=11)

    output_stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_stem.with_suffix(".png"), dpi=220, facecolor="white", metadata={"Creator": "NuSrcAgent"})
    fig.savefig(output_stem.with_suffix(".pdf"), facecolor="white", metadata={"Creator": "NuSrcAgent"})
    plt.close(fig)

    data_path = output_stem.with_name(f"{output_stem.name}_data.csv")
    write_csv(
        data_path,
        [
            {"trial_index": index, "ts": float(ts)}
            for index, ts in enumerate(background_ts)
        ],
    )
    return data_path


def plot_likelihood_surface(
    surface_path: Path,
    output_stem: Path,
    title: str,
    axis_label: str,
    fallback_fit: dict[str, Any],
) -> None:
    with np.load(surface_path, allow_pickle=False) as archive:
        ns_values = np.asarray(archive["ns"], dtype=float)
        gammas = np.asarray(archive["gamma"], dtype=float)
        delta = np.asarray(archive["minus_2_delta_log_likelihood"], dtype=float)
        best_ns = float(archive["best_fit_ns"]) if "best_fit_ns" in archive else float(fallback_fit["ns"])
        best_gamma = (
            float(archive["best_fit_gamma"])
            if "best_fit_gamma" in archive
            else float("nan") if fallback_fit.get("gamma") is None else float(fallback_fit["gamma"])
        )
    if delta.shape != (len(gammas), len(ns_values)):
        raise ValueError(f"surface shape in {surface_path} does not match ns/s axes")

    apply_style()
    fig, ax = plt.subplots(figsize=(8.4, 6.4), constrained_layout=True)
    finite = delta[np.isfinite(delta)]
    available = [level for level in CONTOUR_LEVELS if finite.size and np.min(finite) <= level <= np.max(finite)]
    if available:
        boundary_colors = [
            ("#7752a5", "#d17c12")[index % 2] for index in range(len(available))
        ]
        fill_levels = sorted(
            set([max(0.0, float(np.min(finite))), *available])
        )
        if len(fill_levels) > 1:
            ax.contourf(
                ns_values,
                gammas,
                delta,
                levels=fill_levels,
                colors=boundary_colors[: len(fill_levels) - 1],
                alpha=0.10,
            )
        contours = ax.contour(
            ns_values,
            gammas,
            delta,
            levels=available,
            colors=boundary_colors,
            linewidths=1.5,
            linestyles="-",
        )
        ax.clabel(contours, inline=True, fontsize=9, fmt=CONTOUR_LABELS)

    if np.isclose(best_ns, 0.0) and not np.isfinite(best_gamma):
        ax.plot(
            np.zeros_like(gammas),
            gammas,
            color="#7752a5",
            linewidth=2.4,
            label=r"MLE ridge: $\hat n_s=0$, $s$ unidentified",
            zorder=5,
        )
    else:
        ax.scatter(
            [best_ns],
            [best_gamma],
            marker="*",
            s=180,
            color="black",
            edgecolor="black",
            linewidth=0.5,
            label=rf"MLE: $\hat n_s={best_ns:.2f}$, $\hat s={best_gamma:.2f}$",
            zorder=6,
        )
    ax.set_xlim(min(-0.45, float(ns_values[0])), float(ns_values[-1]))
    ax.set_ylim(float(gammas[0]), float(gammas[-1]))
    ax.set_xlabel(axis_label)
    ax.set_ylabel(r"Spectral index $s$")
    ax.set_title(textwrap.fill(title, width=68))
    ax.grid(color="0.88", alpha=0.65, linewidth=0.6)
    style_ticks(ax)
    ax.legend(frameon=False, loc="upper right")
    ax.text(
        0.98,
        0.04,
        "68% and 95% two-parameter likelihood-drop contours.",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=9,
        color="#4b4b4b",
    )
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_stem.with_suffix(".png"), dpi=220, facecolor="white", metadata={"Creator": "NuSrcAgent"})
    fig.savefig(output_stem.with_suffix(".pdf"), facecolor="white", metadata={"Creator": "NuSrcAgent"})
    plt.close(fig)


def main() -> None:
    args = parse_args()
    if args.source_surface is not None and args.single_source is None:
        raise ValueError("--source-surface requires --single-source")
    root = args.result_dir.resolve()
    output = (args.output_dir or root / "standardized_report").resolve()
    analysis_summary = read_json(root / "analysis_summary.json")
    observed = read_json(root / "observed.json")
    validation = validate_run(root, analysis_summary, args.allow_unvalidated)
    has_sources = bool(analysis_summary.get("has_source_component", True))
    has_stack = bool(analysis_summary.get("has_stacking_component", True))
    if not has_sources and not has_stack:
        raise ValueError("analysis_summary.json declares no renderable analysis component")
    stack_summary = (
        read_json(root / "stacking" / "summary.json") if has_stack else None
    )
    source_rows = (
        read_csv(root / "single_src" / "source_results.csv") if has_sources else []
    )
    stack_rows = (
        read_csv(root / "stacking" / "background_trials.csv") if has_stack else []
    )
    n_trials = int(analysis_summary["n_background_trials"])
    if has_stack and len(stack_rows) != n_trials:
        raise ValueError(f"expected {n_trials} stacking trials, found {len(stack_rows)}")
    if has_sources and len(source_rows) != int(analysis_summary["n_sources"]):
        raise ValueError("source result count does not match analysis_summary.json")
    all_phases = []
    source_windows = []
    phases = []
    uptime_paths: list[Path] = []
    if has_sources:
        uptime_paths = infer_uptime_paths(observed, args.uptime_dir)
        all_phases = read_phases(uptime_paths)
        source_windows = read_source_windows(root / "observed.sources.json")
        phases = phases_overlapping_source_windows(all_phases, source_windows)
    phase_group_counts: dict[str, int] = {}
    timeline_phases = phases
    if has_sources and args.post_trial == "phase-sidak":
        source_manifest = read_json(root / "observed.sources.json")
        selected_datasets = observed["time_dependent_engine"]["dataset_names"]
        grouped_spans = response_uptime(uptime_paths[0].parent, selected_datasets)
        assignments, phase_group_counts = assign_sources_to_response(
            source_manifest["selected"], source_manifest["time_profile"], grouped_spans
        )
        if len(assignments) != len(source_rows):
            raise ValueError("response-phase assignments do not match source results")
        for row, source, assignment in zip(source_rows, source_manifest["selected"], assignments):
            if row["source_name"] != source["name"]:
                raise ValueError("source results and manifest differ in order or membership")
            count = phase_group_counts[assignment["response_phase"]]
            phase_p = sidak_by_response(float(row["p_pre"]), count)
            if row.get("p_post_phase_sidak") not in (None, "") and not np.isclose(
                float(row["p_post_phase_sidak"]), phase_p, rtol=1e-12, atol=1e-12
            ):
                raise ValueError(f"saved response-phase p-value disagrees for {row['source_name']}")
            row.update(assignment)
            row["response_phase_n_sources"] = count
            row["p_post_phase_sidak"] = phase_p
            row["time_profile"] = source["time_profile"]
        timeline_phases = [
            (name.replace("_", " "), min(span[0] for span in spans), max(span[1] for span in spans))
            for name, spans in grouped_spans.items()
        ]

    selected_source = None
    selected_surface = None
    if args.single_source is not None:
        if not has_sources:
            raise ValueError("--single-source is unavailable for a stack-only result")
        selected_source = select_source(source_rows, args.single_source)
        if analysis_summary.get("fit_gamma"):
            source_slug = safe_name(selected_source["source_name"])
            selected_surface = (
                args.source_surface.resolve()
                if args.source_surface is not None
                else root / "single_src" / f"{source_slug}_likelihood_contour.npz"
            )
            if selected_surface.is_file():
                validate_source_surface(selected_surface, selected_source)
            elif args.source_surface is not None:
                raise ValueError(
                    f"no saved likelihood surface for {selected_source['source_name']}: "
                    f"{selected_surface}"
                )
            else:
                selected_surface = None

    catalog_label = args.catalog_label or str(analysis_summary["catalog_label"])
    dataset_label = args.dataset_label or str(analysis_summary["dataset_label"])
    spectrum = spectral_label(analysis_summary)
    generated = []
    if has_sources:
        timeline_stem = output / "single_src" / "source_pvalues_over_time"
        timeline_data = plot_source_timeline(
            timeline_stem,
            source_rows,
            timeline_phases,
            source_windows,
            all_phases[-1][2],
            n_trials,
            f"{single_source_catalog_label(catalog_label)} single-source scan ({spectrum})",
            args.post_trial,
        )
        generated.extend(
            (
                timeline_stem.with_suffix(".png"),
                timeline_stem.with_suffix(".pdf"),
                timeline_data,
            )
        )
    if has_stack:
        histogram_stem = output / "stacking" / "background_ts_histogram"
        plot_stacking_histogram(
            histogram_stem,
            stack_rows,
            stack_summary,
            f"{catalog_label} time-dependent stacking\n({dataset_label}; {spectrum})",
        )
        generated.extend(
            (histogram_stem.with_suffix(".png"), histogram_stem.with_suffix(".pdf"))
        )
    source_specific = None
    if selected_source is not None:
        source_index = int(selected_source["source_index"])
        source_trials, source_observed_ts, observed_npz, trials_npz = read_source_ts_trials(
            root, source_index, n_trials
        )
        if not np.isclose(source_observed_ts, float(selected_source["ts"])):
            raise ValueError(
                f"observed TS for {selected_source['source_name']} disagrees between "
                "source_results.csv and observed.npz"
            )
        source_slug = safe_name(selected_source["source_name"])
        source_histogram_stem = (
            output / "single_src" / f"{source_slug}_background_ts_histogram"
        )
        source_histogram_data = plot_single_source_histogram(
            source_histogram_stem,
            source_trials,
            selected_source,
            bool(
                has_stack
                and stack_summary
                and stack_summary.get("asymptotic_null_distribution")
            ),
            (
                f"{selected_source['source_name']} time-dependent single-source null distribution\n"
                f"({dataset_label}; {spectrum})"
            ),
        )
        generated.extend(
            (
                source_histogram_stem.with_suffix(".png"),
                source_histogram_stem.with_suffix(".pdf"),
                source_histogram_data,
            )
        )
        source_specific = {
            "source_index": source_index,
            "source_id": selected_source["source_id"],
            "source_name": selected_source["source_name"],
            "observed_npz": str(observed_npz),
            "background_trials_npz": str(trials_npz),
            "likelihood_surface": None,
            "likelihood_status": (
                "unavailable_not_saved"
                if analysis_summary.get("fit_gamma")
                else "not_applicable_fixed_gamma"
            ),
        }
        if selected_surface is not None:
            selected_contour_stem = (
                output / "single_src" / f"{source_slug}_likelihood_contour"
            )
            plot_likelihood_surface(
                selected_surface,
                selected_contour_stem,
                f"Observed single-source likelihood surface: {selected_source['source_name']}",
                r"Single-source signal count $n_s$",
                {"ns": selected_source["ns"], "gamma": selected_source.get("gamma") or None},
            )
            generated.extend(
                (
                    selected_contour_stem.with_suffix(".png"),
                    selected_contour_stem.with_suffix(".pdf"),
                )
            )
            source_specific["likelihood_surface"] = str(selected_surface)
            source_specific["likelihood_status"] = "rendered"
    if analysis_summary.get("fit_gamma") and has_sources:
        leading = analysis_summary["single_source"]
        source_slug = safe_name(str(leading["source_name"]))
        source_surface = root / "single_src" / f"{source_slug}_likelihood_contour.npz"
        selected_index = None if selected_source is None else int(selected_source["source_index"])
        if source_surface.is_file() and selected_index != int(leading["source_index"]):
            source_stem = output / "single_src" / f"{source_slug}_likelihood_contour"
            plot_likelihood_surface(
                source_surface,
                source_stem,
                f"Observed single-source likelihood surface: {leading['source_name']}",
                r"Single-source signal count $n_s$",
                {"ns": leading["ns"], "gamma": leading.get("gamma")},
            )
            generated.extend((source_stem.with_suffix(".png"), source_stem.with_suffix(".pdf")))
        stack_surface = root / "stacking" / "stacking_likelihood_contour.npz"
        if has_stack and stack_surface.is_file():
            stack_stem = output / "stacking" / "stacking_likelihood_contour"
            plot_likelihood_surface(
                stack_surface,
                stack_stem,
                f"Observed stacking likelihood surface: {catalog_label}",
                r"Stacked signal count $n_s$",
                {"ns": stack_summary["observed_ns"], "gamma": stack_summary.get("observed_gamma")},
            )
            generated.extend((stack_stem.with_suffix(".png"), stack_stem.with_suffix(".pdf")))

    generated = list(dict.fromkeys(generated))
    manifest_path = output / "plot_manifest.json"
    manifest = {
        "report_profile": PROFILE,
        "source_result_directory": str(root),
        "post_trial_display": args.post_trial,
        "phase_group_sidak": (
            {
                "source_assignment": "box stop or Gaussian center within response period; sole window-overlap fallback outside periods",
                "local_p_value_origin": "saved joint-phase single-source fits",
                "time_coordinate": (
                    "box stop MJD" if source_rows[0]["time_profile"] == "box" else "Gaussian center MJD"
                ),
                "formula": "1 - (1 - p_pre)**N_phase",
                "response_group_counts": phase_group_counts,
            }
            if args.post_trial == "phase-sidak" else None
        ),
        "n_sources": len(source_rows),
        "n_background_trials": n_trials,
        "selected_source": source_specific,
        "detector_phases": [
            {"name": name, "start_mjd": start, "stop_mjd": stop}
            for name, start, stop in phases
        ],
        "phase_selection": (
            {
                "method": "overlap_with_union_of_selected_source_windows",
                "n_available_phases": len(all_phases),
                "n_displayed_phases": len(phases),
                "source_window_extent_mjd": [
                    min(start for start, _ in source_windows),
                    max(stop for _, stop in source_windows),
                ],
            }
            if has_sources
            else {"method": "not_applicable_stack_only"}
        ),
        "validation": validation,
        "generated_files": [
            {"path": str(path), "sha256": sha256(path)} for path in generated
        ],
    }
    write_json(manifest_path, manifest)
    print(json.dumps({"manifest": str(manifest_path), **manifest}, indent=2))


if __name__ == "__main__":
    main()
