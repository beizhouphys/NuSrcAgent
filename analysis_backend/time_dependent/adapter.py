"""NuSrcAgent adapter for fixed catalog windows and shared trial engines.

Positive Gamma is used internally; NuSrcAgent supplies the signed exponent.
Execution resources do not enter the scientific request.
"""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
import tempfile

import numpy as np
import skyllh
from skyllh.core.config import Config

from .analysis import create_time_dependent_catalog_analysis
from .cached import CachedPrecomputedFixedGammaEngine
from .cached_free import CachedPrecomputedFreeGammaEngine
from .optimized import OptimizedSharedScrambleEngine
from .config import (CatalogAnalysisConfig, CatalogConfig, CatalogColumnConfig,
                     DatasetConfig, SpectrumConfig, LikelihoodConfig, PDFConfig,
                     PrecomputedPhasePDFConfig)
from .precomputed import file_sha256


@dataclass
class PreparedAnalysis:
    constructed: object
    engine: object
    metadata: dict
    windows: list
    cached: bool


def resolve_windows(normalized):
    settings = normalized.temporal
    supplied = settings.get("windows")
    if supplied is not None and len(supplied) != len(normalized.sources):
        raise ValueError("Exactly one time window is required per source")
    rows = []
    for index, source in enumerate(normalized.sources):
        if supplied is not None:
            row = supplied[index]
            if row["name"] != source.name:
                raise ValueError("Window names/order must match the normalized catalog exactly")
            start, stop = row["start_mjd"], row["stop_mjd"]
        else:
            columns = settings["window_columns"]
            start, stop = (float(source.metadata[columns[key]]) for key in ("start", "stop"))
        if not np.isfinite([start, stop]).all() or stop <= start:
            raise ValueError(f"Invalid time window for {source.name}")
        if not np.isfinite(source.weight) or source.weight <= 0:
            raise ValueError("Catalog-window engine requires strictly positive source weights")
        rows.append(dict(source_id=str(source.source_number), name=source.name,
                         ra_deg=source.ra_deg, dec_deg=source.dec_deg, weight=source.weight,
                         start_mjd=float(start), stop_mjd=float(stop)))
    return rows


