"""Input-ordered individual-source fits through the supported DR2 backend."""
from __future__ import annotations

from agent_core.progress import track_progress
from agent_core.cpu import THREAD_VARIABLES, positive_worker_count, ordered_worker_map

import os
from pathlib import Path
from time import perf_counter

import numpy as np
from analysis_backend.skyllh_dr2_stacking import run_dr2_stacking, run_dr2_single_source


_WORKER_RUNTIME_CACHE = {}


def _fit_source(job):
    started = perf_counter()
    number, spec, fit_options = job
    single = dict(spec, w_model=1.0)
    use_cache = (fit_options.get("data_selection", "full14") == "full14"
                 and fit_options.get("source_ra_scramble_seed") is None
                 and fit_options.get("event_ra_scramble_seed") is None)
    cache = _WORKER_RUNTIME_CACHE if use_cache else None
    fit = run_dr2_single_source([single], runtime_cache=cache, **fit_options)
    cache_stats = {} if cache is None or "pdf_store" not in cache else {"dataset_loads": cache["dataset_loads"],
        "dataset_cache_hits": cache["dataset_cache_hits"], **cache["pdf_store"].cache_stats}
    return {"source_number": number, "source_name": spec["name"],
            "ra_deg": float(np.rad2deg(spec["ra_rad"])),
            "dec_deg": float(np.rad2deg(spec["dec_rad"])), "fit": fit,
            "execution": {"pid": os.getpid(), "wall_seconds": perf_counter() - started,
                "worker_cache_enabled": use_cache, "cache_stats": cache_stats,
                "numerical_thread_limits": {name: os.environ.get(name) for name in THREAD_VARIABLES}}}


def run_individual_source_scan(source_specs, workers=1, **fit_options):
    """Keep the original source fits, seeds, ordering and per-process caches."""
    workers = positive_worker_count(workers)
    _WORKER_RUNTIME_CACHE.clear()
    jobs = [(number, spec, fit_options) for number, spec in enumerate(source_specs, start=1)]
    try:
        records = ordered_worker_map(_fit_source, jobs, workers)
        # Progress uses current scheduler wall time, not summed worker time.
        return list(track_progress(records, "catalog source fits", total=len(jobs)))
    finally:
        _WORKER_RUNTIME_CACHE.clear()
