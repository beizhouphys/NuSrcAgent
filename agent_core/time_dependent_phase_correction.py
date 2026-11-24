"""Response-phase source grouping for fixed-profile time-dependent reports.

Grouping changes only the analytic multiplicity estimate.  It never changes
the observed fits or the shared-trial empirical null distributions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


IC86_SEASONS = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI")


def response_name(dataset: str) -> str:
    return "IC86_I-XI" if dataset.startswith("IC86_") else dataset


def response_uptime(
    uptime_directory: Path, datasets: list[str] | tuple[str, ...]
) -> dict[str, list[tuple[float, float]]]:
    """Load good-run intervals for only the selected detector datasets."""
    groups: dict[str, list[tuple[float, float]]] = {}
    for dataset in datasets:
        seasons = (
            [f"IC86_{season}" for season in IC86_SEASONS]
            if dataset == "IC86_I-XI" else [dataset]
        )
        for season in seasons:
            path = uptime_directory / f"{season}_exp.csv"
            if not path.is_file():
                raise FileNotFoundError(f"missing selected detector uptime: {path}")
            intervals = np.atleast_2d(np.loadtxt(path))
            if intervals.shape[1] < 2 or not np.isfinite(intervals[:, :2]).all():
                raise ValueError(f"invalid detector uptime: {path}")
            if np.any(intervals[:, 0] >= intervals[:, 1]):
                raise ValueError(f"nonpositive detector uptime interval: {path}")
            groups.setdefault(response_name(dataset), []).extend(
                (float(start), float(stop)) for start, stop in intervals[:, :2]
            )
    return groups


def assign_sources_to_response(
    selected: list[dict[str, Any]],
    time_profile: dict[str, Any],
    uptime: dict[str, list[tuple[float, float]]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Assign by box stop or Gaussian center; preserve a sole-overlap fallback."""
    profile = time_profile.get("type", "box")
    if profile not in {"box", "gaussian"}:
        raise ValueError(f"unsupported time profile for response grouping: {profile}")
    assignments: list[dict[str, Any]] = []
    for source in selected:
        start = float(source["time_start_mjd"])
        stop = float(source["time_end_mjd"])
        anchor = stop if profile == "box" else float(source["time_anchor_mjd"])
        matching = [
            group for group, intervals in uptime.items()
            if any(begin <= anchor <= end for begin, end in intervals)
        ]
        method = "box_stop_within_good_run" if profile == "box" else "gaussian_center_within_good_run"
        if not matching:
            matching = [
                group for group, intervals in uptime.items()
                if min(begin for begin, _ in intervals) <= anchor <= max(end for _, end in intervals)
            ]
            method = "anchor_within_response_period"
        if not matching:
            matching = [
                group for group, intervals in uptime.items()
                if any(begin <= stop and end >= start for begin, end in intervals)
            ]
            method = "anchor_outside_good_run_sole_window_overlap"
        if len(matching) != 1:
            raise ValueError(
                f"source {source['name']} has {len(matching)} response-group assignments: {matching}"
            )
        assignments.append(
            {"response_phase": matching[0], "phase_assignment": method,
             "phase_assignment_mjd": anchor}
        )
    counts = {
        group: sum(item["response_phase"] == group for item in assignments)
        for group in uptime
    }
    return assignments, counts


def sidak_by_response(local_p: float, count: int) -> float:
    """Evaluate 1-(1-p)^count accurately for small p, with endpoint handling."""
    if not 0.0 <= local_p <= 1.0 or count < 1:
        raise ValueError("phase Šidák correction requires 0<=p<=1 and count>=1")
    return 1.0 if local_p == 1.0 else -float(np.expm1(count * np.log1p(-local_p)))
