from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from benchmark import dataset as MODULE  # noqa: E402


class DatasetBuilderTests(unittest.TestCase):
    def test_build_dataset_copies_tiers_and_generates_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_dir = root / "source"
            output_dir = root / "output"
            (source_dir / "core").mkdir(parents=True)
            (source_dir / "extended").mkdir(parents=True)

            core_record = {
                "id": "core-1",
                "scenario_family": "recommendation",
                "scenario": "basic",
                "turns": [{"id": "t1", "kind": "chat_send", "message": "Recommend a white phone."}],
                "account": "anonymous",
                "required_capabilities": [],
                "preconditions": {},
                "expected_outcomes": {"required_any_text_keywords": ["recommend"], "min_response_chars": 8},
                "tags": ["core"],
            }
            extended_record = {
                "id": "ext-1",
                "scenario_family": "transactional_action",
                "scenario": "confirm",
                "turns": [{"id": "t1", "kind": "pending_decision", "decision": "confirm"}],
                "account": "customer",
                "required_capabilities": ["supports_pending_decision"],
                "preconditions": {},
                "expected_outcomes": {"required_any_text_keywords": ["confirm"], "min_response_chars": 8},
                "tags": ["extended"],
            }

            (source_dir / "core" / "recommendation.jsonl").write_text(
                json.dumps(core_record, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            (source_dir / "extended" / "transactional_action.jsonl").write_text(
                json.dumps(extended_record, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            manifest = MODULE.build_dataset(
                source_dir=source_dir,
                output_dir=output_dir,
                seed=20260412,
                rasa_nlu=Path("rasa/data/nlu.yml"),
                lora_jsonl=[],
            )

            self.assertEqual(manifest["seed"], 20260412)
            self.assertTrue((output_dir / "core" / "recommendation.jsonl").exists())
            self.assertTrue((output_dir / "extended" / "transactional_action.jsonl").exists())
            manifest_path = output_dir / "manifest.json"
            self.assertTrue(manifest_path.exists())

            core_written = json.loads((output_dir / "core" / "recommendation.jsonl").read_text(encoding="utf-8").strip())
            extended_written = json.loads((output_dir / "extended" / "transactional_action.jsonl").read_text(encoding="utf-8").strip())
            self.assertEqual(core_written["benchmark_suite"], "shared_core")
            self.assertEqual(extended_written["benchmark_suite"], "agent_extension")

            written = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(written["stats"]["core"]["total_count"], 1)
            self.assertEqual(written["stats"]["extended"]["total_count"], 1)
            self.assertEqual(written["stats"]["core"]["suite_counts"], {"shared_core": 1})
            self.assertEqual(written["stats"]["extended"]["suite_counts"], {"agent_extension": 1})


if __name__ == "__main__":
    unittest.main()
