from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from benchmark import runner as MODULE  # noqa: E402


def make_sample(
    *,
    scenario_family: str = "order_query",
    scenario: str = "query_order",
    account: str = "customer",
    required_capabilities: list[str] | None = None,
    expected: dict | None = None,
) -> MODULE.ConversationSample:
    return MODULE.ConversationSample(
        sample_id="sample-1",
        scenario_family=scenario_family,
        scenario=scenario,
        turns=[
            MODULE.TurnStep(turn_id="login", kind="login"),
            MODULE.TurnStep(turn_id="chat", kind="chat_send", message="查询订单 ORD202603300001"),
        ],
        account=account,
        required_capabilities=required_capabilities or ["supports_auth_queries", "supports_cards"],
        preconditions={"allowed_order_ids": ["ORD202603300001"]},
        expected_outcomes=MODULE.ExpectedOutcomes(
            required_any_text_keywords=["订单", "状态"],
            forbidden_text_keywords=[],
            required_card_types=["order"],
            required_action_types=[],
            requires_confirmation_buttons=False,
            should_return_order_id=True,
            should_block_without_login=False,
            should_be_unsupported=False,
            must_avoid_hallucinated_order_id=True,
            allowed_order_ids=["ORD202603300001"],
            min_response_chars=8,
        )
        if expected is None
        else MODULE.ExpectedOutcomes(**expected),
        tags=["test"],
        tier="core",
        repeatable=True,
        layer="business",
        score_profile="structured_business",
    )


def make_turn_event(
    *,
    sample: MODULE.ConversationSample,
    turn_id: str,
    turn_kind: str,
    success: bool = True,
    unsupported: bool = False,
    response_text: str = "",
    response_card_types: list[str] | None = None,
    response_action_types: list[str] | None = None,
    response_order_ids: list[str] | None = None,
) -> MODULE.TurnEvent:
    return MODULE.TurnEvent(
        timestamp="",
        system="rasa_plus_llm",
        scenario_family=sample.scenario_family,
        scenario=sample.scenario,
        sample_id=sample.sample_id,
        tier=sample.tier,
        repeat=1,
        concurrency=1,
        conversation_index=1,
        turn_index=1,
        turn_id=turn_id,
        turn_kind=turn_kind,
        requires_auth=sample.account == "customer",
        required_capabilities=list(sample.required_capabilities),
        executed=not unsupported,
        unsupported=unsupported,
        success=success,
        http_status=200 if success else None,
        error_type="" if success else "runtime_error",
        error_message="",
        latency_ms=10.0,
        started_at=1.0,
        finished_at=1.1,
        response_text=response_text,
        response_chars=len(response_text),
        response_card_count=len(response_card_types or []),
        response_action_count=len(response_action_types or []),
        response_card_types=response_card_types or [],
        response_action_types=response_action_types or [],
        response_order_ids=response_order_ids or [],
    )


