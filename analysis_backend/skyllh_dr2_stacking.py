"""SkyLLH v26 time-integrated point-source stacking for IceTracks-DR2.

Notation follows the project notes: SkyLLH's source ``weight`` is
``w_{j,model}``; its detector signal yield is ``w_{j,acc}^k``; and its
dataset signal-weight service supplies ``f_k``.
"""

from __future__ import annotations

from agent_core.progress import track_progress
from agent_core.stage_progress import subphase
from agent_core.stacking_progress import start_stacking_progress

from copy import copy, deepcopy
from pathlib import Path

import numpy as np
import skyllh
from skyllh.analyses.i3.publicdata_ps.detsigyield import PDSingleParamFluxPointLikeSourceI3DetSigYieldBuilder
from analysis_backend.spectrum_response import energy_profile, prepare_response
from agent_core.spectrum import response_required
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


class _ProgressLBFGSMinimizerImpl(LBFGSMinimizerImpl):
    """Time the unchanged objective calls; retain all SkyLLH optimizer settings."""
    progress_observer = None

    def minimize(self, initials, bounds, func, func_args=None, **kwargs):
        observer = self.progress_observer
        if observer is None:
            return super().minimize(initials, bounds, func, func_args=func_args, **kwargs)

        def measured(*args, **options):
            return observer.evaluate(func, *args, **options)

        return super().minimize(initials, bounds, measured, func_args=func_args, **kwargs)

