from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

import httpx

ToolHandler = Callable[..., Awaitable[dict[str, Any]]]


@dataclass
class ToolDefinition:
    name: str
    mode: str
    description: str
    handler: ToolHandler


@dataclass
class ToolCallRecord:
    name: str
    mode: str
    args: dict[str, Any]
    success: bool
    error: str | None = None


@dataclass
class AgentExecutionResult:
    text: str
    cards: list[dict[str, Any]]
    actions: list[dict[str, Any]]
    tool_calls: list[ToolCallRecord]


def extract_order_id(message: str) -> str | None:
    match = re.search(r"(ORD\d{10,})", (message or "").upper())
    return match.group(1) if match else None


def extract_reason(message: str) -> str | None:
    text = (message or "").strip()
    if not text:
        return None
    for pattern in [r"(?:原因|理由)[:：]\s*(.+)$", r"(?:because|reason)[:：]?\s*(.+)$"]:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match and match.group(1).strip():
            return match.group(1).strip()
    return None


def infer_message_domains(message: str) -> set[str]:
    text = (message or "").strip()
    lowered = text.lower()
    domains: set[str] = set()

    if any(k in text for k in ["订单", "下单", "购买"]) or any(k in lowered for k in ["order", "checkout"]):
        domains.add("order")
    if any(k in text for k in ["物流", "快递", "运单", "发货"]) or any(
        k in lowered for k in ["shipment", "logistics", "tracking"]
    ):
        domains.add("logistics")
    if any(k in text for k in ["售后", "退款", "退货", "换货"]) or any(
        k in lowered for k in ["refund", "return", "exchange", "after-sales"]
    ):
        domains.add("after_sales")
    if any(k in text for k in ["商品", "推荐", "颜色", "尺码", "说明书", "报错"]) or any(
        k in lowered for k in ["product", "recommend", "color", "size", "manual"]
    ):
        domains.add("product")
    if any(k in text for k in ["补差价", "降价", "保价"]) or any(
        k in lowered for k in ["price protection", "price drop"]
    ):
        domains.add("price_protection")

    return domains


def is_complex_query(message: str) -> bool:
    text = (message or "").strip()
    if not text:
        return False

    domains = infer_message_domains(text)
    if len(domains) >= 2:
        return True

    lowered = text.lower()
    multi_intent_markers = ["或者", "还是", "并且", "同时", "另外", "顺便", "or ", " and "]
    if any(marker in lowered for marker in multi_intent_markers):
        return True

    conditional_markers = ["如果", "要是", "能不能", "是否可以", "怎么处理", "哪个更好"]
    return any(marker in text for marker in conditional_markers)


