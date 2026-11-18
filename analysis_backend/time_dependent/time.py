"""Source-specific time-PDF assembly using native SkyLLH components."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from skyllh.core.backgroundpdf import BackgroundTimePDF
from skyllh.core.flux_model import BoxTimeFluxProfile, TimeFluxProfile
from skyllh.core.livetime import Livetime
from skyllh.core.parameters import Parameter
from skyllh.core.pdfratio import PDFRatio, SigOverBkgPDFRatio
from .compat import GaussianTimeFluxProfile, SignalTimePDF

if TYPE_CHECKING:
    from .analysis import CatalogAnalysisModel


@dataclass(frozen=True)
class SourceTimePDFComponents:
    """Objects used to evaluate source-specific fixed time PDFs."""

    center_parameters: tuple[Parameter, ...]
    width_parameters: tuple[Parameter, ...]
    profile: TimeFluxProfile
    signal_pdf: SignalTimePDF
    background_pdf: BackgroundTimePDF
    ratio: PDFRatio


def create_source_time_pdf_components(
    model: CatalogAnalysisModel,
    livetime: Livetime,
    time_centers_mjd: Sequence[float],
    time_widths_days: Sequence[float],
    *,
    profile_type: str = 'box',
    gaussian_sigmas_days: Sequence[float] | None = None,
    gaussian_tail_tolerance: float = 1e-12,
    center_parameters: Sequence[Parameter] | None = None,
    width_parameters: Sequence[Parameter] | None = None,
) -> SourceTimePDFComponents:
    """Create native time PDFs with fixed center and width per source."""

    centers = np.asarray(time_centers_mjd, dtype=np.float64)
    widths = np.asarray(time_widths_days, dtype=np.float64)
    n_sources = len(model.sources)
    if centers.shape != (n_sources,) or widths.shape != (n_sources,):
        raise ValueError('time center and width arrays must contain exactly one value per source')
    if not np.all(np.isfinite(centers)) or not np.all(np.isfinite(widths)):
        raise ValueError('source time parameters must be finite')
    if np.any(widths <= 0):
        raise ValueError('source time-window widths must be positive')
    if profile_type not in ('box', 'gaussian'):
        raise ValueError('profile_type must be box or gaussian')
    if not 0.0 < gaussian_tail_tolerance < 1.0:
        raise ValueError('gaussian_tail_tolerance must lie strictly between zero and one')
    if profile_type == 'gaussian':
        if gaussian_sigmas_days is None:
            raise ValueError('gaussian_sigmas_days is required for Gaussian time profiles')
        scales = np.asarray(gaussian_sigmas_days, dtype=np.float64)
        if scales.shape != (n_sources,) or not np.all(np.isfinite(scales)) or np.any(scales <= 0.0):
            raise ValueError('Gaussian time sigmas must contain one finite positive value per source')
    else:
        if gaussian_sigmas_days is not None:
            raise ValueError('gaussian_sigmas_days is only valid for Gaussian time profiles')
        scales = widths

    if (center_parameters is None) != (width_parameters is None):
        raise ValueError('center_parameters and width_parameters must be provided together')
    if center_parameters is None:
        centers_params = []
        widths_params = []
        for source_idx, (source, center, scale) in enumerate(zip(model.sources, centers, scales, strict=True)):
            center_parameter = Parameter(name=f't0_src_{source_idx}', initial=center, isfixed=True)
            scale_name = 'tw' if profile_type == 'box' else 'sigma_t'
            width_parameter = Parameter(name=f'{scale_name}_src_{source_idx}', initial=scale, isfixed=True)
            model.pmm.map_param(center_parameter, models=source, model_param_names='t0')
            model.pmm.map_param(width_parameter, models=source, model_param_names=scale_name)
            centers_params.append(center_parameter)
            widths_params.append(width_parameter)
    else:
        centers_params = list(center_parameters)
        widths_params = list(width_parameters or ())
        if len(centers_params) != n_sources or len(widths_params) != n_sources:
            raise ValueError('reused time parameter arrays must match the number of sources')

    if profile_type == 'box':
        profile: TimeFluxProfile = BoxTimeFluxProfile(t0=centers[0], tw=widths[0], cfg=model.analysis.cfg)
    else:
        profile = GaussianTimeFluxProfile(
            t0=centers[0], sigma_t=scales[0], tol=gaussian_tail_tolerance, cfg=model.analysis.cfg
        )
    signal_pdf = SignalTimePDF(
        cfg=model.analysis.cfg,
        pmm=model.pmm,
        livetime=livetime,
        time_flux_profile=profile,
    )
    background_pdf = BackgroundTimePDF(
        cfg=model.analysis.cfg,
        livetime=livetime,
        time_flux_profile=BoxTimeFluxProfile.from_start_and_stop_time(
            start=livetime.time_start,
            stop=livetime.time_stop,
            cfg=model.analysis.cfg,
        ),
    )
    ratio = SigOverBkgPDFRatio(
        cfg=model.analysis.cfg,
        sig_pdf=signal_pdf,
        bkg_pdf=background_pdf,
        same_axes=False,
    )
    return SourceTimePDFComponents(
        center_parameters=tuple(centers_params),
        width_parameters=tuple(widths_params),
        profile=profile,
        signal_pdf=signal_pdf,
        background_pdf=background_pdf,
        ratio=ratio,
    )
