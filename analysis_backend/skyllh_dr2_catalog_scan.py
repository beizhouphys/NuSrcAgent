"""Input-ordered individual-source fits through the supported DR2 backend."""
from __future__ import annotations

import numpy as np
from analysis_backend.skyllh_dr2_stacking import run_dr2_stacking


def run_individual_source_scan(source_specs, **fit_options):
    """Fit each source with the supported single-source LLH, in input order."""
    results = []
    for number, spec in enumerate(source_specs, start=1):
        single = dict(spec, w_model=1.0)
        fit = run_dr2_stacking([single], **fit_options)
        results.append({
            "source_number": number, "source_name": spec["name"],
            "ra_deg": float(np.rad2deg(spec["ra_rad"])),
            "dec_deg": float(np.rad2deg(spec["dec_rad"])), "fit": fit,
        })
    return results
