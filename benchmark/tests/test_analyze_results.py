from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from benchmark import reporting as MODULE  # noqa: E402


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class AnalyzeResultsTests(unittest.TestCase):
    def test_analyze_result_dir_generates_new_metrics_and_charts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result_dir = root / "results" / "run_001_paper_system_benchmark"
            result_dir.mkdir(parents=True)
            labels_path = root / "labels.json"
            labels_path.write_text(
                json.dumps(
                    {
                        "systems": {
                            "rasa_only": "Pure Rasa",
                            "rasa_plus_llm": "Rasa + LLM",
                        },
                        "suites": {
                            "shared_core": "Shared Core",
                            "agent_extension": "Agent Extension",
                        },
                        "scenarios": {
                            "recommendation": "Recommendation",
                            "transactional_action": "Transactional Action",
                        },
                        "failures": {
                            "missing_required_keywords": "Missing Required Keywords",
                            "technical_failure": "Technical Failure / HTTP Error",
                            "unsupported": "Unsupported",
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            write_csv(
                result_dir / "conversation_summary.csv",
                [
                    {
                        "timestamp": "",
                        "system": "rasa_only",
                        "scenario_family": "recommendation",
                        "scenario": "basic",
                        "sample_id": "s1",
                        "benchmark_suite": "shared_core",
                        "tier": "extended",
                        "repeat": 1,
                        "concurrency": 1,
                        "conversation_index": 1,
                        "account": "anonymous",
                        "layer": "business",
                        "score_profile": "structured_business",
                        "required_capabilities": "[]",
                        "turn_count": 1,
                        "executed_turns": 1,
                        "unsupported": False,
                        "success": True,
                        "http_error_count": 0,
                        "latency_ms": 100.0,
                        "started_at": 1.0,
                        "finished_at": 1.1,
                        "quality_status": "pass",
                        "conversation_success": True,
                        "passed": True,
                        "quality_flags": "{}",
                        "supported": True,
                        "hallucination_free": True,
                        "missing_required_keywords": False,
                        "contains_forbidden_keywords": False,
                        "missing_required_cards": False,
                        "missing_required_actions": False,
                        "missing_confirmation_buttons": False,
                        "missing_order_id": False,
                        "hallucinated_order_id": False,
                        "login_block_failure": False,
                        "image_flow_failure": False,
                        "pending_decision_failure": False,
                        "technical_failure": False,
                        "format_error": False,
                        "primary_failure_reason": "",
                    },
                    {
                        "timestamp": "",
                        "system": "rasa_only",
                        "scenario_family": "recommendation",
                        "scenario": "basic",
                        "sample_id": "s1",
                        "benchmark_suite": "shared_core",
                        "tier": "extended",
                        "repeat": 2,
                        "concurrency": 1,
                        "conversation_index": 2,
                        "account": "anonymous",
                        "layer": "business",
                        "score_profile": "structured_business",
                        "required_capabilities": "[]",
                        "turn_count": 1,
                        "executed_turns": 1,
                        "unsupported": False,
                        "success": True,
                        "http_error_count": 0,
                        "latency_ms": 100.0,
                        "started_at": 1.2,
                        "finished_at": 1.3,
                        "quality_status": "pass",
                        "conversation_success": True,
                        "passed": True,
                        "quality_flags": "{}",
                        "supported": True,
                        "hallucination_free": True,
                        "missing_required_keywords": False,
                        "contains_forbidden_keywords": False,
                        "missing_required_cards": False,
                        "missing_required_actions": False,
                        "missing_confirmation_buttons": False,
                        "missing_order_id": False,
                        "hallucinated_order_id": False,
                        "login_block_failure": False,
                        "image_flow_failure": False,
                        "pending_decision_failure": False,
                        "technical_failure": False,
                        "format_error": False,
                        "primary_failure_reason": "",
                    },
                    {
                        "timestamp": "",
                        "system": "rasa_only",
                        "scenario_family": "recommendation",
                        "scenario": "basic",
                        "sample_id": "s1",
                        "benchmark_suite": "shared_core",
                        "tier": "extended",
                        "repeat": 3,
                        "concurrency": 1,
                        "conversation_index": 3,
                        "account": "anonymous",
                        "layer": "business",
                        "score_profile": "structured_business",
                        "required_capabilities": "[]",
                        "turn_count": 1,
                        "executed_turns": 1,
                        "unsupported": False,
                        "success": True,
                        "http_error_count": 0,
                        "latency_ms": 100.0,
                        "started_at": 1.4,
                        "finished_at": 1.5,
                        "quality_status": "pass",
                        "conversation_success": True,
                        "passed": True,
                        "quality_flags": "{}",
                        "supported": True,
                        "hallucination_free": True,
                        "missing_required_keywords": False,
                        "contains_forbidden_keywords": False,
                        "missing_required_cards": False,
                        "missing_required_actions": False,
                        "missing_confirmation_buttons": False,
                        "missing_order_id": False,
                        "hallucinated_order_id": False,
                        "login_block_failure": False,
                        "image_flow_failure": False,
                        "pending_decision_failure": False,
                        "technical_failure": False,
                        "format_error": False,
                        "primary_failure_reason": "",
                    },
                    {
                        "timestamp": "",
                        "system": "rasa_plus_llm",
                        "scenario_family": "recommendation",
                        "scenario": "basic",
                        "sample_id": "s1",
                        "benchmark_suite": "shared_core",
                        "tier": "extended",
                        "repeat": 1,
                        "concurrency": 1,
                        "conversation_index": 4,
                        "account": "anonymous",
                        "layer": "business",
                        "score_profile": "structured_business",
                        "required_capabilities": "[]",
                        "turn_count": 1,
                        "executed_turns": 1,
                        "unsupported": False,
                        "success": True,
                        "http_error_count": 0,
                        "latency_ms": 90.0,
                        "started_at": 2.0,
                        "finished_at": 2.1,
                        "quality_status": "pass",
                        "conversation_success": True,
                        "passed": True,
                        "quality_flags": "{}",
                        "supported": True,
                        "hallucination_free": True,
                        "missing_required_keywords": False,
                        "contains_forbidden_keywords": False,
                        "missing_required_cards": False,
                        "missing_required_actions": False,
                        "missing_confirmation_buttons": False,
                        "missing_order_id": False,
                        "hallucinated_order_id": False,
                        "login_block_failure": False,
                        "image_flow_failure": False,
                        "pending_decision_failure": False,
                        "technical_failure": False,
                        "format_error": False,
                        "primary_failure_reason": "",
                    },
                    {
                        "timestamp": "",
                        "system": "rasa_plus_llm",
                        "scenario_family": "recommendation",
                        "scenario": "advanced",
                        "sample_id": "s2",
                        "benchmark_suite": "shared_core",
                        "tier": "extended",
                        "repeat": 1,
                        "concurrency": 1,
                        "conversation_index": 5,
                        "account": "anonymous",
                        "layer": "business",
                        "score_profile": "structured_business",
                        "required_capabilities": "[]",
                        "turn_count": 1,
                        "executed_turns": 1,
                        "unsupported": False,
                        "success": False,
                        "http_error_count": 1,
                        "latency_ms": 95.0,
                        "started_at": 2.2,
                        "finished_at": 2.3,
                        "quality_status": "fail",
                        "conversation_success": False,
                        "passed": False,
                        "quality_flags": "{}",
                        "supported": True,
                        "hallucination_free": True,
                        "missing_required_keywords": True,
                        "contains_forbidden_keywords": False,
                        "missing_required_cards": False,
                        "missing_required_actions": False,
                        "missing_confirmation_buttons": False,
                        "missing_order_id": False,
                        "hallucinated_order_id": False,
                        "login_block_failure": False,
                        "image_flow_failure": False,
                        "pending_decision_failure": False,
                        "technical_failure": True,
                        "format_error": False,
                        "primary_failure_reason": "technical_failure",
                    },
                    {
                        "timestamp": "",
                        "system": "rasa_plus_llm",
                        "scenario_family": "transactional_action",
                        "scenario": "expired",
                        "sample_id": "transaction_update_shipping_confirm_extended",
                        "benchmark_suite": "agent_extension",
                        "tier": "extended",
                        "repeat": 1,
                        "concurrency": 1,
                        "conversation_index": 6,
                        "account": "customer",
                        "layer": "boundary",
                        "score_profile": "boundary_safe",
                        "required_capabilities": "[]",
                        "turn_count": 1,
                        "executed_turns": 1,
                        "unsupported": False,
                        "success": False,
                        "http_error_count": 0,
                        "latency_ms": 110.0,
                        "started_at": 3.0,
                        "finished_at": 3.1,
                        "quality_status": "fail",
                        "conversation_success": False,
                        "passed": False,
                        "quality_flags": "{}",
                        "supported": True,
                        "hallucination_free": True,
                        "missing_required_keywords": True,
                        "contains_forbidden_keywords": False,
                        "missing_required_cards": False,
                        "missing_required_actions": False,
                        "missing_confirmation_buttons": False,
                        "missing_order_id": False,
                        "hallucinated_order_id": False,
                        "login_block_failure": False,
                        "image_flow_failure": False,
                        "pending_decision_failure": False,
                        "technical_failure": False,
                        "format_error": False,
                        "primary_failure_reason": "missing_required_keywords",
                    },
                ],
            )

            (result_dir / "prompt_versions.json").write_text(
                json.dumps({"items": [{"name": "agent_final_answer", "path": "backend/prompts/agent_final_answer.md", "sha256": "abc123"}]}, ensure_ascii=False),
                encoding="utf-8",
            )
            (result_dir / "run_metadata.json").write_text(
                json.dumps(
                    {
                        "profile": "paper",
                        "selection_mode": "all_unique",
                        "dataset_tier": "extended",
                        "systems": ["rasa_only", "rasa_plus_llm"],
                        "scenario_families": ["recommendation", "transactional_action"],
                        "dataset_files": {},
                        "sample_universe": [],
                        "expected_samples": [
                            {"system": "rasa_only", "benchmark_suite": "shared_core", "scenario_family": "recommendation", "scenario": "basic", "sample_id": "s1", "tier": "extended", "repeatable": True},
                            {"system": "rasa_only", "benchmark_suite": "shared_core", "scenario_family": "recommendation", "scenario": "advanced", "sample_id": "s2", "tier": "extended", "repeatable": True},
                            {"system": "rasa_plus_llm", "benchmark_suite": "shared_core", "scenario_family": "recommendation", "scenario": "basic", "sample_id": "s1", "tier": "extended", "repeatable": True},
                            {"system": "rasa_plus_llm", "benchmark_suite": "shared_core", "scenario_family": "recommendation", "scenario": "advanced", "sample_id": "s2", "tier": "extended", "repeatable": True},
                            {"system": "rasa_plus_llm", "benchmark_suite": "agent_extension", "scenario_family": "transactional_action", "scenario": "expired", "sample_id": "transaction_update_shipping_confirm_extended", "tier": "extended", "repeatable": True},
                            {"system": "rasa_plus_llm", "benchmark_suite": "agent_extension", "scenario_family": "transactional_action", "scenario": "expired", "sample_id": "transaction_pending_action_expired_extended", "tier": "extended", "repeatable": False},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            analysis_dir = MODULE.analyze_result_dir(result_dir=result_dir, labels_path=labels_path)
            self.assertTrue((analysis_dir / "suite_metrics.csv").exists())
            self.assertTrue((analysis_dir / "family_metrics.csv").exists())
            self.assertTrue((analysis_dir / "sample_coverage.csv").exists())
            self.assertTrue((analysis_dir / "failure_breakdown.csv").exists())
            self.assertTrue((analysis_dir / "failure_flags.csv").exists())
            self.assertTrue((analysis_dir / "charts" / "shared_core_ranking.svg").exists())
            self.assertTrue((analysis_dir / "charts" / "agent_extension_ranking.svg").exists())
            self.assertTrue((analysis_dir / "charts" / "exclusive_failure_pie.svg").exists())
            self.assertTrue((analysis_dir / "charts" / "failure_flags_bar.svg").exists())

            suite_metrics = list(csv.DictReader((analysis_dir / "suite_metrics.csv").open("r", encoding="utf-8")))
            coverage_rows = list(csv.DictReader((analysis_dir / "sample_coverage.csv").open("r", encoding="utf-8")))
            leader_rows = list(csv.DictReader((analysis_dir / "suite_scenario_leaders.csv").open("r", encoding="utf-8")))
            failure_rows = list(csv.DictReader((analysis_dir / "failure_breakdown.csv").open("r", encoding="utf-8")))
            flag_rows = list(csv.DictReader((analysis_dir / "failure_flags.csv").open("r", encoding="utf-8")))

            shared_core_rows = [row for row in suite_metrics if row["suite"] == "shared_core" and row["system"] in {"rasa_only", "rasa_plus_llm"}]
            self.assertEqual(shared_core_rows[0]["system"], "rasa_plus_llm")
            self.assertEqual(shared_core_rows[0]["rank"], "1")
            self.assertNotEqual(shared_core_rows[0]["suite_pass_rate"], shared_core_rows[0]["suite_unique_micro_pass_rate"])

            pending_coverage = next(row for row in coverage_rows if row["suite"] == "agent_extension")
            self.assertIn("transaction_pending_action_expired_extended", pending_coverage["missing_sample_ids"])

            agent_leader = next(row for row in leader_rows if row["suite"] == "agent_extension")
            self.assertEqual(agent_leader["leader_status"], "no_pass")
            self.assertEqual(agent_leader["leader_system"], "")

            total_failures = sum(int(row["count"]) for row in failure_rows)
            self.assertEqual(total_failures, 2)

            shared_flag_row = next(row for row in flag_rows if row["suite"] == "shared_core" and row["system"] == "rasa_plus_llm")
            self.assertEqual(shared_flag_row["technical_failure"], "1")

            report_text = (analysis_dir / "report.md").read_text(encoding="utf-8")
            self.assertIn("Coverage", report_text)
            self.assertIn("## shared_core Ranking", report_text)
            self.assertIn("## Family Metrics", report_text)
            self.assertIn("## Stability And CI Notes", report_text)

    def test_analyze_result_dir_generates_new_metrics_and_charts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result_dir = root / "results" / "run_001_paper_system_benchmark"
            result_dir.mkdir(parents=True)
            labels_path = root / "labels.json"
            labels_path.write_text(
                json.dumps(
                    {
                        "systems": {
                            "rasa_only": "Pure Rasa",
                            "rasa_plus_llm": "Rasa + LLM",
                        },
                        "suites": {
                            "shared_core": "Shared Core",
                            "agent_extension": "Agent Extension",
                        },
                        "scenarios": {
                            "recommendation": "Recommendation",
                            "transactional_action": "Transactional Action",
                        },
                        "failures": {
                            "missing_required_keywords": "Missing Required Keywords",
                            "technical_failure": "Technical Failure / HTTP Error",
                            "unsupported": "Unsupported",
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            write_csv(
                result_dir / "conversation_summary.csv",
                [
                    {
                        "timestamp": "",
                        "system": "rasa_only",
                        "scenario_family": "recommendation",
                        "scenario": "basic",
                        "sample_id": "s1",
                        "benchmark_suite": "shared_core",
                        "tier": "extended",
                        "repeat": 1,
                        "concurrency": 1,
                        "conversation_index": 1,
                        "account": "anonymous",
                        "layer": "business",
                        "score_profile": "structured_business",
                        "required_capabilities": "[]",
                        "turn_count": 1,
                        "executed_turns": 1,
                        "unsupported": False,
                        "success": True,
                        "http_error_count": 0,
                        "latency_ms": 100.0,
                        "started_at": 1.0,
                        "finished_at": 1.1,
                        "quality_status": "pass",
                        "conversation_success": True,
                        "passed": True,
                        "quality_flags": "{}",
                        "supported": True,
                        "hallucination_free": True,
                        "missing_required_keywords": False,
                        "contains_forbidden_keywords": False,
                        "missing_required_cards": False,
                        "missing_required_actions": False,
                        "missing_confirmation_buttons": False,
                        "missing_order_id": False,
                        "hallucinated_order_id": False,
                        "login_block_failure": False,
                        "image_flow_failure": False,
                        "pending_decision_failure": False,
                        "technical_failure": False,
                        "format_error": False,
                        "primary_failure_reason": "",
                    },
                    {
                        "timestamp": "",
                        "system": "rasa_only",
                        "scenario_family": "recommendation",
                        "scenario": "basic",
                        "sample_id": "s1",
                        "benchmark_suite": "shared_core",
                        "tier": "extended",
                        "repeat": 2,
                        "concurrency": 1,
                        "conversation_index": 2,
                        "account": "anonymous",
                        "layer": "business",
                        "score_profile": "structured_business",
                        "required_capabilities": "[]",
                        "turn_count": 1,
                        "executed_turns": 1,
                        "unsupported": False,
                        "success": True,
                        "http_error_count": 0,
                        "latency_ms": 100.0,
                        "started_at": 1.2,
                        "finished_at": 1.3,
                        "quality_status": "pass",
                        "conversation_success": True,
                        "passed": True,
                        "quality_flags": "{}",
                        "supported": True,
                        "hallucination_free": True,
                        "missing_required_keywords": False,
                        "contains_forbidden_keywords": False,
                        "missing_required_cards": False,
                        "missing_required_actions": False,
                        "missing_confirmation_buttons": False,
                        "missing_order_id": False,
                        "hallucinated_order_id": False,
                        "login_block_failure": False,
                        "image_flow_failure": False,
                        "pending_decision_failure": False,
                        "technical_failure": False,
                        "format_error": False,
                        "primary_failure_reason": "",
                    },
                    {
                        "timestamp": "",
                        "system": "rasa_only",
                        "scenario_family": "recommendation",
                        "scenario": "basic",
                        "sample_id": "s1",
                        "benchmark_suite": "shared_core",
                        "tier": "extended",
                        "repeat": 3,
                        "concurrency": 1,
                        "conversation_index": 3,
                        "account": "anonymous",
                        "layer": "business",
                        "score_profile": "structured_business",
                        "required_capabilities": "[]",
                        "turn_count": 1,
                        "executed_turns": 1,
                        "unsupported": False,
                        "success": True,
                        "http_error_count": 0,
                        "latency_ms": 100.0,
                        "started_at": 1.4,
                        "finished_at": 1.5,
                        "quality_status": "pass",
                        "conversation_success": True,
                        "passed": True,
                        "quality_flags": "{}",
                        "supported": True,
                        "hallucination_free": True,
                        "missing_required_keywords": False,
                        "contains_forbidden_keywords": False,
                        "missing_required_cards": False,
                        "missing_required_actions": False,
                        "missing_confirmation_buttons": False,
                        "missing_order_id": False,
                        "hallucinated_order_id": False,
                        "login_block_failure": False,
                        "image_flow_failure": False,
                        "pending_decision_failure": False,
                        "technical_failure": False,
                        "format_error": False,
                        "primary_failure_reason": "",
                    },
                    {
                        "timestamp": "",
                        "system": "rasa_plus_llm",
                        "scenario_family": "recommendation",
                        "scenario": "basic",
                        "sample_id": "s1",
                        "benchmark_suite": "shared_core",
                        "tier": "extended",
                        "repeat": 1,
                        "concurrency": 1,
                        "conversation_index": 4,
                        "account": "anonymous",
                        "layer": "business",
                        "score_profile": "structured_business",
                        "required_capabilities": "[]",
                        "turn_count": 1,
                        "executed_turns": 1,
                        "unsupported": False,
                        "success": True,
                        "http_error_count": 0,
                        "latency_ms": 90.0,
                        "started_at": 2.0,
                        "finished_at": 2.1,
                        "quality_status": "pass",
                        "conversation_success": True,
                        "passed": True,
                        "quality_flags": "{}",
                        "supported": True,
                        "hallucination_free": True,
                        "missing_required_keywords": False,
                        "contains_forbidden_keywords": False,
                        "missing_required_cards": False,
                        "missing_required_actions": False,
                        "missing_confirmation_buttons": False,
                        "missing_order_id": False,
                        "hallucinated_order_id": False,
                        "login_block_failure": False,
                        "image_flow_failure": False,
                        "pending_decision_failure": False,
                        "technical_failure": False,
                        "format_error": False,
                        "primary_failure_reason": "",
                    },
                    {
                        "timestamp": "",
                        "system": "rasa_plus_llm",
                        "scenario_family": "recommendation",
                        "scenario": "basic",
                        "sample_id": "s1",
                        "benchmark_suite": "shared_core",
                        "tier": "extended",
                        "repeat": 2,
                        "concurrency": 1,
                        "conversation_index": 5,
                        "account": "anonymous",
                        "layer": "business",
                        "score_profile": "structured_business",
                        "required_capabilities": "[]",
                        "turn_count": 1,
                        "executed_turns": 1,
                        "unsupported": False,
                        "success": True,
                        "http_error_count": 0,
                        "latency_ms": 92.0,
                        "started_at": 2.15,
                        "finished_at": 2.2,
                        "quality_status": "pass",
                        "conversation_success": True,
                        "passed": True,
                        "quality_flags": "{}",
                        "supported": True,
                        "hallucination_free": True,
                        "missing_required_keywords": False,
                        "contains_forbidden_keywords": False,
                        "missing_required_cards": False,
                        "missing_required_actions": False,
                        "missing_confirmation_buttons": False,
                        "missing_order_id": False,
                        "hallucinated_order_id": False,
                        "login_block_failure": False,
                        "image_flow_failure": False,
                        "pending_decision_failure": False,
                        "technical_failure": False,
                        "format_error": False,
                        "primary_failure_reason": "",
                    },
                    {
                        "timestamp": "",
                        "system": "rasa_plus_llm",
                        "scenario_family": "recommendation",
                        "scenario": "advanced",
                        "sample_id": "s2",
                        "benchmark_suite": "shared_core",
                        "tier": "extended",
                        "repeat": 1,
                        "concurrency": 1,
                        "conversation_index": 6,
                        "account": "anonymous",
                        "layer": "business",
                        "score_profile": "structured_business",
                        "required_capabilities": "[]",
                        "turn_count": 1,
                        "executed_turns": 1,
                        "unsupported": False,
                        "success": False,
                        "http_error_count": 1,
                        "latency_ms": 95.0,
                        "started_at": 2.2,
                        "finished_at": 2.3,
                        "quality_status": "fail",
                        "conversation_success": False,
                        "passed": False,
                        "quality_flags": "{}",
                        "supported": True,
                        "hallucination_free": True,
                        "missing_required_keywords": True,
                        "contains_forbidden_keywords": False,
                        "missing_required_cards": False,
                        "missing_required_actions": False,
                        "missing_confirmation_buttons": False,
                        "missing_order_id": False,
                        "hallucinated_order_id": False,
                        "login_block_failure": False,
                        "image_flow_failure": False,
                        "pending_decision_failure": False,
                        "technical_failure": True,
                        "format_error": False,
                        "primary_failure_reason": "technical_failure",
                    },
                    {
                        "timestamp": "",
                        "system": "rasa_plus_llm",
                        "scenario_family": "transactional_action",
                        "scenario": "expired",
                        "sample_id": "transaction_update_shipping_confirm_extended",
                        "benchmark_suite": "agent_extension",
                        "tier": "extended",
                        "repeat": 1,
                        "concurrency": 1,
                        "conversation_index": 7,
                        "account": "customer",
                        "layer": "boundary",
                        "score_profile": "boundary_safe",
                        "required_capabilities": "[]",
                        "turn_count": 1,
                        "executed_turns": 1,
                        "unsupported": False,
                        "success": False,
                        "http_error_count": 0,
                        "latency_ms": 110.0,
                        "started_at": 3.0,
                        "finished_at": 3.1,
                        "quality_status": "fail",
                        "conversation_success": False,
                        "passed": False,
                        "quality_flags": "{}",
                        "supported": True,
                        "hallucination_free": True,
                        "missing_required_keywords": True,
                        "contains_forbidden_keywords": False,
                        "missing_required_cards": False,
                        "missing_required_actions": False,
                        "missing_confirmation_buttons": False,
                        "missing_order_id": False,
                        "hallucinated_order_id": False,
                        "login_block_failure": False,
                        "image_flow_failure": False,
                        "pending_decision_failure": False,
                        "technical_failure": False,
                        "format_error": False,
                        "primary_failure_reason": "missing_required_keywords",
                    },
                ],
            )

            (result_dir / "prompt_versions.json").write_text(
                json.dumps({"items": [{"name": "agent_final_answer", "path": "backend/prompts/agent_final_answer.md", "sha256": "abc123"}]}, ensure_ascii=False),
                encoding="utf-8",
            )
            (result_dir / "run_metadata.json").write_text(
                json.dumps(
                    {
                        "profile": "paper",
                        "selection_mode": "all_unique",
                        "dataset_tier": "extended",
                        "systems": ["rasa_only", "rasa_plus_llm"],
                        "scenario_families": ["recommendation", "transactional_action"],
                        "dataset_files": {},
                        "sample_universe": [],
                        "expected_samples": [
                            {"system": "rasa_only", "benchmark_suite": "shared_core", "scenario_family": "recommendation", "scenario": "basic", "sample_id": "s1", "tier": "extended", "repeatable": True},
                            {"system": "rasa_only", "benchmark_suite": "shared_core", "scenario_family": "recommendation", "scenario": "advanced", "sample_id": "s2", "tier": "extended", "repeatable": True},
                            {"system": "rasa_plus_llm", "benchmark_suite": "shared_core", "scenario_family": "recommendation", "scenario": "basic", "sample_id": "s1", "tier": "extended", "repeatable": True},
                            {"system": "rasa_plus_llm", "benchmark_suite": "shared_core", "scenario_family": "recommendation", "scenario": "advanced", "sample_id": "s2", "tier": "extended", "repeatable": True},
                            {"system": "rasa_plus_llm", "benchmark_suite": "agent_extension", "scenario_family": "transactional_action", "scenario": "expired", "sample_id": "transaction_update_shipping_confirm_extended", "tier": "extended", "repeatable": True},
                            {"system": "rasa_plus_llm", "benchmark_suite": "agent_extension", "scenario_family": "transactional_action", "scenario": "expired", "sample_id": "transaction_pending_action_expired_extended", "tier": "extended", "repeatable": False},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            analysis_dir = MODULE.analyze_result_dir(result_dir=result_dir, labels_path=labels_path)
            self.assertTrue((analysis_dir / "suite_metrics.csv").exists())
            self.assertTrue((analysis_dir / "family_metrics.csv").exists())
            self.assertTrue((analysis_dir / "sample_coverage.csv").exists())
            self.assertTrue((analysis_dir / "failure_breakdown.csv").exists())
            self.assertTrue((analysis_dir / "failure_flags.csv").exists())
            self.assertTrue((analysis_dir / "charts" / "shared_core_ranking.svg").exists())
            self.assertTrue((analysis_dir / "charts" / "agent_extension_ranking.svg").exists())
            self.assertTrue((analysis_dir / "charts" / "exclusive_failure_pie.svg").exists())
            self.assertTrue((analysis_dir / "charts" / "failure_flags_bar.svg").exists())

            suite_metrics = read_csv(analysis_dir / "suite_metrics.csv")
            coverage_rows = read_csv(analysis_dir / "sample_coverage.csv")
            leader_rows = read_csv(analysis_dir / "suite_scenario_leaders.csv")
            failure_rows = read_csv(analysis_dir / "failure_breakdown.csv")
            flag_rows = read_csv(analysis_dir / "failure_flags.csv")

            shared_core_rows = [row for row in suite_metrics if row["suite"] == "shared_core" and row["system"] in {"rasa_only", "rasa_plus_llm"}]
            self.assertEqual(shared_core_rows[0]["system"], "rasa_plus_llm")
            self.assertEqual(shared_core_rows[0]["rank"], "1")
            self.assertNotEqual(shared_core_rows[0]["suite_pass_rate"], shared_core_rows[0]["suite_unique_micro_pass_rate"])

            pending_coverage = next(row for row in coverage_rows if row["suite"] == "agent_extension")
            self.assertIn("transaction_pending_action_expired_extended", pending_coverage["missing_sample_ids"])

            agent_leader = next(row for row in leader_rows if row["suite"] == "agent_extension")
            self.assertEqual(agent_leader["leader_status"], "no_pass")
            self.assertEqual(agent_leader["leader_system"], "")

            total_failures = sum(int(row["count"]) for row in failure_rows)
            self.assertEqual(total_failures, 2)

            shared_flag_row = next(row for row in flag_rows if row["suite"] == "shared_core" and row["system"] == "rasa_plus_llm")
            self.assertEqual(shared_flag_row["technical_failure"], "1")

            report_text = (analysis_dir / "report.md").read_text(encoding="utf-8")
            self.assertIn("Coverage", report_text)
            self.assertIn("## shared_core Ranking", report_text)
            self.assertIn("## Family Metrics", report_text)
            self.assertIn("## Stability And CI Notes", report_text)


if __name__ == "__main__":
    unittest.main()
