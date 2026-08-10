"""Physical DR2 signal-count to diffuse-intensity conversion.

This implements Eq. (10) of arXiv:2103.12813 directly with the public DR2
effective areas and measured livetimes.  It intentionally does not reuse the
10-year paper-calibrated event-count constants from the legacy code.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np


DR2_SUB_PATH = Path("data_input/IceCube_data_released/2026_icecube_14_year_track_data_IceTracks_DR2")
CONFIGURATIONS = ("IC40", "IC59", "IC79", "IC86")
SEASONS = {
    "IC40": ("IC40",),
    "IC59": ("IC59",),
    "IC79": ("IC79",),
    "IC86": ("IC86_I", "IC86_II", "IC86_III", "IC86_IV", "IC86_V", "IC86_VI", "IC86_VII", "IC86_VIII", "IC86_IX", "IC86_X", "IC86_XI"),
}


def powerlaw_bin_integral(emin, emax, gamma, e0=1e5):
    """Integral of ``(E/E0)^(-gamma) dE`` over each bin."""
    emin = np.asarray(emin, dtype=np.float64)
    emax = np.asarray(emax, dtype=np.float64)
    gamma = float(gamma)
    if np.isclose(gamma, 1.0):
        return float(e0) * np.log(emax / emin)
    return float(e0) ** gamma * (emax ** (1.0 - gamma) - emin ** (1.0 - gamma)) / (1.0 - gamma)


def configuration_livetimes_seconds(repo_root="."):
    base = Path(repo_root).resolve() / DR2_SUB_PATH / "uptime"
    result = {}
    for configuration, seasons in SEASONS.items():
        days = 0.0
        for season in seasons:
            table = np.loadtxt(base / f"{season}_exp.csv")
            days += float(np.sum(table[:, 1] - table[:, 0]))
        result[configuration] = days * 86400.0
    return result


def _effective_area(repo_root, configuration):
    path = Path(repo_root).resolve() / DR2_SUB_PATH / "irfs" / f"{configuration}_effectiveArea.csv"
    table = np.loadtxt(path)
    return {
        "emin": 10.0 ** table[:, 0],
        "emax": 10.0 ** table[:, 1],
        "dec_min": table[:, 2],
        "dec_max": table[:, 3],
        "area": table[:, 4],
    }


def diffuse_expected_events_per_phi0_mu(repo_root=".", gamma=2.53, e0=1e5):
    """Expected events for Phi0_mu=1 GeV^-1 cm^-2 s^-1 sr^-1."""
    livetimes = configuration_livetimes_seconds(repo_root)
    by_configuration = {}
    for configuration in CONFIGURATIONS:
        table = _effective_area(repo_root, configuration)
        energy_integral = powerlaw_bin_integral(table["emin"], table["emax"], gamma, e0=e0)
        delta_sin_dec = np.sin(np.deg2rad(table["dec_max"])) - np.sin(np.deg2rad(table["dec_min"]))
        count = 2.0 * np.pi * livetimes[configuration] * np.sum(
            table["area"] * energy_integral * delta_sin_dec, dtype=np.float64
        )
        by_configuration[configuration] = float(count)
    return float(sum(by_configuration.values())), by_configuration


def ns_to_allflavor_e2_intensity_100tev(ns, repo_root=".", gamma=2.53):
    """Convert expected events to all-flavor E^2 dF/dE at 100 TeV."""
    events_per_phi0_mu, _ = diffuse_expected_events_per_phi0_mu(repo_root, gamma=gamma, e0=1e5)
    phi0_mu = float(ns) / events_per_phi0_mu
    return 3.0 * phi0_mu * 1e10


def point_expected_yield_per_phi0(repo_root, dec_deg, gamma=2.53, e0=1e3):
    """Point-source yield for a unit muon-neutrino normalization at E0."""
    livetimes = configuration_livetimes_seconds(repo_root)
    result = {}
    for configuration in CONFIGURATIONS:
        table = _effective_area(repo_root, configuration)
        mask = (float(dec_deg) >= table["dec_min"]) & (float(dec_deg) < table["dec_max"])
        if float(dec_deg) == 90.0:
            mask = table["dec_max"] == 90.0
        energy_integral = powerlaw_bin_integral(table["emin"][mask], table["emax"][mask], gamma, e0=e0)
        result[configuration] = float(livetimes[configuration] * np.sum(table["area"][mask] * energy_integral))
    return result

