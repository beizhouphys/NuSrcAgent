"""Shared declination bounds and source-centered event windows."""
import numpy as np


def _event_declination_bounds(event_abs_dec_max_deg=None, event_dec_min_deg=None, event_dec_max_deg=None):
    if event_abs_dec_max_deg is not None and (event_dec_min_deg is not None or event_dec_max_deg is not None):
        raise ValueError("Use either event_abs_dec_max_deg or event_dec_min_deg/event_dec_max_deg, not both")
    if event_abs_dec_max_deg is not None:
        cut = float(event_abs_dec_max_deg)
        if not 0.0 < cut <= 90.0:
            raise ValueError("event_abs_dec_max_deg must be in (0, 90] deg or None")
        return -cut, cut
    lower = -90.0 if event_dec_min_deg is None else float(event_dec_min_deg)
    upper = 90.0 if event_dec_max_deg is None else float(event_dec_max_deg)
    if not np.isfinite(lower) or not np.isfinite(upper) or not -90.0 <= lower < upper <= 90.0:
        raise ValueError("Event declination bounds must be finite and satisfy -90 <= min < max <= 90 deg")
    return lower, upper


def source_declination_window(event_decs_by_dataset, source_dec_deg, minimum_half_width_deg=20.0):
    """Smallest symmetric Dec interval containing >=20% of each dataset."""
    minimum = float(minimum_half_width_deg)
    if not np.isfinite(minimum) or not 20.0 <= minimum <= 180.0:
        raise ValueError("source_dec_window_deg must be finite and in [20, 180]")
    center = float(source_dec_deg)
    if not np.isfinite(center) or not -90.0 <= center <= 90.0:
        raise ValueError("Source declination must be in [-90, 90] deg")
    half_width = minimum
    for values in event_decs_by_dataset.values():
        values = np.asarray(values, dtype=np.float64)
        if not len(values) or not np.all(np.isfinite(values)):
            raise ValueError("Each dataset must contain finite event declinations")
        index = int(np.ceil(0.2 * len(values))) - 1
        distances = np.abs(values - center)
        half_width = max(half_width, float(np.partition(distances, index)[index]))
    # Outward rounding keeps threshold events on floating-point boundaries.
    half_width = float(np.nextafter(half_width, np.inf))
    lower = max(-90.0, float(np.nextafter(center - half_width, -np.inf)))
    upper = min(90.0, float(np.nextafter(center + half_width, np.inf)))
    return lower, upper, half_width
