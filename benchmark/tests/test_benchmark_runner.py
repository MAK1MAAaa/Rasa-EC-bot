from __future__ import annotations

import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch


PROJECT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from benchmark import runner as MODULE  # noqa: E402


def make_expected_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "required_any_text_keywords": ["����", "״̬"],
        "required_all_text_keywords": [],
        "required_keyword_groups": [],
        "forbidden_text_keywords": [],
        "required_card_types": ["order"],
        "required_action_types": [],
        "requires_confirmation_buttons": False,
        "should_return_order_id": True,
        "should_block_without_login": False,
        "should_be_unsupported": False,
        "must_avoid_hallucinated_order_id": True,
        "allowed_order_ids": ["ORD202603300001"],
        "min_response_chars": 8,
    }
    payload.update(overrides)
    return payload


def make_sample(
    sample_id: str,
    *,
    benchmark_suite: str = "shared_core",
    scenario_family: str = "order_query",
    scenario: str = "query_order",
    repeatable: bool = True,
    tags: list[str] | None = None,
    expected: dict[str, Any] | None = None,
) -> MODULE.ConversationSample:
    return MODULE.ConversationSample(
        sample_id=sample_id,
        benchmark_suite=benchmark_suite,
        scenario_family=scenario_family,
        scenario=scenario,
        turns=[MODULE.TurnStep(turn_id="chat", kind="chat_send", message=f"��ѯ���� {sample_id}")],
        account="customer",
        required_capabilities=["supports_auth_queries", "supports_cards"],
        preconditions={"allowed_order_ids": ["ORD202603300001"]},
        expected_outcomes=MODULE.ExpectedOutcomes(**make_expected_payload(**(expected or {}))),
        tags=tags or ["test"],
        tier="extended",
        repeatable=repeatable,
        layer="business",
        score_profile="structured_business",
    )


def make_turn_event(
    sample: MODULE.ConversationSample,
    *,
    success: bool = True,
    response_text: str = "���� ORD202603300001 ״̬����",
    response_card_types: list[str] | None = None,
    response_order_ids: list[str] | None = None,
) -> MODULE.TurnEvent:
    return MODULE.TurnEvent(
        timestamp="",
        system="rasa_plus_llm",
        scenario_family=sample.scenario_family,
        scenario=sample.scenario,
        sample_id=sample.sample_id,
        benchmark_suite=sample.benchmark_suite,
        tier=sample.tier,
        repeat=1,
        concurrency=1,
        conversation_index=1,
        turn_index=1,
        turn_id="chat",
        turn_kind="chat_send",
        requires_auth=True,
        required_capabilities=list(sample.required_capabilities),
        executed=True,
        unsupported=False,
        success=success,
        http_status=200 if success else None,
        error_type="" if success else "runtime_error",
        error_message="",
        latency_ms=10.0,
        started_at=1.0,
        finished_at=1.1,
        response_text=response_text,
        response_chars=len(response_text),
        response_card_count=len(response_card_types or ["order"]),
        response_action_count=0,
        response_card_types=response_card_types or ["order"],
        response_action_types=[],
        response_order_ids=response_order_ids or ["ORD202603300001"],
    )


