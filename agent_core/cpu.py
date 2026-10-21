"""Execution CPU budgets, separate from immutable scientific requests."""
from __future__ import annotations

from contextlib import contextmanager
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import os


THREAD_VARIABLES = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                    "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS")


def positive_worker_count(value):
    count = int(value)
    if count < 1:
        raise ValueError("CPU budget must be a positive integer")
    return count


def configure_threads(workers):
    """Call before numerical imports in the CLI; children inherit these caps."""
    count = positive_worker_count(workers)
    for name in THREAD_VARIABLES:
        os.environ[name] = str(count)
    return count


@contextmanager
def single_thread_workers():
    previous = {name: os.environ.get(name) for name in THREAD_VARIABLES}
    configure_threads(1)
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def ordered_worker_map(function, jobs, workers=1):
    """Independent jobs in input order; only the parent writes checkpoints."""
    workers = positive_worker_count(workers)
    if workers == 1:
        yield from map(function, jobs)
        return
    with single_thread_workers():
        with ProcessPoolExecutor(max_workers=workers,
                                 mp_context=multiprocessing.get_context("spawn")) as pool:
            yield from pool.map(function, jobs, chunksize=1)


def execution_metadata(workers, normalized):
    count = positive_worker_count(workers)
    scan = (normalized.analysis_type == "catalog_stacking"
            and (normalized.sample == "icecube_public_ps_10yr"
                 or normalized.catalog_operation in {"scan", "scan_and_stack"}))
    return dict(pid=os.getpid(), cpu_budget=count, worker_budget=count,
                scan_workers=count if scan else 0,
                numerical_threads_per_scan_worker=1,
                thread_environment={name: os.environ.get(name) for name in THREAD_VARIABLES})
