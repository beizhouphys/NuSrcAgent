"""Physical public-data signal-count to diffuse-intensity conversion.

This implements Eq. (10) of arXiv:2103.12813 directly with the public DR1 or
DR2 effective areas and measured livetimes.  It intentionally does not apply
the legacy observed/atmospheric-event normalization.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np


DR2_SUB_PATH = Path("data_input/IceCube_data_released/2026_icecube_14_year_track_data_IceTracks_DR2")
DR1_SUB_PATH = Path("data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source")
CONFIGURATIONS = ("IC40", "IC59", "IC79", "IC86")
SEASONS = {
    "IC40": ("IC40",),
    "IC59": ("IC59",),
    "IC79": ("IC79",),
    "IC86": ("IC86_I", "IC86_II", "IC86_III", "IC86_IV", "IC86_V", "IC86_VI", "IC86_VII", "IC86_VIII", "IC86_IX", "IC86_X", "IC86_XI"),
}
DR2_SEASON_SELECTIONS = {
    "dr2_full14": SEASONS,
    "dr2_first10": {
        "IC40": ("IC40",),
        "IC59": ("IC59",),
        "IC79": ("IC79",),
        "IC86": ("IC86_I", "IC86_II", "IC86_III", "IC86_IV", "IC86_V", "IC86_VI", "IC86_VII"),
    },
    "dr2_extra4": {
        "IC86": ("IC86_VIII", "IC86_IX", "IC86_X", "IC86_XI"),
    },
}
DR1_UPTIME_FILES = {
    "IC40": "IC40_exp.csv",
    "IC59": "IC59_exp.csv",
    "IC79": "IC79_exp.csv",
    "IC86_I": "IC86_I_exp.csv",
    "IC86_II": "IC86_II2VII_exp_BZ.csv",
}


def powerlaw_bin_integral(emin, emax, gamma, e0=1e5):
    """Integral of ``(E/E0)^(-gamma) dE`` over each bin."""
    emin = np.asarray(emin, dtype=np.float64)
    emax = np.asarray(emax, dtype=np.float64)
    gamma = float(gamma)
    if np.isclose(gamma, 1.0):
        return float(e0) * np.log(emax / emin)
    return float(e0) ** gamma * (emax ** (1.0 - gamma) - emin ** (1.0 - gamma)) / (1.0 - gamma)


def configuration_livetimes_seconds(repo_root=".", selection="dr2_full14"):
    if str(selection) == "dr1_legacy10":
        base = Path(repo_root).resolve() / DR1_SUB_PATH / "uptime"
        result = {}
        for configuration, filename in DR1_UPTIME_FILES.items():
            table = np.loadtxt(base / filename)
            result[configuration] = float(np.sum(table[:, 1] - table[:, 0])) * 86400.0
        return result
    base = Path(repo_root).resolve() / DR2_SUB_PATH / "uptime"
    try:
        selected_seasons = DR2_SEASON_SELECTIONS[str(selection)]
    except KeyError as error:
        raise ValueError(f"Unknown DR2 season selection {selection!r}") from error
    result = {}
    for configuration, seasons in selected_seasons.items():
        days = 0.0
        for season in seasons:
            table = np.loadtxt(base / f"{season}_exp.csv")
            days += float(np.sum(table[:, 1] - table[:, 0]))
        result[configuration] = days * 86400.0
    return result


def _effective_area(repo_root, configuration, selection="dr2_full14"):
    sub_path = DR1_SUB_PATH if str(selection) == "dr1_legacy10" else DR2_SUB_PATH
    path = Path(repo_root).resolve() / sub_path / "irfs" / f"{configuration}_effectiveArea.csv"
    table = np.loadtxt(path)
    return {
        "emin": 10.0 ** table[:, 0],
        "emax": 10.0 ** table[:, 1],
        "dec_min": table[:, 2],
        "dec_max": table[:, 3],
        "area": table[:, 4],
    }


def diffuse_expected_events_per_phi0_mu(
    repo_root=".", gamma=2.53, e0=1e5, selection="dr2_full14",
    event_abs_dec_max_deg=None,
):
    """Expected events for Phi0_mu=1 GeV^-1 cm^-2 s^-1 sr^-1."""
    if event_abs_dec_max_deg is not None and not 0.0 < float(event_abs_dec_max_deg) <= 90.0:
        raise ValueError("event_abs_dec_max_deg must be in (0, 90] deg or None")
    livetimes = configuration_livetimes_seconds(repo_root, selection=selection)
    by_configuration = {}
    for configuration in livetimes:
        table = _effective_area(repo_root, configuration, selection=selection)
        energy_integral = powerlaw_bin_integral(table["emin"], table["emax"], gamma, e0=e0)
        dec_min = np.asarray(table["dec_min"], dtype=np.float64)
        dec_max = np.asarray(table["dec_max"], dtype=np.float64)
        if event_abs_dec_max_deg is not None:
            cut = float(event_abs_dec_max_deg)
            dec_min = np.maximum(dec_min, -cut)
            dec_max = np.minimum(dec_max, cut)
        delta_sin_dec = np.where(
            dec_max > dec_min,
            np.sin(np.deg2rad(dec_max)) - np.sin(np.deg2rad(dec_min)),
            0.0,
        )
        count = 2.0 * np.pi * livetimes[configuration] * np.sum(
            table["area"] * energy_integral * delta_sin_dec, dtype=np.float64
        )
        by_configuration[configuration] = float(count)
    return float(sum(by_configuration.values())), by_configuration


def ns_to_allflavor_e2_intensity_100tev(ns, repo_root=".", gamma=2.53, selection="dr2_full14"):
    """Convert expected events to all-flavor E^2 dF/dE at 100 TeV."""
    events_per_phi0_mu, _ = diffuse_expected_events_per_phi0_mu(
        repo_root, gamma=gamma, e0=1e5, selection=selection
    )
    phi0_mu = float(ns) / events_per_phi0_mu
    return 3.0 * phi0_mu * 1e10


def point_expected_yield_per_phi0(repo_root, dec_deg, gamma=2.53, e0=1e3, selection="dr2_full14"):
    """Point-source yield for a unit muon-neutrino normalization at E0."""
    livetimes = configuration_livetimes_seconds(repo_root, selection=selection)
    result = {}
    for configuration in livetimes:
        table = _effective_area(repo_root, configuration, selection=selection)
        mask = (float(dec_deg) >= table["dec_min"]) & (float(dec_deg) < table["dec_max"])
        if float(dec_deg) == 90.0:
            mask = table["dec_max"] == 90.0
        energy_integral = powerlaw_bin_integral(table["emin"][mask], table["emax"][mask], gamma, e0=e0)
        result[configuration] = float(livetimes[configuration] * np.sum(table["area"][mask] * energy_integral))
    return result