from analysis_backend.skyllh_chunked import (
    ChunkedMultiSourceMultiDatasetLLHRatioAnalysis,
    ChunkedSpatialOnlySourceWeightedPDFRatio,
    ChunkedSourceWeightedPDFRatio,
    EventOnlyAllEventSelectionMethod,
    _ExactSpatialBlockCache,
    current_stacking_cache_cost,
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


def source_declination_window(event_decs_by_dataset, source_dec_deg, minimum_half_width_deg=20.0):
    """Smallest symmetric Dec interval retaining >=20% in every dataset."""
    minimum = float(minimum_half_width_deg)
    if not np.isfinite(minimum) or not 20.0 <= minimum <= 180.0:
        raise ValueError("source_dec_window_deg must be finite and in [20, 180]")
    center = float(source_dec_deg)
    if not np.isfinite(center) or not -90.0 <= center <= 90.0:
        raise ValueError("Source declination must be in [-90, 90] deg")
    half_width = minimum
    for values in event_decs_by_dataset.values():
        values = np.asarray(values, dtype=np.float64)
        if not len(values) or not np.all(np.isfinite(values)):
            raise ValueError("Each dataset must contain finite event declinations")
        index = int(np.ceil(0.2 * len(values))) - 1
        distances = np.abs(values - center)
        half_width = max(half_width, float(np.partition(distances, index)[index]))
    # Outward rounding keeps threshold events on floating-point boundaries.
    half_width = float(np.nextafter(half_width, np.inf))
    lower = max(-90.0, float(np.nextafter(center - half_width, -np.inf)))
    upper = min(90.0, float(np.nextafter(center + half_width, np.inf)))
    return lower, upper, half_width


def create_dr2_stacking_analysis(
    repo_root,
    source_specs,
    likelihood_mode="spatial_energy",
    gamma_mode="fitted",
    gamma=2.5,
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
    runtime_cache=None,
    source_dec_window_deg=None,
    signal_energy_gamma_interpolation=None,
    spectrum=None,
):
    """Construct the exact, memory-bounded all-event SkyLLH analysis."""
    interpolation = signal_energy_gamma_interpolation or "parabola_v1"
    if interpolation not in {"parabola_v1", "linear_v1"}:
        raise ValueError("Unsupported signal-energy Gamma interpolation")
    if likelihood_mode not in {"spatial_energy", "spatial_only"}:
        raise ValueError("likelihood_mode must be 'spatial_energy' or 'spatial_only'")
    if spectrum and gamma_mode != "fixed":
        raise ValueError("A supplied non-PL spectrum has a fixed shape; do not fit a fictitious Gamma")
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
        energy_profile=energy_profile(cfg, gamma, spectrum),
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
    if source_dec_window_deg is not None:
        if len(source_specs) != 1 or data_selection != "full14":
            raise ValueError("Adaptive source windows require one full14 DR2 source")
        if any(value is not None for value in (event_abs_dec_max_deg, event_dec_min_deg, event_dec_max_deg)):
            raise ValueError("Adaptive source windows cannot be combined with explicit event cuts")
    if runtime_cache is not None:
        if data_selection != "full14" or event_ra_scramble_seed is not None or source_ra_scramble_seed is not None:
            raise ValueError("Input reuse requires unscrambled full14 fits")
        key = (str(root), data_selection, background_pdf_version)
        if runtime_cache.get("key", key) != key:
            raise ValueError("Input cache belongs to a different data selection")
        runtime_cache.setdefault("key", key)
        runtime_cache.setdefault("data", {})
        runtime_cache.setdefault("dataset_loads", 0)
        runtime_cache.setdefault("dataset_cache_hits", 0)
        if "pdf_store" not in runtime_cache:
            runtime_cache["pdf_store"] = DR2PrecalculatedPDFStore(root, background_version=background_pdf_version) if pdf_store is None else pdf_store
        store = runtime_cache["pdf_store"]
        store.assert_files_unchanged()
    else:
        store = DR2PrecalculatedPDFStore(root, background_version=background_pdf_version) if pdf_store is None else pdf_store
    requested_bounds = [-float(gamma_max), -float(gamma_min)] if gamma_mode == "fitted" else None
    prepared_response = None
    if response_required(-float(gamma), spectrum, requested_bounds):
        prepared_response = prepare_response(root, datasets, cfg, gamma, gamma_mode, gamma_min, gamma_max,
                                             spectrum, likelihood_mode)
        from analysis_backend.skyllh_dr2_pdfs import DR2RequestedSpectrumPDFStore
        stores = {} if runtime_cache is None else runtime_cache.setdefault("requested_spectrum_stores", {})
        manifest = prepared_response["manifest"]
        if manifest not in stores:
            stores[manifest] = DR2RequestedSpectrumPDFStore(root, manifest, background_pdf_version)
        store = stores[manifest]
    analysis.spectrum_response = prepared_response
    loaded_data = []
    for dataset_idx, dataset in enumerate(datasets):
        cached = runtime_cache["data"].get(dataset_idx) if runtime_cache is not None else None
        if cached is None:
            data = dataset.load_and_prepare_data()
            if runtime_cache is not None:
                from agent_core.environment import _required_paths
                from agent_core.file_cache import file_signature
                paths = [root / relative for relative in _required_paths(DR2_SAMPLE, "spatial_only")
                         if "IceCube_data_released/" in str(relative)]
                signatures = {path: file_signature(path) for path in paths}
                for table in (data.exp, data.mc):
                    if table is not None:
                        for field in table.field_name_list:
                            table[field].setflags(write=False)
                runtime_cache["data"][dataset_idx] = (data, signatures)
                runtime_cache["dataset_loads"] += 1
        else:
            template, signatures = cached
            from agent_core.file_cache import file_signature
            if any(file_signature(path) != expected for path, expected in signatures.items()):
                raise ValueError("A cached neutrino data or detector-response file changed")
            data = template
            runtime_cache["dataset_cache_hits"] += 1
        if runtime_cache is not None:
            template = data
            data = copy(template)
            data.exp = template.exp.copy()
            data.mc = None if template.mc is None else template.mc.copy()
        loaded_data.append(data)
    half_width = None
    if source_dec_window_deg is not None:
        event_dec_min_resolved, event_dec_max_resolved, half_width = source_declination_window(
            {dataset.name: np.rad2deg(data.exp["dec"]) for dataset, data in zip(datasets, loaded_data)},
            np.rad2deg(source_specs[0]["dec_rad"]), source_dec_window_deg)
    event_counts_before_selection = {dataset.name: int(len(data.exp)) for dataset, data in zip(datasets, loaded_data)}
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
    # One shared payload budget for this fit; single-source and fixed-Gamma
    # fits do not amortize the compression cost over repeated spectral updates.
    spatial_cache = (_ExactSpatialBlockCache() if likelihood_mode == "spatial_energy"
                     and gamma_mode == "fitted" and len(sources) > 1 else None)

    for dataset_idx, dataset in enumerate(datasets):
        data = loaded_data[dataset_idx]
        full_data_exp = data.exp
        pdf_dataset_name = "IC86_I-XI" if dataset.name == "IC86_I-VII" else dataset.name
        if data_selection == "first10":
            _attach_on_the_fly_background(cfg, dataset, full_data_exp)
        event_mask = None
        if source_dec_window_deg is not None or event_abs_dec_max_deg is not None or event_dec_min_deg is not None or event_dec_max_deg is not None:
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
                signal_energy_gamma_interpolation=interpolation,
                signal_energy_declination_mode=signal_energy_declination_mode,
                spatial_cache=spatial_cache,
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
    analysis.event_counts_before_selection = event_counts_before_selection
    analysis.source_dec_window = None if source_dec_window_deg is None else {
        "minimum_half_width_deg": float(source_dec_window_deg), "half_width_deg": half_width,
        "minimum_event_fraction_per_dataset": 0.2,
        "retained_fractions": {name: count / event_counts_before_selection[name] for name, count in event_counts.items()}}
    if analysis.source_dec_window is not None and any(value < 0.2 for value in analysis.source_dec_window["retained_fractions"].values()):
        raise ValueError("Adaptive declination window retained fewer than 20% of a dataset")
    analysis.event_abs_dec_max_deg = None if event_abs_dec_max_deg is None else float(event_abs_dec_max_deg)
    analysis.event_dec_min_deg = None if event_dec_min_deg is None and source_dec_window_deg is None else float(event_dec_min_resolved)
    analysis.event_dec_max_deg = None if event_dec_max_deg is None and source_dec_window_deg is None else float(event_dec_max_resolved)
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
        minimizer=Minimizer(_ProgressLBFGSMinimizerImpl(cfg=cfg), max_repetitions=100)
    )
    return analysis


