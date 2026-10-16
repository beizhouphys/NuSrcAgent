"""SkyLLH v26 time-integrated point-source stacking for IceTracks-DR2.

Notation follows the project notes: SkyLLH's source ``weight`` is
``w_{j,model}``; its detector signal yield is ``w_{j,acc}^k``; and its
dataset signal-weight service supplies ``f_k``.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import numpy as np
import skyllh
from skyllh.analyses.i3.publicdata_ps.detsigyield import PDSingleParamFluxPointLikeSourceI3DetSigYieldBuilder
from skyllh.core.config import Config
from skyllh.core.flux_model import PowerLawEnergyFluxProfile, SteadyPointlikeFFM
from skyllh.core.minimizer import LBFGSMinimizerImpl, Minimizer
from skyllh.core.model import DetectorModel
from skyllh.core.parameters import Parameter, ParameterModelMapper
from skyllh.core.random import RandomStateService
from skyllh.core.source_hypo_grouping import SourceHypoGroup, SourceHypoGroupManager
from skyllh.core.source_model import PointLikeSource
from skyllh.core.test_statistic import WilksTestStatistic
from skyllh.core.trialdata import TrialDataManager
from skyllh.i3.config import add_icecube_specific_analysis_required_data_fields
from skyllh.i3.backgroundpdf import DataBackgroundI3SpatialPDF
from skyllh.analyses.i3.publicdata_ps.backgroundpdf import PDDataBackgroundI3EnergyPDF
from skyllh.core.smoothing import BlockSmoothingFilter

from analysis_backend.skyllh_chunked import (
    ChunkedMultiSourceMultiDatasetLLHRatioAnalysis,
    ChunkedSpatialOnlySourceWeightedPDFRatio,
    ChunkedSourceWeightedPDFRatio,
    EventOnlyAllEventSelectionMethod,
)
from analysis_backend.skyllh_dr2_pdfs import (
    BACKGROUND_ENERGY_FIELD,
    BACKGROUND_SPATIAL_FIELD,
    DR2PrecalculatedPDFStore,
)


from analysis_backend.event_pdf_data import EventPDFData

DR2_SUB_PATH = "2026_icecube_14_year_track_data_IceTracks_DR2"
DR2_SAMPLE = "icecube_public_ps_14yr_dr2"
DR2_DATA_SELECTIONS = ("full14", "first10")
DR2_FIRST10_SEASONS = ("I", "II", "III", "IV", "V", "VI", "VII")


def _uniform_scrambled_ra(size, seed):
    if seed is None:
        return None
    if int(seed) < 0:
        raise ValueError("RA-scramble seeds must be non-negative integers")
    return np.random.default_rng(int(seed)).uniform(0.0, 2.0 * np.pi, int(size))


def _dr2_datasets(root, cfg, data_selection):
    if data_selection not in DR2_DATA_SELECTIONS:
        raise ValueError("data_selection must be 'full14' or 'first10'")
    datasets = list(skyllh.create_datasets(
        "IceTracks-DR2",
        cfg=cfg,
        base_path=str(root / "data_input/IceCube_data_released"),
        sub_path_fmt=DR2_SUB_PATH,
    ))
    if data_selection == "full14":
        return datasets
    ic86 = deepcopy(datasets[-1])
    ic86.name = "IC86_I-VII"
    ic86.exp_pathfilename_list = [f"events/IC86_{season}_exp.csv" for season in DR2_FIRST10_SEASONS]
    ic86.grl_pathfilename_list = [f"uptime/IC86_{season}_exp.csv" for season in DR2_FIRST10_SEASONS]
    return [*datasets[:3], ic86]


def _attach_on_the_fly_background(cfg, dataset, data_exp):
    sin_dec_binning = dataset.get_binning_definition("sin_dec")
    log_energy_binning = dataset.get_binning_definition("log_energy")
    spatial = DataBackgroundI3SpatialPDF(cfg=cfg, data_exp=data_exp, sin_dec_binning=sin_dec_binning)
    energy = PDDataBackgroundI3EnergyPDF(
        cfg=cfg,
        data_exp=data_exp,
        logE_binning=log_energy_binning,
        sinDec_binning=sin_dec_binning,
        smoothing_filter=BlockSmoothingFilter(nbins=1),
        kde_smoothing=False,
    )
    event_view = EventPDFData(data_exp)
    spatial.initialize_for_new_trial(event_view)
    spatial_values, _ = spatial.get_pd(event_view)
    energy.initialize_for_new_trial(event_view)
    energy_values, _ = energy.get_pd(event_view)
    data_exp[BACKGROUND_SPATIAL_FIELD] = np.asarray(spatial_values, dtype=np.float64)
    data_exp[BACKGROUND_ENERGY_FIELD] = np.asarray(energy_values, dtype=np.float64)


def _event_declination_bounds(event_abs_dec_max_deg=None, event_dec_min_deg=None, event_dec_max_deg=None):
    if event_abs_dec_max_deg is not None and (event_dec_min_deg is not None or event_dec_max_deg is not None):
        raise ValueError("Use either event_abs_dec_max_deg or event_dec_min_deg/event_dec_max_deg, not both")
    if event_abs_dec_max_deg is not None:
        cut = float(event_abs_dec_max_deg)
        if not 0.0 < cut <= 90.0:
            raise ValueError("event_abs_dec_max_deg must be in (0, 90] deg or None")
        return -cut, cut
    lower = -90.0 if event_dec_min_deg is None else float(event_dec_min_deg)
    upper = 90.0 if event_dec_max_deg is None else float(event_dec_max_deg)
    if not np.isfinite(lower) or not np.isfinite(upper) or not -90.0 <= lower < upper <= 90.0:
        raise ValueError("Event declination bounds must be finite and satisfy -90 <= min < max <= 90 deg")
    return lower, upper


def _conditional_background_spatial_normalization(cfg, dataset, full_data_exp, event_dec_min_deg, event_dec_max_deg):
    if float(event_dec_min_deg) <= -90.0 and float(event_dec_max_deg) >= 90.0:
        return 1.0
    background = DataBackgroundI3SpatialPDF(
        cfg=cfg,
        data_exp=full_data_exp,
        sin_dec_binning=dataset.get_binning_definition("sin_dec"),
    )
    lower = float(np.sin(np.deg2rad(float(event_dec_min_deg))))
    upper = float(np.sin(np.deg2rad(float(event_dec_max_deg))))
    nodes, weights = np.polynomial.legendre.leggauss(1024)
    half_width = 0.5 * (upper - lower)
    midpoint = 0.5 * (upper + lower)
    normalization = half_width * np.sum(
        weights * np.exp(background._log_spline(midpoint + half_width * nodes)), dtype=np.float64
    )
    if not np.isfinite(normalization) or not 0.0 < normalization <= 1.01:
        raise ValueError("Conditional background spatial-PDF normalization is invalid")
    return float(normalization)


def create_dr2_stacking_analysis(
    repo_root,
    source_specs,
    likelihood_mode="spatial_energy",
    gamma_mode="fitted",
    gamma=2.53,
    gamma_min=1.0,
    gamma_max=6.0,
    ns_seed=10.0,
    ns_max=1e4,
    target_pairs=2**20,
    max_event_chunk=2048,
    max_source_chunk=2048,
    event_abs_dec_max_deg=None,
    event_dec_min_deg=None,
    event_dec_max_deg=None,
    data_selection="full14",
    signal_energy_declination_mode="source",
    source_ra_scramble_seed=None,
    event_ra_scramble_seed=None,
    pdf_store=None,
    background_pdf_version="v3",
):
    """Construct the exact, memory-bounded all-event SkyLLH analysis."""
    if likelihood_mode not in {"spatial_energy", "spatial_only"}:
        raise ValueError("likelihood_mode must be 'spatial_energy' or 'spatial_only'")
    if gamma_mode not in {"fitted", "fixed"}:
        raise ValueError("gamma_mode must be 'fitted' or 'fixed'")
    if likelihood_mode == "spatial_only" and gamma_mode != "fixed":
        raise ValueError("spatial_only requires gamma_mode='fixed'; Gamma is used only for acceptance")
    if not source_specs:
        raise ValueError("At least one source is required")
    event_dec_min_resolved, event_dec_max_resolved = _event_declination_bounds(
        event_abs_dec_max_deg, event_dec_min_deg, event_dec_max_deg
    )

    root = Path(repo_root).resolve()
    cfg = Config()
    add_icecube_specific_analysis_required_data_fields(cfg)
    cfg["datafields"].pop("run", None)
    datasets = _dr2_datasets(root, cfg, data_selection)
    scrambled_source_ras = _uniform_scrambled_ra(len(source_specs), source_ra_scramble_seed)
    sources = [
        PointLikeSource(
            ra=(float(spec["ra_rad"]) if scrambled_source_ras is None else float(scrambled_source_ras[idx])),
            dec=float(spec["dec_rad"]),
            name=str(spec.get("name") or f"source_{idx + 1:04d}"),
            weight=float(spec.get("w_model", 1.0)),
        )
        for idx, spec in enumerate(source_specs)
    ]

    fluxmodel = SteadyPointlikeFFM(
        Phi0=1.0,
        energy_profile=PowerLawEnergyFluxProfile(E0=1e3, gamma=float(gamma), cfg=cfg),
        cfg=cfg,
    )
    param_ns = Parameter(name="ns", initial=float(ns_seed), valmin=0.0, valmax=float(ns_max))
    if gamma_mode == "fitted":
        param_gamma = Parameter(name="gamma", initial=float(gamma), valmin=float(gamma_min), valmax=float(gamma_max))
    else:
        param_gamma = Parameter(name="gamma", initial=float(gamma))
    gamma_grid = param_gamma.as_linear_grid(delta=0.1)
    detsigyield_builder = PDSingleParamFluxPointLikeSourceI3DetSigYieldBuilder(cfg=cfg, param_grid=gamma_grid)
    shg_mgr = SourceHypoGroupManager(
        SourceHypoGroup(sources=sources, fluxmodel=fluxmodel, detsigyield_builders=detsigyield_builder)
    )
    detector_model = DetectorModel("IceCube")
    pmm = ParameterModelMapper(models=[detector_model, *sources])
    pmm.map_param(param_ns, models=detector_model)
    pmm.map_param(param_gamma, models=sources)
    analysis = ChunkedMultiSourceMultiDatasetLLHRatioAnalysis(
        cfg=cfg,
        shg_mgr=shg_mgr,
        pmm=pmm,
        test_statistic=WilksTestStatistic(),
    )
    store = DR2PrecalculatedPDFStore(root, background_version=background_pdf_version) if pdf_store is None else pdf_store
    analysis.background_pdf_version = store.background_version
    analysis.background_pdf_provenance = store.background_provenance
    source_event_pairs = 0
    event_counts = {}
    conditional_normalizations = {}
    all_events = EventOnlyAllEventSelectionMethod(shg_mgr=shg_mgr)
    source_ras = np.asarray([source.ra for source in sources])
    source_decs = np.asarray([source.dec for source in sources])
    if event_ra_scramble_seed is not None and int(event_ra_scramble_seed) < 0:
        raise ValueError("RA-scramble seeds must be non-negative integers")
    event_ra_rng = None if event_ra_scramble_seed is None else np.random.default_rng(int(event_ra_scramble_seed))
    chunked_ratios = []

    for dataset_idx, dataset in enumerate(datasets):
        data = dataset.load_and_prepare_data()
        full_data_exp = data.exp
        pdf_dataset_name = "IC86_I-XI" if dataset.name == "IC86_I-VII" else dataset.name
        if data_selection == "first10":
            _attach_on_the_fly_background(cfg, dataset, full_data_exp)
        event_mask = None
        if event_abs_dec_max_deg is not None or event_dec_min_deg is not None or event_dec_max_deg is not None:
            event_decs_deg = np.rad2deg(np.asarray(full_data_exp["dec"], dtype=np.float64))
            if event_abs_dec_max_deg is not None:
                event_mask = np.abs(event_decs_deg) < float(event_abs_dec_max_deg)
            else:
                event_mask = (event_decs_deg >= event_dec_min_resolved) & (event_decs_deg <= event_dec_max_resolved)
            data.exp = full_data_exp[event_mask]
        if data_selection == "first10":
            conditional_normalization = _conditional_background_spatial_normalization(
                cfg, dataset, full_data_exp, event_dec_min_resolved, event_dec_max_resolved
            )
        else:
            conditional_normalization = store.spatial_integral(
                pdf_dataset_name,
                np.sin(np.deg2rad(event_dec_min_resolved)),
                np.sin(np.deg2rad(event_dec_max_resolved)),
            )
        if data_selection == "first10":
            data.exp[BACKGROUND_SPATIAL_FIELD] = (
                np.asarray(data.exp[BACKGROUND_SPATIAL_FIELD], dtype=np.float64) / conditional_normalization
            )
        else:
            store.attach_background(
                data.exp,
                dataset_name=pdf_dataset_name,
                event_mask=event_mask,
                spatial_normalization=conditional_normalization,
            )
        if event_ra_rng is not None:
            data.exp["ra"] = event_ra_rng.uniform(0.0, 2.0 * np.pi, len(data.exp))
        event_counts[dataset.name] = int(len(data.exp))
        conditional_normalizations[dataset.name] = conditional_normalization
        source_event_pairs += len(sources) * len(data.exp)
        ratio_kwargs = {
            "cfg": cfg,
            "dataset_idx": dataset_idx,
            "dataset_name": pdf_dataset_name,
            "store": store,
            "data_exp": data.exp,
            "source_ras": source_ras,
            "source_decs": source_decs,
            "src_detsigyield_weights_service": None,
            "target_pairs": target_pairs,
            "max_event_chunk": max_event_chunk,
            "max_source_chunk": max_source_chunk,
        }
        if likelihood_mode == "spatial_energy":
            ratio = ChunkedSourceWeightedPDFRatio(
                gamma_grid=gamma_grid,
                signal_energy_declination_mode=signal_energy_declination_mode,
                **ratio_kwargs,
            )
        else:
            ratio = ChunkedSpatialOnlySourceWeightedPDFRatio(**ratio_kwargs)
        tdm = TrialDataManager()
        analysis.add_dataset(
            dataset=dataset,
            data=data,
            pdfratio=ratio,
            tdm=tdm,
            event_selection_method=all_events,
        )
        chunked_ratios.append(ratio)

    analysis.source_event_pair_count = int(source_event_pairs)
    analysis.event_counts = event_counts
    analysis.event_abs_dec_max_deg = None if event_abs_dec_max_deg is None else float(event_abs_dec_max_deg)
    analysis.event_dec_min_deg = None if event_dec_min_deg is None else float(event_dec_min_resolved)
    analysis.event_dec_max_deg = None if event_dec_max_deg is None else float(event_dec_max_resolved)
    analysis.background_spatial_conditional_normalization = conditional_normalizations
    analysis.data_selection = str(data_selection)
    analysis.signal_energy_declination_mode = str(signal_energy_declination_mode)
    analysis.source_ra_scramble_seed = None if source_ra_scramble_seed is None else int(source_ra_scramble_seed)
    analysis.event_ra_scramble_seed = None if event_ra_scramble_seed is None else int(event_ra_scramble_seed)

    analysis.construct_services()
    for ratio in chunked_ratios:
        ratio.weights_service = analysis.src_detsigyield_weights_service
    analysis.chunked_ratios = chunked_ratios
    analysis.llhratio = analysis.construct_llhratio(
        minimizer=Minimizer(LBFGSMinimizerImpl(cfg=cfg), max_repetitions=100)
    )
    return analysis


def run_dr2_stacking(
    source_specs,
    repo_root=".",
    likelihood_mode="spatial_energy",
    gamma_mode="fitted",
    gamma=2.53,
    gamma_min=1.0,
    gamma_max=6.0,
    ns_seed=10.0,
    ns_max=1e4,
    random_seed=1,
    event_abs_dec_max_deg=None,
    event_dec_min_deg=None,
    event_dec_max_deg=None,
    data_selection="full14",
    signal_energy_declination_mode="source",
    source_ra_scramble_seed=None,
    event_ra_scramble_seed=None,
    background_pdf_version="v3",
):
    """Run an unblinded catalog stack and return serializable results."""
    analysis = create_dr2_stacking_analysis(
        repo_root=repo_root,
        source_specs=source_specs,
        likelihood_mode=likelihood_mode,
        gamma_mode=gamma_mode,
        gamma=gamma,
        gamma_min=gamma_min,
        gamma_max=gamma_max,
        ns_seed=ns_seed,
        ns_max=ns_max,
        event_abs_dec_max_deg=event_abs_dec_max_deg,
        event_dec_min_deg=event_dec_min_deg,
        event_dec_max_deg=event_dec_max_deg,
        data_selection=data_selection,
        signal_energy_declination_mode=signal_energy_declination_mode,
        source_ra_scramble_seed=source_ra_scramble_seed,
        event_ra_scramble_seed=event_ra_scramble_seed,
        background_pdf_version=background_pdf_version,
    )
    ts, fitparams, minimizer_status = analysis.unblind(RandomStateService(seed=int(random_seed)))
    result_gamma = float(fitparams.get("gamma", gamma))
    a_jk, _ = analysis.src_detsigyield_weights_service.get_weights()
    f_k, _ = analysis.ds_sig_weight_factors_service.get_weights()
    w_model = np.asarray([float(spec.get("w_model", 1.0)) for spec in source_specs], dtype=np.float64)
    w_acc = np.divide(a_jk, w_model[np.newaxis, :], out=np.full_like(a_jk, np.nan), where=w_model[np.newaxis, :] != 0.0)
    dataset_names = [dataset.name for dataset in analysis.dataset_list]
    if data_selection == "first10":
        background_method = "SkyLLH v26 PDFs rebuilt from selected DR2 first-ten events"
        background_provenance = background_method
        energy_pdf = "precalculated_signal_and_selected_event_background"
    else:
        background_method = f"precalculated full-14 DR2 {analysis.background_pdf_version} background tables"
        background_provenance = analysis.background_pdf_provenance
        energy_pdf = "precalculated_signal_and_background_tables"
    return {
        "analysis": "catalog_stacking" if len(source_specs) > 1 else "single_source",
        "sample": DR2_SAMPLE,
        "data_selection": analysis.data_selection,
        "time_mode": "time_integrated",
        "spatial_model": "point_source_rayleigh_psf",
        "event_selection": ("abs_dec_cut" if analysis.event_abs_dec_max_deg is not None else ("dec_range_cut" if analysis.event_dec_min_deg is not None or analysis.event_dec_max_deg is not None else "all_events")),
        "event_abs_dec_max_deg": analysis.event_abs_dec_max_deg,
        "event_dec_min_deg": analysis.event_dec_min_deg,
        "event_dec_max_deg": analysis.event_dec_max_deg,
        "event_counts": dict(analysis.event_counts),
        "n_events_total": int(sum(analysis.event_counts.values())),
        "background_spatial_conditional_normalization": dict(analysis.background_spatial_conditional_normalization),
        "background_method": background_method,
        "background_pdf_version": analysis.background_pdf_version if data_selection == "full14" else "on_the_fly_skyllh_v1",
        "likelihood_mode": likelihood_mode,
        "energy_pdf": energy_pdf if likelihood_mode == "spatial_energy" else "not_used",
        "signal_energy_declination_mode": analysis.signal_energy_declination_mode if likelihood_mode == "spatial_energy" else None,
        "ra_scramble": {
            "distribution": "independent_uniform_[0,2pi)",
            "source_seed": analysis.source_ra_scramble_seed,
            "event_seed": analysis.event_ra_scramble_seed,
            "source_dec_preserved": True,
            "event_dec_energy_ang_err_and_row_order_preserved": True,
        },
        "pdf_provenance": ({
            "background": background_provenance,
            "signal_energy": "data_output/signal_energy_pdfs/14yr_dr2/signal_energy_pdf_powerlaw_provenance_DR2.json",
        } if likelihood_mode == "spatial_energy" else {
            "background_spatial": background_provenance,
        }),
        "gamma_mode": gamma_mode,
        "gamma_role": "acceptance_only" if likelihood_mode == "spatial_only" else "signal_spectrum",
        "gamma": result_gamma,
        "gamma_legacy": -result_gamma,
        "gamma_convention": "SkyLLH gamma is positive in E^-gamma; gamma_legacy is its negative",
        "acceptance_gamma_skyllh": result_gamma if likelihood_mode == "spatial_only" else None,
        "acceptance_gamma_legacy": -result_gamma if likelihood_mode == "spatial_only" else None,
        "fit_bounds": {
            "gamma_skyllh": [float(gamma_min), float(gamma_max)] if gamma_mode == "fitted" else None,
            "gamma_legacy": [-float(gamma_max), -float(gamma_min)] if gamma_mode == "fitted" else None,
            "ns": [0.0, float(ns_max)],
        },
        "fit_seeds": {"gamma_skyllh": float(gamma) if gamma_mode == "fitted" else None, "ns": float(ns_seed)},
        "ns": float(fitparams["ns"]),
        "TS": float(ts),
        "n_sources": len(source_specs),
        "source_event_pairs": int(analysis.source_event_pair_count),
        "working_set": {
            "cartesian_source_event_arrays_materialized": False,
            "signal_energy_tables_loaded": likelihood_mode == "spatial_energy",
            "datasets": {
                ratio.dataset_name: ratio.chunk_provenance for ratio in analysis.chunked_ratios
            },
        },
        "weight_notation": {
            "source_model": "w_{j,model}",
            "source_acceptance": "w_{j,acc}^k",
            "dataset_fraction": "f_k",
        },
        "w_model": w_model.tolist(),
        "w_acc_by_dataset": {name: _json_safe(w_acc[idx]) for idx, name in enumerate(dataset_names)},
        "f_k": {name: float(f_k[idx]) for idx, name in enumerate(dataset_names)},
        "minimizer_status": _json_safe(minimizer_status),
    }


def _json_safe(value):
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value
