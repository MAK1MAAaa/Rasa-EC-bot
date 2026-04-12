import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

RASA_DIR = Path(__file__).resolve().parent.parent
load_dotenv(RASA_DIR / '.env')

OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434')
OLLAMA_CHAT_PATH = os.getenv('OLLAMA_CHAT_PATH', '/api/chat')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen3.5:2b')
BACKEND_API_URL = os.getenv('BACKEND_API_URL', 'http://127.0.0.1:8000/api/v1')
ACTION_HTTP_TIMEOUT_SEC = float(os.getenv('ACTION_HTTP_TIMEOUT_SEC', '20'))
FRONTEND_BASE_URL = os.getenv('FRONTEND_BASE_URL', 'http://localhost:5173')
RASA_INTERNAL_TOKEN = os.getenv('RASA_INTERNAL_TOKEN', '')

SYSTEM_PROMPT = (
    '你是电商平台智能客服助手。'
    '请使用简洁、友好的中文回答。'
    '涉及订单/物流/售后时，不要编造信息，优先建议用户使用订单链接查看详情。'
)


def _safe_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return ''


def _build_context(tracker: Tracker) -> str:
    lines: list[str] = []
    for event in tracker.events[-10:]:
        event_type = event.get('event')
        if event_type == 'user':
            text = _safe_text(event.get('text'))
            if text:
                lines.append(f'用户: {text}')
        elif event_type == 'bot':
            text = _safe_text(event.get('text'))
            if text:
                lines.append(f'助手: {text}')
    return '\n'.join(lines)


def _latest_metadata(tracker: Tracker) -> dict[str, Any]:
    metadata = tracker.latest_message.get('metadata')
    if isinstance(metadata, dict):
        return metadata
    return {}


def _parse_order_id(text: str) -> str:
    match = re.search(r'ORD\d{8,}', text.upper())
    return match.group(0) if match else ''


def _order_status_label(status: str) -> str:
    if status == 'pending_shipment':
        return '待发货'
    if status == 'shipped':
        return '已发货'
    return status or '未知状态'


def _after_sales_type_label(value: str) -> str:
    if value == 'return':
        return '退货'
    if value == 'exchange':
        return '换货'
    return value or '售后'


def _after_sales_status_label(value: str) -> str:
    mapping = {
        'submitted': '待商家处理',
        'merchant_approved': '商家已同意',
        'processing': '处理中',
        'merchant_rejected': '商家已拒绝',
        'completed': '已完成',
        'cancelled': '已取消',
    }
    return mapping.get(value, value or '未知状态')


def _format_time(value: Any) -> str:
    text = _safe_text(value)
    if not text:
        return ''
    try:
        dt = datetime.fromisoformat(text.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M')
    except ValueError:
        return text


def _build_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    if RASA_INTERNAL_TOKEN.strip():
        headers['X-Rasa-Token'] = RASA_INTERNAL_TOKEN.strip()
    return headers


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


class ActionOllamaReply(Action):
    def name(self) -> str:
        return 'action_ollama_reply'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict[str, Any]) -> list[dict[str, Any]]:
        user_text = _safe_text(tracker.latest_message.get('text'))
        if not user_text:
            dispatcher.utter_message(text='我在的，你可以告诉我想咨询的内容。')
            return []

        context = _build_context(tracker)
        messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]
        if context:
            messages.append({'role': 'system', 'content': f'最近对话:\n{context}'})
        messages.append({'role': 'user', 'content': user_text})

        ollama_url = f"{OLLAMA_BASE_URL.rstrip('/')}/{OLLAMA_CHAT_PATH.lstrip('/')}"

        try:
            response = requests.post(
                ollama_url,
                json={
                    'model': OLLAMA_MODEL,
                    'messages': messages,
                    'stream': False,
                    'options': {'temperature': 0.5},
                },
                timeout=ACTION_HTTP_TIMEOUT_SEC,
            )
            response.raise_for_status()
            payload = response.json()
            reply = _safe_text(payload.get('message', {}).get('content'))
            if not reply:
                reply = '我刚刚有点忙，请再说一次你的问题。'
        except requests.RequestException:
            reply = '本地大模型服务暂时不可用，请稍后再试。'

        dispatcher.utter_message(text=reply)
        return []