def prepare_analysis(
    normalized,
    root,
    *,
    workers=1,
    for_trials=False,
    build_engine=True,
):
    """Build the donor engine from canonical source coordinates and weights."""
    from agent_core.temporal import temporal_errors
    from agent_core.dr2_pdf_release import _manifest, verify_signal_file, BACKGROUND_PDF_DIRECTORY
    errors = temporal_errors(normalized.temporal)
    if errors:
        raise ValueError("; ".join(errors))
    if normalized.sample != "icecube_public_ps_14yr_dr2" or normalized.likelihood_mode != "spatial_energy" or normalized.spectrum:
        raise ValueError("Catalog windows require DR2 spatial+energy power-law analysis")
    if isinstance(workers, bool) or int(workers) != workers or workers < 1:
        raise ValueError("workers must be a positive integer")
    root = Path(root).resolve()
    settings = normalized.temporal
    windows = resolve_windows(normalized)
    cfg = Config()
    data_base = root / "data_input/IceCube_data_released"
    sub_path = "2026_icecube_14_year_track_data_IceTracks_DR2"
    datasets = tuple(skyllh.create_datasets("IceTracks-DR2", cfg=cfg,
        names=settings["datasets"], base_path=str(data_base), sub_path_fmt=sub_path))
    backend = settings.get("pdf_backend", "precomputed")
    phases, hashes = {}, {}
    # This engine uses event-indexed tables, not the time-integrated continuous
    # spatial models. Verify every consumed table against the same immutable
    # production manifest, without requiring unused phase/model files.
    expected_background = ({row["path"]: row["sha256"] for row in _manifest(root)["files"]
                            if row["kind"] == "background_v3"} if backend == "precomputed" else {})
    for ds in datasets:
        events = tuple(data_base / sub_path / name for name in ds.exp_pathfilename_list)
        if backend == "precomputed":
            # A single IC86 season uses the pooled response but binds its own
            # events against the full row-identity input of that response.
            response = "IC86_I-XI" if ds.name.startswith("IC86_") else ds.name
            signal = root / f"data_output/signal_energy_pdfs/14yr_dr2/signal_energy_pdf_powerlaw_{response}_DR2.npz"
            background = root / BACKGROUND_PDF_DIRECTORY / f"bkgd_pdf_{response}_exp_DR2.txt"
            verify_signal_file(root, signal)
            relative_background = str(background.relative_to(root))
            if relative_background not in expected_background or file_sha256(background) != expected_background[relative_background]:
                raise ValueError("Frozen DR2 background table hash mismatch: " + relative_background)
            if response == "IC86_I-XI":
                events = tuple(data_base / sub_path / f"events/IC86_{season}_exp.csv"
                    for season in ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI"))
            phases[ds.name] = PrecomputedPhasePDFConfig(signal, background, events)
            for path in (signal, background):
                hashes[str(path.relative_to(root))] = file_sha256(path)
        for path in (*events, *(data_base / sub_path / name for name in ds.grl_pathfilename_list),
                     *(data_base / sub_path / name for name in ds.get_aux_data_definition("eff_area_datafile"))):
            hashes[str(path.relative_to(root))] = file_sha256(path)
    gamma = -float(normalized.spectral_indices[0])
    bounds = normalized.gamma_bounds
    lower, upper = (-bounds[1], -bounds[0]) if bounds else (1., 4.)
    if normalized.gamma_mode == "fixed":
        lower, upper = min(lower, gamma), max(upper, gamma)
    engine_name = settings.get("engine", "auto")
    if engine_name == "auto":
        engine_name = ("cached-free" if normalized.gamma_mode == "fitted" else "cached-fixed") if backend == "precomputed" else "reference"
    cached = engine_name != "reference"
    if cached and backend != "precomputed":
        raise ValueError("Cached engines require precomputed PDFs")
    if (engine_name == "cached-free") != (normalized.gamma_mode == "fitted") and cached:
        raise ValueError("Cached engine and Gamma mode disagree")
    with tempfile.TemporaryDirectory(prefix="nusrcagent-td-") as directory:
        catalog = Path(directory) / "sources.csv"
        with catalog.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(windows[0]))
            writer.writeheader()
            writer.writerows(windows)
        config = CatalogAnalysisConfig(mode="stacking",
            dataset=DatasetConfig("IceTracks-DR2", tuple(settings["datasets"]), base_path=data_base, sub_path_fmt=sub_path),
            catalog=CatalogConfig(catalog, CatalogColumnConfig("source_id", "name", "ra_deg", "dec_deg", "weight", "start_mjd", "stop_mjd")),
            pdfs=PDFConfig(backend=backend, phases=phases),
            spectrum=SpectrumConfig(gamma=gamma, fit_gamma=normalized.gamma_mode == "fitted",
                gamma_min=lower, gamma_max=upper, gamma_grid_step=settings.get("gamma_grid_step", .1)),
            likelihood=LikelihoodConfig(ns_max=settings.get("ns_max", 1000.),
                event_selection_angle_deg=settings.get("event_selection_angle_deg", 10.)))
        constructed = create_time_dependent_catalog_analysis(cfg, datasets, config,
            construct_background_generator=for_trials and not cached)
    selected = [item.source.source_id for item in constructed.selection.selected]
    if selected != [row["source_id"] for row in windows]:
        raise ValueError("Source windows outside detector uptime would change catalog membership; select an explicit supported catalog")
    if cached and build_engine:
        from numba import set_num_threads
        set_num_threads(int(workers))
        engine = (CachedPrecomputedFreeGammaEngine if engine_name == "cached-free" else CachedPrecomputedFixedGammaEngine)(constructed)
    elif build_engine:
        engine = OptimizedSharedScrambleEngine(constructed)
    else:
        engine = None
    metadata = dict(engine=engine_name, pdf_backend=backend, likelihood_family="skyllh_conditional",
        spectrum=asdict(config.spectrum), likelihood=asdict(config.likelihood),
        dataset_names=[ds.name for ds in datasets], input_sha256=hashes,
        fit_procedure="catalog_continuous_profile_v1", gamma_interpolation="linear_density",
        background_trial_method="seasonal_time_scrambling", event_count="fixed_per_phase",
        shared_realization=True, workers=1 if cached else int(workers), threads=int(workers) if cached else 1,
        windows=windows)
    return PreparedAnalysis(constructed, engine, metadata, windows, cached)


def fit_observed(prepared):
    return prepared.engine.fit_observed()


def run_background_trials(prepared, *, n_trials, base_seed, trial_index_start=0, workers=1):
    if any(isinstance(x, bool) or not isinstance(x, int) for x in (n_trials, base_seed, trial_index_start)) or n_trials < 1 or base_seed < 0 or trial_index_start < 0:
        raise ValueError("Trial count must be positive and seed/index nonnegative integers")
    options = dict(n_trials=n_trials, base_seed=base_seed, trial_index_start=trial_index_start)
    if not prepared.cached:
        options["n_workers"] = workers
    return prepared.engine.run_trials(**options)


def run_catalog_windows(normalized, root, workers=1):
    from agent_core.temporal import unavailable_significance
    prepared = prepare_analysis(normalized, root, workers=workers)
    observed = fit_observed(prepared)
    def record(ts, ns, gamma, ok, status):
        return dict(TS=float(ts), ns=float(ns), gamma=None if gamma is None or not np.isfinite(gamma) else float(gamma),
                    gamma_mode=normalized.gamma_mode, gamma_status=str(status), fit_ok=bool(ok),
                    **unavailable_significance())
    source_results = [dict(source_number=source.source_number, source_name=source.name,
        ra_deg=source.ra_deg, dec_deg=source.dec_deg,
        fit=record(observed.source_ts[i], observed.source_ns[i], observed.source_gamma[i], observed.source_fit_ok[i], observed.source_gamma_status[i]))
        for i, source in enumerate(normalized.sources)]
    stack = record(observed.stack.ts, observed.stack.ns, observed.stack.gamma, observed.stack.fit_ok, observed.stack.gamma_status)
    return dict(time_mode="time_dependent", temporal_scope="per_source_catalog_windows",
        backend="skyllh_catalog_windows_v1", catalog_operation=normalized.catalog_operation,
        source_results=source_results, stack_result=stack,
        time_dependent_engine=prepared.metadata, n_sources=len(source_results), **unavailable_significance())