class BenchmarkRunnerTests(unittest.TestCase):
    def test_load_dataset_file_parses_conversation_model(self) -> None:
        payload = {
            "id": "conversation-1",
            "scenario_family": "transactional_action",
            "scenario": "update_shipping_confirm",
            "turns": [
                {"id": "login", "kind": "login"},
                {"id": "draft", "kind": "chat_send", "message": "帮我修改订单 ORD202603300001 的地址"},
                {"id": "confirm", "kind": "pending_decision", "decision": "confirm"},
            ],
            "account": "customer",
            "required_capabilities": ["supports_pending_action", "supports_pending_decision"],
            "preconditions": {"allowed_order_ids": ["ORD202603300001"]},
            "expected_outcomes": {
                "required_any_text_keywords": ["修改", "确认"],
                "forbidden_text_keywords": [],
                "required_card_types": ["pending_action", "order"],
                "required_action_types": ["pending_action_decision"],
                "requires_confirmation_buttons": True,
                "should_return_order_id": True,
                "should_block_without_login": False,
                "should_be_unsupported": False,
                "must_avoid_hallucinated_order_id": True,
                "allowed_order_ids": ["ORD202603300001"],
                "min_response_chars": 8,
            },
            "tags": ["core"],
            "tier": "core",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset_path = Path(temp_dir) / "transactional_action.jsonl"
            dataset_path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")
            samples = MODULE.load_dataset_file(dataset_path)
        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0].scenario_family, "transactional_action")
        self.assertEqual(samples[0].turns[2].kind, "pending_decision")
        self.assertTrue(samples[0].expected_outcomes.requires_confirmation_buttons)
        self.assertEqual(samples[0].layer, "boundary")

    def test_score_conversation_passes_with_required_cards_and_order_id(self) -> None:
        sample = make_sample()
        turn_events = [
            make_turn_event(sample=sample, turn_id="login", turn_kind="login"),
            make_turn_event(
                sample=sample,
                turn_id="chat",
                turn_kind="chat_send",
                response_text="订单 ORD202603300001 当前状态为待发货。",
                response_card_types=["order"],
                response_order_ids=["ORD202603300001"],
            ),
        ]
        status, conversation_success, passed, flags = MODULE.score_conversation(
            sample=sample,
            turn_events=turn_events,
            unsupported=False,
        )
        self.assertEqual(status, "pass")
        self.assertTrue(conversation_success)
        self.assertTrue(passed)
        self.assertFalse(flags["missing_required_cards"])

    def test_score_conversation_detects_login_block_failure(self) -> None:
        sample = make_sample(
            scenario_family="order_query",
            scenario="login_required",
            account="anonymous",
            required_capabilities=["supports_auth_queries"],
            expected={
                "required_any_text_keywords": ["请先登录"],
                "forbidden_text_keywords": [],
                "required_card_types": [],
                "required_action_types": [],
                "requires_confirmation_buttons": False,
                "should_return_order_id": False,
                "should_block_without_login": True,
                "should_be_unsupported": False,
                "must_avoid_hallucinated_order_id": True,
                "allowed_order_ids": [],
                "min_response_chars": 8,
            },
        )
        turn_events = [
            make_turn_event(
                sample=sample,
                turn_id="chat",
                turn_kind="chat_send",
                response_text="我直接帮你查到了最新订单。",
                response_order_ids=[],
            )
        ]
        status, conversation_success, passed, flags = MODULE.score_conversation(
            sample=sample,
            turn_events=turn_events,
            unsupported=False,
        )
        self.assertEqual(status, "fail")
        self.assertTrue(conversation_success)
        self.assertFalse(passed)
        self.assertTrue(flags["login_block_failure"])

    def test_score_conversation_unsupported_is_na(self) -> None:
        sample = make_sample(required_capabilities=["supports_kb_manual"])
        status, conversation_success, passed, flags = MODULE.score_conversation(
            sample=sample,
            turn_events=[],
            unsupported=True,
        )
        self.assertEqual(status, "na")
        self.assertFalse(conversation_success)
        self.assertFalse(passed)
        self.assertFalse(flags["supported"])

    def test_summary_rows_track_unsupported_and_success_rate(self) -> None:
        supported_event = MODULE.ConversationEvent(
            timestamp="",
            system="rasa_plus_llm",
            scenario_family="knowledge_and_multimodal",
            scenario="manual_query",
            sample_id="s1",
            tier="core",
            repeat=1,
            concurrency=1,
            conversation_index=1,
            account="anonymous",
            layer="boundary",
            score_profile="boundary_safe",
            required_capabilities=["supports_kb_manual"],
            turn_count=1,
            executed_turns=1,
            unsupported=False,
            success=True,
            http_error_count=0,
            latency_ms=100.0,
            started_at=1.0,
            finished_at=1.1,
            quality_status="pass",
            conversation_success=True,
            passed=True,
            quality_flags={"supported": True},
        )
        unsupported_event = MODULE.ConversationEvent(
            timestamp="",
            system="rasa_plus_llm",
            scenario_family="knowledge_and_multimodal",
            scenario="manual_query",
            sample_id="s2",
            tier="core",
            repeat=1,
            concurrency=1,
            conversation_index=2,
            account="anonymous",
            layer="boundary",
            score_profile="boundary_safe",
            required_capabilities=["supports_kb_manual"],
            turn_count=1,
            executed_turns=0,
            unsupported=True,
            success=False,
            http_error_count=0,
            latency_ms=0.0,
            started_at=1.2,
            finished_at=1.2,
            quality_status="na",
            conversation_success=False,
            passed=False,
            quality_flags={"supported": False},
        )
        rows = MODULE.build_summary_rows([supported_event, unsupported_event])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["unsupported_rate"], 0.5)
        self.assertEqual(rows[0]["conversation_success_rate"], 1.0)
        self.assertEqual(rows[0]["boundary_safety_pass_rate"], 1.0)

    def test_capability_coverage_rows(self) -> None:
        event_1 = MODULE.ConversationEvent(
            timestamp="",
            system="rasa_plus_llm",
            scenario_family="after_sales_query",
            scenario="policy",
            sample_id="s1",
            tier="core",
            repeat=1,
            concurrency=1,
            conversation_index=1,
            account="anonymous",
            layer="business",
            score_profile="structured_business",
            required_capabilities=["supports_kb_policy"],
            turn_count=1,
            executed_turns=1,
            unsupported=False,
            success=True,
            http_error_count=0,
            latency_ms=80.0,
            started_at=1.0,
            finished_at=1.08,
            quality_status="pass",
            conversation_success=True,
            passed=True,
            quality_flags={},
        )
        event_2 = MODULE.ConversationEvent(
            timestamp="",
            system="rasa_plus_llm",
            scenario_family="knowledge_and_multimodal",
            scenario="manual",
            sample_id="s2",
            tier="core",
            repeat=1,
            concurrency=1,
            conversation_index=2,
            account="anonymous",
            layer="boundary",
            score_profile="boundary_safe",
            required_capabilities=["supports_kb_policy"],
            turn_count=1,
            executed_turns=0,
            unsupported=True,
            success=False,
            http_error_count=0,
            latency_ms=0.0,
            started_at=2.0,
            finished_at=2.0,
            quality_status="na",
            conversation_success=False,
            passed=False,
            quality_flags={},
        )
        rows = MODULE.build_capability_coverage_rows([event_1, event_2])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["capability"], "supports_kb_policy")
        self.assertEqual(rows[0]["support_rate"], 0.5)

    def test_system_matrix_contains_family_metrics(self) -> None:
        event = MODULE.ConversationEvent(
            timestamp="",
            system="rasa_plus_lora_llm",
            scenario_family="transactional_action",
            scenario="confirm",
            sample_id="s1",
            tier="core",
            repeat=1,
            concurrency=1,
            conversation_index=1,
            account="customer",
            layer="boundary",
            score_profile="boundary_safe",
            required_capabilities=["supports_pending_action"],
            turn_count=3,
            executed_turns=3,
            unsupported=False,
            success=True,
            http_error_count=0,
            latency_ms=120.0,
            started_at=1.0,
            finished_at=1.12,
            quality_status="pass",
            conversation_success=True,
            passed=True,
            quality_flags={},
        )
        rows = MODULE.build_system_matrix([event], ["transactional_action"])
        self.assertEqual(len(rows), 1)
        self.assertIn("transactional_action_quality_pass_rate", rows[0])
        self.assertEqual(rows[0]["transactional_action_conversation_success_rate"], 1.0)
        self.assertEqual(rows[0]["boundary_safety_pass_rate"], 1.0)


