"""Declination-aware signal-energy PDF ratios for source catalogs."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

import numpy as np

from skyllh.analyses.i3.publicdata_ps.pdfratio import PDSigSetOverBkgPDFRatio
from skyllh.analyses.i3.publicdata_ps.signalpdf import PDSignalEnergyPDF, PDSignalEnergyPDFSet
from skyllh.analyses.i3.publicdata_ps.smearing_matrix import PDSmearingMatrix
from skyllh.core.config import Config
from skyllh.core.dataset import Dataset
from skyllh.core.flux_model import FactorizedFluxModel
from skyllh.core.parameters import ParameterGrid
from skyllh.core.pdf import PDF
from skyllh.core.pdfratio import PDFRatio
from skyllh.core.progressbar import ProgressBar
from skyllh.core.storage import DataFieldRecordArray
from skyllh.core.timing import TimeLord
from skyllh.core.trialdata import TrialDataManager


class MultiSourcePDEnergyPDFRatio(PDFRatio):
    """Route each source-event pair through its detector-response bin.

    Child ratios return values for all source-event pairs.  This adapter copies
    only the entries belonging to sources in the child's declination bin.  The
    child PDF objects are shared by all sources in the same tabulated response
    bin.
    """

    def __init__(
        self,
        source_bin_indices: Sequence[int],
        ratios_by_bin: Mapping[int, PDFRatio],
        **kwargs,
    ):
        source_bin_indices = np.asarray(source_bin_indices, dtype=np.int64)
        if source_bin_indices.ndim != 1 or len(source_bin_indices) == 0:
            raise ValueError('source_bin_indices must be a non-empty one-dimensional sequence')
        missing_bins = sorted(set(source_bin_indices).difference(ratios_by_bin))
        if missing_bins:
            raise ValueError(f'no energy PDF ratio supplied for response bins {missing_bins}')
        if any(not isinstance(ratio, PDFRatio) for ratio in ratios_by_bin.values()):
            raise TypeError('all ratios_by_bin values must be PDFRatio instances')

        self._source_bin_indices = source_bin_indices
        self._ratios_by_bin = dict(ratios_by_bin)
        sig_names = sorted({name for ratio in ratios_by_bin.values() for name in ratio.sig_param_names})
        bkg_names = sorted({name for ratio in ratios_by_bin.values() for name in ratio.bkg_param_names})
        super().__init__(sig_param_names=sig_names, bkg_param_names=bkg_names, **kwargs)

    @property
    def source_bin_indices(self) -> np.ndarray:
        return self._source_bin_indices.copy()

    @property
    def ratios_by_bin(self) -> dict[int, PDFRatio]:
        return dict(self._ratios_by_bin)

    def initialize_for_new_trial(self, tdm: TrialDataManager, tl: TimeLord | None = None, **kwargs):
        for ratio in self._ratios_by_bin.values():
            ratio.initialize_for_new_trial(tdm=tdm, tl=tl, **kwargs)

    def _validate_tdm(self, tdm: TrialDataManager) -> tuple[np.ndarray, np.ndarray]:
        if tdm.n_sources != len(self._source_bin_indices):
            raise ValueError(
                f'trial data contains {tdm.n_sources} sources but the energy adapter was built for '
                f'{len(self._source_bin_indices)}'
            )
        if tdm.src_evt_idxs is None:
            raise ValueError('trial data has no source-event index mapping')
        return tdm.src_evt_idxs

    def _route(self, tdm: TrialDataManager, evaluate) -> np.ndarray:
        src_idxs, _ = self._validate_tdm(tdm)
        result = np.empty(tdm.get_n_values(), dtype=np.float64)
        for bin_idx, ratio in self._ratios_by_bin.items():
            values = evaluate(ratio)
            if np.isscalar(values):
                values = np.full(tdm.get_n_values(), values, dtype=np.float64)
            values = np.asarray(values)
            if values.shape != result.shape:
                raise ValueError(
                    f'energy ratio for response bin {bin_idx} returned shape {values.shape}; expected {result.shape}'
                )
            source_mask = self._source_bin_indices == bin_idx
            value_mask = source_mask[src_idxs]
            result[value_mask] = values[value_mask]
        return result

    def get_ratio(
        self,
        tdm: TrialDataManager,
        src_params_recarray: np.ndarray,
        tl: TimeLord | None = None,
    ) -> np.ndarray:
        return self._route(
            tdm,
            lambda ratio: ratio.get_ratio(tdm=tdm, src_params_recarray=src_params_recarray, tl=tl),
        )

    def get_gradient(
        self,
        tdm: TrialDataManager,
        src_params_recarray: np.ndarray,
        fitparam_id: int,
        tl: TimeLord | None = None,
    ) -> np.ndarray:
        return self._route(
            tdm,
            lambda ratio: ratio.get_gradient(
                tdm=tdm,
                src_params_recarray=src_params_recarray,
                fitparam_id=fitparam_id,
                tl=tl,
            ),
        )


class PrecomputedFixedGammaEnergyPDFRatio(PDFRatio):
    """Look up fixed-gamma energy ratios by source response row and event ID."""

    def __init__(
        self,
        source_response_rows: Sequence[int],
        ratio_table: np.ndarray,
        event_id_field: str = 'catalog_event_id',
        **kwargs,
    ):
        source_response_rows = np.asarray(source_response_rows, dtype=np.int32)
        ratio_table = np.asarray(ratio_table)
        if source_response_rows.ndim != 1 or len(source_response_rows) == 0:
            raise ValueError('source_response_rows must be a non-empty one-dimensional sequence')
        if ratio_table.ndim != 2:
            raise ValueError('ratio_table must have shape (response rows, events)')
        if np.any(source_response_rows < 0) or np.any(source_response_rows >= ratio_table.shape[0]):
            raise ValueError('source response row lies outside ratio_table')
        self._source_response_rows = source_response_rows
        self._ratio_table = ratio_table
        self._event_id_field = event_id_field
        super().__init__(sig_param_names=(), bkg_param_names=(), **kwargs)

    @property
    def ratio_table(self) -> np.ndarray:
        return self._ratio_table

    def initialize_for_new_trial(self, tdm: TrialDataManager, tl: TimeLord | None = None, **kwargs):
        if tdm.n_sources != len(self._source_response_rows):
            raise ValueError('trial source count does not match precomputed energy table')
        if self._event_id_field not in tdm:
            raise KeyError(f'trial data is missing event ID field {self._event_id_field!r}')

    def get_ratio(
        self,
        tdm: TrialDataManager,
        src_params_recarray: np.ndarray,
        tl: TimeLord | None = None,
    ) -> np.ndarray:
        if tdm.src_evt_idxs is None:
            raise ValueError('trial data has no source-event index mapping')
        src_idxs, evt_idxs = tdm.src_evt_idxs
        event_ids = tdm[self._event_id_field][evt_idxs]
        response_rows = self._source_response_rows[src_idxs]
        return np.asarray(self._ratio_table[response_rows, event_ids], dtype=np.float64)

    def get_gradient(
        self,
        tdm: TrialDataManager,
        src_params_recarray: np.ndarray,
        fitparam_id: int,
        tl: TimeLord | None = None,
    ) -> np.ndarray:
        return np.zeros(tdm.get_n_values(), dtype=np.float64)


class ExactSourceFixedGammaEnergyPDFRatio(PDFRatio):
    """Evaluate one exact fixed-gamma signal-energy spline per source.

    This adapter is intended for independent source scans.  The stacking
    adapter can share one representative signal PDF within a detector response
    bin, whereas an independent scan must reproduce the PDF built at each
    source's exact declination.
    """

    def __init__(
        self,
        signal_pdfs: Sequence[PDSignalEnergyPDF],
        background_pdf: PDF,
        **kwargs,
    ):
        if not signal_pdfs:
            raise ValueError('signal_pdfs must contain at least one source PDF')
        self._signal_pdfs = tuple(signal_pdfs)
        self._background_pdf = background_pdf
        super().__init__(sig_param_names=(), bkg_param_names=(), **kwargs)

    def initialize_for_new_trial(self, tdm: TrialDataManager, tl: TimeLord | None = None, **kwargs):
        if tdm.n_sources != len(self._signal_pdfs):
            raise ValueError('trial source count does not match exact source energy PDFs')
        self._background_pdf.initialize_for_new_trial(tdm=tdm, tl=tl, **kwargs)

    def get_ratio(
        self,
        tdm: TrialDataManager,
        src_params_recarray: np.ndarray,
        tl: TimeLord | None = None,
    ) -> np.ndarray:
        if tdm.src_evt_idxs is None:
            raise ValueError('trial data has no source-event index mapping')
        src_idxs, evt_idxs = tdm.src_evt_idxs
        result = np.empty(tdm.get_n_values(), dtype=np.float64)
        log_energy = tdm['log_energy']
        background_values, _ = self._background_pdf.get_pd(tdm=tdm, params_recarray=None, tl=tl)
        pair_background = background_values[evt_idxs]
        for source_idx, signal_pdf in enumerate(self._signal_pdfs):
            mask = src_idxs == source_idx
            result[mask] = signal_pdf.get_pd_by_log10_reco_e(log_energy[evt_idxs[mask]], tl=tl)

        nonzero = pair_background > 0
        np.divide(result, pair_background, where=nonzero, out=result)
        np.divide(result, np.finfo(np.double).resolution, where=~nonzero, out=result)
        result[np.isposinf(result)] = np.finfo(np.float32).max
        return result

    def get_gradient(
        self,
        tdm: TrialDataManager,
        src_params_recarray: np.ndarray,
        fitparam_id: int,
        tl: TimeLord | None = None,
    ) -> np.ndarray:
        return np.zeros(tdm.get_n_values(), dtype=np.float64)


def create_exact_source_fixed_gamma_energy_pdfratio(
    cfg: Config,
    dataset: Dataset,
    source_decs: Sequence[float],
    fluxmodel: FactorizedFluxModel,
    gamma_grid: ParameterGrid,
    background_pdf: PDF,
    fixed_gamma: float,
    ppbar: ProgressBar | None = None,
) -> ExactSourceFixedGammaEnergyPDFRatio:
    """Build compact exact-declination energy splines for a source scan."""

    source_decs = np.asarray(source_decs, dtype=np.float64)
    if source_decs.ndim != 1 or len(source_decs) == 0:
        raise ValueError('source_decs must be a non-empty one-dimensional sequence')
    smearing_matrix = PDSmearingMatrix(
        pathfilenames=dataset.get_abs_pathfilename_list(dataset.get_aux_data_definition('smearing_datafile'))
    )
    signal_pdfs = []
    for source_dec in source_decs:
        signal_pdf_set = PDSignalEnergyPDFSet(
            cfg=cfg,
            ds=dataset,
            src_dec=float(source_dec),
            fluxmodel=fluxmodel,
            param_grid_set=gamma_grid,
            ppbar=ppbar,
            sm=smearing_matrix,
        )
        signal_pdfs.append(cast(PDSignalEnergyPDF, signal_pdf_set.get_pdf({'gamma': fixed_gamma})))
    return ExactSourceFixedGammaEnergyPDFRatio(
        cfg=cfg,
        signal_pdfs=signal_pdfs,
        background_pdf=background_pdf,
    )


def _dataset_file_fingerprints(dataset: Dataset) -> list[dict[str, int | str]]:
    paths = dataset.get_abs_pathfilename_list(dataset.exp_pathfilename_list)
    for definition in ('smearing_datafile', 'eff_area_datafile'):
        paths.extend(dataset.get_abs_pathfilename_list(dataset.get_aux_data_definition(definition)))
    fingerprints = []
    for path in sorted(set(paths)):
        stat = Path(path).stat()
        fingerprints.append({'path': str(path), 'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns})
    return fingerprints


def _fixed_energy_cache_key(
    dataset: Dataset,
    source_decs: np.ndarray,
    fixed_gamma: float,
    n_events: int,
) -> tuple[str, dict]:
    metadata = {
        'format_version': 1,
        'dataset_name': dataset.name,
        'dataset_version': dataset.version,
        'fixed_gamma': fixed_gamma,
        'n_events': n_events,
        'source_decs_sha256': hashlib.sha256(source_decs.tobytes()).hexdigest(),
        'files': _dataset_file_fingerprints(dataset),
    }
    payload = json.dumps(metadata, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(payload).hexdigest(), metadata


def _write_energy_cache(
    cache_dir: Path,
    cache_key: str,
    ratio_table: np.ndarray,
    source_response_rows: np.ndarray,
    metadata: dict,
) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    table_path = cache_dir / f'{cache_key}.npy'
    metadata_path = cache_dir / f'{cache_key}.json'
    with tempfile.NamedTemporaryFile(dir=cache_dir, prefix=f'.{cache_key}.', suffix='.npy', delete=False) as stream:
        tmp_table_path = Path(stream.name)
        np.save(stream, ratio_table, allow_pickle=False)
    tmp_metadata_path = tmp_table_path.with_suffix('.json')
    try:
        payload = {
            **metadata,
            'source_response_rows': source_response_rows.tolist(),
            'shape': list(ratio_table.shape),
            'dtype': str(ratio_table.dtype),
        }
        tmp_metadata_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        os.replace(tmp_table_path, table_path)
        os.replace(tmp_metadata_path, metadata_path)
    finally:
        tmp_table_path.unlink(missing_ok=True)
        tmp_metadata_path.unlink(missing_ok=True)


def _load_energy_cache(
    cache_dir: Path,
    cache_key: str,
) -> tuple[np.ndarray, np.ndarray] | None:
    table_path = cache_dir / f'{cache_key}.npy'
    metadata_path = cache_dir / f'{cache_key}.json'
    if not table_path.is_file() or not metadata_path.is_file():
        return None
    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    ratio_table = np.load(table_path, mmap_mode='r', allow_pickle=False)
    if list(ratio_table.shape) != metadata['shape'] or str(ratio_table.dtype) != metadata['dtype']:
        raise ValueError(f'invalid fixed-gamma energy cache {table_path}')
    return ratio_table, np.asarray(metadata['source_response_rows'], dtype=np.int32)


def _build_fixed_gamma_ratio_table(
    cfg: Config,
    dataset: Dataset,
    source_decs: np.ndarray,
    fluxmodel: FactorizedFluxModel,
    gamma_grid: ParameterGrid,
    background_pdf: PDF,
    smearing_matrix: PDSmearingMatrix,
    event_data: DataFieldRecordArray,
    fixed_gamma: float,
    ppbar: ProgressBar | None,
) -> tuple[np.ndarray, np.ndarray]:
    source_bin_indices = np.asarray(
        [smearing_matrix.get_true_dec_idx(dec) for dec in source_decs],
        dtype=np.int64,
    )
    unique_bins = np.unique(source_bin_indices)
    bin_to_row = {int(bin_idx): row for row, bin_idx in enumerate(unique_bins)}
    source_response_rows = np.asarray([bin_to_row[int(bin_idx)] for bin_idx in source_bin_indices], dtype=np.int32)

    bkg_spline = background_pdf._pdf_spline
    background_values = bkg_spline(event_data['log_energy'], event_data['sin_dec'], grid=False)
    ratio_table = np.empty((len(unique_bins), len(event_data)), dtype=np.float64)
    for response_row, bin_idx in enumerate(unique_bins):
        representative_source_idx = int(np.flatnonzero(source_bin_indices == bin_idx)[0])
        signal_pdf_set = PDSignalEnergyPDFSet(
            cfg=cfg,
            ds=dataset,
            src_dec=float(source_decs[representative_source_idx]),
            fluxmodel=fluxmodel,
            param_grid_set=gamma_grid,
            ppbar=ppbar,
            sm=smearing_matrix,
        )
        signal_pdf = cast(PDSignalEnergyPDF, signal_pdf_set.get_pdf({'gamma': fixed_gamma}))
        signal_values = signal_pdf.get_pd_by_log10_reco_e(event_data['log_energy'])
        ratio = signal_values.copy()
        nonzero = background_values > 0
        np.divide(ratio, background_values, where=nonzero, out=ratio)
        np.divide(ratio, np.finfo(np.double).resolution, where=~nonzero, out=ratio)
        ratio[np.isposinf(ratio)] = np.finfo(np.float32).max
        ratio_table[response_row] = ratio
    return ratio_table, source_response_rows


def create_multi_source_energy_pdfratio(
    cfg: Config,
    dataset: Dataset,
    source_decs: Sequence[float],
    fluxmodel: FactorizedFluxModel,
    gamma_grid: ParameterGrid,
    background_pdf: PDF,
    smearing_matrix: PDSmearingMatrix | None,
    event_data: DataFieldRecordArray | None = None,
    fixed_gamma: float | None = None,
    cache_dir: str | Path | None = None,
    ppbar: ProgressBar | None = None,
) -> MultiSourcePDEnergyPDFRatio | PrecomputedFixedGammaEnergyPDFRatio:
    """Build one public-data signal-energy PDF grid per occupied dec bin."""

    source_decs = np.asarray(source_decs, dtype=np.float64)
    if source_decs.ndim != 1 or len(source_decs) == 0:
        raise ValueError('source_decs must be a non-empty one-dimensional sequence')
    if fixed_gamma is not None:
        if event_data is None:
            raise ValueError('event_data is required for a fixed-gamma energy lookup')
        cached = None
        cache_key = None
        cache_metadata = None
        if cache_dir is not None:
            cache_dir = Path(cache_dir)
            cache_key, cache_metadata = _fixed_energy_cache_key(dataset, source_decs, fixed_gamma, len(event_data))
            cached = _load_energy_cache(cache_dir, cache_key)
        if cached is None:
            if smearing_matrix is None:
                smearing_matrix = PDSmearingMatrix(
                    pathfilenames=dataset.get_abs_pathfilename_list(
                        dataset.get_aux_data_definition('smearing_datafile')
                    )
                )
            ratio_table, source_response_rows = _build_fixed_gamma_ratio_table(
                cfg=cfg,
                dataset=dataset,
                source_decs=source_decs,
                fluxmodel=fluxmodel,
                gamma_grid=gamma_grid,
                background_pdf=background_pdf,
                smearing_matrix=smearing_matrix,
                event_data=event_data,
                fixed_gamma=fixed_gamma,
                ppbar=ppbar,
            )
            if cache_dir is not None:
                assert cache_key is not None and cache_metadata is not None
                _write_energy_cache(
                    cache_dir,
                    cache_key,
                    ratio_table,
                    source_response_rows,
                    cache_metadata,
                )
                cached = _load_energy_cache(cache_dir, cache_key)
                assert cached is not None
                ratio_table, source_response_rows = cached
        else:
            ratio_table, source_response_rows = cached
        return PrecomputedFixedGammaEnergyPDFRatio(
            cfg=cfg,
            source_response_rows=source_response_rows,
            ratio_table=ratio_table,
        )

    if smearing_matrix is None:
        smearing_matrix = PDSmearingMatrix(
            pathfilenames=dataset.get_abs_pathfilename_list(dataset.get_aux_data_definition('smearing_datafile'))
        )
    source_bin_indices = np.asarray(
        [smearing_matrix.get_true_dec_idx(dec) for dec in source_decs],
        dtype=np.int64,
    )
    ratios_by_bin = {}
    for bin_idx in np.unique(source_bin_indices):
        representative_source_idx = int(np.flatnonzero(source_bin_indices == bin_idx)[0])
        signal_pdf_set = PDSignalEnergyPDFSet(
            cfg=cfg,
            ds=dataset,
            src_dec=float(source_decs[representative_source_idx]),
            fluxmodel=fluxmodel,
            param_grid_set=gamma_grid,
            ppbar=ppbar,
            sm=smearing_matrix,
        )
        ratios_by_bin[int(bin_idx)] = PDSigSetOverBkgPDFRatio(
            cfg=cfg,
            sig_pdf_set=signal_pdf_set,
            bkg_pdf=background_pdf,
        )
    return MultiSourcePDEnergyPDFRatio(
        cfg=cfg,
        source_bin_indices=source_bin_indices,
        ratios_by_bin=ratios_by_bin,
    )

