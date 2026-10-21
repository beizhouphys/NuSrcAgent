"""Execution CPU budgets, separate from immutable scientific requests."""
from __future__ import annotations

from contextlib import contextmanager
import os


THREAD_VARIABLES = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                    "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS")


def positive_cpu_count(value):
    count = int(value)
    if count < 1:
        raise ValueError("CPU budget must be a positive integer")
    return count


def configure_threads(cpus):
    """Call before numerical imports in the CLI; children inherit these caps."""
    count = positive_cpu_count(cpus)
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


def execution_metadata(cpus, normalized):
    count = positive_cpu_count(cpus)
    scan = (normalized.sample == "icecube_public_ps_14yr_dr2"
            and normalized.analysis_type == "catalog_stacking"
            and normalized.catalog_operation in {"scan", "scan_and_stack"})
    return dict(pid=os.getpid(), cpu_budget=count, scan_workers=count if scan else 0,
                numerical_threads_per_scan_worker=1,
                thread_environment={name: os.environ.get(name) for name in THREAD_VARIABLES})
