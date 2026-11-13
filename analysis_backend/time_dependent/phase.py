"""Phase-aware detector-yield helpers for transient catalog analyses."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

import numpy as np

from skyllh.core.dataset import Dataset, DatasetData
from skyllh.core.detsigyield import DetSigYield, DetSigYieldBuilder
from skyllh.core.livetime import Livetime
from skyllh.core.progressbar import ProgressBar
from skyllh.core.source_hypo_grouping import SourceHypoGroup

from .catalog import CatalogSelectionResult, ExcludedCatalogSource, SelectedCatalogSource


def source_phase_exposure_fractions(
    livetime: Livetime,
    time_centers_mjd: Sequence[float],
    time_widths_days: Sequence[float],
) -> np.ndarray:
    """Return each box window's on-time overlap divided by phase livetime."""

    centers = np.asarray(time_centers_mjd, dtype=np.float64)
    widths = np.asarray(time_widths_days, dtype=np.float64)
    if centers.ndim != 1 or widths.shape != centers.shape:
        raise ValueError('source centers and widths must be same-length vectors')
    if np.any(~np.isfinite(centers)) or np.any(~np.isfinite(widths)) or np.any(widths <= 0):
        raise ValueError('source centers must be finite and widths must be finite and positive')
    phase_livetime = float(livetime.livetime)
    if phase_livetime <= 0:
        raise ValueError('phase livetime must be positive')
    intervals = livetime.uptime_mjd_intervals_arr
    starts = centers - 0.5 * widths
    stops = centers + 0.5 * widths
    overlap = np.maximum(
        0.0,
        np.minimum(stops[:, np.newaxis], intervals[np.newaxis, :, 1])
        - np.maximum(starts[:, np.newaxis], intervals[np.newaxis, :, 0]),
    ).sum(axis=1)
    return overlap / phase_livetime


def filter_catalog_selection_for_livetimes(
    selection: CatalogSelectionResult,
    livetimes: Sequence[Livetime],
) -> CatalogSelectionResult:
    """Exclude bounding-period matches whose windows contain no detector on-time."""

    kept = []
    excluded = list(selection.excluded)
    for item in selection.selected:
        source = item.source
        fractions = [
            source_phase_exposure_fractions(
                livetime,
                [source.time_center_mjd],
                [source.time_width_days],
            )[0]
            for livetime in livetimes
        ]
        if any(fraction > 0 for fraction in fractions):
            kept.append(item)
        else:
            excluded.append(ExcludedCatalogSource(source=source, reasons=('no_detector_livetime_overlap',)))
    if not kept:
        raise ValueError('no selected catalog source window overlaps detector livetime')
    weight_sum = sum(float(item.source.weight_raw) for item in kept if item.source.weight_raw is not None)
    normalized = tuple(
        SelectedCatalogSource(
            source=item.source,
            normalized_weight=float(item.source.weight_raw) / weight_sum,
            observable_window_fraction=item.observable_window_fraction,
        )
        for item in kept
    )
    return replace(selection, selected=normalized, excluded=tuple(excluded))


class PhaseExposureDetSigYield(DetSigYield):
    """Scale a native detector yield by per-source transient exposure."""

    def __init__(self, base: DetSigYield, exposure_fractions: Sequence[float]):
        self.base = base
        self.exposure_fractions = np.asarray(exposure_fractions, dtype=np.float64)
        if self.exposure_fractions.ndim != 1 or np.any(self.exposure_fractions < 0):
            raise ValueError('exposure fractions must be a nonnegative vector')
        super().__init__(
            param_names=base.param_names,
            dataset=base.dataset,
            fluxmodel=base.fluxmodel,
            livetime=base.livetime,
        )

    def sources_to_recarray(self, sources):
        return self.base.sources_to_recarray(sources)

    def __call__(self, src_recarray, src_params_recarray):
        values, gradients = self.base(src_recarray, src_params_recarray)
        if len(values) != len(self.exposure_fractions):
            raise ValueError('detector yield source count does not match phase exposure count')
        return (
            values * self.exposure_fractions,
            {key: value * self.exposure_fractions for key, value in gradients.items()},
        )


class PhaseExposureDetSigYieldBuilder(DetSigYieldBuilder):
    """Redistribute each source's combined-phase yield over active phases.

    Native public-data yields contain the full phase livetime.  Multiplying by
    ``overlap / phase_livetime`` supplies the transient exposure.  A per-source
    common normalization then preserves the total combined-phase convention;
    in particular, every active source has factor one in a one-phase analysis.
    """

    def __init__(
        self,
        base: DetSigYieldBuilder,
        livetimes_by_dataset: dict[str, Livetime],
        time_centers_mjd: Sequence[float],
        time_widths_days: Sequence[float],
    ):
        super().__init__(cfg=base.cfg)
        self.base = base
        local_fractions = {
            name: source_phase_exposure_fractions(livetime, time_centers_mjd, time_widths_days)
            for name, livetime in livetimes_by_dataset.items()
        }
        phase_livetimes = {name: float(livetime.livetime) for name, livetime in livetimes_by_dataset.items()}
        total_overlap = sum(
            local_fractions[name] * phase_livetimes[name] for name in livetimes_by_dataset
        )
        if np.any(total_overlap <= 0):
            raise ValueError('every selected source must overlap at least one configured phase')
        total_livetime = sum(phase_livetimes.values())
        self.exposure_by_dataset = {
            name: fractions * total_livetime / total_overlap for name, fractions in local_fractions.items()
        }

    def construct_detsigyield(
        self,
        dataset: Dataset,
        data: DatasetData,
        shg: SourceHypoGroup,
        ppbar: ProgressBar | None = None,
    ) -> PhaseExposureDetSigYield:
        if dataset.name not in self.exposure_by_dataset:
            raise KeyError(f'no phase exposure configured for dataset {dataset.name!r}')
        base = self.base.construct_detsigyield(dataset=dataset, data=data, shg=shg, ppbar=ppbar)
        return PhaseExposureDetSigYield(base, self.exposure_by_dataset[dataset.name])

