"""Reproducible-runtime and data preflight checks for supported analyses."""

from __future__ import annotations

import sys
from importlib import metadata
from pathlib import Path
from typing import Any, Dict, List


TESTED_PYTHON = (3, 12)
PINNED_PACKAGES = {
    "astropy": "8.0.1",
    "numpy": "2.5.1",
    "reportlab": "5.0.0",
    "scipy": "1.18.0",
    "skyllh": "26.0.0",
}
DR2_DATASET_NAMES = ("IC40", "IC59", "IC79", "IC86_I-XI")
DR2_SEASON_NAMES = (
    "IC40", "IC59", "IC79", "IC86_I", "IC86_II", "IC86_III", "IC86_IV",
    "IC86_V", "IC86_VI", "IC86_VII", "IC86_VIII", "IC86_IX", "IC86_X", "IC86_XI",
)
TEN_YEAR_DATASET_NAMES = ("IC40", "IC59", "IC79", "IC86_I", "IC86_II2VII_exp_BZ")


def check_environment(repo_root: str | Path, data_sample: str, likelihood_mode: str | None = None) -> Dict[str, Any]:
    """Return a machine-readable preflight result without importing a backend."""
    root = Path(repo_root).resolve()
    checks: List[Dict[str, Any]] = []

    expected_prefix = root / ".venv"
    actual_prefix = Path(sys.prefix).resolve()
    _append_check(
        checks,
        "project_virtual_environment",
        actual_prefix == expected_prefix.resolve(),
        str(actual_prefix),
        str(expected_prefix),
        "Run commands with .venv/bin/python.",
    )
    actual_python = tuple(sys.version_info[:2])
    _append_check(
        checks,
        "python_version",
        actual_python == TESTED_PYTHON,
        ".".join(map(str, actual_python)),
        ".".join(map(str, TESTED_PYTHON)),
        "Recreate .venv with Python 3.12.",
    )

    for package, expected in PINNED_PACKAGES.items():
        try:
            actual = metadata.version(package)
        except metadata.PackageNotFoundError:
            actual = None
        _append_check(
            checks,
            f"package:{package}",
            actual == expected,
            actual,
            expected,
            "Install requirements_skyllh_v26_lock_cdx.txt with --require-hashes.",
        )

    selected_mode = likelihood_mode or ("spatial_energy" if data_sample == "icecube_public_ps_14yr_dr2" else "spatial_only")
    required_paths = _required_paths(data_sample, selected_mode)
    missing = [str(path) for path in required_paths if not (root / path).is_file()]
    _append_check(
        checks,
        f"data:{data_sample}",
        not missing,
        {"required_file_count": len(required_paths), "missing": missing},
        "all required files present",
        "Restore the selected public-data release and its pre-calculated PDF products.",
    )

    failed = [check for check in checks if check["status"] == "fail"]
    return {
        "status": "fail" if failed else "pass",
        "data_sample": data_sample,
        "likelihood_mode": selected_mode,
        "repo_root": str(root),
        "interpreter": sys.executable,
        "checks": checks,
    }


def _append_check(
    checks: List[Dict[str, Any]],
    name: str,
    passed: bool,
    actual: Any,
    expected: Any,
    remediation: str,
) -> None:
    checks.append(
        {
            "name": name,
            "status": "pass" if passed else "fail",
            "actual": actual,
            "expected": expected,
            "remediation": None if passed else remediation,
        }
    )


def _required_paths(data_sample: str, likelihood_mode: str | None = None) -> List[Path]:
    if data_sample == "icecube_public_ps_14yr_dr2":
        base = Path("data_input/IceCube_data_released/2026_icecube_14_year_track_data_IceTracks_DR2")
        selected_mode = likelihood_mode or "spatial_energy"
        if selected_mode not in {"spatial_energy", "spatial_only"}:
            raise ValueError(f"Unsupported likelihood mode: {selected_mode}")
        result = [
            base / "DR2_readme.txt",
            Path("data_output/bkgd_pdfs_cdx/14yr_dr2_cdx/background_pdf_provenance_DR2_cdx.json"),
        ]
        if selected_mode == "spatial_energy":
            result.append(Path("data_output/signal_energy_pdfs_cdx/14yr_dr2_cdx/signal_energy_pdf_powerlaw_provenance_DR2_cdx.json"))
        for name in DR2_SEASON_NAMES:
            result.append(base / f"events/{name}_exp.csv")
            result.append(base / f"uptime/{name}_exp.csv")
        for name in ("IC40", "IC59", "IC79", "IC86"):
            result.append(base / f"irfs/{name}_effectiveArea.csv")
            result.append(base / f"irfs/{name}_smearing.csv")
        for name in DR2_DATASET_NAMES:
            result.append(Path(f"data_output/bkgd_pdfs_cdx/14yr_dr2_cdx/bkgd_pdf_{name}_exp_DR2_cdx.txt"))
            if selected_mode == "spatial_energy":
                result.append(Path(f"data_output/signal_energy_pdfs_cdx/14yr_dr2_cdx/signal_energy_pdf_powerlaw_{name}_DR2_cdx.npz"))
        return result
    if data_sample == "icecube_public_ps_10yr":
        if likelihood_mode not in {None, "spatial_only"}:
            raise ValueError("The 10-year environment supports likelihood_mode='spatial_only' only")
        base = Path("data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source")
        result = []
        for name in TEN_YEAR_DATASET_NAMES:
            final_period = name == "IC86_II2VII_exp_BZ"
            event_filename = "IC86_II2VII_exp_BZ.csv" if final_period else f"{name}_exp.csv"
            irf_name = "IC86_II" if final_period else name
            bkgd_filename = "bkgd_pdf_IC86_II2VII_exp_BZ_cdx.txt" if final_period else f"bkgd_pdf_{name}_exp_cdx.txt"
            result.extend(
                [
                    base / "events/uncorrected_probably" / event_filename,
                    base / "uptime" / event_filename,
                    base / f"irfs/{irf_name}_effectiveArea.csv",
                    Path("data_output/bkgd_pdfs_cdx") / bkgd_filename,
                ]
            )
        return result
    raise ValueError(f"Unsupported data sample: {data_sample}")
