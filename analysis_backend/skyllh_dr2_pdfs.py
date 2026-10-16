"""Pre-calculated IceTracks-DR2 PDF adapters for SkyLLH v26.

This module loads the frozen production package; it never rebuilds a PDF
during an analysis run. PDF construction tools are not distributed.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from skyllh.analyses.i3.publicdata_ps.backgroundpdf import PDDataBackgroundI3EnergyPDF
from skyllh.core.pdf import EnergyPDF, PDFAxis, SpatialPDF
from skyllh.i3.backgroundpdf import DataBackgroundI3SpatialPDF


DATASET_NAMES = ("IC40", "IC59", "IC79", "IC86_I-XI")
BACKGROUND_SPATIAL_FIELD = "precalculated_background_spatial_pdf"
BACKGROUND_ENERGY_FIELD = "precalculated_background_energy_pdf"
from agent_core.dr2_pdf_release import (
    background_spec, verify_v3_release, verify_signal_file,
)


class DR2PrecalculatedPDFStore:
    """Load and validate event-level background and multi-D signal tables."""

    def __init__(self, repo_root: str | Path, background_version="v3"):
        root = Path(repo_root).resolve()
        self.root = root
        self._verified_signal_files = set()
        directory, self.background_model_pattern, self.background_provenance = background_spec(background_version)
        self.background_version = background_version
        verify_v3_release(root)
        self.background_dir = root / directory
        self.signal_dir = root / "data_output/signal_energy_pdfs/14yr_dr2"
        self._background = {}
        self._background_spatial_models = {}
        self._signal = {}
        self._attached_names = {}
        for name in DATASET_NAMES:
            path = self.background_dir / f"bkgd_pdf_{name}_exp_DR2.txt"
            values = np.loadtxt(path)
            if values.ndim != 2 or values.shape[1] != 4:
                raise ValueError(f"Invalid DR2 background table {path}: {values.shape}")
            if np.any(values[:, 2:] < 0) or not np.all(np.isfinite(values[:, 2:])):
                raise ValueError(f"Invalid PDF values in {path}")
            self._background[name] = values

    def background_spatial_model(self, dataset_name):
        if self.background_model_pattern is None:
            raise ValueError(f"DR2 {self.background_version} has no stored continuous spatial model")
        if dataset_name not in self._background_spatial_models:
            path = self.background_dir / self.background_model_pattern.format(name=dataset_name)
            with np.load(path, allow_pickle=False) as data:
                self._background_spatial_models[dataset_name] = (
                    data["u_grid"].astype(np.float64),
                    data["spatial_density"].astype(np.float64),
                )
        return self._background_spatial_models[dataset_name]

    def spatial_integral(self, dataset_name, u_lower=-1.0, u_upper=1.0):
        if dataset_name not in self._background:
            raise RuntimeError(f"Unknown DR2 background dataset {dataset_name!r}")
        grid, density = self.background_spatial_model(dataset_name)
        lower = float(max(-1.0, u_lower))
        upper = float(min(1.0, u_upper))
        interior = grid[(grid > lower) & (grid < upper)]
        integration_grid = np.concatenate(([lower], interior, [upper]))
        value = float(np.trapezoid(np.interp(integration_grid, grid, density), integration_grid))
        if not np.isfinite(value) or not 0.0 < value <= 1.0 + 1e-10:
            raise RuntimeError(
                f"Invalid spatial integral for {dataset_name}: {value} over [{u_lower}, {u_upper}]"
            )
        return float(value)

    def identify_dataset(self, data_exp):
        matches = [name for name, values in self._background.items() if len(values) == len(data_exp)]
        if len(matches) != 1:
            raise RuntimeError(f"DR2 event count {len(data_exp)} does not identify one dataset: {matches}")
        return matches[0]

    @property
    def n_events_total(self):
        return sum(len(values) for values in self._background.values())

    def attach_background(
        self,
        data_exp,
        dataset_name=None,
        event_mask=None,
        spatial_normalization=1.0,
    ):
        if BACKGROUND_SPATIAL_FIELD in data_exp.field_name_list and BACKGROUND_ENERGY_FIELD in data_exp.field_name_list:
            return self._attached_names.get(id(data_exp), dataset_name)
        name = self.identify_dataset(data_exp) if dataset_name is None else str(dataset_name)
        if name not in self._background:
            raise RuntimeError(f"Unknown DR2 background dataset {name!r}")
        table = self._background[name]
        if event_mask is not None:
            mask = np.asarray(event_mask, dtype=bool)
            if len(mask) != len(table):
                raise RuntimeError(f"Background event mask for {name} has length {len(mask)}, expected {len(table)}")
            table = table[mask]
        normalization = float(spatial_normalization)
        if not np.isfinite(normalization) or not 0.0 < normalization <= 1.01:
            raise ValueError("Conditional background spatial-PDF normalization is invalid")
        if len(table) != len(data_exp):
            raise RuntimeError(f"Background table for {name} has {len(table)} selected rows, expected {len(data_exp)}")
        dra = np.max(np.abs(np.rad2deg(data_exp["ra"]) - table[:, 0]))
        ddec = np.max(np.abs(np.rad2deg(data_exp["dec"]) - table[:, 1]))
        if dra > 5e-8 or ddec > 5e-8:
            raise RuntimeError(f"Background table is not aligned with {name}: RA={dra}, Dec={ddec} deg")
        if BACKGROUND_SPATIAL_FIELD not in data_exp.field_name_list:
            data_exp[BACKGROUND_SPATIAL_FIELD] = table[:, 2] / normalization
        if BACKGROUND_ENERGY_FIELD not in data_exp.field_name_list:
            data_exp[BACKGROUND_ENERGY_FIELD] = table[:, 3]
        self._attached_names[id(data_exp)] = name
        return name

    def _verify_signal(self, path):
        if path not in self._verified_signal_files:
            verify_signal_file(self.root, path)
            self._verified_signal_files.add(path)

    def signal_table(self, dataset_name):
        if dataset_name not in self._signal:
            path = self.signal_dir / f"signal_energy_pdf_powerlaw_{dataset_name}_DR2.npz"
            self._verify_signal(path)
            with np.load(path, allow_pickle=False) as data:
                table = {
                    "dec_edges": data["dec_bin_edges_rad"].astype(np.float64),
                    "energy": data["log10_reco_energy"].astype(np.float64),
                    "gamma": data["gamma_skyllh"].astype(np.float64),
                    "values": data["signal_energy_pdf"].astype(np.float32, copy=False),
                }
            if table["gamma"][0] > table["gamma"][-1]:
                table["gamma"] = table["gamma"][::-1]
                table["values"] = table["values"][:, :, ::-1]
            self._signal[dataset_name] = table
        return self._signal[dataset_name]

    def signal_values(self, dataset_name, gamma):
        table = self.signal_table(dataset_name)
        axis = table["gamma"]
        if gamma < axis[0] or gamma > axis[-1]:
            raise ValueError(f"Gamma {gamma} is outside table range [{axis[0]}, {axis[-1]}]")
        upper = int(np.searchsorted(axis, gamma, side="left"))
        if upper == 0 or np.isclose(axis[upper], gamma, atol=1e-12):
            values = table["values"][:, :, upper]
        elif upper == len(axis):
            values = table["values"][:, :, -1]
        else:
            lower = upper - 1
            fraction = (gamma - axis[lower]) / (axis[upper] - axis[lower])
            values = (1.0 - fraction) * table["values"][:, :, lower] + fraction * table["values"][:, :, upper]
        return table["dec_edges"], table["energy"], np.asarray(values, dtype=np.float64)

    def compact_signal_grid(self, dataset_name, gamma_values):
        """Load only the SkyLLH interpolation slices and release the dense table.

        The source files use a 0.01 Gamma grid and are about 0.5 GB per
        dataset.  The likelihood uses a 0.1 Gamma grid, so retaining only those
        exact/interpolated slices substantially lowers steady-state memory.
        """
        gamma_values = np.asarray(gamma_values, dtype=np.float64)
        path = self.signal_dir / f"signal_energy_pdf_powerlaw_{dataset_name}_DR2.npz"
        self._verify_signal(path)
        with np.load(path, allow_pickle=False) as data:
            dec_edges = data["dec_bin_edges_rad"].astype(np.float64)
            energy = data["log10_reco_energy"].astype(np.float64)
            axis = data["gamma_skyllh"].astype(np.float64)
            dense = data["signal_energy_pdf"]
            if axis[0] > axis[-1]:
                axis = axis[::-1]
                dense = dense[:, :, ::-1]
            if gamma_values.min() < axis[0] or gamma_values.max() > axis[-1]:
                raise ValueError(
                    f"Requested Gamma grid [{gamma_values.min()}, {gamma_values.max()}] "
                    f"is outside table range [{axis[0]}, {axis[-1]}]"
                )
            compact = np.empty((*dense.shape[:2], len(gamma_values)), dtype=np.float32)
            for idx, gamma in enumerate(gamma_values):
                upper = int(np.searchsorted(axis, gamma, side="left"))
                if upper == 0 or np.isclose(axis[upper], gamma, atol=1e-12):
                    compact[:, :, idx] = dense[:, :, upper]
                else:
                    lower = upper - 1
                    fraction = (gamma - axis[lower]) / (axis[upper] - axis[lower])
                    compact[:, :, idx] = (1.0 - fraction) * dense[:, :, lower] + fraction * dense[:, :, upper]
        return {"dec_edges": dec_edges, "energy": energy, "gamma": gamma_values.copy(), "values": compact}


class TableBackgroundSpatialPDF(DataBackgroundI3SpatialPDF):
    def __init__(self, store, data_exp, sin_dec_binning, **kwargs):
        store.attach_background(data_exp)
        SpatialPDF.__init__(
            self,
            pmm=None,
            ra_range=(0.0, 2.0 * np.pi),
            dec_range=(np.arcsin(sin_dec_binning.lower_edge), np.arcsin(sin_dec_binning.upper_edge)),
            **kwargs,
        )

    def initialize_for_new_trial(self, tdm, tl=None, **kwargs):
        self._pd = np.asarray(tdm.get_data(BACKGROUND_SPATIAL_FIELD), dtype=np.float64)

    def get_pd(self, tdm, params_recarray=None, tl=None):
        return self._pd, {}


class TableBackgroundEnergyPDF(PDDataBackgroundI3EnergyPDF):
    def __init__(self, store, data_exp, logE_binning, sinDec_binning, **kwargs):
        store.attach_background(data_exp)
        EnergyPDF.__init__(self, pmm=None, **kwargs)
        self.add_axis(PDFAxis("log_energy", logE_binning.lower_edge, logE_binning.upper_edge))
        self.add_axis(PDFAxis("sin_dec", sinDec_binning.lower_edge, sinDec_binning.upper_edge))

    def initialize_for_new_trial(self, tdm, tl=None, **kwargs):
        self._pd = np.asarray(tdm.get_data(BACKGROUND_ENERGY_FIELD), dtype=np.float64)

    def get_pd(self, tdm, params_recarray=None, tl=None):
        return self._pd, {}
