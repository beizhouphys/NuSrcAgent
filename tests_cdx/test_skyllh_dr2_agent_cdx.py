from __future__ import annotations

import unittest
from pathlib import Path

from agent_core_cdx.analysis_agent_cdx import build_catalog_request, build_single_source_request
from agent_core_cdx.normalize_cdx import normalize_config
from agent_core_cdx.planner_cdx import plan_catalog_task
from agent_core_cdx.schemas_cdx import AnalysisConfig
from agent_core_cdx.validate_cdx import validate_config
from run_agent_wrap_cdx import default_gamma


class DR2AgentRoutingTests(unittest.TestCase):
    def test_schema_defaults_to_dr2_fitted_gamma(self):
        config = AnalysisConfig.from_dict(
            {"analysis": {"type": "single_source"}, "data": {}, "source": {"ra_deg": 10.0, "dec_deg": 20.0}}
        )
        self.assertEqual(config.data.sample, "icecube_public_ps_14yr_dr2")
        self.assertEqual(config.stacking.gamma_mode, "fitted")
        self.assertEqual(config.stacking.spectral_indices, [-3.0])
        self.assertEqual(config.analysis.likelihood_mode, "spatial_energy")

    def test_single_request_defaults_to_dr2_and_fitted_gamma(self):
        payload = build_single_source_request("A", 10.0, 20.0, -3.0, "data_output/runs_cdx")
        self.assertEqual(payload["data"]["sample"], "icecube_public_ps_14yr_dr2")
        self.assertEqual(payload["stacking"]["gamma_mode"], "fitted")
        self.assertEqual(payload["analysis"]["likelihood_mode"], "spatial_energy")

    def test_dr2_spatial_only_defaults_to_fixed_acceptance_gamma(self):
        gamma = default_gamma(None, "icecube_public_ps_14yr_dr2", "spatial_only", "fixed")
        payload = build_single_source_request(
            "A", 10.0, 20.0, gamma, "data_output/runs_cdx",
            "icecube_public_ps_14yr_dr2", "fixed", "spatial_only",
        )
        config = AnalysisConfig.from_dict(payload)
        normalized = normalize_config(config)
        self.assertEqual(gamma, -2.5)
        self.assertEqual(normalized.likelihood_mode, "spatial_only")
        self.assertEqual(normalized.gamma_mode, "fixed")
        self.assertEqual(normalized.spectral_indices, [-2.5])
        self.assertTrue(validate_config(config).ok)

    def test_dr2_spatial_only_rejects_fitted_gamma(self):
        payload = build_single_source_request(
            "A", 10.0, 20.0, -3.0, "data_output/runs_cdx",
            "icecube_public_ps_14yr_dr2", "fitted", "spatial_only",
        )
        validation = validate_config(AnalysisConfig.from_dict(payload))
        self.assertFalse(validation.ok)
        self.assertTrue(any("spatial-only" in error for error in validation.errors))

    def test_catalog_normalization_preserves_model_weights_and_gamma_mode(self):
        payload = build_catalog_request(
            None,
            [{"name": "A", "ra_deg": 10.0, "dec_deg": 20.0}, {"name": "B", "ra_deg": 30.0, "dec_deg": -5.0}],
            None,
            None,
            None,
            None,
            [1.0, 3.0],
            [-3.0],
            False,
            "data_output/runs_cdx",
        )
        normalized = normalize_config(AnalysisConfig.from_dict(payload))
        self.assertEqual(normalized.gamma_mode, "fitted")
        self.assertEqual([source.weight for source in normalized.sources], [0.25, 0.75])

    def test_legacy_sample_can_still_be_selected_explicitly(self):
        payload = build_single_source_request(
            "A", 10.0, 20.0, -2.53, "data_output/runs_cdx", "icecube_public_ps_10yr", "fixed"
        )
        self.assertEqual(payload["data"]["sample"], "icecube_public_ps_10yr")
        self.assertEqual(payload["stacking"]["gamma_mode"], "fixed")
        self.assertEqual(AnalysisConfig.from_dict(payload).analysis.likelihood_mode, "spatial_only")

    def test_dr2_catalog_over_thirty_sources_is_not_memory_blocked(self):
        sources = [
            {"name": f"S{idx}", "ra_deg": float(idx), "dec_deg": 0.0}
            for idx in range(31)
        ]
        task = plan_catalog_task(
            "31-source DR2 stack",
            Path("."),
            None,
            sources,
            None,
            None,
            None,
            -3.0,
            "uniform",
            None,
            None,
            None,
        )
        self.assertNotIn("at most 30 sources", " ".join(task["planning_errors"]))


if __name__ == "__main__":
    unittest.main()
