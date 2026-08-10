from __future__ import annotations

import math
import tempfile
import unittest
from pathlib import Path

import numpy as np

from analysis_backend_cdx.dr2_flux_conversion_cdx import (
    diffuse_expected_events_per_phi0_mu,
    ns_to_allflavor_e2_intensity_100tev,
    powerlaw_bin_integral,
)
from analysis_backend_cdx.skyllh_dr2_catalog_scan_cdx import fit_ns
from tools_cdx.build_radio_bright_agn_catalog_cdx import build_catalog


REPO_ROOT = Path(__file__).resolve().parents[1]


class DR2CatalogScanTests(unittest.TestCase):
    def test_rfc_selection_reproduces_3386_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "catalog.csv"
            path, rows = build_catalog(REPO_ROOT, str(output))
            self.assertEqual(path, output)
            self.assertEqual(len(rows), 3386)
            self.assertTrue(all(float(row["xband_flux_jy"]) >= 0.15 for row in rows))
            self.assertTrue(all(abs(float(row["dec_deg"])) < 87.0 for row in rows))

    def test_concave_ns_fit_finds_known_maximum(self):
        ratios = [np.asarray([8.0, 0.4, 0.7, 1.1]), np.asarray([3.0, 0.2, 1.4])]
        fractions = np.asarray([0.35, 0.65])
        ns, ts, _ = fit_ns(ratios, fractions, ns_min=0.0, ns_max=10.0)
        self.assertGreaterEqual(ns, 0.0)
        self.assertGreaterEqual(ts, 0.0)
        epsilon = 1e-5
        from analysis_backend_cdx.skyllh_dr2_catalog_scan_cdx import _logl

        counts = [len(value) for value in ratios]
        self.assertGreaterEqual(_logl(ns, ratios, fractions, counts), _logl(max(0.0, ns - epsilon), ratios, fractions, counts))
        self.assertGreaterEqual(_logl(ns, ratios, fractions, counts), _logl(min(10.0, ns + epsilon), ratios, fractions, counts))

    def test_zero_compressed_fit_matches_dense_fit(self):
        ratios = [np.asarray([0.0, 0.0, 8.0, 0.4]), np.asarray([0.0, 3.0, 0.2])]
        fractions = np.asarray([0.35, 0.65])
        dense = fit_ns(ratios, fractions, ns_min=-1.0, ns_max=10.0)
        compact = [(ratio[ratio != 0.0], int(np.count_nonzero(ratio == 0.0)), len(ratio)) for ratio in ratios]
        sparse = fit_ns(compact, fractions, ns_min=-1.0, ns_max=10.0)
        np.testing.assert_allclose(sparse, dense, rtol=1e-11, atol=1e-11)

    def test_powerlaw_integral_gamma_two(self):
        value = powerlaw_bin_integral(np.asarray([1e2]), np.asarray([1e3]), 2.0, e0=1e5)[0]
        self.assertAlmostEqual(value, 1e10 * (1.0 / 1e2 - 1.0 / 1e3))

    def test_dr2_diffuse_conversion_is_finite_and_linear(self):
        expected, parts = diffuse_expected_events_per_phi0_mu(REPO_ROOT, gamma=2.53)
        self.assertTrue(math.isfinite(expected) and expected > 0.0)
        self.assertEqual(set(parts), {"IC40", "IC59", "IC79", "IC86"})
        one = ns_to_allflavor_e2_intensity_100tev(100.0, REPO_ROOT, gamma=2.53)
        two = ns_to_allflavor_e2_intensity_100tev(200.0, REPO_ROOT, gamma=2.53)
        self.assertAlmostEqual(two / one, 2.0)


if __name__ == "__main__":
    unittest.main()
