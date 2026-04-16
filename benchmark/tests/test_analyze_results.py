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
        for row in rows:
            writer.writerow(row)


class AnalyzeResultsTests(unittest.TestCase):
    def test_analyze_result_dir_generates_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result_dir = root / "results" / "run_001"
            result_dir.mkdir(parents=True)
            labels_path = root / "labels.json"
            labels_path.write_text(
                json.dumps(
                    {
                        "systems": {
                            "rasa_only": "纯 Rasa",
                            "rasa_plus_llm": "Rasa + LLM",
                        },
                        "scenarios": {
                            "recommendation": "商品推荐",
                            "transactional_action": "事务操作",
                        },
                        "failures": {
                            "missing_required_keywords": "缺少必需关键词",
                            "login_block_failures": "登录阻断失败",
                        },
                        "charts": {},
                        "report": {},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            write_csv(
                result_dir / "summary.csv",
                [
                    {
                        "system": "rasa_only",
                        "scenario_family": "recommendation",
                        "concurrency": 1,
                        "repeat": 1,
                        "eligible_conversations": 2,
                        "p95_ms": 120.0,
                    },
                    {
                        "system": "rasa_plus_llm",
                        "scenario_family": "transactional_action",
                        "concurrency": 1,
                        "repeat": 1,
                        "eligible_conversations": 2,
                        "p95_ms": 90.0,
                    },
                ],
            )
            write_csv(
                result_dir / "scenario_quality.csv",
                [
                    {
                        "system": "rasa_only",
                        "scenario_family": "recommendation",
                        "layer": "business",
                        "score_profile": "structured_business",
                        "conversations": 2,
                        "eligible_conversations": 2,
                        "unsupported_conversations": 0,
                        "conversation_success": 1,
                        "quality_pass": 1,
                        "missing_required_keywords": 1,
                        "contains_forbidden_keywords": 0,
                        "missing_required_cards": 0,
                        "missing_required_actions": 0,
                        "missing_confirmation_buttons": 0,
                        "missing_order_id": 0,
                        "hallucinated_order_id": 0,
                        "login_block_failures": 0,
                        "image_flow_failures": 0,
                        "pending_decision_failures": 0,
                    },
                    {
                        "system": "rasa_plus_llm",
                        "scenario_family": "transactional_action",
                        "layer": "boundary",
                        "score_profile": "boundary_safe",
                        "conversations": 2,
                        "eligible_conversations": 2,
                        "unsupported_conversations": 0,
                        "conversation_success": 2,
                        "quality_pass": 2,
                        "missing_required_keywords": 0,
                        "contains_forbidden_keywords": 0,
                        "missing_required_cards": 0,
                        "missing_required_actions": 0,
                        "missing_confirmation_buttons": 0,
                        "missing_order_id": 0,
                        "hallucinated_order_id": 0,
                        "login_block_failures": 0,
                        "image_flow_failures": 0,
                        "pending_decision_failures": 0,
                    },
                ],
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
                        "tier": "core",
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
                        "latency_ms": 120.0,
                        "started_at": 1.0,
                        "finished_at": 1.1,
                        "quality_status": "fail",
                        "conversation_success": True,
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
                    },
                    {
                        "timestamp": "",
                        "system": "rasa_plus_llm",
                        "scenario_family": "transactional_action",
                        "scenario": "confirm",
                        "sample_id": "s2",
                        "tier": "core",
                        "repeat": 1,
                        "concurrency": 1,
                        "conversation_index": 2,
                        "account": "customer",
                        "layer": "boundary",
                        "score_profile": "boundary_safe",
                        "required_capabilities": "[]",
                        "turn_count": 2,
                        "executed_turns": 2,
                        "unsupported": False,
                        "success": True,
                        "http_error_count": 0,
                        "latency_ms": 90.0,
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
                    },
                ],
            )

            analysis_dir = MODULE.analyze_result_dir(result_dir=result_dir, labels_path=labels_path)
            self.assertTrue((analysis_dir / "overall_metrics.csv").exists())
            self.assertTrue((analysis_dir / "scenario_leaders.csv").exists())
            self.assertTrue((analysis_dir / "failure_breakdown.csv").exists())
            self.assertTrue((analysis_dir / "business_vs_boundary.csv").exists())
            self.assertTrue((analysis_dir / "hallucination_breakdown.csv").exists())
            self.assertTrue((analysis_dir / "conclusions.json").exists())
            self.assertTrue((analysis_dir / "report.md").exists())
            self.assertTrue((analysis_dir / "plots" / "overall_pass_rate.png").exists())
            conclusions = json.loads((analysis_dir / "conclusions.json").read_text(encoding="utf-8"))
            self.assertTrue(conclusions["findings"])


if __name__ == "__main__":
    unittest.main()
