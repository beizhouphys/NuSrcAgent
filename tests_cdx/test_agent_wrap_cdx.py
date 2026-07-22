from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from agent_core_cdx.agent_orchestrator_cdx import classify_error, evaluate_completion, execute_task, resume_interrupted_task
from agent_core_cdx.planner_cdx import plan_catalog_task, plan_single_task, revalidate_task_plan
from agent_core_cdx.task_state_cdx import confirm_parameters, load_task, save_task
from run_agent_wrap_cdx import build_parser


class AgentPlanningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_single_source_selects_single_workflow(self):
        task = plan_single_task("analyze this source", "A", 10.0, 20.0, -2.5)
        self.assertEqual(task["workflow"], "single_source")
        self.assertEqual(task["status"], "READY")
        self.assertIn("run_agent_wrap_cdx.py run", task["planned_tools"])

    def test_single_source_missing_gamma_waits(self):
        task = plan_single_task("分析这个源", "A", 10.0, 20.0, None)
        self.assertEqual(task["status"], "AWAITING_CONFIRMATION")
        self.assertEqual(task["missing_parameters"], ["gamma"])

    def test_multiple_sources_select_scan_and_stacking(self):
        sources = [{"name": "A", "ra_deg": 10.0, "dec_deg": 20.0}, {"name": "B", "ra_deg": 30.0, "dec_deg": -5.0}]
        task = plan_catalog_task("分析这两个源", self.root, None, sources, None, None, None, None, None, None, None, None)
        self.assertEqual(task["workflow"], "catalog_scan_and_stacking")
        self.assertEqual(set(task["missing_parameters"]), {"gamma", "weight_mode"})

    def test_one_inline_source_uses_single_workflow(self):
        source = [{"name": "A", "ra_deg": 10.0, "dec_deg": 20.0}]
        task = plan_catalog_task("one", self.root, None, source, None, None, None, -2.5, None, None, None, None)
        self.assertEqual(task["workflow"], "single_source")
        self.assertEqual(task["status"], "READY")

    def test_column_weight_requires_meaning(self):
        path = self.write_catalog("name,ra,dec,flux\nA,10,20,1\nB,30,-5,2\n")
        task = plan_catalog_task("use flux", self.root, str(path), None, "name", "ra", "dec", -2.5, "column", "flux", None, None)
        self.assertIn("weight_meaning", task["missing_parameters"])

    def test_uniform_confirmation_makes_task_ready(self):
        sources = [{"name": "A", "ra_deg": 10.0, "dec_deg": 20.0}, {"name": "B", "ra_deg": 30.0, "dec_deg": -5.0}]
        task = plan_catalog_task("分析", self.root, None, sources, None, None, None, None, None, None, None, None)
        confirm_parameters(task, {"gamma": -2.53, "weight_mode": "uniform"})
        revalidate_task_plan(task, self.root)
        self.assertEqual(task["status"], "READY")

    def test_positive_gamma_is_blocked(self):
        task = plan_single_task("bad gamma", "A", 10.0, 20.0, 2.5)
        self.assertIn("gamma must use the negative power-law convention", task["planning_errors"])
        self.assertEqual(task["status"], "AWAITING_CONFIRMATION")
        self.assertIn("Provide a finite negative gamma value.", task["questions"])

    def test_nonfinite_gamma_is_blocked(self):
        task = plan_single_task("bad gamma", "A", 10.0, 20.0, float("nan"))
        self.assertEqual(task["status"], "AWAITING_CONFIRMATION")

    def test_invalid_inline_coordinate_is_blocked(self):
        task = plan_single_task("bad coordinate", "A", 361.0, 20.0, -2.5)
        self.assertEqual(task["status"], "AWAITING_CONFIRMATION")
        self.assertTrue(task["planning_errors"])

    def test_manual_weight_count_is_checked(self):
        sources = [{"name": "A", "ra_deg": 10.0, "dec_deg": 20.0}, {"name": "B", "ra_deg": 30.0, "dec_deg": -5.0}]
        task = plan_catalog_task("manual", self.root, None, sources, None, None, None, -2.5, "manual", None, None, [1.0])
        self.assertTrue(task["planning_errors"])

    def test_nonfinite_manual_weight_is_blocked(self):
        sources = [{"name": "A", "ra_deg": 10.0, "dec_deg": 20.0}, {"name": "B", "ra_deg": 30.0, "dec_deg": -5.0}]
        task = plan_catalog_task("manual", self.root, None, sources, None, None, None, -2.5, "manual", None, None, [1.0, float("nan")])
        self.assertEqual(task["status"], "AWAITING_CONFIRMATION")

    def test_invalid_catalog_coordinates_are_blocked(self):
        path = self.write_catalog("name,ra,dec\nA,400,20\nB,30,-5\n")
        task = plan_catalog_task("bad catalog", self.root, str(path), None, "name", "ra", "dec", -2.5, "uniform", None, None, None)
        self.assertEqual(task["status"], "AWAITING_CONFIRMATION")
        self.assertTrue(task["planning_errors"])

    def test_task_round_trip(self):
        task = plan_single_task("persist", "A", 10.0, 20.0, -2.5)
        path = save_task(task, self.root)
        loaded, loaded_path = load_task(str(path), self.root)
        self.assertEqual(loaded["task_id"], task["task_id"])
        self.assertEqual(loaded_path, path)

    def test_terminal_task_cannot_be_mutated(self):
        task = plan_single_task("done", "A", 10.0, 20.0, -2.5)
        task["status"] = "COMPLETED"
        with self.assertRaises(ValueError):
            confirm_parameters(task, {"gamma": -3.0})

    def write_catalog(self, content):
        path = self.root / "catalog_cdx.csv"
        path.write_text(content, encoding="utf-8")
        return path


