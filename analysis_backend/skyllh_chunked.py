"""Memory-bounded exact all-event stacking components for SkyLLH v26.

The public SkyLLH multi-source path materializes one value for every
source--event pair.  The classes here preserve the same sum, but evaluate it
in event and source blocks and immediately reduce each block to event-only
values.  No source or event is selected out.
"""

from __future__ import annotations

from time import perf_counter
import zlib

import numpy as np
from skyllh.core.analysis import MultiSourceMultiDatasetLLHRatioAnalysis
from skyllh.core.event_selection import AllEventSelectionMethod
from skyllh.core.llhratio import MultiDatasetTCLLHRatio, ZeroSigH0SingleDatasetTCLLHRatio
from skyllh.core.pdfratio import PDFRatio

from analysis_backend.skyllh_dr2_pdfs import (
    BACKGROUND_ENERGY_FIELD,
    BACKGROUND_SPATIAL_FIELD,
)


DEFAULT_TARGET_PAIRS = 2**20
DEFAULT_MAX_EVENT_CHUNK = 2048
DEFAULT_MAX_SOURCE_CHUNK = 2048
DEFAULT_SPATIAL_CACHE_BYTES = 2**30
DEFAULT_ENERGY_CACHE_BYTES = 2**24


class _ExactEnergyInterpolationCache:
    """Evaluate np.interp once per exact observed energy and PDF table node.

    The inverse map restores every event in its original order. Neither the
    observed energies nor the tabulated PDF values are rounded or rebinned.
    The payload budget includes the inverse map and the distinct energies.
    """

    def __init__(self, max_bytes=DEFAULT_ENERGY_CACHE_BYTES, node_count=3):
        self.max_bytes = max(0, int(max_bytes))
        self.node_count = int(node_count)
        self.initialize(np.empty(0), 0.0, 0.0, prepare=False)

    def initialize(self, loge, energy_min, energy_max, prepare=True):
        self._values = {}
        self.positions = None
        self.energies = None
        self.nbytes = 0
        self.hits = self.misses = self.interpolation_calls = 0
        self.interpolation_seconds = 0.0
        self._full = False
        self.reason = "not_initialized" if not prepare else "payload_budget"
        if not prepare or self.max_bytes == 0:
            return
        dtype = np.int32 if len(loge) < np.iinfo(np.int32).max else np.int64
        position_bytes = len(loge) * np.dtype(dtype).itemsize
        if position_bytes >= self.max_bytes:
            return
        valid = (loge >= energy_min) & (loge < energy_max)
        energies, inverse = np.unique(loge[valid], return_inverse=True)
        # Reserve the requested two-node or three-node interpolation lookups.
        base_bytes = position_bytes + energies.nbytes
        if base_bytes + self.node_count * (len(energies) + 1) * 8 > self.max_bytes:
            return
        positions = np.full(len(loge), len(energies), dtype=dtype)
        positions[valid] = inverse
        positions.setflags(write=False)
        energies.setflags(write=False)
        self.positions, self.energies = positions, energies
        self.nbytes = base_bytes
        self.reason = "enabled"

    def interpolate(self, key, axis, values, positions):
        lookup = self._values.get(key)
        if lookup is None:
            self.misses += 1
            vector_bytes = (len(self.energies) + 1) * 8
            if self._full or self.nbytes + vector_bytes > self.max_bytes:
                self._full = True
                return None
            started = perf_counter()
            # The last entry is the original positive zero for invalid events.
            lookup = np.zeros(len(self.energies) + 1, dtype=np.float64)
            lookup[:-1] = np.interp(self.energies, axis, values)
            self.interpolation_seconds += perf_counter() - started
            self.interpolation_calls += 1
            lookup.setflags(write=False)
            self._values[key] = lookup
            self.nbytes += lookup.nbytes
        else:
            self.hits += 1
        return lookup[positions]

    def provenance(self):
        return dict(enabled=self.positions is not None, reason=self.reason,
                    strategy="exact_observed_energy_np_interp_lookup",
                    payload_budget_bytes=self.max_bytes, payload_bytes=self.nbytes,
                    unique_valid_energies=0 if self.energies is None else len(self.energies),
                    cached_pdf_nodes=len(self._values), hits=self.hits, misses=self.misses,
                    np_interp_calls=self.interpolation_calls,
                    np_interp_seconds=self.interpolation_seconds, budget_saturated=self._full)


