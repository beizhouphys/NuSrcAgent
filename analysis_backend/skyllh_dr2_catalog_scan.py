"""Input-ordered individual-source fits through the supported DR2 backend."""
from __future__ import annotations

import os
from pathlib import Path
from time import perf_counter

import numpy as np
from analysis_backend.skyllh_dr2_stacking import run_dr2_stacking


_WORKER_RUNTIME_CACHE = {}


def _fit_source(job):
    started = perf_counter()
    number, spec, fit_options = job
    single = dict(spec, w_model=1.0)
    use_cache = (fit_options.get("data_selection", "full14") == "full14"
                 and fit_options.get("source_ra_scramble_seed") is None
                 and fit_options.get("event_ra_scramble_seed") is None)
    cache = _WORKER_RUNTIME_CACHE if use_cache else None
    fit = run_dr2_stacking([single], runtime_cache=cache, **fit_options)
    cache_stats = {} if cache is None or "pdf_store" not in cache else {"dataset_loads": cache["dataset_loads"],
        "dataset_cache_hits": cache["dataset_cache_hits"], **cache["pdf_store"].cache_stats}
    return {"source_number": number, "source_name": spec["name"],
            "ra_deg": float(np.rad2deg(spec["ra_rad"])),
            "dec_deg": float(np.rad2deg(spec["dec_rad"])), "fit": fit,
            "execution": {"pid": os.getpid(), "wall_seconds": perf_counter() - started,
                "worker_cache_enabled": use_cache, "cache_stats": cache_stats}}


def run_individual_source_scan(source_specs, **fit_options):
    """Input-ordered individual fits with a fresh cache for each scan."""
    _WORKER_RUNTIME_CACHE.clear()
    try:
        return [_fit_source((number, spec, fit_options))
                for number, spec in enumerate(source_specs, start=1)]
    finally:
        _WORKER_RUNTIME_CACHE.clear()
