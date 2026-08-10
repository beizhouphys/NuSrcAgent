#!/usr/bin/env python3
"""Pre-calculate and interpolate IceTracks-DR2 signal-energy PDFs."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import skyllh
from scipy.integrate import quad
from scipy.interpolate import RegularGridInterpolator, interp1d
from skyllh.analyses.i3.publicdata_ps.aeff import PDAeff
from skyllh.analyses.i3.publicdata_ps.signalpdf import (
    PDSignalEnergyPDFSet,
)
from skyllh.analyses.i3.publicdata_ps.smearing_matrix import (
    PDSmearingMatrix,
)
from skyllh.core.config import Config
from skyllh.core.flux_model import (
    FunctionEnergyFluxProfile,
    PowerLawEnergyFluxProfile,
    SteadyPointlikeFFM,
)
from skyllh.core.parameters import ParameterGrid


DR2_SUB_PATH = "2026_icecube_14_year_track_data_IceTracks_DR2"
DEFAULT_DATASETS = ("IC40", "IC59", "IC79", "IC86_I-XI")
DEFAULT_OUTPUT_DIR = "data_output/signal_energy_pdfs_cdx/14yr_dr2_cdx"
POWERLAW_GAMMA_MIN = 0.9
POWERLAW_GAMMA_MAX = 6.1
POWERLAW_OUTPUT_FILENAMES = {
    name: f"signal_energy_pdf_powerlaw_{name}_DR2_cdx.npz"
    for name in DEFAULT_DATASETS
}


class SignalEnergyPDFTable:
    """Load a pre-calculated table and evaluate it without IRF convolution."""

    def __init__(self, path: Path | str):
        self.path = Path(path).expanduser().resolve()
        with np.load(self.path, allow_pickle=False) as table:
            self.dec_bin_edges_rad = table["dec_bin_edges_rad"].astype(np.float64)
            self.dec_bin_centers_rad = table["dec_bin_centers_rad"].astype(np.float64)
            self.log10_reco_energy = table["log10_reco_energy"].astype(np.float64)
            self.signal_energy_pdf = table["signal_energy_pdf"].astype(np.float64)
            self.spectrum_mode = str(table["spectrum_mode"].item())
            self.gamma_legacy = (
                table["gamma_legacy"].astype(np.float64)
                if "gamma_legacy" in table.files
                else None
            )

    def evaluate(self, dec_rad, log10_reco_energy, gamma_legacy=None):
        """Evaluate with native declination-bin selection and table interpolation."""
        dec, energy = np.broadcast_arrays(
            np.asarray(dec_rad, dtype=float),
            np.asarray(log10_reco_energy, dtype=float),
        )
        dec_idx = np.searchsorted(self.dec_bin_edges_rad, dec, side="right") - 1
        dec_idx = np.where(dec == self.dec_bin_edges_rad[-1], len(self.dec_bin_centers_rad) - 1, dec_idx)
        valid_dec = (dec_idx >= 0) & (dec_idx < len(self.dec_bin_centers_rad))
        result = np.zeros(dec.shape, dtype=float)

        if self.spectrum_mode == "power_law":
            if gamma_legacy is None:
                raise ValueError("gamma_legacy is required for a power-law table")
            gamma = np.broadcast_to(np.asarray(gamma_legacy, dtype=float), dec.shape)
            for idx in np.unique(dec_idx[valid_dec]):
                mask = valid_dec & (dec_idx == idx)
                interpolator = RegularGridInterpolator(
                    (self.log10_reco_energy, self.gamma_legacy),
                    self.signal_energy_pdf[idx],
                    bounds_error=False,
                    fill_value=0.0,
                )
                points = np.column_stack((energy[mask], gamma[mask]))
                result[mask] = interpolator(points)
        else:
            for idx in np.unique(dec_idx[valid_dec]):
                mask = valid_dec & (dec_idx == idx)
                result[mask] = np.interp(
                    energy[mask],
                    self.log10_reco_energy,
                    self.signal_energy_pdf[idx],
                    left=0.0,
                    right=0.0,
                )
        return result


class TabulatedFunctionEnergyFluxProfile(FunctionEnergyFluxProfile):
    """Concrete SkyLLH function profile for a user-supplied tabulated spectrum."""

    @property
    def math_function_str(self):
        return "tabulated dN/dE"

    def get_integral(self, E1, E2, unit=None):
        """Integrate a vectorized spectrum with SciPy's scalar quad API."""
        E1 = np.atleast_1d(E1).astype(float)
        E2 = np.atleast_1d(E2).astype(float)
        if unit is not None and unit != self.energy_unit:
            conversion = unit.to(self.energy_unit)
            E1 = E1 * conversion
            E2 = E2 * conversion

        def scalar_log_energy_function(log_energy):
            energy = np.exp(log_energy)
            dnde = float(np.asarray(self.function(energy)).reshape(-1)[0])
            return dnde * energy

        return np.array(
            [
                quad(scalar_log_energy_function, np.log(low), np.log(high), limit=200)[0]
                for low, high in zip(E1, E2, strict=True)
            ],
            dtype=float,
        )