class _ExactSpatialBlockCache:
    """Fit-local, byte-bounded, lossless cache shared by the dataset ratios.

    Compression preserves every float64 bit, including underflows and NaNs.
    No angular cut, value threshold or change of summation order is applied.
    Uncached blocks retain the original calculation when the budget is full.
    """

    def __init__(self, max_bytes=DEFAULT_SPATIAL_CACHE_BYTES):
        self.max_bytes = max(0, int(max_bytes))
        self.nbytes = 0
        self._blocks = {}
        self._stats = {}
        self._full = self.max_bytes == 0

    def reset(self, namespace):
        for key in [key for key in self._blocks if key[0] is namespace]:
            self.nbytes -= len(self._blocks.pop(key)[0])
        self._full = self.nbytes >= self.max_bytes
        self._stats[namespace] = dict(hits=0, misses=0, cached_blocks=0,
            compressed_bytes=0, geometry_seconds=0.0, compression_seconds=0.0,
            decompression_seconds=0.0)

    def get(self, namespace, block):
        record = self._blocks.get((namespace, *block))
        stats = self._stats[namespace]
        if record is None:
            stats["misses"] += 1
            return None
        started = perf_counter()
        payload, shape = record
        result = np.frombuffer(zlib.decompress(payload), dtype=np.float64).reshape(shape)
        stats["decompression_seconds"] += perf_counter() - started
        stats["hits"] += 1
        return result

    def put(self, namespace, block, values, geometry_seconds):
        stats = self._stats[namespace]
        stats["geometry_seconds"] += geometry_seconds
        if self._full:
            return
        started = perf_counter()
        payload = zlib.compress(values.tobytes(order="C"), level=1)
        stats["compression_seconds"] += perf_counter() - started
        if self.nbytes + len(payload) > self.max_bytes:
            self._full = True
            return
        self._blocks[(namespace, *block)] = (payload, values.shape)
        self.nbytes += len(payload)
        stats["compressed_bytes"] += len(payload)
        stats["cached_blocks"] += 1

    def provenance(self, namespace):
        return dict(enabled=True, storage="lossless_zlib_float64_blocks",
                    shared_payload_budget_bytes=self.max_bytes,
                    shared_compressed_bytes=self.nbytes, **self._stats[namespace])