def run_dr2_stacking(
    source_specs,
    repo_root=".",
    likelihood_mode="spatial_energy",
    gamma_mode="fitted",
    gamma=2.5,
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
    runtime_cache=None,
    source_dec_window_deg=None,
    signal_energy_gamma_interpolation=None,
    spectrum=None,
    flux_upper_limit_cl=None,
    flux_measurement_ts_threshold=None,
    fit_procedure="skyllh_lbfgs_v1",
    temporal_settings=None,
):
    """Run an unblinded catalog stack and return serializable results."""
    if fit_procedure != "skyllh_lbfgs_v1":
        raise ValueError("Unsupported DR2 fit procedure; this runtime uses skyllh_lbfgs_v1")
    if temporal_settings is not None and (len(source_specs) != 1 or data_selection != "full14"
            or flux_upper_limit_cl is not None or flux_measurement_ts_threshold is not None
            or event_ra_scramble_seed is not None or source_ra_scramble_seed is not None):
        raise ValueError("Time-dependent runtime requires one unscrambled full14 DR2 source, no trials and no time-integrated flux products")
    with subphase('input loading and analysis setup'):
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
            runtime_cache=runtime_cache,
            source_dec_window_deg=source_dec_window_deg,
            signal_energy_gamma_interpolation=signal_energy_gamma_interpolation,
            spectrum=spectrum,
        )
    temporal_controller = None
    if temporal_settings is not None:
        from analysis_backend.skyllh_dr2_time_dependent import attach_temporal_profile
        temporal_controller = attach_temporal_profile(analysis, temporal_settings)
    progress = None if temporal_controller is not None else start_stacking_progress(source_specs, gamma_mode,
        cost_state=lambda: tuple(ratio._cache_key for ratio in analysis.chunked_ratios),
        cache_cost=lambda **options: current_stacking_cache_cost(analysis.chunked_ratios,**options))
    minimizer_impl = analysis.llhratio.minimizer.minimizer_impl
    minimizer_impl.progress_observer = progress
    fit_timing = None
    try:
        ts, fitparams, minimizer_status = (analysis.unblind(RandomStateService(seed=int(random_seed)))
            if temporal_controller is None else temporal_controller.maximize(random_seed))
    finally:
        minimizer_impl.progress_observer = None
        if progress is not None:
            fit_timing = progress.close()
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
    result = {
        "analysis": "catalog_stacking" if len(source_specs) > 1 else "single_source",
        "sample": DR2_SAMPLE,
        "data_selection": analysis.data_selection,
        "time_mode": "time_integrated",
        "spatial_model": "point_source_rayleigh_psf",
        "event_selection": ("adaptive_source_dec_window" if analysis.source_dec_window is not None else "abs_dec_cut" if analysis.event_abs_dec_max_deg is not None else ("dec_range_cut" if analysis.event_dec_min_deg is not None or analysis.event_dec_max_deg is not None else "all_events")),
        "event_abs_dec_max_deg": analysis.event_abs_dec_max_deg,
        "event_dec_min_deg": analysis.event_dec_min_deg,
        "event_dec_max_deg": analysis.event_dec_max_deg,
        "event_counts": dict(analysis.event_counts),
        "event_counts_before_selection": dict(analysis.event_counts_before_selection),
        "source_dec_window": analysis.source_dec_window,
        "n_events_total": int(sum(analysis.event_counts.values())),
        "background_spatial_conditional_normalization": dict(analysis.background_spatial_conditional_normalization),
        "background_method": background_method,
        "background_pdf_version": analysis.background_pdf_version if data_selection == "full14" else "on_the_fly_skyllh_v1",
        "likelihood_mode": likelihood_mode,
        "signal_energy_gamma_interpolation": (signal_energy_gamma_interpolation or "parabola_v1") if likelihood_mode == "spatial_energy" else None,
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
        "fit_procedure": fit_procedure,
    }

    if spectrum:
        result.update(spectrum=spectrum, gamma=None, gamma_legacy=None,
                      gamma_convention="fixed tabulated shape; no power-law index",
                      gamma_role="fixed_spectrum_shape", acceptance_gamma_skyllh=None, acceptance_gamma_legacy=None)
    if analysis.spectrum_response:
        result["spectrum_response"] = analysis.spectrum_response
        result["pdf_provenance"]["signal_energy" if likelihood_mode == "spatial_energy" else "background_spatial"] = (
            analysis.spectrum_response["manifest"] if likelihood_mode == "spatial_energy" else background_provenance)
    if fit_timing is not None:
        result['fit_timing'] = fit_timing
    if temporal_controller is not None:
        from agent_core.temporal import unavailable_significance
        result.update(time_mode="time_dependent", temporal=temporal_controller.metadata,
                      **unavailable_significance())
        result["w_acc_by_dataset"] = {name: _json_safe(w_acc[idx] * temporal_controller.yield_factors[idx])
                                     for idx, name in enumerate(dataset_names)}
    if flux_upper_limit_cl is not None:
        from analysis_backend.profile_upper_limit import fixed_gamma_flux_upper_limit
        with subphase('fixed-spectrum likelihood profile'):
            result["flux_upper_limit"] = fixed_gamma_flux_upper_limit(analysis, result, flux_upper_limit_cl)
    if flux_measurement_ts_threshold is not None:
        from analysis_backend.profile_flux import source_flux_measurement
        result["flux_measurement"] = source_flux_measurement(analysis, result, flux_measurement_ts_threshold)
    return result