class ActionRecommendProducts(Action):
    def name(self) -> str:
        return 'action_recommend_products'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict[str, Any]) -> list[dict[str, Any]]:
        category = _safe_text(tracker.get_slot('category'))
        metadata = _latest_metadata(tracker)
        user_text = _safe_text(tracker.latest_message.get('text'))
        is_authenticated = bool(metadata.get('is_authenticated'))
        user_id = _safe_text(metadata.get('user_id'))
        frontend_base_url = _safe_text(metadata.get('frontend_base_url')) or FRONTEND_BASE_URL
        frontend_base_url = frontend_base_url.rstrip('/')

        params: dict[str, Any] = {
            'limit': 5,
            'query': user_text,
        }
        if category:
            params['category'] = category
        if is_authenticated and user_id:
            params['user_id'] = user_id

        try:
            response = requests.get(
                f"{BACKEND_API_URL.rstrip('/')}/chat/internal/product-recommendations",
                params=params,
                headers=_build_headers(),
                timeout=ACTION_HTTP_TIMEOUT_SEC,
            )
            response.raise_for_status()
            payload = response.json()
            items = payload.get('items', [])
            personalized = bool(payload.get('personalized'))
        except requests.RequestException:
            dispatcher.utter_message(text='暂时无法读取商品数据，请稍后重试。')
            return []

        if not items:
            dispatcher.utter_message(text='暂时没有匹配的在售商品，你可以换个分类试试。')
            return []

        cards: list[dict[str, Any]] = []
        for item in items:
            name = _safe_text(item.get('name')) or '未命名商品'
            cat = _safe_text(item.get('category')) or '未分类'
            price = _safe_float(item.get('price'))
            product_id = _safe_text(item.get('id'))
            product_link = f'{frontend_base_url}/products/{product_id}' if product_id else ''
            cards.append(
                {
                    'type': 'product',
                    'data': {
                        'id': product_id,
                        'name': name,
                        'category': cat,
                        'brand': _safe_text(item.get('brand')),
                        'price': price,
                        'stock': _safe_int(item.get('stock')),
                        'rating': _safe_float(item.get('rating')),
                        'review_count': _safe_int(item.get('review_count')),
                        'monthly_sales': _safe_int(item.get('monthly_sales')),
                        'ship_in_hours': _safe_int(item.get('ship_in_hours')),
                        'tags': item.get('tags') if isinstance(item.get('tags'), list) else [],
                        'shop_name': _safe_text(item.get('shop_name')),
                        'product_link': product_link,
                        'image_url': _safe_text(item.get('image_url')),
                    },
                }
            )

        prefix = '给你推荐这几款商品：'
        if personalized:
            prefix = '结合你最近浏览的商品，为你推荐这几款：'
        if category:
            prefix = f'给你推荐几款 {category} 商品：'
            if personalized:
                prefix = f'结合你最近浏览的偏好，为你推荐几款 {category} 商品：'
        dispatcher.utter_message(text=prefix, json_message={'cards': cards})
        return []


class ActionQueryMyOrders(Action):
    def name(self) -> str:
        return 'action_query_my_orders'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict[str, Any]) -> list[dict[str, Any]]:
        metadata = _latest_metadata(tracker)
        is_authenticated = bool(metadata.get('is_authenticated'))
        user_id = _safe_text(metadata.get('user_id'))
        frontend_base_url = _safe_text(metadata.get('frontend_base_url')) or FRONTEND_BASE_URL
        frontend_base_url = frontend_base_url.rstrip('/')

        if not is_authenticated or not user_id:
            dispatcher.utter_message(
                text=(
                    '你当前还没有登录账号，暂时无法读取你的订单。\n'
                    f'先去登录：{frontend_base_url}/login'
                )
            )
            return []

        try:
            response = requests.get(
                f"{BACKEND_API_URL.rstrip('/')}/chat/internal/orders-summary",
                params={'user_id': user_id, 'limit': 5},
                headers=_build_headers(),
                timeout=ACTION_HTTP_TIMEOUT_SEC,
            )
            response.raise_for_status()
            items = response.json().get('items', [])
        except requests.RequestException:
            dispatcher.utter_message(text='读取你的订单失败，请稍后重试。')
            return []

        if not items:
            dispatcher.utter_message(
                text=(
                    '你当前还没有订单。\n'
                    f'可以先逛逛商品：{frontend_base_url}/products'
                )
            )
            return []

        cards: list[dict[str, Any]] = []
        for item in items:
            order_id = _safe_text(item.get('id'))
            raw_status = _safe_text(item.get('status'))
            status = _order_status_label(raw_status)
            item_count = _safe_int(item.get('item_count'))
            total_amount = _safe_float(item.get('total_amount'))
            order_link = _safe_text(item.get('order_link'))
            cards.append(
                {
                    'type': 'order',
                    'data': {
                        'id': order_id,
                        'status': raw_status,
                        'status_label': status,
                        'item_count': item_count,
                        'total_amount': total_amount,
                        'created_at': _safe_text(item.get('created_at')),
                        'order_link': order_link,
                    },
                }
            )

        dispatcher.utter_message(text='这是你最近的订单：', json_message={'cards': cards})
        return []


