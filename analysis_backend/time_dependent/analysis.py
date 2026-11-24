"""Analysis assembly for single-source and stacked catalog searches."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

import numpy as np

from skyllh.analyses.i3.publicdata_ps.backgroundpdf import PDDataBackgroundI3EnergyPDF
from skyllh.analyses.i3.publicdata_ps.detsigyield import (
    PDSingleParamFluxPointLikeSourceI3DetSigYieldBuilder,
)
from skyllh.analyses.i3.publicdata_ps.utils import clip_grl_start_times
from skyllh.core.analysis import MultiSourceMultiDatasetLLHRatioAnalysis
from skyllh.core.background_generator import DatasetBackgroundGenerator
from skyllh.core.config import Config
from skyllh.core.dataset import Dataset
from skyllh.core.detsigyield import DetSigYieldBuilder
from skyllh.core.event_selection import SpatialBoxEventSelectionMethod
from skyllh.core.flux_model import PowerLawEnergyFluxProfile, SteadyPointlikeFFM
from skyllh.core.minimizer import LBFGSMinimizerImpl, Minimizer
from skyllh.core.minimizers.iminuit import IMinuitMinimizerImpl
from skyllh.core.model import DetectorModel
from skyllh.core.parameters import Parameter, ParameterGrid, ParameterModelMapper
from skyllh.core.pdf import PDF
from skyllh.core.pdfratio import PDFRatio, SigOverBkgPDFRatio
from skyllh.core.progressbar import ProgressBar
from skyllh.core.random import RandomStateService
from skyllh.core.scrambling import DataScrambler
from skyllh.core.signal_generator import MultiDatasetSignalGenerator
from skyllh.core.signalpdf import RayleighPSFPointSourceSignalSpatialPDF
from skyllh.core.smoothing import BlockSmoothingFilter
from skyllh.core.source_hypo_grouping import SourceHypoGroup, SourceHypoGroupManager
from skyllh.core.source_model import PointLikeSource
from skyllh.core.test_statistic import WilksTestStatistic
from skyllh.core.timing import TimeLord
from skyllh.core.trialdata import TrialDataManager
from skyllh.core.utils.analysis import pointlikesource_to_data_field_array
from skyllh.core.utils.tdm import get_tdm_field_func_psi
from skyllh.i3.background_generation import FixedScrambledExpDataI3BkgGenMethod
from skyllh.i3.backgroundpdf import DataBackgroundI3SpatialPDF
from skyllh.i3.config import add_icecube_specific_analysis_required_data_fields
from skyllh.i3.dataset import I3DatasetData
from skyllh.i3.livetime import I3Livetime
from skyllh.i3.scrambling import I3SeasonalVariationTimeScramblingMethod

from .catalog import CatalogSelectionResult, select_catalog_sources, selected_sources_to_arrays
from .config import CatalogAnalysisConfig
from .energy import create_multi_source_energy_pdfratio
from .event_selection import SourceTimeSpatialBoxEventSelectionMethod
from .phase import (
    PhaseExposureDetSigYieldBuilder,
    filter_catalog_selection_for_livetimes,
    source_phase_profile_exposure_fractions,
)
from .precomputed import (
    BoundPrecomputedBackground,
    EventIndexedBackgroundPDF,
    PrecomputedEventBackgroundTable,
    PrecomputedSignalEnergyGrid,
    PrecomputedSignalEnergyPDFRatio,
)
from .time import SourceTimePDFComponents, create_source_time_pdf_components


@dataclass(frozen=True)
class CatalogAnalysisModel:
    """The source, parameter, and likelihood objects shared by all datasets."""

    sources: tuple[PointLikeSource, ...]
    fluxmodel: SteadyPointlikeFFM
    gamma_grid: ParameterGrid
    ns_parameter: Parameter
    gamma_parameter: Parameter
    detector_model: DetectorModel
    shg_mgr: SourceHypoGroupManager
    pmm: ParameterModelMapper
    minimizer: Minimizer
    analysis: MultiSourceMultiDatasetLLHRatioAnalysis


@dataclass(frozen=True)
class ConstructedCatalogAnalysis:
    """A fully constructed analysis and its resolved catalog inputs."""

    config: CatalogAnalysisConfig
    datasets: tuple[Dataset, ...]
    selection: CatalogSelectionResult
    model: CatalogAnalysisModel
    data_list: tuple[I3DatasetData, ...]
    livetimes: tuple[I3Livetime, ...]
    time_components_list: tuple[SourceTimePDFComponents, ...]
    tdms: tuple[TrialDataManager, ...]
    pdfratios: tuple[PDFRatio, ...]
    spatial_pdfratios: tuple[PDFRatio, ...]
    energy_background_pdfs: tuple[PDF, ...]
    precomputed_backgrounds: tuple[BoundPrecomputedBackground | None, ...]
    precomputed_signal_grids: tuple[PrecomputedSignalEnergyGrid | None, ...]

    @property
    def analysis(self) -> MultiSourceMultiDatasetLLHRatioAnalysis:
        return self.model.analysis

    def _single(self, values, label: str):
        if len(values) != 1:
            raise ValueError(f'{label} is only available for a single-phase construction')
        return values[0]

    @property
    def dataset(self) -> Dataset:
        return self._single(self.datasets, 'dataset')

    @property
    def data(self) -> I3DatasetData:
        return self._single(self.data_list, 'data')

    @property
    def livetime(self) -> I3Livetime:
        return self._single(self.livetimes, 'livetime')

    @property
    def time_components(self) -> SourceTimePDFComponents:
        return self._single(self.time_components_list, 'time_components')

    @property
    def tdm(self) -> TrialDataManager:
        return self._single(self.tdms, 'tdm')

    @property
    def pdfratio(self) -> PDFRatio:
        return self._single(self.pdfratios, 'pdfratio')

    @property
    def spatial_pdfratio(self) -> PDFRatio:
        return self._single(self.spatial_pdfratios, 'spatial_pdfratio')

    @property
    def energy_background_pdf(self) -> PDF:
        return self._single(self.energy_background_pdfs, 'energy_background_pdf')

    def unblind(self, seed: int | None = None, tl: TimeLord | None = None):
        """Fit the configured analysis to its unscrambled experimental data."""

        if seed is None:
            seed = self.config.background.seed
        return self.analysis.unblind(minimizer_rss=RandomStateService(seed=seed), tl=tl)


def _create_minimizer(cfg: Config, name: str) -> Minimizer:
    if name == 'LBFGS':
        return Minimizer(LBFGSMinimizerImpl(cfg=cfg))
    if name == 'minuit':
        return Minimizer(IMinuitMinimizerImpl(cfg=cfg, ftol=1e-8))
    raise ValueError(f'unsupported minimizer {name!r}')


def _create_gamma_grid(config: CatalogAnalysisConfig) -> ParameterGrid:
    spectrum = config.spectrum
    if not spectrum.fit_gamma:
        return ParameterGrid(
            'gamma',
            np.asarray([spectrum.gamma]),
            delta=spectrum.gamma_grid_step,
        )
    n_steps = int(np.ceil((spectrum.gamma_max - spectrum.gamma_min) / spectrum.gamma_grid_step))
    grid = spectrum.gamma_min + np.arange(n_steps + 1) * spectrum.gamma_grid_step
    if grid[-1] < spectrum.gamma_max:
        grid = np.append(grid, spectrum.gamma_max)
    else:
        grid[-1] = spectrum.gamma_max
    return ParameterGrid('gamma', grid)


def create_catalog_analysis_model(
    cfg: Config,
    sources: Sequence[PointLikeSource],
    config: CatalogAnalysisConfig,
    detsigyield_builder: DetSigYieldBuilder | None = None,
) -> CatalogAnalysisModel:
    """Create the common model graph used by one source or a source stack.

    Dataset PDFs and generators are attached in a separate step.  Keeping this
    assembly independent of catalog size makes single-source analyses a
    one-element special case of the stacking implementation.
    """

    sources = tuple(sources)
    if not sources:
        raise ValueError('at least one source is required')
    if len({source.name for source in sources}) != len(sources):
        raise ValueError('source names must be unique within one analysis')

    spectrum = config.spectrum
    fluxmodel = SteadyPointlikeFFM(
        Phi0=spectrum.reference_flux,
        energy_profile=PowerLawEnergyFluxProfile(
            E0=spectrum.reference_energy_gev,
            gamma=spectrum.gamma,
            cfg=cfg,
        ),
        cfg=cfg,
    )
    gamma_grid = _create_gamma_grid(config)
    if detsigyield_builder is None:
        detsigyield_builder = PDSingleParamFluxPointLikeSourceI3DetSigYieldBuilder(
            cfg=cfg,
            param_grid=gamma_grid,
        )
    shg_mgr = SourceHypoGroupManager(
        SourceHypoGroup(
            sources=sources,
            fluxmodel=fluxmodel,
            detsigyield_builders=detsigyield_builder,
        )
    )

    likelihood = config.likelihood
    ns_parameter = Parameter(
        name='ns',
        initial=likelihood.ns_seed,
        valmin=likelihood.ns_min,
        valmax=likelihood.ns_max,
    )
    if spectrum.fit_gamma:
        gamma_parameter = Parameter(
            name='gamma',
            initial=spectrum.gamma,
            valmin=spectrum.gamma_min,
            valmax=spectrum.gamma_max,
        )
    else:
        gamma_parameter = Parameter(name='gamma', initial=spectrum.gamma, isfixed=True)

    detector_model = DetectorModel('IceCube')
    pmm = ParameterModelMapper(models=[detector_model, *sources])
    pmm.map_param(ns_parameter, models=detector_model)
    pmm.map_param(gamma_parameter, models=sources)

    minimizer = _create_minimizer(cfg=cfg, name=likelihood.minimizer)
    analysis = MultiSourceMultiDatasetLLHRatioAnalysis(
        cfg=cfg,
        shg_mgr=shg_mgr,
        pmm=pmm,
        test_statistic=WilksTestStatistic(),
        sig_generator_cls=MultiDatasetSignalGenerator,
    )
    return CatalogAnalysisModel(
        sources=sources,
        fluxmodel=fluxmodel,
        gamma_grid=gamma_grid,
        ns_parameter=ns_parameter,
        gamma_parameter=gamma_parameter,
        detector_model=detector_model,
        shg_mgr=shg_mgr,
        pmm=pmm,
        minimizer=minimizer,
        analysis=analysis,
    )


def create_time_dependent_catalog_analysis(
    cfg: Config,
    datasets: Sequence[Dataset],
    config: CatalogAnalysisConfig,
    *,
    keep_data_fields: list[str] | None = None,
    compress_data: bool = False,
    construct_background_generator: bool = True,
    tl: TimeLord | None = None,
    ppbar: ProgressBar | None = None,
) -> ConstructedCatalogAnalysis:
    """Construct a complete single-source or stacking catalog analysis.

    Each input dataset is an independent detector phase with its own event
    sample, GRL, PDFs, scrambling, and detector yield.  A single global
    signal count and (when enabled) gamma are shared across all phases.
    """

    datasets = tuple(datasets)
    if not datasets:
        raise ValueError('at least one dataset phase is required')
    if len({dataset.name for dataset in datasets}) != len(datasets):
        raise ValueError('dataset phase names must be unique')

    add_icecube_specific_analysis_required_data_fields(cfg)
    if config.pdfs.backend != 'precomputed':
        cfg['datafields'].pop('run', None)
    dtc_dict = {np.dtype(np.float64): np.dtype(np.float32)} if compress_data else None
    dtc_except_fields = ['mcweight', 'time'] if compress_data else None
    loaded_data = []
    livetimes = []
    for dataset in datasets:
        data = cast(
            I3DatasetData,
            dataset.load_and_prepare_data(
                keep_fields=keep_data_fields,
                dtc_dict=dtc_dict,
                dtc_except_fields=dtc_except_fields,
                tl=tl,
            ),
        )
        if data.exp is None or data.grl is None:
            raise ValueError(f'dataset {dataset.name!r} must provide experimental events and a GRL')
        if 'catalog_event_id' not in data.exp:
            data.exp.append_field('catalog_event_id', np.arange(len(data.exp), dtype=np.int32))
        clip_grl_start_times(grl_data=cast(np.ndarray, data.grl))
        loaded_data.append(data)
        livetimes.append(I3Livetime.from_grl_data(grl_data=cast(np.ndarray, data.grl)))

    selection = select_catalog_sources(
        config,
        period_start_mjd=min(livetime.time_start for livetime in livetimes),
        period_end_mjd=max(livetime.time_stop for livetime in livetimes),
    )
    profile_type = config.catalog.time_profile.type
    selection = filter_catalog_selection_for_livetimes(
        selection,
        livetimes,
        profile_type=profile_type,
        gaussian_tail_tolerance=config.catalog.time_profile.tail_tolerance,
    )
    sources, time_centers, time_widths = selected_sources_to_arrays(selection.selected)
    gaussian_sigmas = None
    if profile_type == 'gaussian':
        gaussian_sigmas = np.asarray(
            [item.source.time_sigma_days for item in selection.selected], dtype=np.float64
        )
    time_kwargs = {
        'profile_type': profile_type,
        'gaussian_sigmas_days': gaussian_sigmas,
        'gaussian_tail_tolerance': config.catalog.time_profile.tail_tolerance,
    }
    exposure_by_dataset = {
        dataset.name: source_phase_profile_exposure_fractions(
            livetime, time_centers, time_widths, **time_kwargs
        )
        for dataset, livetime in zip(datasets, livetimes, strict=True)
    }
    inactive = [name for name, fractions in exposure_by_dataset.items() if not np.any(fractions > 0)]
    if inactive:
        raise ValueError(
            'dataset phases without live-time overlap with any selected source window are not informative and '
            f'must be omitted: {inactive}'
        )
    base_detsigyield_builder = PDSingleParamFluxPointLikeSourceI3DetSigYieldBuilder(
        cfg=cfg,
        param_grid=_create_gamma_grid(config),
    )
    phase_detsigyield_builder = PhaseExposureDetSigYieldBuilder(
        base=base_detsigyield_builder,
        livetimes_by_dataset=dict(zip((dataset.name for dataset in datasets), livetimes, strict=True)),
        time_centers_mjd=time_centers,
        time_widths_days=time_widths,
        **time_kwargs,
    )
    model = create_catalog_analysis_model(
        cfg=cfg,
        sources=sources,
        config=config,
        detsigyield_builder=phase_detsigyield_builder,
    )
    selection_angle = np.deg2rad(config.likelihood.event_selection_angle_deg)
    time_components_list = []
    tdms = []
    pdfratios = []
    spatial_pdfratios = []
    energy_background_pdfs = []
    precomputed_backgrounds = []
    precomputed_signal_grids = []
    shared_center_parameters = None
    shared_width_parameters = None
    for dataset, data, livetime in zip(datasets, loaded_data, livetimes, strict=True):
        time_components = create_source_time_pdf_components(
            model=model,
            livetime=livetime,
            time_centers_mjd=time_centers,
            time_widths_days=time_widths,
            **time_kwargs,
            center_parameters=shared_center_parameters,
            width_parameters=shared_width_parameters,
        )
        shared_center_parameters = time_components.center_parameters
        shared_width_parameters = time_components.width_parameters
        sin_dec_binning = dataset.get_binning_definition('sin_dec')
        log_energy_binning = dataset.get_binning_definition('log_energy')
        spatial_signal_pdf = RayleighPSFPointSourceSignalSpatialPDF(
            cfg=cfg,
            dec_range=tuple(np.arcsin(sin_dec_binning.range)),
        )
        bound_precomputed_background = None
        precomputed_signal_grid = None
        if config.pdfs.backend == 'precomputed':
            phase_config = config.pdfs.phases[dataset.name]
            background_table = PrecomputedEventBackgroundTable(phase_config)
            bound_precomputed_background = background_table.bind(
                data.exp,
                verify_event_coordinates=config.pdfs.verify_event_coordinates,
            )
            precomputed_signal_grid = PrecomputedSignalEnergyGrid(phase_config.signal_path)
            precomputed_signal_grid.validate_gamma_bounds(config.spectrum.gamma_min, config.spectrum.gamma_max)
            spatial_background_pdf = EventIndexedBackgroundPDF(
                cfg=cfg,
                values=bound_precomputed_background.spatial,
                axes=spatial_signal_pdf.axes,
            )
        else:
            spatial_background_pdf = DataBackgroundI3SpatialPDF(
                cfg=cfg,
                data_exp=data.exp,
                sin_dec_binning=sin_dec_binning,
            )
        spatial_ratio = SigOverBkgPDFRatio(cfg=cfg, sig_pdf=spatial_signal_pdf, bkg_pdf=spatial_background_pdf)
        if config.pdfs.backend == 'precomputed':
            assert bound_precomputed_background is not None and precomputed_signal_grid is not None
            energy_background_pdf = EventIndexedBackgroundPDF(cfg=cfg, values=bound_precomputed_background.energy)
            energy_ratio = PrecomputedSignalEnergyPDFRatio(
                cfg=cfg,
                grid=precomputed_signal_grid,
                source_bin_indices=precomputed_signal_grid.declination_bins([source.dec for source in sources]),
                background_energy=bound_precomputed_background.energy,
            )
        else:
            energy_background_pdf = PDDataBackgroundI3EnergyPDF(
                cfg=cfg,
                data_exp=data.exp,
                logE_binning=log_energy_binning,
                sinDec_binning=sin_dec_binning,
                smoothing_filter=BlockSmoothingFilter(nbins=1),
                kde_smoothing=False,
            )
            energy_ratio = create_multi_source_energy_pdfratio(
                cfg=cfg,
                dataset=dataset,
                source_decs=[source.dec for source in sources],
                fluxmodel=model.fluxmodel,
                gamma_grid=model.gamma_grid,
                background_pdf=energy_background_pdf,
                smearing_matrix=None,
                event_data=data.exp,
                fixed_gamma=None if config.spectrum.fit_gamma else config.spectrum.gamma,
                cache_dir=config.dataset.cache_dir,
                ppbar=ppbar,
            )
        total_ratio = spatial_ratio * energy_ratio * time_components.ratio
        tdm = TrialDataManager()
        tdm.add_source_data_field(name='src_array', func=pointlikesource_to_data_field_array)
        tdm.add_data_field(name='psi', func=get_tdm_field_func_psi(), dt='dec', is_srcevt_data=True)
        if config.likelihood.event_selection_method == 'source_time_spatial_box':
            event_selection = SourceTimeSpatialBoxEventSelectionMethod(
                shg_mgr=model.shg_mgr,
                time_centers_mjd=time_centers,
                time_widths_days=time_widths,
                delta_angle=selection_angle,
            )
        else:
            event_selection = SpatialBoxEventSelectionMethod(shg_mgr=model.shg_mgr, delta_angle=selection_angle)
        bkg_generator = None
        if construct_background_generator:
            scrambling_method = I3SeasonalVariationTimeScramblingMethod(data=data)
            scrambler = DataScrambler(scrambling_method)
            bkg_method = FixedScrambledExpDataI3BkgGenMethod(cfg=cfg, data_scrambler=scrambler)
            bkg_generator = DatasetBackgroundGenerator(
                cfg=cfg,
                dataset=dataset,
                data=data,
                bkg_gen_method=bkg_method,
            )
        model.analysis.add_dataset(
            dataset,
            data,
            pdfratio=total_ratio,
            tdm=tdm,
            event_selection_method=event_selection,
            bkg_generator=bkg_generator,
            sig_generator=None,
        )
        time_components_list.append(time_components)
        tdms.append(tdm)
        pdfratios.append(total_ratio)
        spatial_pdfratios.append(spatial_ratio)
        energy_background_pdfs.append(energy_background_pdf)
        precomputed_backgrounds.append(bound_precomputed_background)
        precomputed_signal_grids.append(precomputed_signal_grid)

    model.analysis.construct_services(ppbar=ppbar)
    model.analysis.llhratio = model.analysis.construct_llhratio(minimizer=model.minimizer, ppbar=ppbar)
    if construct_background_generator:
        model.analysis.construct_background_generator()

    return ConstructedCatalogAnalysis(
        config=config,
        datasets=datasets,
        selection=selection,
        model=model,
        data_list=tuple(loaded_data),
        livetimes=tuple(livetimes),
        time_components_list=tuple(time_components_list),
        tdms=tuple(tdms),
        pdfratios=tuple(pdfratios),
        spatial_pdfratios=tuple(spatial_pdfratios),
        energy_background_pdfs=tuple(energy_background_pdfs),
        precomputed_backgrounds=tuple(precomputed_backgrounds),
        precomputed_signal_grids=tuple(precomputed_signal_grids),
    )