def run_dr2_single_source(source_specs, flux_upper_limit_cl=None, flux_upper_limit_gammas=None, flux_measurement_ts_threshold=None, runtime_cache=None, **fit_options):
    """Run the requested fit plus separately recorded fixed-spectrum limits."""
    if len(source_specs) != 1:
        raise ValueError("Individual-source fits require exactly one source")
    return run_dr2_flux_suite(source_specs, flux_upper_limit_cl, flux_upper_limit_gammas,
                             flux_measurement_ts_threshold, runtime_cache, **fit_options)


def run_dr2_flux_suite(source_specs, flux_upper_limit_cl=None, flux_upper_limit_gammas=None,
                       flux_measurement_ts_threshold=None, runtime_cache=None,
                       primary_result=None, **fit_options):
    """Use the existing primary fit or maximize once, then calculate flux outputs."""
    gammas = list(flux_upper_limit_gammas or [])
    owned_cache = runtime_cache is None and bool(gammas)
    cache = {} if owned_cache else runtime_cache
    try:
        if primary_result is None:
            result = run_dr2_stacking(source_specs, runtime_cache=cache,
                flux_upper_limit_cl=None if gammas else flux_upper_limit_cl,
                flux_measurement_ts_threshold=flux_measurement_ts_threshold, **fit_options)
        else:
            expected = fit_options.get("signal_energy_gamma_interpolation") or "parabola_v1"
            recorded = primary_result.get("signal_energy_gamma_interpolation") or "parabola_v1"
            if recorded != expected:
                raise ValueError("Primary checkpoint uses a different Gamma interpolation; create a new task")
            import copy
            result = copy.deepcopy(primary_result)
            result.pop("generated_files", None)
            analysis_options = {key: value for key, value in fit_options.items()
                                if key not in {"random_seed", "fit_procedure"}}
            with subphase('saved primary likelihood reconstruction and verification'):
                analysis = create_dr2_stacking_analysis(source_specs=source_specs,
                    runtime_cache=cache, **analysis_options)
                analysis.initialize_trial([data.exp for data in analysis._data_list])
                fitted = result["gamma_mode"] == "fitted"
                values = np.asarray([result["ns"], result["gamma"]] if fitted else [result["ns"]])
                value, _ = analysis.llhratio.evaluate(values)
                if not np.isclose(2*value, result["TS"], rtol=1e-7, atol=1e-6):
                    raise ValueError("Saved primary fit does not match the reconstructed likelihood")
            if flux_measurement_ts_threshold is not None:
                from analysis_backend.profile_flux import source_flux_measurement
                result["flux_measurement"] = source_flux_measurement(analysis, result, flux_measurement_ts_threshold)
            if flux_upper_limit_cl is not None and not gammas:
                from analysis_backend.profile_upper_limit import fixed_gamma_flux_upper_limit
                result["flux_upper_limit"] = fixed_gamma_flux_upper_limit(analysis, result, flux_upper_limit_cl)
            result["primary_maximization_repeated"] = False
        if gammas:
            fixed_options = dict(fit_options, gamma_mode="fixed", fit_procedure="skyllh_lbfgs_v1", spectrum=None)
            result["flux_upper_limit_fits"] = []
            for exponent in track_progress(gammas, "fixed-spectrum flux upper limits"):
                fixed_options["gamma"] = -float(exponent)
                fit = run_dr2_stacking(source_specs, runtime_cache=cache,
                    flux_upper_limit_cl=flux_upper_limit_cl, **fixed_options)
                result["flux_upper_limit_fits"].append(fit)
        return result
    finally:
        if owned_cache:
            cache.clear()


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
