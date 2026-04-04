import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

RASA_DIR = Path(__file__).resolve().parent.parent
load_dotenv(RASA_DIR / ".env")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_CHAT_PATH = os.getenv("OLLAMA_CHAT_PATH", "/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:9b")
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://127.0.0.1:8000/api/v1")
ACTION_HTTP_TIMEOUT_SEC = float(os.getenv("ACTION_HTTP_TIMEOUT_SEC", "20"))
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")
RASA_INTERNAL_TOKEN = os.getenv("RASA_INTERNAL_TOKEN", "")

SYSTEM_PROMPT = (
    "你是电商平台智能客服助手。"
    "请使用简洁、友好的中文回答。"
    "不要编造订单数据或物流状态；如果用户需要订单明细，请提示其提供订单号。"
)


def _safe_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _build_context(tracker: Tracker) -> str:
    lines: list[str] = []
    for event in tracker.events[-10:]:
        event_type = event.get("event")
        if event_type == "user":
            text = _safe_text(event.get("text"))
            if text:
                lines.append(f"用户: {text}")
        elif event_type == "bot":
            text = _safe_text(event.get("text"))
            if text:
                lines.append(f"助手: {text}")
    return "\n".join(lines)


def _latest_metadata(tracker: Tracker) -> dict[str, Any]:
    metadata = tracker.latest_message.get("metadata")
    if isinstance(metadata, dict):
        return metadata
    return {}


class ActionOllamaReply(Action):
    def name(self) -> str:
        return "action_ollama_reply"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict[str, Any]) -> list[dict[str, Any]]:
        user_text = _safe_text(tracker.latest_message.get("text"))
        if not user_text:
            dispatcher.utter_message(text="我在的，你可以告诉我想咨询的内容。")
            return []

        context = _build_context(tracker)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if context:
            messages.append({"role": "system", "content": f"最近对话:\n{context}"})
        messages.append({"role": "user", "content": user_text})

        ollama_url = f"{OLLAMA_BASE_URL.rstrip('/')}/{OLLAMA_CHAT_PATH.lstrip('/')}"

        try:
            response = requests.post(
                ollama_url,
                json={
                    "model": OLLAMA_MODEL,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": 0.5,
                    },
                },
                timeout=ACTION_HTTP_TIMEOUT_SEC,
            )
            response.raise_for_status()
            payload = response.json()
            reply = _safe_text(payload.get("message", {}).get("content"))
            if not reply:
                reply = "我刚刚有点忙，请再说一次你的问题。"
        except requests.RequestException:
            reply = "本地大模型服务暂时不可用，请稍后再试。"

        dispatcher.utter_message(text=reply)
        return []


class ActionRecommendProducts(Action):
    def name(self) -> str:
        return "action_recommend_products"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict[str, Any]) -> list[dict[str, Any]]:
        category = _safe_text(tracker.get_slot("category"))
        metadata = _latest_metadata(tracker)
        frontend_base_url = _safe_text(metadata.get("frontend_base_url")) or FRONTEND_BASE_URL
        frontend_base_url = frontend_base_url.rstrip("/")

        params: dict[str, Any] = {
            "page": 1,
            "page_size": 5,
            "sort_by": "newest",
            "in_stock": True,
        }
        if category:
            params["category"] = category

        try:
            response = requests.get(
                f"{BACKEND_API_URL.rstrip('/')}/products",
                params=params,
                timeout=ACTION_HTTP_TIMEOUT_SEC,
            )
            response.raise_for_status()
            items = response.json().get("items", [])
        except requests.RequestException:
            dispatcher.utter_message(text="暂时无法读取商品数据，请稍后重试。")
            return []

        if not items:
            dispatcher.utter_message(text="暂时没有匹配的在售商品，你可以换个分类试试。")
            return []

        lines: list[str] = []
        for item in items:
            name = _safe_text(item.get("name")) or "未命名商品"
            cat = _safe_text(item.get("category")) or "未分类"
            price = float(item.get("price", 0))
            product_id = _safe_text(item.get("id"))
            if product_id:
                product_link = f"{frontend_base_url}/products/{product_id}"
                lines.append(f"- {name} | {cat} | ¥{price:.2f}\n  商品链接: {product_link}")
            else:
                lines.append(f"- {name} | {cat} | ¥{price:.2f}")

        prefix = "给你推荐这几款商品："
        if category:
            prefix = f"给你推荐几款 {category} 商品："
        dispatcher.utter_message(text=f"{prefix}\n" + "\n".join(lines))
        return []


class ActionQueryMyOrders(Action):
    def name(self) -> str:
        return "action_query_my_orders"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict[str, Any]) -> list[dict[str, Any]]:
        metadata = _latest_metadata(tracker)
        is_authenticated = bool(metadata.get("is_authenticated"))
        user_id = _safe_text(metadata.get("user_id"))
        frontend_base_url = _safe_text(metadata.get("frontend_base_url")) or FRONTEND_BASE_URL
        frontend_base_url = frontend_base_url.rstrip("/")

        if not is_authenticated or not user_id:
            dispatcher.utter_message(
                text=(
                    "你当前还没有登录账号，暂时无法读取你的订单。\n"
                    f"先去登录：{frontend_base_url}/login"
                )
            )
            return []

        headers: dict[str, str] = {}
        if RASA_INTERNAL_TOKEN.strip():
            headers["X-Rasa-Token"] = RASA_INTERNAL_TOKEN.strip()

        try:
            response = requests.get(
                f"{BACKEND_API_URL.rstrip('/')}/chat/internal/orders-summary",
                params={"user_id": user_id, "limit": 5},
                headers=headers,
                timeout=ACTION_HTTP_TIMEOUT_SEC,
            )
            response.raise_for_status()
            items = response.json().get("items", [])
        except requests.RequestException:
            dispatcher.utter_message(text="读取你的订单失败，请稍后重试。")
            return []

        if not items:
            dispatcher.utter_message(
                text=(
                    "你当前还没有订单。\n"
                    f"可以先逛逛商品：{frontend_base_url}/products"
                )
            )
            return []

        lines = ["这是你最近的订单："]
        for item in items:
            order_id = _safe_text(item.get("id"))
            status = _safe_text(item.get("status")) or "未知状态"
            item_count = int(item.get("item_count") or 0)
            total_amount = float(item.get("total_amount") or 0)
            order_link = _safe_text(item.get("order_link"))
            lines.append(f"- {order_id} | {status} | {item_count} 件 | ¥{total_amount:.2f}")
            if order_link:
                lines.append(f"  订单链接: {order_link}")

        dispatcher.utter_message(text="\n".join(lines))
        return []