class ActionQueryOrderLogistics(Action):
    def name(self) -> str:
        return 'action_query_order_logistics'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict[str, Any]) -> list[dict[str, Any]]:
        metadata = _latest_metadata(tracker)
        is_authenticated = bool(metadata.get('is_authenticated'))
        user_id = _safe_text(metadata.get('user_id'))
        frontend_base_url = _safe_text(metadata.get('frontend_base_url')) or FRONTEND_BASE_URL
        frontend_base_url = frontend_base_url.rstrip('/')

        if not is_authenticated or not user_id:
            dispatcher.utter_message(
                text=(
                    '要查询物流，需要先登录账号。\n'
                    f'登录入口：{frontend_base_url}/login'
                )
            )
            return []

        user_text = _safe_text(tracker.latest_message.get('text'))
        order_id = _parse_order_id(user_text)

        params: dict[str, Any] = {'user_id': user_id, 'limit': 3}
        if order_id:
            params['order_id'] = order_id

        try:
            response = requests.get(
                f"{BACKEND_API_URL.rstrip('/')}/chat/internal/orders-logistics-summary",
                params=params,
                headers=_build_headers(),
                timeout=ACTION_HTTP_TIMEOUT_SEC,
            )
            response.raise_for_status()
            items = response.json().get('items', [])
        except requests.RequestException:
            dispatcher.utter_message(text='物流信息读取失败，请稍后重试。')
            return []

        if not items:
            if order_id:
                dispatcher.utter_message(text=f'没有找到订单 {order_id}，请检查订单号后重试。')
            else:
                dispatcher.utter_message(text=f'目前没有可查询的物流信息，你可以先查看订单页：{frontend_base_url}/orders')
            return []

        cards: list[dict[str, Any]] = []
        for item in items:
            current_order_id = _safe_text(item.get('id'))
            raw_status = _safe_text(item.get('status'))
            status = _order_status_label(raw_status)
            tracking_no = _safe_text(item.get('tracking_no'))
            current_location = _safe_text(item.get('current_location'))
            eta_text = _format_time(item.get('estimated_delivery_at'))
            order_link = _safe_text(item.get('order_link'))
            route_plan = item.get('route_plan') if isinstance(item.get('route_plan'), list) else []
            cards.append(
                {
                    'type': 'logistics',
                    'data': {
                        'id': current_order_id,
                        'status': raw_status,
                        'status_label': status,
                        'tracking_no': tracking_no,
                        'current_location': current_location,
                        'estimated_delivery_at': _safe_text(item.get('estimated_delivery_at')),
                        'estimated_delivery_text': eta_text,
                        'route_plan': [_safe_text(point) for point in route_plan if _safe_text(point)],
                        'order_link': order_link,
                        'created_at': _safe_text(item.get('created_at')),
                    },
                }
            )

        dispatcher.utter_message(text='帮你查到这些物流信息：', json_message={'cards': cards})
        return []


class ActionQueryAfterSales(Action):
    def name(self) -> str:
        return 'action_query_after_sales'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict[str, Any]) -> list[dict[str, Any]]:
        metadata = _latest_metadata(tracker)
        is_authenticated = bool(metadata.get('is_authenticated'))
        user_id = _safe_text(metadata.get('user_id'))
        frontend_base_url = _safe_text(metadata.get('frontend_base_url')) or FRONTEND_BASE_URL
        frontend_base_url = frontend_base_url.rstrip('/')

        if not is_authenticated or not user_id:
            dispatcher.utter_message(
                text=(
                    '要查询售后进度，需要先登录账号。\n'
                    f'登录入口：{frontend_base_url}/login'
                )
            )
            return []

        try:
            response = requests.get(
                f"{BACKEND_API_URL.rstrip('/')}/chat/internal/after-sales-summary",
                params={'user_id': user_id, 'limit': 5},
                headers=_build_headers(),
                timeout=ACTION_HTTP_TIMEOUT_SEC,
            )
            response.raise_for_status()
            items = response.json().get('items', [])
        except requests.RequestException:
            dispatcher.utter_message(text='读取售后信息失败，请稍后重试。')
            return []

        if not items:
            dispatcher.utter_message(
                text=(
                    '你当前还没有售后申请记录。\n'
                    f'可以到订单页发起退货/换货：{frontend_base_url}/orders'
                )
            )
            return []

        cards: list[dict[str, Any]] = []
        for item in items:
            request_id = _safe_text(item.get('id'))
            order_id = _safe_text(item.get('order_id'))
            raw_type = _safe_text(item.get('type'))
            request_type = _after_sales_type_label(raw_type)
            raw_status = _safe_text(item.get('status'))
            status = _after_sales_status_label(raw_status)
            reason = _safe_text(item.get('reason'))
            order_link = _safe_text(item.get('order_link'))
            cards.append(
                {
                    'type': 'after_sales',
                    'data': {
                        'id': request_id,
                        'order_id': order_id,
                        'type': raw_type,
                        'type_label': request_type,
                        'status': raw_status,
                        'status_label': status,
                        'created_at': _safe_text(item.get('created_at')),
                        'created_at_text': _format_time(item.get('created_at')),
                        'reason': reason,
                        'order_link': order_link,
                    },
                }
            )

        dispatcher.utter_message(
            text=f'这是你最近的售后进度，可前往订单页继续处理：{frontend_base_url}/orders',
            json_message={'cards': cards},
        )
        return []

