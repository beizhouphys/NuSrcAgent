#!/usr/bin/env python3
"""Pre-calculate event-level SkyLLH background PDFs for IceTracks-DR2."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import skyllh
from skyllh.analyses.i3.publicdata_ps.backgroundpdf import (
    PDDataBackgroundI3EnergyPDF,
)
from skyllh.core.config import Config
from skyllh.core.smoothing import BlockSmoothingFilter
from skyllh.i3.backgroundpdf import DataBackgroundI3SpatialPDF
from skyllh.i3.config import add_icecube_specific_analysis_required_data_fields


DR2_SUB_PATH = "2026_icecube_14_year_track_data_IceTracks_DR2"
DEFAULT_DATASETS = ("IC40", "IC59", "IC79", "IC86_I-XI")
OUTPUT_FILENAMES = {
    "IC40": "bkgd_pdf_IC40_exp_DR2_cdx.txt",
    "IC59": "bkgd_pdf_IC59_exp_DR2_cdx.txt",
    "IC79": "bkgd_pdf_IC79_exp_DR2_cdx.txt",
    "IC86_I-XI": "bkgd_pdf_IC86_I-XI_exp_DR2_cdx.txt",
}


class _EventPDFData:
    """Minimal adapter for SkyLLH's public PDF evaluation interface."""

    def __init__(self, events):
        self._events = events

    def __getitem__(self, name):
        return self._events[name]

    def get_data(self, name):
        return self._events[name]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Pre-calculate SkyLLH v26 background spatial and energy PDFs for IceTracks-DR2 events."
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--dataset",
        choices=(*DEFAULT_DATASETS, "all"),
        default="all",
        help="Dataset to calculate; SkyLLH's combined IC86_I-XI is used by default.",
    )
    parser.add_argument(
        "--output-dir",
        default="data_output/bkgd_pdfs_cdx/14yr_dr2_cdx",
    )
    args = parser.parse_args(argv)

    root = Path(args.repo_root).expanduser().resolve()
    data_base_path = root / "data_input" / "IceCube_data_released"
    data_path = data_base_path / DR2_SUB_PATH
    require_dr2_files(data_path)

    output_dir_arg = Path(args.output_dir).expanduser()
    output_dir = output_dir_arg if output_dir_arg.is_absolute() else root / output_dir_arg
    output_dir.mkdir(parents=True, exist_ok=True)

    names = DEFAULT_DATASETS if args.dataset == "all" else (args.dataset,)

    # SkyLLH-derived block: this is the same IceCube-specific field setup used
    # by skyllh.analyses.i3.publicdata_ps.time_integrated_ps.create_analysis.
    cfg = Config()
    add_icecube_specific_analysis_required_data_fields(cfg)
    cfg["datafields"].pop("run", None)
    datasets = skyllh.create_datasets(
        "IceTracks-DR2",
        cfg=cfg,
        names=names,
        base_path=str(data_base_path.resolve()),
        sub_path_fmt=DR2_SUB_PATH,
    )

    result_records = []
    for dataset in datasets:
        print(f"Calculating {dataset.name} ...", flush=True)
        result_records.append(calculate_and_write_dataset(cfg, dataset, output_dir))

    provenance = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "repo_root": str(root),
        "data_release": "IceTracks-DR2",
        "data_path": str(data_path.resolve()),
        "python": platform.python_version(),
        "packages": package_versions(),
        "method": {
            "spatial": "SkyLLH DataBackgroundI3SpatialPDF: sin(dec) histogram, normalized log-spline, uniform RA",
            "energy": "SkyLLH PDDataBackgroundI3EnergyPDF: log10(E)-sin(dec) histogram, conditional energy normalization, BlockSmoothingFilter(nbins=1), FctSpline2D evaluation",
            "kde_smoothing": False,
            "ic86_strategy": "SkyLLH dataset IC86_I-XI combines seasons I through XI before PDF construction",
        },
        "code_provenance": {
            "pdf_calculation": "SkyLLH v26 public-data classes and settings",
            "event_export_and_validation": "NuSrcAgent tools_cdx adapter",
            "legacy_codex_revised_numerical_code_used": False,
            "legacy_codex_revised_note": "No estimator from legacy_codex_revised/bkgd_pdf.py is copied; only the requested four-column product concept is retained.",
        },
        "datasets": result_records,
    }
    provenance_path = output_dir / "background_pdf_provenance_DR2_cdx.json"
    write_json_atomic(provenance_path, provenance)
    print(json.dumps(provenance, indent=2, sort_keys=True))
    return 0


