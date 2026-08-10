from __future__ import annotations

import importlib.util
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HAS_SKYLLH = importlib.util.find_spec("skyllh") is not None
HAS_DR2_TABLES = (ROOT / "data_output/bkgd_pdfs_cdx/14yr_dr2_cdx/bkgd_pdf_IC40_exp_DR2_cdx.txt").exists()


@unittest.skipUnless(HAS_SKYLLH and HAS_DR2_TABLES, "requires the pinned SkyLLH v26 environment and DR2 tables")
class DR2ScientificRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from analysis_backend_cdx.skyllh_dr2_stacking_cdx import run_dr2_stacking

        cls.run_analysis = staticmethod(run_dr2_stacking)
        cls.sources = [
            {"name": "NGC 1068", "ra_rad": math.radians(40.67), "dec_rad": math.radians(-0.01), "w_model": 1.0},
            {"name": "offset", "ra_rad": math.radians(140.0), "dec_rad": math.radians(20.0), "w_model": 1.0},
        ]

    def test_fixed_gamma_two_source_regression(self):
        result = self.run_analysis(self.sources, repo_root=ROOT, gamma_mode="fixed", gamma=3.0)
        self.assertAlmostEqual(result["TS"], 16.969557680506, places=7)
        self.assertAlmostEqual(result["ns"], 82.32263399641919, places=6)
        self.assertEqual(result["gamma"], 3.0)
        self.assertEqual(result["event_selection"], "all_events")
        self.assertFalse(result["working_set"]["cartesian_source_event_arrays_materialized"])
        for chunk in result["working_set"]["datasets"].values():
            self.assertLessEqual(chunk["maximum_working_pairs"], chunk["target_pairs"])
        self.assertAlmostEqual(sum(result["f_k"].values()), 1.0, places=12)
        self.assertEqual(result["weight_notation"]["source_acceptance"], "w_{j,acc}^k")

    def test_fitted_gamma_is_default_capability(self):
        result = self.run_analysis(self.sources, repo_root=ROOT, gamma_mode="fitted", gamma=3.0)
        self.assertAlmostEqual(result["TS"], 17.698142347199067, places=6)
        self.assertAlmostEqual(result["gamma"], 3.215306281826972, places=5)
        self.assertEqual(result["n_sources"], 2)
        self.assertEqual(result["fit_bounds"]["gamma_skyllh"], [1.0, 6.0])
        self.assertEqual(result["fit_bounds"]["gamma_legacy"], [-6.0, -1.0])
        self.assertEqual(result["fit_bounds"]["ns"], [0.0, 10000.0])
        self.assertEqual(result["fit_seeds"], {"gamma_skyllh": 3.0, "ns": 10.0})

    def test_spatial_only_two_source_regression(self):
        result = self.run_analysis(
            self.sources, repo_root=ROOT, likelihood_mode="spatial_only", gamma_mode="fixed", gamma=2.5
        )
        self.assertAlmostEqual(result["TS"], 16.909762643382145, places=7)
        self.assertAlmostEqual(result["ns"], 84.12406398644453, places=6)
        self.assertEqual(result["energy_pdf"], "not_used")
        self.assertEqual(result["acceptance_gamma_legacy"], -2.5)
        self.assertEqual(result["gamma_role"], "acceptance_only")
        self.assertIsNone(result["fit_bounds"]["gamma_skyllh"])
        self.assertIsNone(result["fit_seeds"]["gamma_skyllh"])
        self.assertFalse(result["working_set"]["signal_energy_tables_loaded"])
        self.assertEqual(list(result["pdf_provenance"]), ["background_spatial"])

    def test_source_order_invariance(self):
        forward = self.run_analysis(self.sources, repo_root=ROOT, gamma_mode="fixed", gamma=3.0)
        reverse = self.run_analysis(list(reversed(self.sources)), repo_root=ROOT, gamma_mode="fixed", gamma=3.0)
        self.assertAlmostEqual(forward["TS"], reverse["TS"], places=10)
        self.assertAlmostEqual(forward["ns"], reverse["ns"], places=9)

    def test_adaptive_chunk_shape(self):
        from analysis_backend_cdx.skyllh_dr2_chunked_cdx import choose_chunk_shape

        self.assertEqual(choose_chunk_shape(1_643_355, 2), (2048, 2))
        self.assertEqual(choose_chunk_shape(1_643_355, 500), (2048, 500))
        self.assertEqual(choose_chunk_shape(1_643_355, 3000), (512, 2048))


if __name__ == "__main__":
    unittest.main()