class NexAUAgentOrchestrator:
    """轻量 ReAct 风格编排器：本地工具规划 + LLM 汇总回答。"""

    def __init__(
        self,
        *,
        ollama_base_url: str,
        ollama_model: str,
        ollama_timeout_sec: float,
        frontend_base_url: str,
    ) -> None:
        self._ollama_base_url = ollama_base_url.rstrip("/")
        self._ollama_model = ollama_model
        self._ollama_timeout_sec = ollama_timeout_sec
        self._frontend_base_url = frontend_base_url.rstrip("/")
        self._tools: dict[str, ToolDefinition] = {}

    def register_tool(self, *, name: str, mode: str, description: str, handler: ToolHandler) -> None:
        normalized_mode = mode.strip().lower()
        if normalized_mode not in {"read", "write"}:
            raise ValueError(f"Unsupported tool mode: {mode}")
        self._tools[name] = ToolDefinition(
            name=name,
            mode=normalized_mode,
            description=description.strip(),
            handler=handler,
        )

    async def run(
        self,
        *,
        message: str,
        user_id: str,
        is_authenticated: bool,
        attachments: list[str] | None = None,
    ) -> AgentExecutionResult:
        normalized_attachments = [item for item in (attachments or []) if isinstance(item, str) and item.strip()]
        domains = infer_message_domains(message)
        tool_plan = self._build_tool_plan(
            message=message,
            user_id=user_id,
            domains=domains,
            is_authenticated=is_authenticated,
            attachments=normalized_attachments,
        )
        cards: list[dict[str, Any]] = []
        actions: list[dict[str, Any]] = []
        observations: list[dict[str, Any]] = []
        tool_calls: list[ToolCallRecord] = []

        if not is_authenticated and domains.intersection({"order", "logistics", "after_sales", "price_protection"}):
            text = (
                "这类问题需要先登录后才能查询你的订单与售后数据。\n"
                f"请先登录：{self._frontend_base_url}/login"
            )
            return AgentExecutionResult(text=text, cards=[], actions=[], tool_calls=[])

        for step in tool_plan:
            tool_name = step["name"]
            args = step["args"]
            tool = self._tools.get(tool_name)
            if not tool:
                tool_calls.append(
                    ToolCallRecord(name=tool_name, mode="read", args=args, success=False, error="tool not found")
                )
                continue

            try:
                result = await tool.handler(**args)
                result_cards = result.get("cards")
                result_actions = result.get("actions")
                result_observation = result.get("observation")
                if isinstance(result_cards, list):
                    cards.extend([item for item in result_cards if isinstance(item, dict)])
                if isinstance(result_actions, list):
                    actions.extend([item for item in result_actions if isinstance(item, dict)])
                if isinstance(result_observation, dict):
                    observations.append(
                        {
                            "tool": tool_name,
                            "mode": tool.mode,
                            "output": result_observation,
                        }
                    )
                tool_calls.append(ToolCallRecord(name=tool_name, mode=tool.mode, args=args, success=True))
            except Exception as exc:  # noqa: BLE001
                tool_calls.append(
                    ToolCallRecord(name=tool_name, mode=tool.mode, args=args, success=False, error=str(exc))
                )

        text = await self._generate_final_answer(message=message, observations=observations)
        if not text:
            text = self._fallback_answer(message=message, observations=observations, domains=domains)
        return AgentExecutionResult(text=text, cards=cards, actions=actions, tool_calls=tool_calls)

    def _build_tool_plan(
        self,
        *,
        message: str,
        user_id: str,
        domains: set[str],
        is_authenticated: bool,
        attachments: list[str],
    ) -> list[dict[str, Any]]:
        plan: list[dict[str, Any]] = []
        seen_keys: set[str] = set()

        def add_step(name: str, args: dict[str, Any]) -> None:
            key = f"{name}:{json.dumps(args, ensure_ascii=False, sort_keys=True)}"
            if key in seen_keys:
                return
            seen_keys.add(key)
            plan.append({"name": name, "args": args})

        has_policy_keywords = any(k in message for k in ["政策", "规则", "条款", "补差价", "保价", "退货"]) or (
            "price_protection" in domains
        )
        has_manual_keywords = any(k in message for k in ["说明书", "报错", "故障", "安装", "使用"]) or ("product" in domains)

        if has_policy_keywords or "after_sales" in domains:
            add_step("retrieve_policy_knowledge", {"query": message or "售后政策"})
        if has_manual_keywords:
            add_step("retrieve_manual_knowledge", {"query": message or "商品说明书"})

        if attachments:
            for attachment_id in attachments:
                add_step("analyze_uploaded_image_vlm", {"attachment_id": attachment_id})
            add_step("retrieve_manual_knowledge", {"query": message or "图片问题诊断"})

        if "order" in domains and is_authenticated:
            add_step("query_orders_summary", {"user_id": user_id, "limit": 5})
        if "logistics" in domains and is_authenticated:
            order_id = extract_order_id(message)
            add_step("query_logistics_summary", {"user_id": user_id, "order_id": order_id, "limit": 5})
        if "after_sales" in domains and is_authenticated:
            add_step("query_after_sales_summary", {"user_id": user_id, "limit": 5})
        if "price_protection" in domains and is_authenticated:
            add_step("query_price_protection", {"user_id": user_id})

        should_draft_after_sales = (
            "after_sales" in domains
            and is_authenticated
            and any(marker in message for marker in ["申请", "发起", "提交", "帮我", "给我"])
        )
        if should_draft_after_sales:
            order_id = extract_order_id(message)
            reason = extract_reason(message)
            request_type = "exchange" if "换货" in message else "return"
            if order_id and reason:
                add_step(
                    "draft_after_sales_request",
                    {"order_id": order_id, "request_type": request_type, "reason": reason},
                )

        return plan

    async def _generate_final_answer(self, *, message: str, observations: list[dict[str, Any]]) -> str:
        system_prompt = (
            "你是电商客服复杂问题处理 Agent。"
            "请基于工具观测结果给出简洁中文结论，不要编造订单、物流、售后、政策或图片识别结果。"
            "当观测不足时，请明确说出缺少的信息。"
        )
        user_payload = {
            "user_message": message,
            "tool_observations": observations,
        }
        try:
            async with httpx.AsyncClient(timeout=self._ollama_timeout_sec) as client:
                response = await client.post(
                    f"{self._ollama_base_url}/api/chat",
                    json={
                        "model": self._ollama_model,
                        "stream": False,
                        "options": {"temperature": 0.2},
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
                        ],
                    },
                )
            response.raise_for_status()
            payload = response.json()
            content = payload.get("message", {}).get("content", "") if isinstance(payload, dict) else ""
            if isinstance(content, str):
                return content.strip()
        except Exception:  # noqa: BLE001
            return ""
        return ""

    def _fallback_answer(self, *, message: str, observations: list[dict[str, Any]], domains: set[str]) -> str:
        if not observations:
            return "我已切入复杂问题处理模式，但当前缺少可执行信息。请补充订单号、具体诉求或上传图片后再试。"

        if "price_protection" in domains and "after_sales" in domains:
            return "我已查询相关信息。如需继续处理补差价或退换货，我可以先生成待确认草案，确认后再执行。"

        if any(item.get("tool") == "analyze_uploaded_image_vlm" for item in observations):
            return "我已完成图片分析并给出建议，可继续为你生成售后待确认草案。"

        return "我已完成复杂问题查询，请查看上方结果；如果你要继续执行操作，我可以先生成待确认草案。"