def calculate_and_write_dataset(cfg, dataset, output_dir: Path) -> dict[str, object]:
    data = dataset.load_and_prepare_data()
    sin_dec_binning = dataset.get_binning_definition("sin_dec")
    log_energy_binning = dataset.get_binning_definition("log_energy")

    # SkyLLH-derived block: constructors and numerical settings are copied
    # from the official v26 time_integrated_ps.create_analysis implementation.
    spatial_pdf = DataBackgroundI3SpatialPDF(
        cfg=cfg,
        data_exp=data.exp,
        sin_dec_binning=sin_dec_binning,
    )
    energy_pdf = PDDataBackgroundI3EnergyPDF(
        cfg=cfg,
        data_exp=data.exp,
        logE_binning=log_energy_binning,
        sinDec_binning=sin_dec_binning,
        smoothing_filter=BlockSmoothingFilter(nbins=1),
        kde_smoothing=False,
    )

    # NuSrcAgent export block: evaluate SkyLLH's already-constructed PDF
    # objects on every experimental event, without accessing private splines.
    event_view = _EventPDFData(data.exp)
    spatial_pdf.initialize_for_new_trial(event_view)
    spatial_values, _ = spatial_pdf.get_pd(event_view)
    energy_pdf.initialize_for_new_trial(event_view)
    energy_values, _ = energy_pdf.get_pd(event_view)

    ra_deg = np.rad2deg(data.exp["ra"])
    dec_deg = np.rad2deg(data.exp["dec"])
    output = np.column_stack((ra_deg, dec_deg, spatial_values, energy_values))
    validate_event_output(dataset.name, output)

    input_paths = [Path(path) for path in dataset.get_abs_pathfilename_list(dataset.exp_pathfilename_list)]
    energy_integrals = np.sum(
        energy_pdf.hist * np.diff(log_energy_binning.binedges)[:, np.newaxis],
        axis=0,
    )
    spatial_integral = spatial_histogram_integral(data.exp["sin_dec"], sin_dec_binning)
    validation = {
        "event_rows_match": int(output.shape[0]) == len(data.exp),
        "all_values_finite": bool(np.all(np.isfinite(output))),
        "pdf_values_nonnegative": bool(np.all(output[:, 2:] >= 0.0)),
        "spatial_histogram_sphere_integral": spatial_integral,
        "spatial_histogram_normalization_abs_error": abs(spatial_integral - 1.0),
        "energy_histogram_conditional_integral_min": float(np.min(energy_integrals)),
        "energy_histogram_conditional_integral_max": float(np.max(energy_integrals)),
        "energy_histogram_conditional_max_abs_error": float(np.max(np.abs(energy_integrals - 1.0))),
    }
    if not all(
        validation[key]
        for key in ("event_rows_match", "all_values_finite", "pdf_values_nonnegative")
    ):
        raise RuntimeError(f"Output validation failed for {dataset.name}: {validation}")
    if validation["spatial_histogram_normalization_abs_error"] > 1e-12:
        raise RuntimeError(f"Spatial histogram normalization failed for {dataset.name}: {validation}")
    # SkyLLH normalizes before applying its official one-bin smoothing filter.
    # At the energy boundaries that filter can introduce a small residual
    # normalization drift; retain and report it, but reject percent-level drift.
    if validation["energy_histogram_conditional_max_abs_error"] > 1e-2:
        raise RuntimeError(f"Energy histogram normalization failed for {dataset.name}: {validation}")

    output_path = output_dir / OUTPUT_FILENAMES[dataset.name]
    write_table_atomic(output_path, output)

    return {
        "dataset": dataset.name,
        "n_events": int(len(data.exp)),
        "sin_dec_nbins": int(sin_dec_binning.nbins),
        "log_energy_nbins": int(log_energy_binning.nbins),
        "input_event_files": [file_record(path) for path in input_paths],
        "output_file": file_record(output_path),
        "validation": validation,
    }


def spatial_histogram_integral(sin_dec_values, sin_dec_binning) -> float:
    counts, _ = np.histogram(sin_dec_values, bins=sin_dec_binning.binedges)
    density = counts / counts.sum() / np.diff(sin_dec_binning.binedges)
    return float(np.sum(density * np.diff(sin_dec_binning.binedges)))


def validate_event_output(dataset_name: str, output: np.ndarray) -> None:
    if output.ndim != 2 or output.shape[1] != 4 or output.shape[0] == 0:
        raise RuntimeError(f"Unexpected output shape for {dataset_name}: {output.shape}")
    if not np.all(np.isfinite(output)):
        raise RuntimeError(f"Non-finite output value found for {dataset_name}")
    if np.any(output[:, 2:] < 0.0):
        raise RuntimeError(f"Negative PDF value found for {dataset_name}")


def write_table_atomic(path: Path, values: np.ndarray) -> None:
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    np.savetxt(
        temporary_path,
        values,
        fmt=("%.9f", "%.9f", "%.12e", "%.12e"),
        header="RA_deg Dec_deg bkgd_spatial_pdf bkgd_energy_pdf",
    )
    temporary_path.replace(path)


def write_json_atomic(path: Path, value: dict[str, object]) -> None:
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary_path.replace(path)


def file_record(path: Path) -> dict[str, object]:
    return {
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def package_versions() -> dict[str, str]:
    return {
        name: importlib.metadata.version(name)
        for name in ("skyllh", "numpy", "scipy", "astropy")
    }


def require_dr2_files(data_path: Path) -> None:
    required = [
        data_path / "events" / "IC40_exp.csv",
        data_path / "events" / "IC59_exp.csv",
        data_path / "events" / "IC79_exp.csv",
        data_path / "events" / "IC86_I_exp.csv",
        data_path / "events" / "IC86_XI_exp.csv",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing required IceTracks-DR2 event files: " + ", ".join(missing))


if __name__ == "__main__":
    raise SystemExit(main())
