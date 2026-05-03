from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
APP_DIR = BACKEND_DIR / "app"

backend_pkg = types.ModuleType("backend")
backend_pkg.__path__ = [str(BACKEND_DIR)]
app_pkg = types.ModuleType("backend.app")
app_pkg.__path__ = [str(APP_DIR)]
sys.modules.setdefault("backend", backend_pkg)
sys.modules.setdefault("backend.app", app_pkg)

pil_module = types.ModuleType("PIL")
pil_image_module = types.ModuleType("PIL.Image")
pil_module.Image = pil_image_module
sys.modules.setdefault("PIL", pil_module)
sys.modules.setdefault("PIL.Image", pil_image_module)

MAIN_SPEC = importlib.util.spec_from_file_location("backend.app.main", APP_DIR / "main.py")
MAIN_MODULE = importlib.util.module_from_spec(MAIN_SPEC)
assert MAIN_SPEC and MAIN_SPEC.loader
sys.modules["backend.app.main"] = MAIN_MODULE
MAIN_SPEC.loader.exec_module(MAIN_MODULE)


def make_customer_user() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        role="customer",
        email="customer@example.com",
        username="测试用户",
    )


class ChatRouterLogicTests(unittest.IsolatedAsyncioTestCase):
    def test_kb_index_item_accepts_metadata_alias_without_sqlmodel_shadowing(self) -> None:
        models_module = sys.modules["backend.app.models"]
        item = models_module.KBIndexItem(
            source_type="manual",
            title="Shipping policy",
            content="Orders ship within 48 hours.",
            metadata={"section": "logistics"},
        )

        self.assertEqual(item.metadata_, {"section": "logistics"})

    def test_extract_address_accepts_natural_marker(self) -> None:
        self.assertEqual(
            MAIN_MODULE.extract_address_from_message("帮我下单，地址为上海电力大学"),
            "上海电力大学",
        )
        self.assertEqual(
            MAIN_MODULE.extract_address_from_message("修改地址 ORD202604010001 收货地址是上海市浦东新区世纪大道200号"),
            "上海市浦东新区世纪大道200号",
        )

    async def test_business_intent_high_review_uses_rasa(self) -> None:
        rasa_messages = [MAIN_MODULE.build_chat_message("规则链路回复")]
        review = MAIN_MODULE.RasaIntentReviewResult(
            confidence=0.96,
            route="rule",
            intent_match=True,
            reason="intent_clear_and_rule_safe",
        )

        with (
            patch.object(MAIN_MODULE, "get_current_db_user_optional", new=AsyncMock(return_value=None)),
            patch.object(MAIN_MODULE, "validate_chat_attachments", new=AsyncMock(return_value=None)),
            patch.object(MAIN_MODULE, "handle_chat_transaction_action", new=AsyncMock(return_value=None)),
            patch.object(MAIN_MODULE, "parse_rasa_intent", new=AsyncMock(return_value=("ask_order_help", 0.93))),
            patch.object(MAIN_MODULE, "review_rasa_business_intent", new=AsyncMock(return_value=review)),
            patch.object(MAIN_MODULE, "call_rasa_webhook", new=AsyncMock(return_value=rasa_messages)) as call_rasa,
            patch.object(MAIN_MODULE, "run_nexau_agent_orchestrator", new=AsyncMock()) as run_agent,
            patch.object(MAIN_MODULE, "infer_message_domains", return_value={"order"}),
            patch.object(MAIN_MODULE, "is_complex_query", return_value=False),
        ):
            response = await MAIN_MODULE.chat_send(
                MAIN_MODULE.ChatSendRequest(message="订单 ORD202603300001 现在是什么状态"),
                object(),
                session=object(),
            )

        self.assertEqual(response.messages[0].text, "规则链路回复")
        call_rasa.assert_awaited_once()
        run_agent.assert_not_awaited()

    async def test_business_intent_low_review_uses_agent(self) -> None:
        review = MAIN_MODULE.RasaIntentReviewResult(
            confidence=0.62,
            route="agent",
            intent_match=False,
            reason="needs_semantic_disambiguation",
        )
        agent_reply = MAIN_MODULE.build_chat_message("Agent 复核后处理")

        with (
            patch.object(MAIN_MODULE, "get_current_db_user_optional", new=AsyncMock(return_value=None)),
            patch.object(MAIN_MODULE, "validate_chat_attachments", new=AsyncMock(return_value=None)),
            patch.object(MAIN_MODULE, "handle_chat_transaction_action", new=AsyncMock(return_value=None)),
            patch.object(MAIN_MODULE, "parse_rasa_intent", new=AsyncMock(return_value=("ask_product_recommendation", 0.95))),
            patch.object(MAIN_MODULE, "review_rasa_business_intent", new=AsyncMock(return_value=review)),
            patch.object(MAIN_MODULE, "call_rasa_webhook", new=AsyncMock()) as call_rasa,
            patch.object(
                MAIN_MODULE,
                "run_nexau_agent_orchestrator",
                new=AsyncMock(return_value=(agent_reply, [])),
            ) as run_agent,
            patch.object(MAIN_MODULE, "infer_message_domains", return_value={"product"}),
            patch.object(MAIN_MODULE, "is_complex_query", return_value=False),
        ):
            response = await MAIN_MODULE.chat_send(
                MAIN_MODULE.ChatSendRequest(message="推荐一台白色 27 寸显示器"),
                object(),
                session=object(),
            )

        self.assertEqual(response.messages[0].text, "Agent 复核后处理")
        run_agent.assert_awaited_once()
        call_rasa.assert_not_awaited()

    async def test_light_intent_skips_business_review(self) -> None:
        rasa_messages = [MAIN_MODULE.build_chat_message("你好，我是客服助手。")]

        with (
            patch.object(MAIN_MODULE, "get_current_db_user_optional", new=AsyncMock(return_value=None)),
            patch.object(MAIN_MODULE, "validate_chat_attachments", new=AsyncMock(return_value=None)),
            patch.object(MAIN_MODULE, "handle_chat_transaction_action", new=AsyncMock(return_value=None)),
            patch.object(MAIN_MODULE, "parse_rasa_intent", new=AsyncMock(return_value=("greet", 0.99))),
            patch.object(MAIN_MODULE, "review_rasa_business_intent", new=AsyncMock(side_effect=AssertionError("should not review"))) as review_mock,
            patch.object(MAIN_MODULE, "call_rasa_webhook", new=AsyncMock(return_value=rasa_messages)) as call_rasa,
            patch.object(MAIN_MODULE, "run_nexau_agent_orchestrator", new=AsyncMock()) as run_agent,
            patch.object(MAIN_MODULE, "infer_message_domains", return_value=set()),
            patch.object(MAIN_MODULE, "is_complex_query", return_value=False),
        ):
            response = await MAIN_MODULE.chat_send(
                MAIN_MODULE.ChatSendRequest(message="你好"),
                object(),
                session=object(),
            )

        self.assertEqual(response.messages[0].text, "你好，我是客服助手。")
        review_mock.assert_not_awaited()
        call_rasa.assert_awaited_once()
        run_agent.assert_not_awaited()

    async def test_transactional_action_preempts_rasa_review(self) -> None:
        transaction_reply = MAIN_MODULE.build_chat_message("已生成待确认操作")

        with (
            patch.object(MAIN_MODULE, "get_current_db_user_optional", new=AsyncMock(return_value=make_customer_user())),
            patch.object(MAIN_MODULE, "validate_chat_attachments", new=AsyncMock(return_value=None)),
            patch.object(MAIN_MODULE, "handle_chat_transaction_action", new=AsyncMock(return_value=transaction_reply)) as action_mock,
            patch.object(MAIN_MODULE, "parse_rasa_intent", new=AsyncMock(side_effect=AssertionError("should not parse"))),
            patch.object(MAIN_MODULE, "review_rasa_business_intent", new=AsyncMock(side_effect=AssertionError("should not review"))),
        ):
            response = await MAIN_MODULE.chat_send(
                MAIN_MODULE.ChatSendRequest(message="帮我取消订单 ORD202603300001"),
                object(),
                session=object(),
            )

        self.assertEqual(response.messages[0].text, "已生成待确认操作")
        action_mock.assert_awaited_once()

    async def test_review_exception_falls_back_to_default_rule_route(self) -> None:
        rasa_messages = [MAIN_MODULE.build_chat_message("物流信息稍后展示")]

        with (
            patch.object(MAIN_MODULE, "get_current_db_user_optional", new=AsyncMock(return_value=None)),
            patch.object(MAIN_MODULE, "validate_chat_attachments", new=AsyncMock(return_value=None)),
            patch.object(MAIN_MODULE, "handle_chat_transaction_action", new=AsyncMock(return_value=None)),
            patch.object(MAIN_MODULE, "parse_rasa_intent", new=AsyncMock(return_value=("ask_shipping_help", 0.97))),
            patch.object(MAIN_MODULE, "review_rasa_business_intent", new=AsyncMock(side_effect=RuntimeError("review down"))),
            patch.object(MAIN_MODULE, "call_rasa_webhook", new=AsyncMock(return_value=rasa_messages)) as call_rasa,
            patch.object(MAIN_MODULE, "run_nexau_agent_orchestrator", new=AsyncMock()) as run_agent,
            patch.object(MAIN_MODULE, "infer_message_domains", return_value={"logistics"}),
            patch.object(MAIN_MODULE, "is_complex_query", return_value=False),
        ):
            response = await MAIN_MODULE.chat_send(
                MAIN_MODULE.ChatSendRequest(message="帮我查一下订单 ORD202603300002 的物流"),
                object(),
                session=object(),
            )

        self.assertEqual(response.messages[0].text, "物流信息稍后展示")
        call_rasa.assert_awaited_once()
        run_agent.assert_not_awaited()

    async def test_low_review_agent_failure_does_not_fallback_to_rule(self) -> None:
        review = MAIN_MODULE.RasaIntentReviewResult(
            confidence=0.58,
            route="agent",
            intent_match=False,
            reason="mixed_constraints_require_agent",
        )

        with (
            patch.object(MAIN_MODULE, "get_current_db_user_optional", new=AsyncMock(return_value=None)),
            patch.object(MAIN_MODULE, "validate_chat_attachments", new=AsyncMock(return_value=None)),
            patch.object(MAIN_MODULE, "handle_chat_transaction_action", new=AsyncMock(return_value=None)),
            patch.object(MAIN_MODULE, "parse_rasa_intent", new=AsyncMock(return_value=("ask_product_recommendation", 0.94))),
            patch.object(MAIN_MODULE, "review_rasa_business_intent", new=AsyncMock(return_value=review)),
            patch.object(MAIN_MODULE, "call_rasa_webhook", new=AsyncMock(side_effect=AssertionError("should not fallback to rasa"))) as call_rasa,
            patch.object(
                MAIN_MODULE,
                "run_nexau_agent_orchestrator",
                new=AsyncMock(side_effect=RuntimeError("agent down")),
            ) as run_agent,
            patch.object(MAIN_MODULE, "infer_message_domains", return_value={"product"}),
            patch.object(MAIN_MODULE, "is_complex_query", return_value=False),
        ):
            response = await MAIN_MODULE.chat_send(
                MAIN_MODULE.ChatSendRequest(message="推荐一台适合游戏也适合剪视频的白色显示器"),
                object(),
                session=object(),
            )

        self.assertIn("进一步语义判断", response.messages[0].text)
        run_agent.assert_awaited_once()
        call_rasa.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