def main(argv=None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    root = Path(args.repo_root).expanduser().resolve()
    data_base_path = root / "data_input" / "IceCube_data_released"
    data_path = data_base_path / DR2_SUB_PATH
    require_dr2_files(data_path)

    output_dir_arg = Path(args.output_dir).expanduser()
    output_dir = output_dir_arg if output_dir_arg.is_absolute() else root / output_dir_arg
    output_dir.mkdir(parents=True, exist_ok=True)

    names = DEFAULT_DATASETS if args.dataset == "all" else (args.dataset,)
    cfg = Config()
    datasets = skyllh.create_datasets(
        "IceTracks-DR2",
        cfg=cfg,
        names=names,
        base_path=str(data_base_path.resolve()),
        sub_path_fmt=DR2_SUB_PATH,
    )

    spectrum = None
    spectrum_record = None
    if args.mode == "realistic-spectrum":
        spectrum, spectrum_record = load_realistic_spectrum(
            Path(args.spectrum_file),
            spectrum_kind=args.spectrum_kind,
            energy_unit=args.energy_unit,
            outside_support=args.outside_support,
        )

    records = []
    for dataset in datasets:
        print(f"Calculating {args.mode} table for {dataset.name} ...", flush=True)
        if args.mode == "power-law":
            record = calculate_powerlaw_dataset(
                cfg=cfg,
                dataset=dataset,
                output_dir=output_dir,
                gamma_step=args.gamma_step,
                log_energy_step=args.log_energy_step,
                ncpu=args.ncpu,
            )
        else:
            record = calculate_realistic_dataset(
                cfg=cfg,
                dataset=dataset,
                output_dir=output_dir,
                spectrum=spectrum,
                spectrum_record=spectrum_record,
                output_label=args.output_label,
                log_energy_step=args.log_energy_step,
                ncpu=args.ncpu,
            )
        records.append(record)

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "mode": "power_law" if args.mode == "power-law" else "realistic_spectrum",
        "repo_root": str(root),
        "data_release": "IceTracks-DR2",
        "data_path": str(data_path.resolve()),
        "python": platform.python_version(),
        "packages": package_versions(),
        "method": method_record(),
        "spectrum": spectrum_record,
        "datasets": records,
    }
    if args.mode == "power-law":
        summary_path = output_dir / "signal_energy_pdf_powerlaw_provenance_DR2_cdx.json"
    else:
        summary_path = output_dir / f"signal_energy_pdf_realistic_{safe_label(args.output_label)}_provenance_DR2_cdx.json"
    write_json_atomic(summary_path, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pre-calculate SkyLLH v26 signal-energy PDFs for IceTracks-DR2."
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--dataset", choices=(*DEFAULT_DATASETS, "all"), default="all")
    parser.add_argument("--log-energy-step", type=positive_float, default=0.0025)
    parser.add_argument("--ncpu", type=positive_int, default=1)

    subparsers = parser.add_subparsers(dest="mode", required=True)
    powerlaw = subparsers.add_parser("power-law")
    powerlaw.add_argument("--gamma-step", type=positive_float, default=0.01)

    realistic = subparsers.add_parser("realistic-spectrum")
    realistic.add_argument("--spectrum-file", required=True)
    realistic.add_argument("--spectrum-kind", choices=("dnde", "ednde", "e2dnde"), required=True)
    realistic.add_argument("--energy-unit", choices=("GeV", "TeV"), required=True)
    realistic.add_argument("--outside-support", choices=("zero", "extrapolate"), required=True)
    realistic.add_argument("--output-label", required=True)
    return parser


def calculate_powerlaw_dataset(cfg, dataset, output_dir, gamma_step, log_energy_step, ncpu):
    gamma_internal = inclusive_grid(POWERLAW_GAMMA_MIN, POWERLAW_GAMMA_MAX, gamma_step)
    gamma_legacy = -gamma_internal[::-1]
    log_energy = dense_energy_centers(dataset, log_energy_step)
    sm = load_smearing_matrix(dataset)
    dec_edges = combined_response_dec_edges(dataset, sm)
    dec_centers = 0.5 * (dec_edges[:-1] + dec_edges[1:])
    values = np.empty((len(dec_centers), len(log_energy), len(gamma_legacy)), dtype=np.float32)

    # SkyLLH-derived numerical block: PDSignalEnergyPDFSet is the exact class
    # used by the official v26 time_integrated_ps analysis. It performs the
    # Aeff weighting, smearing-matrix marginalization, and PDF normalization.
    fluxmodel = SteadyPointlikeFFM(
        Phi0=1.0,
        energy_profile=PowerLawEnergyFluxProfile(E0=1.0e3, gamma=2.0, cfg=cfg),
        cfg=cfg,
    )
    gamma_grid = ParameterGrid(
        name="gamma",
        grid=gamma_internal,
        delta=gamma_step,
        decimals=decimal_places(gamma_step),
    )

    start = time.perf_counter()
    per_dec_seconds = []
    interpolation_l1_errors = []
    interpolation_max_abs_errors = []
    for dec_idx, dec in enumerate(dec_centers):
        dec_start = time.perf_counter()
        pdf_set = PDSignalEnergyPDFSet(
            cfg=cfg,
            ds=dataset,
            src_dec=float(dec),
            fluxmodel=fluxmodel,
            param_grid_set=gamma_grid,
            ncpu=ncpu,
            sm=sm,
        )
        for gamma_idx, gamma_user in enumerate(gamma_legacy):
            pdf = pdf_set.get_pdf({"gamma": float(abs(gamma_user))})
            values[dec_idx, :, gamma_idx] = pdf.get_pd_by_log10_reco_e(log_energy)
        # NuSrcAgent validation block: compare dense-table linear interpolation
        # against the original SkyLLH spline between adjacent table points.
        check_energy = 0.5 * (log_energy[:-1] + log_energy[1:])
        for gamma_idx in (0, len(gamma_legacy) // 2, len(gamma_legacy) - 1):
            pdf = pdf_set.get_pdf({"gamma": float(abs(gamma_legacy[gamma_idx]))})
            direct = pdf.get_pd_by_log10_reco_e(check_energy)
            interpolated = np.interp(
                check_energy,
                log_energy,
                values[dec_idx, :, gamma_idx].astype(float),
            )
            interpolation_l1_errors.append(
                float(np.sum(np.abs(interpolated - direct)) * log_energy_step)
            )
            interpolation_max_abs_errors.append(float(np.max(np.abs(interpolated - direct))))
        per_dec_seconds.append(time.perf_counter() - dec_start)
        print(
            f"  {dataset.name}: declination bin {dec_idx + 1}/{len(dec_centers)}",
            flush=True,
        )
    construction_seconds = time.perf_counter() - start

    validation = validate_powerlaw_table(
        values=values,
        log_energy=log_energy,
        log_energy_step=log_energy_step,
        gamma_legacy=gamma_legacy,
        dec_edges=dec_edges,
    )
    validation["energy_interpolation_fractional_l1_error_max"] = float(max(interpolation_l1_errors))
    validation["energy_interpolation_max_abs_error"] = float(max(interpolation_max_abs_errors))
    if validation["energy_interpolation_fractional_l1_error_max"] > 1e-3:
        raise RuntimeError(f"Dense energy interpolation validation failed: {validation}")
    output_path = output_dir / POWERLAW_OUTPUT_FILENAMES[dataset.name]
    write_table_atomic(
        output_path,
        dec_bin_edges_rad=dec_edges,
        dec_bin_centers_rad=dec_centers,
        log10_reco_energy=log_energy,
        gamma_legacy=gamma_legacy,
        gamma_skyllh=abs(gamma_legacy),
        signal_energy_pdf=values,
        spectrum_mode=np.array("power_law"),
        axis_order=np.array("declination_bin,log10_reco_energy,gamma_legacy"),
    )
    lookup_benchmark = benchmark_lookup(output_path, with_gamma=True)
    return dataset_record(
        dataset=dataset,
        sm=sm,
        output_path=output_path,
        values=values,
        dec_edges=dec_edges,
        log_energy=log_energy,
        validation=validation,
        construction_seconds=construction_seconds,
        per_dec_seconds=per_dec_seconds,
        lookup_benchmark=lookup_benchmark,
        extra={
            "gamma_legacy_min": float(gamma_legacy[0]),
            "gamma_legacy_max": float(gamma_legacy[-1]),
            "gamma_step": float(gamma_step),
            "n_gamma": int(len(gamma_legacy)),
        },
    )


def calculate_realistic_dataset(
    cfg,
    dataset,
    output_dir,
    spectrum,
    spectrum_record,
    output_label,
    log_energy_step,
    ncpu,
):
    log_energy = dense_energy_centers(dataset, log_energy_step)
    sm = load_smearing_matrix(dataset)
    dec_edges = combined_response_dec_edges(dataset, sm)
    dec_centers = 0.5 * (dec_edges[:-1] + dec_edges[1:])
    values = np.empty((len(dec_centers), len(log_energy)), dtype=np.float32)

    # SkyLLH-derived numerical block: FunctionEnergyFluxProfile uses the
    # user-supplied dN/dE function, while PDSignalEnergyPDFSet retains the same
    # official Aeff/smearing convolution as the power-law analysis.
    fluxmodel = SteadyPointlikeFFM(
        Phi0=1.0,
        energy_profile=TabulatedFunctionEnergyFluxProfile(function=spectrum, cfg=cfg),
        cfg=cfg,
    )
    # NuSrcAgent adapter: Phi0 is a harmless dummy grid because the normalized
    # signal-energy PDF is independent of the overall spectrum normalization.
    normalization_grid = ParameterGrid(name="Phi0", grid=np.array([1.0, 2.0]), delta=1.0, decimals=0)

    start = time.perf_counter()
    per_dec_seconds = []
    interpolation_l1_errors = []
    interpolation_max_abs_errors = []
    for dec_idx, dec in enumerate(dec_centers):
        dec_start = time.perf_counter()
        pdf_set = PDSignalEnergyPDFSet(
            cfg=cfg,
            ds=dataset,
            src_dec=float(dec),
            fluxmodel=fluxmodel,
            param_grid_set=normalization_grid,
            ncpu=ncpu,
            sm=sm,
        )
        pdf = pdf_set.get_pdf({"Phi0": 1.0})
        values[dec_idx] = pdf.get_pd_by_log10_reco_e(log_energy)
        check_energy = 0.5 * (log_energy[:-1] + log_energy[1:])
        direct = pdf.get_pd_by_log10_reco_e(check_energy)
        interpolated = np.interp(check_energy, log_energy, values[dec_idx].astype(float))
        interpolation_l1_errors.append(
            float(np.sum(np.abs(interpolated - direct)) * log_energy_step)
        )
        interpolation_max_abs_errors.append(float(np.max(np.abs(interpolated - direct))))
        per_dec_seconds.append(time.perf_counter() - dec_start)
        print(
            f"  {dataset.name}: declination bin {dec_idx + 1}/{len(dec_centers)}",
            flush=True,
        )
    construction_seconds = time.perf_counter() - start

    validation = validate_realistic_table(values, log_energy, log_energy_step, dec_edges)
    validation["energy_interpolation_fractional_l1_error_max"] = float(max(interpolation_l1_errors))
    validation["energy_interpolation_max_abs_error"] = float(max(interpolation_max_abs_errors))
    if validation["energy_interpolation_fractional_l1_error_max"] > 1e-3:
        raise RuntimeError(f"Dense energy interpolation validation failed: {validation}")
    filename = f"signal_energy_pdf_realistic_{safe_label(output_label)}_{dataset.name}_DR2_cdx.npz"
    output_path = output_dir / filename
    write_table_atomic(
        output_path,
        dec_bin_edges_rad=dec_edges,
        dec_bin_centers_rad=dec_centers,
        log10_reco_energy=log_energy,
        signal_energy_pdf=values,
        spectrum_mode=np.array("realistic_spectrum"),
        spectrum_sha256=np.array(spectrum_record["input_file"]["sha256"]),
        axis_order=np.array("declination_bin,log10_reco_energy"),
    )
    lookup_benchmark = benchmark_lookup(output_path, with_gamma=False)
    return dataset_record(
        dataset=dataset,
        sm=sm,
        output_path=output_path,
        values=values,
        dec_edges=dec_edges,
        log_energy=log_energy,
        validation=validation,
        construction_seconds=construction_seconds,
        per_dec_seconds=per_dec_seconds,
        lookup_benchmark=lookup_benchmark,
        extra={},
    )


def load_realistic_spectrum(path, spectrum_kind, energy_unit, outside_support):
    path = path.expanduser().resolve()
    data = np.loadtxt(path, comments="#", ndmin=2)
    if data.ndim != 2 or data.shape[1] < 2 or data.shape[0] < 2:
        raise ValueError("Spectrum file must contain at least two rows and two columns: energy and value")
    energy = np.asarray(data[:, 0], dtype=float)
    value = np.asarray(data[:, 1], dtype=float)
    if energy_unit == "TeV":
        energy = energy * 1.0e3
    if not np.all(np.isfinite(energy)) or not np.all(np.isfinite(value)):
        raise ValueError("Spectrum energy and value columns must be finite")
    if np.any(energy <= 0.0) or np.any(value <= 0.0):
        raise ValueError("Log-log spectrum interpolation requires strictly positive energies and values")
    order = np.argsort(energy)
    energy = energy[order]
    value = value[order]
    if np.any(np.diff(energy) <= 0.0):
        raise ValueError("Spectrum energies must be unique")
    if spectrum_kind == "ednde":
        dnde = value / energy
    elif spectrum_kind == "e2dnde":
        dnde = value / energy**2
    else:
        dnde = value

    log_energy = np.log(energy)
    log_dnde = np.log(dnde)
    fill_value = "extrapolate" if outside_support == "extrapolate" else -np.inf
    interpolator = interp1d(
        log_energy,
        log_dnde,
        kind="linear",
        bounds_error=False,
        fill_value=fill_value,
        assume_sorted=True,
    )

    def spectrum(energy_gev):
        energy_gev = np.asarray(energy_gev, dtype=float)
        result = np.zeros_like(energy_gev)
        valid = energy_gev > 0.0
        result[valid] = np.exp(interpolator(np.log(energy_gev[valid])))
        return result

    record = {
        "input_file": file_record(path),
        "input_columns": "energy,value",
        "input_spectrum_kind": spectrum_kind,
        "input_energy_unit": energy_unit,
        "converted_internal_spectrum_kind": "dnde",
        "internal_energy_unit": "GeV",
        "outside_support": outside_support,
        "energy_min_gev": float(energy[0]),
        "energy_max_gev": float(energy[-1]),
        "n_input_points": int(len(energy)),
    }
    return spectrum, record


def validate_powerlaw_table(values, log_energy, log_energy_step, gamma_legacy, dec_edges):
    base = validate_common(values, log_energy, log_energy_step, dec_edges)
    base.update(
        {
            "gamma_monotonic": bool(np.all(np.diff(gamma_legacy) > 0.0)),
            "gamma_range_exact": bool(
                np.isclose(gamma_legacy[0], -POWERLAW_GAMMA_MAX)
                and np.isclose(gamma_legacy[-1], -POWERLAW_GAMMA_MIN)
            ),
        }
    )
    if not base["gamma_monotonic"] or not base["gamma_range_exact"]:
        raise RuntimeError(f"Gamma-grid validation failed: {base}")
    return base


def validate_realistic_table(values, log_energy, log_energy_step, dec_edges):
    return validate_common(values, log_energy, log_energy_step, dec_edges)


def validate_common(values, log_energy, log_energy_step, dec_edges):
    finite = bool(np.all(np.isfinite(values)))
    nonnegative = bool(np.all(values >= 0.0))
    norms = np.sum(values.astype(np.float64), axis=1) * log_energy_step
    max_error = float(np.max(np.abs(norms - 1.0)))
    result = {
        "all_values_finite": finite,
        "pdf_values_nonnegative": nonnegative,
        "declination_edges_monotonic": bool(np.all(np.diff(dec_edges) > 0.0)),
        "log_energy_grid_monotonic": bool(np.all(np.diff(log_energy) > 0.0)),
        "dense_grid_integral_min": float(np.min(norms)),
        "dense_grid_integral_max": float(np.max(norms)),
        "dense_grid_normalization_max_abs_error": max_error,
    }
    if not all(
        result[key]
        for key in (
            "all_values_finite",
            "pdf_values_nonnegative",
            "declination_edges_monotonic",
            "log_energy_grid_monotonic",
        )
    ):
        raise RuntimeError(f"Signal-energy table validation failed: {result}")
    if max_error > 5e-3:
        raise RuntimeError(f"Signal-energy normalization validation failed: {result}")
    return result


def benchmark_lookup(path, with_gamma):
    table = SignalEnergyPDFTable(path)
    rng = np.random.default_rng(20260803)
    n_values = 100000
    dec = rng.uniform(table.dec_bin_edges_rad[0], table.dec_bin_edges_rad[-1], n_values)
    energy = rng.uniform(table.log10_reco_energy[0], table.log10_reco_energy[-1], n_values)
    start = time.perf_counter()
    if with_gamma:
        gamma = rng.uniform(table.gamma_legacy[0], table.gamma_legacy[-1], n_values)
        result = table.evaluate(dec, energy, gamma)
    else:
        result = table.evaluate(dec, energy)
    seconds = time.perf_counter() - start
    if not np.all(np.isfinite(result)) or np.any(result < 0.0):
        raise RuntimeError("Lookup benchmark returned invalid PDF values")
    return {
        "n_values": n_values,
        "seconds": seconds,
        "values_per_second": n_values / seconds,
    }


def dataset_record(
    dataset,
    sm,
    output_path,
    values,
    dec_edges,
    log_energy,
    validation,
    construction_seconds,
    per_dec_seconds,
    lookup_benchmark,
    extra,
):
    irf_paths = []
    for key in ("eff_area_datafile", "smearing_datafile"):
        irf_paths.extend(dataset.get_abs_pathfilename_list(dataset.get_aux_data_definition(key)))
    return {
        "dataset": dataset.name,
        "table_shape": list(values.shape),
        "table_dtype": str(values.dtype),
        "n_declination_bins": int(len(dec_edges) - 1),
        "n_log10_reco_energy_points": int(len(log_energy)),
        "log10_reco_energy_min": float(log_energy[0]),
        "log10_reco_energy_max": float(log_energy[-1]),
        "input_irf_files": [file_record(Path(path)) for path in irf_paths],
        "output_file": file_record(output_path),
        "timing": {
            "construction_seconds": construction_seconds,
            "mean_seconds_per_declination_bin": float(np.mean(per_dec_seconds)),
            "lookup_benchmark": lookup_benchmark,
            "indicative_pdf_stage_speedup_vs_100k_lookup": float(
                np.mean(per_dec_seconds) / lookup_benchmark["seconds"]
            ),
        },
        "validation": validation,
        **extra,
    }


def method_record():
    return {
        "pdf_calculation": "SkyLLH v26 PDSignalEnergyPDFSet",
        "effective_area": "SkyLLH PDAeff through PDSignalEnergyPDFSet",
        "smearing_matrix": "SkyLLH PDSmearingMatrix through PDSignalEnergyPDFSet",
        "declination": "intersection intervals from the union of DR2 Aeff and smearing-matrix declination edges; lookup selects the combined native-response interval without cross-bin interpolation",
        "energy": "dense log10(E_reco/GeV) cell-center grid with linear lookup interpolation",
        "power_law_gamma": "table stores legacy negative convention; SkyLLH receives its positive index",
        "legacy_codex_revised_numerical_code_used": False,
        "legacy_codex_revised_concept_used": "S_Epdf.py's pre-calculate-then-interpolate workflow only",
        "event_analysis_note": "No source spatial PDF or likelihood calculation is performed by this tool",
    }


def dense_energy_centers(dataset, step):
    binning = dataset.get_binning_definition("log_energy")
    n = int(round((binning.upper_edge - binning.lower_edge) / step))
    if not np.isclose(n * step, binning.upper_edge - binning.lower_edge, atol=1e-10):
        raise ValueError("log-energy step must divide the dataset log-energy range exactly")
    return binning.lower_edge + (np.arange(n, dtype=float) + 0.5) * step


def load_smearing_matrix(dataset):
    return PDSmearingMatrix(
        pathfilenames=dataset.get_abs_pathfilename_list(
            dataset.get_aux_data_definition("smearing_datafile")
        )
    )


def combined_response_dec_edges(dataset, sm):
    """Return intervals on which both Aeff and smearing Dec bins are fixed."""
    aeff = PDAeff(
        pathfilenames=dataset.get_abs_pathfilename_list(
            dataset.get_aux_data_definition("eff_area_datafile")
        )
    )
    edges = np.unique(np.concatenate((aeff.decnu_binedges, sm.true_dec_bin_edges)))
    if not np.all(np.diff(edges) > 0.0):
        raise RuntimeError(f"Combined response declination edges are invalid for {dataset.name}")
    return edges


def inclusive_grid(start, stop, step):
    n = int(round((stop - start) / step))
    if not np.isclose(start + n * step, stop, atol=1e-10):
        raise ValueError(f"gamma step must divide the interval from {start} to {stop} exactly")
    return np.round(start + np.arange(n + 1) * step, decimal_places(step))


def decimal_places(value):
    text = f"{value:.16f}".rstrip("0")
    return len(text.split(".")[1]) if "." in text else 0


def write_table_atomic(path, **arrays):
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    with temporary_path.open("wb") as stream:
        np.savez_compressed(stream, **arrays)
    temporary_path.replace(path)


def write_json_atomic(path, value):
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary_path.replace(path)


def file_record(path):
    return {
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def package_versions():
    return {
        name: importlib.metadata.version(name)
        for name in ("skyllh", "numpy", "scipy", "astropy")
    }


def require_dr2_files(data_path):
    required = [
        data_path / "irfs" / "IC40_effectiveArea.csv",
        data_path / "irfs" / "IC40_smearing.csv",
        data_path / "irfs" / "IC59_effectiveArea.csv",
        data_path / "irfs" / "IC59_smearing.csv",
        data_path / "irfs" / "IC79_effectiveArea.csv",
        data_path / "irfs" / "IC79_smearing.csv",
        data_path / "irfs" / "IC86_effectiveArea.csv",
        data_path / "irfs" / "IC86_smearing.csv",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing required IceTracks-DR2 IRF files: " + ", ".join(missing))


def safe_label(label):
    cleaned = "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in label)
    if not cleaned:
        raise ValueError("output label must contain at least one letter or number")
    return cleaned


def positive_float(value):
    result = float(value)
    if not np.isfinite(result) or result <= 0.0:
        raise argparse.ArgumentTypeError("value must be a positive finite number")
    return result


def positive_int(value):
    result = int(value)
    if result <= 0:
        raise argparse.ArgumentTypeError("value must be a positive integer")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