def choose_chunk_shape(
    n_events,
    n_sources,
    target_pairs=DEFAULT_TARGET_PAIRS,
    max_event_chunk=DEFAULT_MAX_EVENT_CHUNK,
    max_source_chunk=DEFAULT_MAX_SOURCE_CHUNK,
):
    """Choose deterministic event/source blocks within the pair budget."""
    n_events = max(1, int(n_events))
    n_sources = max(1, int(n_sources))
    target_pairs = max(1, int(target_pairs))
    source_chunk = min(n_sources, int(max_source_chunk), target_pairs)
    event_chunk = min(n_events, int(max_event_chunk), max(1, target_pairs // source_chunk))
    return event_chunk, source_chunk


class EventOnlyAllEventSelectionMethod(AllEventSelectionMethod):
    """Select all events without allocating the Cartesian source/event map.

    The one-to-one index arrays satisfy TrialDataManager's storage contract;
    the chunked PDF ratio reads the event and source arrays directly and does
    not interpret these arrays as scientific source/event associations.
    """

    def select_events(self, events, src_evt_idxs=None, ret_original_evt_idxs=False, tl=None):
        evt_idxs = np.arange(len(events), dtype=np.int64)
        lightweight_idxs = (np.zeros(len(events), dtype=np.int64), evt_idxs)
        if ret_original_evt_idxs:
            return events, lightweight_idxs, np.asarray(events.indices)
        return events, lightweight_idxs


class ChunkedMultiSourceMultiDatasetLLHRatioAnalysis(MultiSourceMultiDatasetLLHRatioAnalysis):
    """Use already source-weighted, event-only PDF ratios in SkyLLH's LLH."""

    def construct_llhratio(self, minimizer, ppbar=None):
        llhratio_list = [
            ZeroSigH0SingleDatasetTCLLHRatio(
                cfg=self._cfg,
                pmm=self._pmm,
                minimizer=minimizer,
                shg_mgr=self._shg_mgr,
                tdm=tdm,
                pdfratio=pdfratio,
            )
            for tdm, pdfratio in zip(self._tdm_list, self._pdfratio_list, strict=True)
        ]
        return MultiDatasetTCLLHRatio(
            cfg=self._cfg,
            pmm=self._pmm,
            minimizer=minimizer,
            src_detsigyield_weights_service=self.src_detsigyield_weights_service,
            ds_sig_weight_factors_service=self.ds_sig_weight_factors_service,
            llhratio_list=llhratio_list,
        )


class ChunkedSourceWeightedPDFRatio(PDFRatio):
    r"""Evaluate the exact project stacking PDF without a full pair matrix.

    For dataset ``k`` this evaluates

    .. math::

       S_i^k = \frac{\sum_j w_{j,\mathrm{model}}w_{j,\mathrm{acc}}^k
       S_{ij}^{k,\mathrm{spatial}}S_{ij}^{k,\mathrm{energy}}}
       {\sum_j w_{j,\mathrm{model}}w_{j,\mathrm{acc}}^k}

    and returns ``S_i^k / B_i^k``.  SkyLLH's detector-yield service supplies
    the product of the two source weights and its Gamma derivative.
    """

    signal_energy_gamma_interpolation = "parabola_v1"

    def __init__(
        self,
        dataset_idx,
        dataset_name,
        store,
        data_exp,
        source_ras,
        source_decs,
        src_detsigyield_weights_service,
        gamma_grid,
        signal_energy_declination_mode="source",
        target_pairs=DEFAULT_TARGET_PAIRS,
        max_event_chunk=DEFAULT_MAX_EVENT_CHUNK,
        max_source_chunk=DEFAULT_MAX_SOURCE_CHUNK,
        spatial_cache=None,
        energy_cache_max_bytes=DEFAULT_ENERGY_CACHE_BYTES,
        signal_energy_gamma_interpolation="parabola_v1",
        **kwargs,
    ):
        super().__init__(sig_param_names=["gamma"], bkg_param_names=None, **kwargs)
        if signal_energy_gamma_interpolation not in {"parabola_v1", "linear_v1"}:
            raise ValueError("Unsupported signal-energy Gamma interpolation")
        self.signal_energy_gamma_interpolation = signal_energy_gamma_interpolation
        self.dataset_idx = int(dataset_idx)
        self.dataset_name = str(dataset_name)
        self.store = store
        self.source_ras = np.asarray(source_ras, dtype=np.float64)
        self.source_decs = np.asarray(source_decs, dtype=np.float64)
        self.weights_service = src_detsigyield_weights_service
        self.gamma_grid = gamma_grid.copy()
        if signal_energy_declination_mode not in {"source", "event"}:
            raise ValueError("signal_energy_declination_mode must be 'source' or 'event'")
        self.signal_energy_declination_mode = str(signal_energy_declination_mode)
        self.gamma_grid.add_extra_lower_and_upper_bin()
        self.gamma_values = np.asarray(self.gamma_grid.grid, dtype=np.float64)
        self.energy_table = store.compact_signal_grid(self.dataset_name, self.gamma_values)
        self.dec_edges = self.energy_table["dec_edges"]
        self.log_energy_axis = self.energy_table["energy"]
        energy_step = float(np.median(np.diff(self.log_energy_axis)))
        self.energy_min = float(self.log_energy_axis[0] - 0.5 * energy_step)
        self.energy_max = float(self.log_energy_axis[-1] + 0.5 * energy_step)
        self.signal_energy_grid = self.energy_table["values"]
        self.source_dec_indices = np.searchsorted(self.dec_edges, self.source_decs, side="right") - 1
        self.source_dec_indices = np.where(
            self.source_decs == self.dec_edges[-1], len(self.dec_edges) - 2, self.source_dec_indices
        )
        if np.any(self.source_dec_indices < 0) or np.any(self.source_dec_indices >= len(self.dec_edges) - 1):
            raise ValueError("At least one source declination is outside the signal-energy table")
        store.attach_background(data_exp)
        self.target_pairs = int(target_pairs)
        self.n_events = len(data_exp)
        self.event_chunk, self.source_chunk = choose_chunk_shape(
            len(data_exp),
            len(self.source_ras),
            target_pairs=target_pairs,
            max_event_chunk=max_event_chunk,
            max_source_chunk=max_source_chunk,
        )
        self._cache_key = None
        self._cache_ratio = None
        self._cache_gamma_gradient = None
        self._spatial_cache = spatial_cache
        self._spatial_cache_namespace = object()
        if self._spatial_cache is not None:
            self._spatial_cache.reset(self._spatial_cache_namespace)
        self._energy_cache = (_ExactEnergyInterpolationCache(energy_cache_max_bytes,
            node_count=2 if self.signal_energy_gamma_interpolation == "linear_v1" else 3)
                              if len(self.source_ras) > 1 else None)

    @property
    def chunk_provenance(self):
        return {
            "strategy": "exact_adaptive_event_source_double_batching",
            "signal_energy_gamma_interpolation": self.signal_energy_gamma_interpolation,
            "n_events": self.n_events,
            "target_pairs": self.target_pairs,
            "event_chunk": self.event_chunk,
            "source_chunk": self.source_chunk,
            "maximum_working_pairs": self.event_chunk * self.source_chunk,
            "pair_dtype": "float64",
            "spatial_cache": (self._spatial_cache.provenance(self._spatial_cache_namespace)
                              if self._spatial_cache is not None else {"enabled": False}),
            "energy_interpolation_cache": (self._energy_cache.provenance()
                                           if self._energy_cache is not None else {"enabled": False}),
        }

    def initialize_for_new_trial(self, tdm, tl=None, **kwargs):
        self.event_ra = np.asarray(tdm["ra"], dtype=np.float64)
        self.event_dec = np.asarray(tdm["dec"], dtype=np.float64)
        self.event_sigma = np.asarray(tdm["ang_err"], dtype=np.float64)
        self.event_log_energy = np.asarray(tdm["log_energy"], dtype=np.float64)
        self.background = np.asarray(tdm[BACKGROUND_SPATIAL_FIELD], dtype=np.float64) * np.asarray(
            tdm[BACKGROUND_ENERGY_FIELD], dtype=np.float64
        )
        if np.any(self.background <= 0.0):
            raise ValueError("The chunked DR2 backend requires positive pre-calculated background PDFs")
        self._cache_key = None
        if self._spatial_cache is not None:
            self._spatial_cache.reset(self._spatial_cache_namespace)
        if self._energy_cache is not None:
            self._energy_cache.initialize(self.event_log_energy, self.energy_min, self.energy_max)

    def get_ratio(self, tdm, src_params_recarray, tl=None):
        gamma = self._common_gamma(src_params_recarray)
        weights, weight_grads = self.weights_service.get_weights()
        a = np.asarray(weights[self.dataset_idx], dtype=np.float64)
        gamma_fitparam_id = self._gamma_fitparam_id(src_params_recarray)
        da = np.zeros_like(a)
        if gamma_fitparam_id is not None and gamma_fitparam_id in weight_grads:
            da = np.asarray(weight_grads[gamma_fitparam_id][self.dataset_idx], dtype=np.float64)
        cache_key = (tdm.trial_data_state_id, gamma, a.tobytes(), da.tobytes())
        if cache_key != self._cache_key:
            self._cache_ratio, self._cache_gamma_gradient = self._calculate(gamma, a, da)
            self._cache_key = cache_key
        return self._cache_ratio

    def get_gradient(self, tdm, src_params_recarray, fitparam_id, tl=None):
        self.get_ratio(tdm=tdm, src_params_recarray=src_params_recarray, tl=tl)
        gamma_fitparam_id = self._gamma_fitparam_id(src_params_recarray)
        if gamma_fitparam_id == fitparam_id:
            return self._cache_gamma_gradient
        return np.zeros(len(self.event_ra), dtype=np.float64)

    @staticmethod
    def _common_gamma(src_params_recarray):
        gamma = np.asarray(src_params_recarray["gamma"], dtype=np.float64)
        if not np.all(gamma == gamma[0]):
            raise ValueError("The current DR2 stacking backend requires one common Gamma for all sources")
        return float(gamma[0])

    @staticmethod
    def _gamma_fitparam_id(src_params_recarray):
        field = "gamma:gpidx"
        if field not in src_params_recarray.dtype.fields:
            return None
        ids = np.asarray(src_params_recarray[field], dtype=np.int64)
        ids = np.unique(ids[ids > 0])
        if len(ids) == 0:
            return None
        if len(ids) != 1:
            raise ValueError("Gamma must map to one common global fit parameter")
        return int(ids[0] - 1)

    def _gamma_slice_indices(self, gamma):
        if self.signal_energy_gamma_interpolation == "linear_v1":
            if not np.isfinite(gamma) or not self.gamma_values[0] <= gamma <= self.gamma_values[-1]:
                raise ValueError("Gamma is outside the signal-energy interpolation grid")
            upper = min(int(np.searchsorted(self.gamma_values, gamma, side="right")), len(self.gamma_values)-1)
            lower = upper-1
            x0, x1 = self.gamma_values[[lower, upper]]
            return float(x0), float(x1-x0), [lower, upper]
        x1 = float(self.gamma_grid.round_to_nearest_grid_point(gamma))
        dx = float(self.gamma_grid.delta)
        x0 = float(self.gamma_grid.round_to_nearest_grid_point(x1 - dx))
        x2 = float(self.gamma_grid.round_to_nearest_grid_point(x1 + dx))
        indices = [int(np.flatnonzero(np.isclose(self.gamma_values, x, atol=1e-12))[0]) for x in (x0, x1, x2)]
        return x1, dx, indices

    def _gamma_slices(self, gamma):
        x1, dx, indices = self._gamma_slice_indices(gamma)
        return x1, dx, self.signal_energy_grid[:, :, indices]

    def _calculate(self, gamma, a, da):
        A = float(np.sum(a))
        if not np.isfinite(A) or A <= 0.0:
            raise ValueError("The sum of w_{j,model} w_{j,acc}^k must be positive")
        dA = float(np.sum(da))
        x1, dx, gamma_indices = self._gamma_slice_indices(gamma)
        energy_grid = self.signal_energy_grid[:, :, gamma_indices]
        offset = gamma - x1
        n_events = len(self.event_ra)
        numerator = np.zeros(n_events, dtype=np.float64)
        numerator_grad = np.zeros(n_events, dtype=np.float64)

        for e0 in range(0, n_events, self.event_chunk):
            e1 = min(e0 + self.event_chunk, n_events)
            era = self.event_ra[e0:e1]
            edec = self.event_dec[e0:e1]
            sigma_sq = self.event_sigma[e0:e1] ** 2
            loge = self.event_log_energy[e0:e1]
            energy_positions = (self._energy_cache.positions[e0:e1]
                                if self._energy_cache is not None and self._energy_cache.positions is not None
                                else None)
            sin_edec = np.sin(edec)[:, np.newaxis]
            cos_edec = np.cos(edec)[:, np.newaxis]
            block_sum = np.zeros(e1 - e0, dtype=np.float64)
            block_grad = np.zeros(e1 - e0, dtype=np.float64)
            spatial_sum = np.zeros(e1 - e0, dtype=np.float64)
            spatial_grad = np.zeros(e1 - e0, dtype=np.float64)

            for s0 in range(0, len(a), self.source_chunk):
                s1 = min(s0 + self.source_chunk, len(a))
                spatial = self._spatial_block(e0, s0, s1, era, sin_edec, cos_edec, sigma_sq)
                if self.signal_energy_declination_mode == "source":
                    dec_indices = self.source_dec_indices[s0:s1]
                    for dec_idx in np.unique(dec_indices):
                        source_mask = dec_indices == dec_idx
                        M0 = self._interpolate_energy(loge, energy_grid[dec_idx, :, 0], (dec_idx, gamma_indices[0]), energy_positions)
                        M1 = self._interpolate_energy(loge, energy_grid[dec_idx, :, 1], (dec_idx, gamma_indices[1]), energy_positions)
                        if self.signal_energy_gamma_interpolation == "linear_v1":
                            fraction = offset / dx
                            energy = (1.0-fraction)*M0 + fraction*M1
                            energy_grad = (M1-M0) / dx
                        else:
                            M2 = self._interpolate_energy(loge, energy_grid[dec_idx, :, 2], (dec_idx, gamma_indices[2]), energy_positions)
                            parabola_a = 0.5 * (M0 - 2.0 * M1 + M2) / dx**2
                            parabola_b = 0.5 * (M2 - M0) / dx
                            energy = parabola_a * offset**2 + parabola_b * offset + M1
                            energy_grad = 2.0 * parabola_a * offset + parabola_b
                        spatial_subset = spatial[:, source_mask]
                        weighted_spatial = spatial_subset @ a[s0:s1][source_mask]
                        weighted_spatial_grad = spatial_subset @ da[s0:s1][source_mask]
                        block_sum += energy * weighted_spatial
                        block_grad += energy_grad * weighted_spatial + energy * weighted_spatial_grad
                else:
                    spatial_sum += spatial @ a[s0:s1]
                    spatial_grad += spatial @ da[s0:s1]

            if self.signal_energy_declination_mode == "event":
                event_dec_indices = np.searchsorted(self.dec_edges, edec, side="right") - 1
                event_dec_indices = np.where(edec == self.dec_edges[-1], len(self.dec_edges) - 2, event_dec_indices)
                if np.any(event_dec_indices < 0) or np.any(event_dec_indices >= len(self.dec_edges) - 1):
                    raise ValueError("At least one event declination is outside the signal-energy table")
                energy = np.zeros(e1 - e0, dtype=np.float64)
                energy_grad = np.zeros(e1 - e0, dtype=np.float64)
                for dec_idx in np.unique(event_dec_indices):
                    event_mask = event_dec_indices == dec_idx
                    positions = energy_positions[event_mask] if energy_positions is not None else None
                    M0 = self._interpolate_energy(loge[event_mask], energy_grid[dec_idx, :, 0], (dec_idx, gamma_indices[0]), positions)
                    M1 = self._interpolate_energy(loge[event_mask], energy_grid[dec_idx, :, 1], (dec_idx, gamma_indices[1]), positions)
                    if self.signal_energy_gamma_interpolation == "linear_v1":
                        fraction = offset / dx
                        energy[event_mask] = (1.0-fraction)*M0 + fraction*M1
                        energy_grad[event_mask] = (M1-M0) / dx
                    else:
                        M2 = self._interpolate_energy(loge[event_mask], energy_grid[dec_idx, :, 2], (dec_idx, gamma_indices[2]), positions)
                        parabola_a = 0.5 * (M0 - 2.0 * M1 + M2) / dx**2
                        parabola_b = 0.5 * (M2 - M0) / dx
                        energy[event_mask] = parabola_a * offset**2 + parabola_b * offset + M1
                        energy_grad[event_mask] = 2.0 * parabola_a * offset + parabola_b
                block_sum = energy * spatial_sum
                block_grad = energy_grad * spatial_sum + energy * spatial_grad

            numerator[e0:e1] = block_sum
            numerator_grad[e0:e1] = block_grad

        ratio = numerator / (A * self.background)
        gradient = (numerator_grad * A - numerator * dA) / (A**2 * self.background)
        return ratio, gradient

    def _spatial_block(self, e0, s0, s1, era, sin_edec, cos_edec, sigma_sq):
        cache = self._spatial_cache
        namespace = self._spatial_cache_namespace
        block = (e0, s0)
        if cache is not None:
            cached = cache.get(namespace, block)
            if cached is not None:
                return cached
        started = perf_counter()
        sra = self.source_ras[s0:s1]
        sdec = self.source_decs[s0:s1]
        cospsi = sin_edec * np.sin(sdec) + cos_edec * np.cos(sdec) * np.cos(
            era[:, np.newaxis] - sra
        )
        psi = np.arccos(np.clip(cospsi, -1.0, 1.0))
        spatial = 0.5 / (np.pi * np.sin(psi)) * (psi / sigma_sq[:, np.newaxis]) * np.exp(
            -0.5 * psi**2 / sigma_sq[:, np.newaxis]
        )
        if cache is not None:
            cache.put(namespace, block, spatial, perf_counter() - started)
        return spatial

    def _interpolate_energy(self, loge, values, cache_key=None, positions=None):
        if cache_key is not None and positions is not None:
            result = self._energy_cache.interpolate(cache_key, self.log_energy_axis, values, positions)
            if result is not None:
                return result
        result = np.zeros(len(loge), dtype=np.float64)
        valid = (loge >= self.energy_min) & (loge < self.energy_max)
        result[valid] = np.interp(loge[valid], self.log_energy_axis, values)
        return result


class ChunkedSpatialOnlySourceWeightedPDFRatio(PDFRatio):
    r"""Evaluate the exact spatial-only stacking PDF in bounded chunks.

    For dataset ``k`` this evaluates

    .. math::

       S_i^k = \frac{\sum_j w_{j,\mathrm{model}}w_{j,\mathrm{acc}}^k
       S_{ij}^{k,\mathrm{spatial}}}
       {\sum_j w_{j,\mathrm{model}}w_{j,\mathrm{acc}}^k}

    and returns ``S_i^k / B_{i,spatial}^k``.  The acceptance Gamma is fixed,
    so this ratio has no fitted signal-shape parameter or Gamma gradient.
    """

    def __init__(
        self,
        dataset_idx,
        dataset_name,
        store,
        data_exp,
        source_ras,
        source_decs,
        src_detsigyield_weights_service,
        target_pairs=DEFAULT_TARGET_PAIRS,
        max_event_chunk=DEFAULT_MAX_EVENT_CHUNK,
        max_source_chunk=DEFAULT_MAX_SOURCE_CHUNK,
        **kwargs,
    ):
        super().__init__(sig_param_names=[], bkg_param_names=None, **kwargs)
        self.dataset_idx = int(dataset_idx)
        self.dataset_name = str(dataset_name)
        self.store = store
        self.source_ras = np.asarray(source_ras, dtype=np.float64)
        self.source_decs = np.asarray(source_decs, dtype=np.float64)
        self.weights_service = src_detsigyield_weights_service
        store.attach_background(data_exp)
        self.target_pairs = int(target_pairs)
        self.n_events = len(data_exp)
        self.event_chunk, self.source_chunk = choose_chunk_shape(
            len(data_exp),
            len(self.source_ras),
            target_pairs=target_pairs,
            max_event_chunk=max_event_chunk,
            max_source_chunk=max_source_chunk,
        )
        self._cache_key = None
        self._cache_ratio = None

    @property
    def chunk_provenance(self):
        return {
            "strategy": "exact_adaptive_event_source_double_batching",
            "n_events": self.n_events,
            "target_pairs": self.target_pairs,
            "event_chunk": self.event_chunk,
            "source_chunk": self.source_chunk,
            "maximum_working_pairs": self.event_chunk * self.source_chunk,
            "pair_dtype": "float64",
        }

    def initialize_for_new_trial(self, tdm, tl=None, **kwargs):
        self.event_ra = np.asarray(tdm["ra"], dtype=np.float64)
        self.event_dec = np.asarray(tdm["dec"], dtype=np.float64)
        self.event_sigma = np.asarray(tdm["ang_err"], dtype=np.float64)
        self.background = np.asarray(tdm[BACKGROUND_SPATIAL_FIELD], dtype=np.float64)
        if np.any(self.background <= 0.0):
            raise ValueError("The chunked DR2 spatial-only backend requires positive background spatial PDFs")
        self._cache_key = None

    def get_ratio(self, tdm, src_params_recarray, tl=None):
        weights, _ = self.weights_service.get_weights()
        a = np.asarray(weights[self.dataset_idx], dtype=np.float64)
        cache_key = (tdm.trial_data_state_id, a.tobytes())
        if cache_key != self._cache_key:
            self._cache_ratio = self._calculate(a)
            self._cache_key = cache_key
        return self._cache_ratio

    def get_gradient(self, tdm, src_params_recarray, fitparam_id, tl=None):
        return np.zeros(len(self.event_ra), dtype=np.float64)

    def _calculate(self, a):
        A = float(np.sum(a))
        if not np.isfinite(A) or A <= 0.0:
            raise ValueError("The sum of w_{j,model} w_{j,acc}^k must be positive")
        numerator = np.zeros(len(self.event_ra), dtype=np.float64)

        for e0 in range(0, len(self.event_ra), self.event_chunk):
            e1 = min(e0 + self.event_chunk, len(self.event_ra))
            era = self.event_ra[e0:e1]
            edec = self.event_dec[e0:e1]
            sigma_sq = self.event_sigma[e0:e1] ** 2
            sin_edec = np.sin(edec)[:, np.newaxis]
            cos_edec = np.cos(edec)[:, np.newaxis]
            block_sum = np.zeros(e1 - e0, dtype=np.float64)

            for s0 in range(0, len(a), self.source_chunk):
                s1 = min(s0 + self.source_chunk, len(a))
                sra = self.source_ras[s0:s1]
                sdec = self.source_decs[s0:s1]
                cospsi = sin_edec * np.sin(sdec) + cos_edec * np.cos(sdec) * np.cos(
                    era[:, np.newaxis] - sra
                )
                psi = np.arccos(np.clip(cospsi, -1.0, 1.0))
                spatial = 0.5 / (np.pi * np.sin(psi)) * (psi / sigma_sq[:, np.newaxis]) * np.exp(
                    -0.5 * psi**2 / sigma_sq[:, np.newaxis]
                )
                block_sum += spatial @ a[s0:s1]

            numerator[e0:e1] = block_sum

        return numerator / (A * self.background)