class SeedKnowledgeTests(unittest.IsolatedAsyncioTestCase):
    async def test_seed_knowledge_wraps_document_in_items_payload(self) -> None:
        class RecordingResponse:
            status_code = 200
            text = ""

            def raise_for_status(self) -> None:
                return None

        class RecordingClient:
            def __init__(self) -> None:
                self.calls: list[dict[str, Any]] = []

            async def post(self, url: str, json: dict[str, Any], headers: dict[str, str]) -> RecordingResponse:
                self.calls.append({"url": url, "json": json, "headers": headers})
                return RecordingResponse()

        async def fake_login_for_auth_context(*args: Any, **kwargs: Any) -> MODULE.AuthContext:
            return MODULE.AuthContext(token="merchant-token")

        system = MODULE.SystemTarget(
            name="rasa_plus_llm",
            kind="backend_chat",
            base_url="http://127.0.0.1:8000",
            path="/api/v1/chat/send",
            model="backend",
            auth_mode="bearer",
            sender_id="benchmark-user",
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
        with tempfile.TemporaryDirectory() as temp_dir:
            knowledge_path = Path(temp_dir) / "after_sales_policy.md"
            knowledge_path.write_text("# after sales policy\nseven day return.", encoding="utf-8")
            config = {
                "knowledge_seed": {
                    "index_path": "/api/v1/kb/index",
                    "documents": [
                        {
                            "source_type": "policy",
                            "title": "after_sales_policy",
                            "path": str(knowledge_path),
                            "version": "benchmark-v1",
                            "status": "active",
                            "metadata": {"category": "after_sales"},
                        }
                    ],
                }
            }
            client = RecordingClient()
            original_login = MODULE.login_for_auth_context
            MODULE.login_for_auth_context = fake_login_for_auth_context
            try:
                await MODULE.seed_knowledge_for_system(client, system, auth_cfg, config)
            finally:
                MODULE.login_for_auth_context = original_login

        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.calls[0]["url"], "http://127.0.0.1:8000/api/v1/kb/index")
        self.assertEqual(client.calls[0]["headers"], {"Authorization": "Bearer merchant-token"})
        self.assertIn("items", client.calls[0]["json"])
        self.assertEqual(len(client.calls[0]["json"]["items"]), 1)
        item = client.calls[0]["json"]["items"][0]
        self.assertEqual(item["source_type"], "policy")
        self.assertEqual(item["title"], "after_sales_policy")
        self.assertIn("seven day return", item["content"])
        self.assertEqual(item["version"], "benchmark-v1")
        self.assertEqual(item["status"], "active")
        self.assertEqual(item["metadata"], {"category": "after_sales"})


if __name__ == "__main__":
    unittest.main()
