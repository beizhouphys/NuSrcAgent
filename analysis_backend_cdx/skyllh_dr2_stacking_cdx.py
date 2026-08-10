"""SkyLLH v26 time-integrated point-source stacking for IceTracks-DR2.

Notation follows the project notes: SkyLLH's source ``weight`` is
``w_{j,model}``; its detector signal yield is ``w_{j,acc}^k``; and its
dataset signal-weight service supplies ``f_k``.
"""

from __future__ import annotations

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

from analysis_backend_cdx.skyllh_dr2_chunked_cdx import (
    ChunkedMultiSourceMultiDatasetLLHRatioAnalysis,
    ChunkedSpatialOnlySourceWeightedPDFRatio,
    ChunkedSourceWeightedPDFRatio,
    EventOnlyAllEventSelectionMethod,
)
from analysis_backend_cdx.skyllh_dr2_pdfs_cdx import (
    DR2PrecalculatedPDFStore,
)


DR2_SUB_PATH = "2026_icecube_14_year_track_data_IceTracks_DR2"
DR2_SAMPLE = "icecube_public_ps_14yr_dr2"


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

    root = Path(repo_root).resolve()
    cfg = Config()
    add_icecube_specific_analysis_required_data_fields(cfg)
    cfg["datafields"].pop("run", None)
    datasets = skyllh.create_datasets(
        "IceTracks-DR2",
        cfg=cfg,
        base_path=str(root / "data_input/IceCube_data_released"),
        sub_path_fmt=DR2_SUB_PATH,
    )
    sources = [
        PointLikeSource(
            ra=float(spec["ra_rad"]),
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
    store = DR2PrecalculatedPDFStore(root)
    source_event_pairs = len(sources) * store.n_events_total
    analysis.source_event_pair_count_cdx = source_event_pairs
    all_events = EventOnlyAllEventSelectionMethod(shg_mgr=shg_mgr)
    source_ras = np.asarray([source.ra for source in sources])
    source_decs = np.asarray([source.dec for source in sources])
    chunked_ratios = []

    for dataset_idx, dataset in enumerate(datasets):
        data = dataset.load_and_prepare_data()
        ratio_kwargs = {
            "cfg": cfg,
            "dataset_idx": dataset_idx,
            "dataset_name": dataset.name,
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
            ratio = ChunkedSourceWeightedPDFRatio(gamma_grid=gamma_grid, **ratio_kwargs)
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

    analysis.construct_services()
    for ratio in chunked_ratios:
        ratio.weights_service = analysis.src_detsigyield_weights_service
    analysis.chunked_ratios_cdx = chunked_ratios
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
    )
    ts, fitparams, minimizer_status = analysis.unblind(RandomStateService(seed=int(random_seed)))
    result_gamma = float(fitparams.get("gamma", gamma))
    a_jk, _ = analysis.src_detsigyield_weights_service.get_weights()
    f_k, _ = analysis.ds_sig_weight_factors_service.get_weights()
    w_model = np.asarray([float(spec.get("w_model", 1.0)) for spec in source_specs], dtype=np.float64)
    w_acc = np.divide(a_jk, w_model[np.newaxis, :], out=np.full_like(a_jk, np.nan), where=w_model[np.newaxis, :] != 0.0)
    dataset_names = [dataset.name for dataset in analysis.dataset_list]
    return {
        "analysis": "catalog_stacking" if len(source_specs) > 1 else "single_source",
        "sample": DR2_SAMPLE,
        "time_mode": "time_integrated",
        "spatial_model": "point_source_rayleigh_psf",
        "event_selection": "all_events",
        "likelihood_mode": likelihood_mode,
        "energy_pdf": "precalculated_signal_and_background_tables" if likelihood_mode == "spatial_energy" else "not_used",
        "pdf_provenance": ({
            "background": "data_output/bkgd_pdfs_cdx/14yr_dr2_cdx/background_pdf_provenance_DR2_cdx.json",
            "signal_energy": "data_output/signal_energy_pdfs_cdx/14yr_dr2_cdx/signal_energy_pdf_powerlaw_provenance_DR2_cdx.json",
        } if likelihood_mode == "spatial_energy" else {
            "background_spatial": "data_output/bkgd_pdfs_cdx/14yr_dr2_cdx/background_pdf_provenance_DR2_cdx.json",
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
        "source_event_pairs": int(analysis.source_event_pair_count_cdx),
        "working_set": {
            "cartesian_source_event_arrays_materialized": False,
            "signal_energy_tables_loaded": likelihood_mode == "spatial_energy",
            "datasets": {
                ratio.dataset_name: ratio.chunk_provenance for ratio in analysis.chunked_ratios_cdx
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