class BenchmarkRunnerTests(unittest.TestCase):
    def test_load_dataset_file_parses_repeatable_and_suite(self) -> None:
        payload = {
            "id": "transaction_pending_action_expired_extended",
            "benchmark_suite": "agent_extension",
            "scenario_family": "transactional_action",
            "scenario": "pending_action_expired",
            "turns": [{"id": "chat", "kind": "chat_send", "message": "ȡ������"}],
            "account": "customer",
            "required_capabilities": ["supports_pending_action"],
            "preconditions": {},
            "expected_outcomes": make_expected_payload(required_card_types=[]),
            "tags": ["paper_only"],
            "tier": "extended",
            "repeatable": False,
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset_path = Path(temp_dir) / "transactional_action.jsonl"
            dataset_path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")
            samples = MODULE.load_dataset_file(dataset_path)
        self.assertEqual(samples[0].benchmark_suite, "agent_extension")
        self.assertFalse(samples[0].repeatable)

    def test_pick_samples_all_unique_covers_all_and_non_repeatable_only_once(self) -> None:
        samples = [
            make_sample("s1"),
            make_sample("s2"),
            make_sample("fixed", repeatable=False, tags=["paper_only"]),
        ]
        first = MODULE.pick_samples(samples, 1, 7, selection_mode="all_unique", repeat=1)
        second = MODULE.pick_samples(samples, 1, 7, selection_mode="all_unique", repeat=2)
        self.assertEqual({sample.sample_id for sample in first}, {"s1", "s2", "fixed"})
        self.assertEqual({sample.sample_id for sample in second}, {"s1", "s2"})

    def test_pick_samples_sampled_shuffles_and_does_not_repeat_non_repeatable(self) -> None:
        samples = [
            make_sample("s1"),
            make_sample("s2"),
            make_sample("s3"),
            make_sample("s4"),
            make_sample("fixed", repeatable=False),
        ]
        selected = MODULE.pick_samples(samples, 7, 11, selection_mode="sampled", repeat=1)
        ids = [sample.sample_id for sample in selected]
        self.assertEqual(ids.count("fixed"), 1)
        self.assertEqual(set(ids[:5]), {"s1", "s2", "s3", "s4", "fixed"})
        self.assertNotEqual(ids[:4], ["s1", "s2", "s3", "s4"])

    def test_sample_allowed_for_profile_respects_paper_only(self) -> None:
        sample = make_sample("paper", tags=["paper_only"])
        self.assertFalse(MODULE.sample_allowed_for_profile(sample, "standard"))
        self.assertTrue(MODULE.sample_allowed_for_profile(sample, "paper"))

    def test_score_conversation_formats_primary_failure_reason(self) -> None:
        sample = make_sample(
            "format",
            expected={
                "required_card_types": [],
                "should_return_order_id": False,
                "allowed_order_ids": [],
                "min_response_chars": 20,
            },
        )
        status, technical_success, passed, flags = MODULE.score_conversation(
            sample=sample,
            turn_events=[make_turn_event(sample, response_text="̫��")],
            unsupported=False,
        )
        self.assertEqual(status, "fail")
        self.assertTrue(technical_success)
        self.assertFalse(passed)
        self.assertTrue(flags["format_error"])
        self.assertEqual(flags["primary_failure_reason"], "format_error")

    def test_score_conversation_supported_failure_always_has_primary_reason(self) -> None:
        sample = make_sample("tech")
        status, _, passed, flags = MODULE.score_conversation(
            sample=sample,
            turn_events=[make_turn_event(sample, success=False, response_text="")],
            unsupported=False,
        )
        self.assertEqual(status, "fail")
        self.assertFalse(passed)
        self.assertEqual(flags["primary_failure_reason"], "technical_failure")

    def test_score_conversation_unsupported_maps_to_na_and_reason(self) -> None:
        sample = make_sample("unsupported", benchmark_suite="agent_extension")
        status, technical_success, passed, flags = MODULE.score_conversation(sample=sample, turn_events=[], unsupported=True)
        self.assertEqual(status, "na")
        self.assertFalse(technical_success)
        self.assertFalse(passed)
        self.assertEqual(flags["primary_failure_reason"], "unsupported")

    def test_build_conversation_summary_rows_exports_new_failure_fields(self) -> None:
        event = MODULE.ConversationEvent(
            timestamp="",
            system="rasa_plus_llm",
            scenario_family="order_query",
            scenario="query_order",
            sample_id="s1",
            benchmark_suite="shared_core",
            tier="extended",
            repeat=1,
            concurrency=1,
            conversation_index=1,
            account="customer",
            layer="business",
            score_profile="structured_business",
            required_capabilities=["supports_auth_queries"],
            turn_count=1,
            executed_turns=1,
            unsupported=False,
            success=False,
            http_error_count=1,
            latency_ms=12.0,
            started_at=1.0,
            finished_at=1.1,
            quality_status="fail",
            conversation_success=False,
            passed=False,
            quality_flags={
                "supported": True,
                "technical_failure": True,
                "format_error": False,
                "primary_failure_reason": "technical_failure",
            },
        )
        rows = MODULE.build_conversation_summary_rows([event])
        self.assertTrue(rows[0]["technical_failure"])
        self.assertFalse(rows[0]["format_error"])
        self.assertEqual(rows[0]["primary_failure_reason"], "technical_failure")

    def test_score_conversation_formats_primary_failure_reason(self) -> None:
        sample = make_sample(
            "format_override",
            expected={
                "required_any_text_keywords": [],
                "required_card_types": [],
                "should_return_order_id": False,
                "allowed_order_ids": [],
                "min_response_chars": 20,
            },
        )
        status, technical_success, passed, flags = MODULE.score_conversation(
            sample=sample,
            turn_events=[make_turn_event(sample, response_text="short")],
            unsupported=False,
        )
        self.assertEqual(status, "fail")
        self.assertTrue(technical_success)
        self.assertFalse(passed)
        self.assertTrue(flags["format_error"])
        self.assertEqual(flags["primary_failure_reason"], "format_error")


class ExecuteBenchmarkTests(unittest.IsolatedAsyncioTestCase):
    async def test_execute_benchmark_writes_selection_mode_and_run_metadata(self) -> None:
        captured_kwargs: dict[str, Any] = {}

        class RecordingAsyncClient:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                captured_kwargs.update(kwargs)

            async def __aenter__(self) -> "RecordingAsyncClient":
                return self

            async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
                return None

        async def fake_seed_knowledge_for_system(*args: Any, **kwargs: Any) -> None:
            return None

        async def fake_warmup_system(*args: Any, **kwargs: Any) -> None:
            return None

        async def fake_execute_batch(*args: Any, **kwargs: Any) -> tuple[list[MODULE.ConversationEvent], list[MODULE.TurnEvent]]:
            return [], []

        system = MODULE.SystemTarget(
            name="rasa_plus_llm",
            kind="backend_chat",
            base_url="http://127.0.0.1:8000",
            path="/api/v1/chat/send",
            model="backend",
            auth_mode="bearer",
            sender_id="benchmark-rasa-plus-llm",
            upload_path="/api/v1/chat/upload-image",
            pending_action_path="/api/v1/chat/pending-action",
            login_url="/api/v1/auth/login",
            me_url="/api/v1/auth/me",
            capabilities={},
        )
        auth_cfg = MODULE.AuthConfig(
            login_url="/api/v1/auth/login",
            me_url="/api/v1/auth/me",
            customer_email="customer@example.com",
            customer_password="customer-password",
            merchant_email="merchant@example.com",
            merchant_password="merchant-password",
        )
        sample = make_sample("s1", scenario_family="recommendation", scenario="basic")
        config = {
            "profiles": {
                "standard": {
                    "dataset_tier": "extended",
                    "selection_mode": "all_unique",
                    "scenarios": ["recommendation"],
                    "concurrency": [1],
                    "requests_per_level": 6,
                    "repeats": 1,
                }
            },
            "timeout_sec": 12,
            "warmup_requests": 0,
            "seed": 20260412,
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            args = argparse.Namespace(
                systems="",
                scenarios="recommendation",
                profile="standard",
                config=temp_path / "experiment.yaml",
                dataset=None,
                dataset_tier="",
                results_root=temp_path,
                requests_per_level=None,
                repeats=None,
                concurrency="",
                timeout_sec=None,
                warmup_requests=None,
                seed=None,
                verbose=False,
            )
            with (
                patch("builtins.print"),
                patch.object(MODULE, "load_config", return_value=config),
                patch.object(MODULE, "resolve_auth_config", return_value=auth_cfg),
                patch.object(MODULE, "resolve_system_targets", return_value={"rasa_plus_llm": system}),
                patch.object(MODULE, "resolve_dataset_files", return_value={"recommendation": temp_path / "recommendation.jsonl"}),
                patch.object(MODULE, "load_dataset_file", return_value=[sample]),
                patch.object(MODULE, "collect_prompt_versions", return_value=[]),
                patch.object(MODULE, "seed_knowledge_for_system", new=fake_seed_knowledge_for_system),
                patch.object(MODULE, "warmup_system", new=fake_warmup_system),
                patch.object(MODULE, "execute_batch", new=fake_execute_batch),
                patch.object(MODULE.httpx, "AsyncClient", RecordingAsyncClient),
            ):
                output_dir = await MODULE.execute_benchmark(args)

            metadata = json.loads((output_dir / "run_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["selection_mode"], "all_unique")
            self.assertEqual(metadata["dataset_tier"], "extended")
            self.assertEqual(metadata["expected_samples"][0]["sample_id"], "s1")

        self.assertIs(captured_kwargs["trust_env"], False)
        self.assertEqual(captured_kwargs["timeout"], 12.0)


if __name__ == "__main__":
    unittest.main()
