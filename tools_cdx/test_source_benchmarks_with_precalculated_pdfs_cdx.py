#!/usr/bin/env python3
"""Reproduce DR2 source benchmarks using pre-calculated PDF values only.

SkyLLH supplies the official analysis definitions, signal spatial PDF, time PDF,
event selection, detector yields, likelihood, and optimizers.  The NuSrcAgent
adapter classes in this file replace only background spatial, background energy,
and signal energy PDF construction with lookups from project-local tables.

No numerical code from legacy_codex_revised is used here.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import numpy as np
import skyllh
import skyllh.analyses.i3.publicdata_ps.time_dependent_ps as time_dependent_ps
import skyllh.analyses.i3.publicdata_ps.time_integrated_ps as time_integrated_ps
from skyllh.analyses.i3.publicdata_ps.backgroundpdf import PDDataBackgroundI3EnergyPDF
from skyllh.analyses.i3.publicdata_ps.signalpdf import PDSignalEnergyPDF, PDSignalEnergyPDFSet
from skyllh.core.config import Config
from skyllh.core.pdf import EnergyPDF, PDF, PDFAxis, PDFSet, SpatialPDF
from skyllh.core.random import RandomStateService
from skyllh.core.source_model import PointLikeSource
from skyllh.i3.backgroundpdf import DataBackgroundI3SpatialPDF


DR2_SUB_PATH = "2026_icecube_14_year_track_data_IceTracks_DR2"
DATASET_NAMES = ("IC40", "IC59", "IC79", "IC86_I-XI")
BACKGROUND_FILENAMES = {
    "IC40": "bkgd_pdf_IC40_exp_DR2_cdx.txt",
    "IC59": "bkgd_pdf_IC59_exp_DR2_cdx.txt",
    "IC79": "bkgd_pdf_IC79_exp_DR2_cdx.txt",
    "IC86_I-XI": "bkgd_pdf_IC86_I-XI_exp_DR2_cdx.txt",
}
SIGNAL_FILENAMES = {
    name: f"signal_energy_pdf_powerlaw_{name}_DR2_cdx.npz"
    for name in DATASET_NAMES
}
OFFICIAL_RESULTS = {
    "ngc1068_time_integrated": {"ts": 29.154, "ns": 80.09, "gamma": 3.21},
    "txs0506_time_dependent": {
        "ts": 15.4799,
        "mu_mjd": 56966.1,
        "sigma_days": 28.3169,
        "ns": 7.12294,
        "gamma": 2.21386,
    },
}
ABS_TOLERANCES = {
    "ngc1068_time_integrated": {"ts": 0.01, "ns": 0.02, "gamma": 0.01},
    "txs0506_time_dependent": {
        "ts": 0.01,
        "mu_mjd": 0.2,
        "sigma_days": 0.2,
        "ns": 0.02,
        "gamma": 0.01,
    },
}
BACKGROUND_SPATIAL_FIELD = "precalculated_background_spatial_pdf"
BACKGROUND_ENERGY_FIELD = "precalculated_background_energy_pdf"


class PrecalculatedPDFStore:
    """Load, validate, and serve the project-local PDF tables."""

    def __init__(self, background_dir: Path, signal_dir: Path):
        self.background_dir = background_dir.resolve()
        self.signal_dir = signal_dir.resolve()
        self.background_tables = {}
        self.signal_tables = {}
        self.event_alignment = {}
        self.lookup_counts = {"background_attach": 0, "signal_slices": 0}

        # NuSrcAgent table-loading block.  These four-column files already hold
        # one spatial and one energy background PDF value per experimental event.
        for dataset_name, filename in BACKGROUND_FILENAMES.items():
            path = self.background_dir / filename
            values = np.loadtxt(path)
            if values.ndim != 2 or values.shape[1] != 4:
                raise ValueError(f"Invalid background table for {dataset_name}: {values.shape}")
            if not np.all(np.isfinite(values[:, 2:])) or np.any(values[:, 2:] < 0.0):
                raise ValueError(f"Non-finite or negative background PDF in {path}")
            self.background_tables[dataset_name] = {"path": path, "values": values}

    def identify_dataset(self, data_exp):
        matches = [
            name
            for name, record in self.background_tables.items()
            if len(record["values"]) == len(data_exp)
        ]
        if len(matches) != 1:
            raise RuntimeError(f"Event count {len(data_exp)} does not identify one dataset: {matches}")
        return matches[0]

    def attach_background(self, data_exp):
        dataset_name = self.identify_dataset(data_exp)
        table = self.background_tables[dataset_name]["values"]
        ra_difference = np.rad2deg(data_exp["ra"]) - table[:, 0]
        dec_difference = np.rad2deg(data_exp["dec"]) - table[:, 1]
        max_ra_difference = float(np.max(np.abs(ra_difference)))
        max_dec_difference = float(np.max(np.abs(dec_difference)))
        if max_ra_difference > 5e-8 or max_dec_difference > 5e-8:
            raise RuntimeError(
                f"Background rows do not match {dataset_name} events: "
                f"RA={max_ra_difference}, Dec={max_dec_difference} deg"
            )
        if BACKGROUND_SPATIAL_FIELD not in data_exp.field_name_list:
            data_exp[BACKGROUND_SPATIAL_FIELD] = table[:, 2]
        if BACKGROUND_ENERGY_FIELD not in data_exp.field_name_list:
            data_exp[BACKGROUND_ENERGY_FIELD] = table[:, 3]
        self.lookup_counts["background_attach"] += 1
        self.event_alignment[dataset_name] = {
            "n_events": int(len(data_exp)),
            "max_ra_difference_deg": max_ra_difference,
            "max_dec_difference_deg": max_dec_difference,
            "all_pdf_values_finite_nonnegative": True,
        }
        return dataset_name

    def load_signal(self, dataset_name):
        if dataset_name not in self.signal_tables:
            path = self.signal_dir / SIGNAL_FILENAMES[dataset_name]
            with np.load(path, allow_pickle=False) as table:
                dec_edges = table["dec_bin_edges_rad"].astype(np.float64)
                energy = table["log10_reco_energy"].astype(np.float64)
                gamma = table["gamma_skyllh"].astype(np.float64)
                values = table["signal_energy_pdf"].astype(np.float32, copy=False)
            if len(dec_edges) - 1 != 78:
                raise ValueError(f"Expected 78 Dec bins in {path}, found {len(dec_edges) - 1}")
            if values.shape != (78, len(energy), len(gamma)):
                raise ValueError(f"Signal table axes and shape disagree in {path}: {values.shape}")
            if not np.isclose(np.min(gamma), 0.9) or not np.isclose(np.max(gamma), 6.1):
                raise ValueError(f"Expected Gamma 0.9--6.1 in {path}")
            if len(gamma) != 521:
                raise ValueError(f"Expected 521 Gamma points in {path}, found {len(gamma)}")
            if not np.all(np.isfinite(values)) or np.any(values < 0.0):
                raise ValueError(f"Non-finite or negative signal PDF in {path}")
            # The file stores gamma_skyllh in descending order because it also
            # preserves the legacy negative-Gamma convention.  Reverse the Gamma
            # axis as a view so interpolation uses a monotonically increasing axis.
            self.signal_tables[dataset_name] = {
                "path": path,
                "dec_edges": dec_edges,
                "energy": energy,
                "gamma": gamma[::-1],
                "values": values[:, :, ::-1],
            }
        return self.signal_tables[dataset_name]

    def signal_slice(self, dataset_name, source_dec, gamma):
        table = self.load_signal(dataset_name)
        dec_index = int(np.searchsorted(table["dec_edges"], source_dec, side="right") - 1)
        if source_dec == table["dec_edges"][-1]:
            dec_index = len(table["dec_edges"]) - 2
        if dec_index < 0 or dec_index >= len(table["dec_edges"]) - 1:
            raise ValueError(f"Source Dec {source_dec} is outside the {dataset_name} table")

        gamma_axis = table["gamma"]
        if gamma < gamma_axis[0] or gamma > gamma_axis[-1]:
            raise ValueError(
                f"Gamma {gamma} is outside pre-calculated range "
                f"[{gamma_axis[0]}, {gamma_axis[-1]}]"
            )
        upper = int(np.searchsorted(gamma_axis, gamma, side="left"))
        if upper == 0:
            pdf_values = table["values"][dec_index, :, 0]
        elif upper == len(gamma_axis):
            pdf_values = table["values"][dec_index, :, -1]
        elif np.isclose(gamma_axis[upper], gamma, atol=1e-12):
            pdf_values = table["values"][dec_index, :, upper]
        else:
            lower = upper - 1
            weight = (gamma - gamma_axis[lower]) / (gamma_axis[upper] - gamma_axis[lower])
            pdf_values = (
                (1.0 - weight) * table["values"][dec_index, :, lower]
                + weight * table["values"][dec_index, :, upper]
            )
        self.lookup_counts["signal_slices"] += 1
        return table["energy"], np.asarray(pdf_values, dtype=np.float64)

    def input_file_records(self):
        records = []
        for dataset_name in DATASET_NAMES:
            records.append(file_record(self.background_tables[dataset_name]["path"], "background"))
            records.append(file_record(self.signal_dir / SIGNAL_FILENAMES[dataset_name], "signal_energy"))
        return records


ACTIVE_STORE = None
ACTIVE_AUDIT = None


class TableBackgroundSpatialPDF(DataBackgroundI3SpatialPDF):
    """SkyLLH interface backed by the event-level spatial table column."""

    def __init__(self, data_exp, sin_dec_binning, **kwargs):
        require_active_store()
        ACTIVE_STORE.attach_background(data_exp)
        ACTIVE_AUDIT["background_spatial_adapter_constructions"] += 1
        SpatialPDF.__init__(
            self,
            pmm=None,
            ra_range=(0.0, 2.0 * np.pi),
            dec_range=(
                np.arcsin(sin_dec_binning.lower_edge),
                np.arcsin(sin_dec_binning.upper_edge),
            ),
            **kwargs,
        )

    def initialize_for_new_trial(self, tdm, tl=None, **kwargs):
        self._pd = np.asarray(tdm.get_data(BACKGROUND_SPATIAL_FIELD), dtype=np.float64)

    def get_pd(self, tdm, params_recarray=None, tl=None):
        return self._pd, {}


class TableBackgroundEnergyPDF(PDDataBackgroundI3EnergyPDF):
    """SkyLLH interface backed by the event-level energy table column."""

    def __init__(self, data_exp, logE_binning, sinDec_binning, **kwargs):
        require_active_store()
        ACTIVE_STORE.attach_background(data_exp)
        ACTIVE_AUDIT["background_energy_adapter_constructions"] += 1
        kwargs.pop("smoothing_filter", None)
        kwargs.pop("kde_smoothing", None)
        EnergyPDF.__init__(self, pmm=None, **kwargs)
        self.add_axis(PDFAxis("log_energy", logE_binning.lower_edge, logE_binning.upper_edge))
        self.add_axis(PDFAxis("sin_dec", sinDec_binning.lower_edge, sinDec_binning.upper_edge))

    def initialize_for_new_trial(self, tdm, tl=None, **kwargs):
        self._pd = np.asarray(tdm.get_data(BACKGROUND_ENERGY_FIELD), dtype=np.float64)

    def get_pd(self, tdm, params_recarray=None, tl=None):
        return self._pd, {}


class TableSignalEnergyPDF(PDSignalEnergyPDF):
    """One pre-calculated Gamma slice with dense energy interpolation."""

    def __init__(self, log_energy, values, **kwargs):
        PDF.__init__(self, pmm=None, **kwargs)
        self.log_energy = np.asarray(log_energy, dtype=np.float64)
        self.values = np.asarray(values, dtype=np.float64)
        step = float(np.median(np.diff(self.log_energy)))
        self.energy_min = float(self.log_energy[0] - 0.5 * step)
        self.energy_max = float(self.log_energy[-1] + 0.5 * step)
        self.add_axis(PDFAxis("log_energy", self.energy_min, self.energy_max))

    def assert_is_valid_for_trial_data(self, tdm, tl=None):
        energy = np.asarray(tdm["log_energy"])
        if np.any(energy < self.energy_min) or np.any(energy > self.energy_max):
            raise ValueError("Trial energy lies outside the pre-calculated signal table")

    def get_pd_by_log10_reco_e(self, log10_reco_e, tl=None):
        energy = np.asarray(log10_reco_e, dtype=np.float64)
        result = np.zeros(energy.shape, dtype=np.float64)
        mask = (energy >= self.energy_min) & (energy < self.energy_max)
        result[mask] = np.interp(
            energy[mask],
            self.log_energy,
            self.values,
            left=self.values[0],
            right=self.values[-1],
        )
        return result

    def get_pd(self, tdm, params_recarray=None, tl=None):
        event_indices = tdm.src_evt_idxs[1]
        energy = np.take(tdm["log_energy"], event_indices)
        return self.get_pd_by_log10_reco_e(energy), {}


class TableSignalEnergyPDFSet(PDSignalEnergyPDFSet):
    """SkyLLH PDFSet assembled only from pre-calculated table slices."""

    def __init__(
        self,
        ds,
        src_dec,
        fluxmodel,
        param_grid_set,
        ncpu=None,
        ppbar=None,
        sm=None,
        **kwargs,
    ):
        require_active_store()
        ACTIVE_AUDIT["signal_energy_adapter_constructions"] += 1
        param_grid_set = param_grid_set.copy()
        param_grid_set.add_extra_lower_and_upper_bin()
        PDFSet.__init__(self, param_grid_set=param_grid_set, ncpu=ncpu, **kwargs)
        for gridparams in self.gridparams_list:
            gamma = float(gridparams["gamma"])
            energy, values = ACTIVE_STORE.signal_slice(ds.name, src_dec, gamma)
            self.add_pdf(TableSignalEnergyPDF(energy, values, cfg=self.cfg), gridparams)


def require_active_store():
    if ACTIVE_STORE is None or ACTIVE_AUDIT is None:
        raise RuntimeError("No active pre-calculated PDF store")


def intercepted_smearing_matrix(*args, **kwargs):
    """Prevent the official builder from loading a smearing matrix onsite."""
    require_active_store()
    ACTIVE_AUDIT["smearing_matrix_constructions_intercepted"] += 1
    return None


def intercepted_signal_generator(*args, **kwargs):
    """Prevent unused signal-injection generators from requiring smearing data."""
    require_active_store()
    ACTIVE_AUDIT["signal_generator_constructions_intercepted"] += 1
    return None


@contextmanager
def official_analysis_with_table_pdfs(module):
    """Temporarily replace exactly the three requested SkyLLH PDF builders."""
    signal_generator_name = (
        "PDDatasetSignalGenerator"
        if module is time_integrated_ps
        else "TimeDependentPDDatasetSignalGenerator"
    )
    with ExitStack() as stack:
        stack.enter_context(patch.object(module, "DataBackgroundI3SpatialPDF", TableBackgroundSpatialPDF))
        stack.enter_context(patch.object(module, "PDDataBackgroundI3EnergyPDF", TableBackgroundEnergyPDF))
        stack.enter_context(patch.object(module, "PDSignalEnergyPDFSet", TableSignalEnergyPDFSet))
        stack.enter_context(patch.object(module, "PDSmearingMatrix", intercepted_smearing_matrix))
        stack.enter_context(patch.object(module, signal_generator_name, intercepted_signal_generator))
        yield


def run_ngc1068(data_base_path):
    # SkyLLH-derived analysis block: official time-integrated source coordinates,
    # datasets, Gamma range, optimizer, and unblinding seed.
    cfg = Config()
    datasets = create_datasets(cfg, data_base_path)
    source = PointLikeSource(ra=np.deg2rad(40.67), dec=np.deg2rad(-0.01), name="NGC 1068")
    with official_analysis_with_table_pdfs(time_integrated_ps):
        analysis = time_integrated_ps.create_analysis(
            cfg=cfg,
            datasets=datasets,
            source=source,
            gamma_min=1.0,
            gamma_max=4.0,
            construct_sig_generator=False,
        )
    ts, fitparams, minimizer_status = analysis.unblind(RandomStateService(seed=1))
    return compare_result(
        "ngc1068_time_integrated",
        {"ts": float(ts), "ns": float(fitparams["ns"]), "gamma": float(fitparams["gamma"])},
        {
            "source": {"name": source.name, "ra_deg": 40.67, "dec_deg": -0.01},
            "datasets": [dataset.name for dataset in datasets],
            "gamma_fit_range": [1.0, 4.0],
            "random_seed": 1,
            "minimizer_status": json_safe(minimizer_status),
        },
    )


def run_txs0506(data_base_path):
    # SkyLLH-derived analysis block: official time-dependent setup and the
    # unblind_single_flare helper, including its full 1--5, 51-point EM scan.
    cfg = Config()
    datasets = create_datasets(cfg, data_base_path, names=["IC86_I-XI"])
    with official_analysis_with_table_pdfs(time_dependent_ps):
        analysis = time_dependent_ps.create_analysis(
            cfg=cfg,
            datasets=datasets,
            source=time_dependent_ps.TXS_0506_PLUS056_SOURCE,
            refplflux_gamma=2.0,
            gamma_min=1.0,
            gamma_max=5.0,
            gauss={"mu": 57000.0, "sigma": 65.0},
            construct_bkg_generator=False,
            construct_sig_generator=False,
        )
    ts, best_em_result, fitparams = time_dependent_ps.unblind_single_flare(
        ana=analysis,
        remove_time=time_dependent_ps.TXS_0506_PLUS056_ALERT_TIME,
    )
    source = time_dependent_ps.TXS_0506_PLUS056_SOURCE
    return compare_result(
        "txs0506_time_dependent",
        {
            "ts": float(ts),
            "mu_mjd": float(best_em_result["mu"]),
            "sigma_days": float(best_em_result["sigma"]),
            "ns": float(fitparams[0]),
            "gamma": float(fitparams[1]),
        },
        {
            "source": {
                "name": "TXS 0506+056",
                "ra_deg": float(np.rad2deg(source.ra)),
                "dec_deg": float(np.rad2deg(source.dec)),
            },
            "datasets": [dataset.name for dataset in datasets],
            "gamma_fit_range": [1.0, 5.0],
            "em_gamma_scan": {"min": 1.0, "max": 5.0, "n_points": 51, "step": 0.08},
            "removed_alert_event_time_mjd": float(time_dependent_ps.TXS_0506_PLUS056_ALERT_TIME),
            "random_seed": 1,
        },
    )


def create_datasets(cfg, data_base_path, names=None):
    return skyllh.create_datasets(
        "IceTracks-DR2",
        cfg=cfg,
        names=names,
        base_path=str(data_base_path.resolve()),
        sub_path_fmt=DR2_SUB_PATH,
    )


def compare_result(name, measured, extra):
    checks = {}
    for field, official in OFFICIAL_RESULTS[name].items():
        difference = measured[field] - official
        tolerance = ABS_TOLERANCES[name][field]
        checks[field] = {
            "status": "pass" if abs(difference) <= tolerance else "fail",
            "measured": measured[field],
            "official": official,
            "difference": difference,
            "absolute_tolerance": tolerance,
        }
    return {
        "benchmark": name,
        "status": "pass" if all(check["status"] == "pass" for check in checks.values()) else "fail",
        "checks": checks,
        **extra,
    }


def file_record(path, role):
    path = Path(path).resolve()
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return {"role": role, "path": str(path), "bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def package_versions():
    versions = {}
    for name in ("skyllh", "numpy", "scipy", "astropy"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def json_safe(value):
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value


def write_json_atomic(path, payload):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Run NGC 1068 and TXS 0506+056 with only pre-calculated requested PDFs."
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--output-dir",
        default="data_output/test_source_benchmarks_with_precalculated_pdfs_cdx",
    )
    args = parser.parse_args(argv)

    root = Path(args.repo_root).expanduser().resolve()
    output_arg = Path(args.output_dir).expanduser()
    output_dir = output_arg if output_arg.is_absolute() else root / output_arg
    output_dir.mkdir(parents=True, exist_ok=True)

    store = PrecalculatedPDFStore(
        root / "data_output" / "bkgd_pdfs_cdx" / "14yr_dr2_cdx",
        root / "data_output" / "signal_energy_pdfs_cdx" / "14yr_dr2_cdx",
    )
    audit = {
        "background_spatial_adapter_constructions": 0,
        "background_energy_adapter_constructions": 0,
        "signal_energy_adapter_constructions": 0,
        "smearing_matrix_constructions_intercepted": 0,
        "signal_generator_constructions_intercepted": 0,
    }
    global ACTIVE_STORE, ACTIVE_AUDIT
    ACTIVE_STORE = store
    ACTIVE_AUDIT = audit

    data_base_path = root / "data_input" / "IceCube_data_released"
    ngc_result = run_ngc1068(data_base_path)
    txs_result = run_txs0506(data_base_path)
    results = [ngc_result, txs_result]

    no_live_requested_pdf_construction = bool(
        audit["background_spatial_adapter_constructions"] == 5
        and audit["background_energy_adapter_constructions"] == 5
        and audit["signal_energy_adapter_constructions"] == 5
        and audit["smearing_matrix_constructions_intercepted"] == 5
        and audit["signal_generator_constructions_intercepted"] == 5
    )
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass"
        if all(result["status"] == "pass" for result in results) and no_live_requested_pdf_construction
        else "fail",
        "python": platform.python_version(),
        "packages": package_versions(),
        "method": {
            "background_spatial": "event-level pre-calculated table values",
            "background_energy": "event-level pre-calculated table values",
            "signal_energy": "78-Dec-bin, dense-energy, Gamma-0.9-to-6.1 pre-calculated tables",
            "signal_energy_lookup": "native response Dec-bin selection plus linear Gamma and log-energy interpolation",
            "skyllh_onsite_construction_of_requested_pdfs": False,
            "skyllh_remaining_roles": [
                "signal spatial PDF",
                "time PDF",
                "event selection",
                "detector yields",
                "likelihood and TS",
                "optimizer",
            ],
            "legacy_codex_revised_numerical_code_used": False,
        },
        "construction_audit": audit,
        "no_live_requested_pdf_construction_check": no_live_requested_pdf_construction,
        "lookup_counts": store.lookup_counts,
        "event_alignment": store.event_alignment,
        "input_files": store.input_file_records(),
        "results": results,
    }
    write_json_atomic(output_dir / "test_ngc1068_with_precalculated_pdfs_cdx.json", ngc_result)
    write_json_atomic(output_dir / "test_txs0506_with_precalculated_pdfs_cdx.json", txs_result)
    write_json_atomic(output_dir / "test_source_benchmarks_summary_cdx.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