class AgentCompletionTests(unittest.TestCase):
    def ready_task(self):
        return plan_single_task("run", "A", 10.0, 20.0, -2.5)

    def test_pass_review_completes(self):
        task = self.ready_task()
        task["artifacts"] = {"run_directory": "/tmp/run"}
        self.assertEqual(evaluate_completion(task, {"status": "pass", "checks": []})["status"], "COMPLETED")

    def test_warning_review_preserves_warning(self):
        task = self.ready_task()
        task["artifacts"] = {"run_directory": "/tmp/run"}
        self.assertEqual(evaluate_completion(task, {"status": "warning", "checks": []})["status"], "COMPLETED_WITH_WARNINGS")

    def test_fail_review_cannot_complete(self):
        task = self.ready_task()
        task["artifacts"] = {"run_directory": "/tmp/run"}
        result = evaluate_completion(task, {"status": "fail", "checks": [{"status": "fail", "auto_fix_allowed": False}]})
        self.assertEqual(result["status"], "FAILED")
        self.assertFalse(result["auto_fix_allowed"])

    def test_all_output_failures_allow_retry(self):
        task = self.ready_task()
        task["artifacts"] = {"run_directory": "/tmp/run"}
        result = evaluate_completion(task, {"status": "fail", "checks": [{"status": "fail", "auto_fix_allowed": True}]})
        self.assertTrue(result["auto_fix_allowed"])

    def test_error_classification(self):
        self.assertEqual(classify_error(ModuleNotFoundError("reportlab")), "DEPENDENCY_ERROR")
        self.assertEqual(classify_error(ValueError("bad catalog")), "DATA_VALIDATION_ERROR")

    def test_resume_requires_interrupted_state(self):
        task = self.ready_task()
        with self.assertRaises(ValueError):
            resume_interrupted_task(task)
        task["status"] = "RUNNING"
        self.assertEqual(resume_interrupted_task(task)["status"], "READY")

    def test_safe_error_retries_identical_request_once(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            task = self.ready_task()
            task_path = save_task(task, root)

            class FakeAgent:
                calls = 0

                def __init__(self, repo_root):
                    pass

                def prepare_request(self, payload, request_path):
                    Path(request_path).write_text("request\n", encoding="utf-8")

                def run(self, request_path, backend="likelihood", prepare_only=False):
                    FakeAgent.calls += 1
                    if FakeAgent.calls == 1:
                        raise ModuleNotFoundError("reportlab")
                    run_dir = root / "data_output" / "runs_cdx" / "run_fake_cdx"
                    run_dir.mkdir(parents=True)
                    return SimpleNamespace(run_dir=run_dir, review={"status": "pass", "checks": []})

            with patch("agent_core_cdx.agent_orchestrator_cdx.AnalysisAgent", FakeAgent):
                result = execute_task(task, task_path, root, backend="mock", max_safe_retries=1)
            self.assertEqual(result["status"], "COMPLETED")
            self.assertEqual(len(result["attempts"]), 2)
            self.assertEqual(result["attempts"][0]["request_sha256"], result["attempts"][1]["request_sha256"])
            self.assertFalse(result["attempts"][0]["recovery"]["scientific_parameters_changed"])


class AgentCliTests(unittest.TestCase):
    def test_catalog_inspection_uses_public_entry_point(self):
        args = build_parser().parse_args(["inspect-catalog", "--catalog", "catalog.csv"])
        self.assertEqual(args.command, "inspect-catalog")

    def test_run_review_uses_public_entry_point(self):
        args = build_parser().parse_args(["review-run", "--run-directory", "run"])
        self.assertEqual(args.command, "review-run")


if __name__ == "__main__":
    unittest.main()
