"""Owner-approved local half-chi-square p-value/significance estimates."""
from __future__ import annotations

import math
from scipy.special import ndtri_exp


def local_p_value_estimate(ts: float, gamma_mode: str) -> dict[str, object]:
    """Use dof=2 for fitted Gamma and dof=1 for fixed Gamma; no calibration implied.

    Retain the reporting convention p=0.5, Z=0 at TS=0. Negative fit statistics
    are still rejected by scientific review. Log-probability inversion avoids
    losing a finite significance when the stored float p-value underflows.
    """
    if gamma_mode not in {"fitted", "fixed"}:
        raise ValueError("Gamma mode must be fitted or fixed for a local estimate")
    value = max(float(ts), 0.0)
    dof = 2 if gamma_mode == "fitted" else 1
    if dof == 2:
        log_p = -math.log(2.0) - value / 2.0
        p_value = math.exp(log_p)
        significance = float(-ndtri_exp(log_p))
    else:
        p_value = math.erfc(math.sqrt(value / 2.0)) / 2.0
        significance = math.sqrt(value)
    return {"pre_trial_p": p_value, "pre_trial_significance": significance,
            "p_value_method": f"analytic_half_chi_square_df{dof}_estimate",
            "p_value_dof": dof, "p_value_is_estimate": True,
            "significance_convention": "one_sided_gaussian_sigma"}
