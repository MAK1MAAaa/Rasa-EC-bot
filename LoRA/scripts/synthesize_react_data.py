#!/usr/bin/env python
"""Synthesize QA SFT records into ReAct-style agent records with schema-aligned observations.

Pipeline:
1) Sample high-value QA records with soft stratified action ratios.
2) Ask Ollama to generate thought/action/action_input/response only.
3) Inject observation from local schema templates (strict key alignment).
4) Output react-only split and base+react combined split.
"""

from __future__ import annotations

import argparse
import copy
import json
import random
import re
import socket
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

from env_utils import load_env_file

SYSTEM_PROMPT = (
    "You are an ecommerce customer-support assistant. "
    "Be concise, factual, and safe. "
    "Never fabricate order IDs, shipment status, or refunds. "
    "If a user asks to execute sensitive actions (place order, cancel order, refund), "
    "ask for explicit confirmation first."
)

ACTION_ORDER = [
    "query_order_status",
    "query_logistics",
    "query_product_info",
    "create_return_request",
    "query_refund_status",
    "query_orders_summary",
]

# Default action-level targets in percentage points (sum = 100).
ACTION_TARGET_RATIOS: dict[str, int] = {
    "query_order_status": 28,
    "query_logistics": 17,
    "query_product_info": 20,
    "create_return_request": 18,
    "query_refund_status": 12,
    "query_orders_summary": 5,
}

# Group-level target ratios for summary reporting.
GROUP_TARGET_RATIOS: dict[str, int] = {
    "orders_logistics": 45,
    "after_sales": 35,
    "product": 20,
}

ACTION_TO_GROUP: dict[str, str] = {
    "query_order_status": "orders_logistics",
    "query_logistics": "orders_logistics",
    "query_orders_summary": "orders_logistics",
    "create_return_request": "after_sales",
    "query_refund_status": "after_sales",
    "query_product_info": "product",
}

ORDER_ID_RE = re.compile(r"(ORD\d{10,})", flags=re.IGNORECASE)
REASON_RE = re.compile(r"(?:reason|because|原因|理由)[:：]?\s*(.+)$", flags=re.IGNORECASE)
WS_RE = re.compile(r"\s+")
FULL_PLACEHOLDER_RE = re.compile(r"^\{\{\s*([a-zA-Z0-9_]+)\s*\}\}$")
PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")
READ_ENCODINGS = ("utf-8", "utf-8-sig", "gb18030", "latin-1")

DEFAULT_FALLBACK_USERS: dict[str, list[str]] = {
    "query_order_status": [
        "请帮我查一下订单 ORD202604080001 的状态。",
        "Where is order ORD202604080002 now?",
    ],
    "query_logistics": [
        "我想看一下最近订单的物流进度。",
        "Track my shipment for order ORD202604080003.",
    ],
    "query_product_info": [
        "有没有轻薄笔记本推荐？",
        "Show me available phone accessories under 100.",
    ],
    "create_return_request": [
        "我要申请退货，订单号 ORD202604080004，原因：尺码不合适。",
        "Please create a return request for ORD202604080005 because item is damaged.",
    ],
    "query_refund_status": [
        "帮我查一下退款进度。",
        "What is the status of my after-sales request?",
    ],
    "query_orders_summary": [
        "给我看看我最近的订单列表。",
        "List my latest orders.",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Synthesize QA records into ReAct agent records via local Ollama."
    )
    parser.add_argument("--input-train", type=Path, default=Path("data/processed/train.jsonl"))
    parser.add_argument("--input-val", type=Path, default=Path("data/processed/val.jsonl"))
    parser.add_argument("--input-test", type=Path, default=Path("data/processed/test.jsonl"))
    parser.add_argument(
        "--schema-config",
        type=Path,
        default=Path("configs/react_action_schemas.json"),
    )
    parser.add_argument("--sample-size", type=int, default=1500)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--pool-multiplier", type=int, default=8)
    parser.add_argument("--min-pool-size", type=int, default=300)
    parser.add_argument("--max-retries", type=int, default=4)
    parser.add_argument("--temperature", type=float, default=0.4)
    parser.add_argument("--timeout-sec", type=int, default=120)
    parser.add_argument("--ollama-base-url", type=str, default="http://127.0.0.1:11434")
    parser.add_argument("--ollama-model", type=str, default=None)
    parser.add_argument(
        "--react-out-dir",
        type=Path,
        default=Path("data/processed/react_agent"),
    )
    parser.add_argument(
        "--combined-out-dir",
        type=Path,
        default=Path("data/processed/combined_react_agent"),
    )
    parser.add_argument("--train-ratio", type=float, default=0.90)
    parser.add_argument("--val-ratio", type=float, default=0.05)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not call Ollama, use deterministic fallback synthesis only.",
    )
    return parser.parse_args()


def resolve_path(path: Path, root: Path) -> Path:
    return path if path.is_absolute() else (root / path).resolve()


def normalize_text(text: str, max_chars: int = 1200) -> str:
    return WS_RE.sub(" ", text).strip()[:max_chars].strip()


def iter_lines_with_fallback(path: Path, encodings: tuple[str, ...] = READ_ENCODINGS):
    last_error: UnicodeDecodeError | None = None
    for encoding in encodings:
        try:
            with path.open("r", encoding=encoding) as f:
                for line in f:
                    yield line
            return
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
    if last_error is not None:
        raise last_error


def extract_message_text(messages: list[dict[str, Any]], role: str) -> str:
    for item in messages:
        if str(item.get("role", "")).strip().lower() == role:
            return normalize_text(str(item.get("content", "")))
    return ""


def bool_like(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "on"}


def infer_candidate_actions(user_text: str, assistant_text: str, intent: str) -> set[str]:
    text = " ".join([user_text, assistant_text, intent]).lower()
    actions: set[str] = set()

    order_status_keywords = [
        "order status",
        "where is my order",
        "订单状态",
        "订单详情",
        "order detail",
        "check order",
        "查订单",
        "订单号",
    ]
    logistics_keywords = [
        "track",
        "tracking",
        "shipment",
        "shipping",
        "delivery",
        "logistics",
        "物流",
        "快递",
        "发货",
        "运单",
        "到哪",
    ]
    product_keywords = [
        "product",
        "recommend",
        "price",
        "stock",
        "category",
        "details",
        "spec",
        "商品",
        "产品",
        "推荐",
        "价格",
        "库存",
        "规格",
    ]
    return_keywords = [
        "return",
        "exchange",
        "refund",
        "after-sales",
        "售后",
        "退货",
        "换货",
        "退款",
    ]
    return_action_markers = [
        "apply",
        "request",
        "submit",
        "start",
        "帮我",
        "我要",
        "申请",
        "发起",
        "提交",
    ]
    refund_status_keywords = [
        "refund status",
        "refund progress",
        "after-sales status",
        "售后进度",
        "退款进度",
        "退款状态",
        "退货进度",
        "处理进度",
    ]
    order_summary_keywords = [
        "my orders",
        "order history",
        "list orders",
        "all orders",
        "recent orders",
        "我的订单",
        "订单列表",
        "全部订单",
        "最近订单",
    ]

    if any(k in text for k in order_status_keywords):
        actions.add("query_order_status")
    if any(k in text for k in logistics_keywords):
        actions.add("query_logistics")
    if any(k in text for k in product_keywords):
        actions.add("query_product_info")
    if any(k in text for k in return_keywords):
        if any(k in text for k in return_action_markers):
            actions.add("create_return_request")
        actions.add("query_refund_status")
    if any(k in text for k in refund_status_keywords):
        actions.add("query_refund_status")
    if any(k in text for k in order_summary_keywords):
        actions.add("query_orders_summary")

    intent_lower = intent.lower()
    if any(x in intent_lower for x in ["track_order", "shipping", "order_status"]):
        actions.update({"query_order_status", "query_logistics"})
    if any(x in intent_lower for x in ["refund", "return", "exchange", "after_sales"]):
        actions.update({"create_return_request", "query_refund_status"})
    if any(x in intent_lower for x in ["product", "recommend", "availability"]):
        actions.add("query_product_info")
    if any(x in intent_lower for x in ["order_history", "order_list"]):
        actions.add("query_orders_summary")

    return actions.intersection(ACTION_ORDER)


def reservoir_add(
    pool: list[dict[str, Any]],
    value: dict[str, Any],
    seen_count: int,
    cap: int,
    rng: random.Random,
) -> int:
    seen_count += 1
    if cap <= 0:
        return seen_count
    if len(pool) < cap:
        pool.append(value)
        return seen_count
    idx = rng.randint(0, seen_count - 1)
    if idx < cap:
        pool[idx] = value
    return seen_count


def allocate_counts(total: int, ratio_map: dict[str, int]) -> dict[str, int]:
    if total <= 0:
        return {k: 0 for k in ratio_map}
    raw: dict[str, float] = {k: total * (v / 100.0) for k, v in ratio_map.items()}
    base: dict[str, int] = {k: int(raw[k]) for k in raw}
    remain = total - sum(base.values())
    if remain > 0:
        frac_order = sorted(
            raw.keys(),
            key=lambda k: (raw[k] - base[k]),
            reverse=True,
        )
        for key in frac_order[:remain]:
            base[key] += 1
    return base


def collect_action_pools(
    input_paths: list[Path],
    action_caps: dict[str, int],
    rng: random.Random,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    pools: dict[str, list[dict[str, Any]]] = {k: [] for k in ACTION_ORDER}
    seen_counter: dict[str, int] = {k: 0 for k in ACTION_ORDER}

    scan_stats = {
        "total_lines": 0,
        "json_parse_failed": 0,
        "message_missing": 0,
        "candidate_lines": 0,
        "action_seen_distribution": {k: 0 for k in ACTION_ORDER},
        "source_distribution": {},
    }
    source_counter: Counter[str] = Counter()

    for path in input_paths:
        if not path.exists():
            raise FileNotFoundError(f"Input jsonl not found: {path}")
        for line in iter_lines_with_fallback(path):
            scan_stats["total_lines"] += 1
            text = line.strip()
            if not text:
                continue
            try:
                row = json.loads(text)
            except json.JSONDecodeError:
                scan_stats["json_parse_failed"] += 1
                continue
            messages = row.get("messages", [])
            if not isinstance(messages, list):
                scan_stats["message_missing"] += 1
                continue
            user_text = extract_message_text(messages, "user")
            assistant_text = extract_message_text(messages, "assistant")
            system_text = extract_message_text(messages, "system") or SYSTEM_PROMPT
            if not user_text or not assistant_text:
                scan_stats["message_missing"] += 1
                continue
            source = str(row.get("source", "unknown"))
            intent = str(row.get("intent", "unknown"))
            actions = infer_candidate_actions(user_text, assistant_text, intent)
            if not actions:
                continue
            scan_stats["candidate_lines"] += 1
            source_counter[source] += 1
            candidate = {
                "user": user_text,
                "assistant": assistant_text,
                "system": system_text,
                "intent": intent,
                "source": source,
            }
            for action in actions:
                scan_stats["action_seen_distribution"][action] += 1
                seen_counter[action] = reservoir_add(
                    pool=pools[action],
                    value=candidate,
                    seen_count=seen_counter[action],
                    cap=action_caps[action],
                    rng=rng,
                )

    scan_stats["source_distribution"] = dict(source_counter)
    pool_sizes = {k: len(v) for k, v in pools.items()}
    return pools, {
        "scan_stats": scan_stats,
        "pool_sizes": pool_sizes,
    }


def synthesize_fallback_candidate(action: str, rng: random.Random) -> dict[str, Any]:
    user = rng.choice(DEFAULT_FALLBACK_USERS[action])
    return {
        "user": user,
        "assistant": "请参考系统返回信息。",
        "system": SYSTEM_PROMPT,
        "intent": f"fallback_{action}",
        "source": "fallback_seed",
    }


def pick_candidates_for_actions(
    pools: dict[str, list[dict[str, Any]]],
    target_counts: dict[str, int],
    rng: random.Random,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, int]]:
    selected: dict[str, list[dict[str, Any]]] = {k: [] for k in ACTION_ORDER}
    shortages: dict[str, int] = {k: 0 for k in ACTION_ORDER}
    used_user_keys: set[str] = set()

    def user_key(candidate: dict[str, Any]) -> str:
        return normalize_text(str(candidate.get("user", "")), max_chars=600).lower()

    priority = sorted(
        ACTION_ORDER,
        key=lambda a: (
            len(pools[a]) / max(1, target_counts[a]),
            len(pools[a]),
        ),
    )

    for action in priority:
        target = target_counts[action]
        pool = list(pools[action])
        rng.shuffle(pool)

        for candidate in pool:
            if len(selected[action]) >= target:
                break
            key = user_key(candidate)
            if key and key in used_user_keys:
                continue
            selected[action].append(candidate)
            if key:
                used_user_keys.add(key)

        shortage = max(0, target - len(selected[action]))
        shortages[action] = shortage
        if shortage <= 0:
            continue

        if pool:
            # Fill remaining slots with replacement if unique pool is not enough.
            for _ in range(shortage):
                selected[action].append(rng.choice(pool))
        else:
            for _ in range(shortage):
                selected[action].append(synthesize_fallback_candidate(action, rng))

    return selected, shortages


def load_schema_config(path: Path) -> dict[str, dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    actions = data.get("actions")
    if not isinstance(actions, dict):
        raise ValueError("Invalid schema config: `actions` must be an object.")
    missing = [a for a in ACTION_ORDER if a not in actions]
    if missing:
        raise ValueError(f"Schema config missing actions: {missing}")
    return {k: actions[k] for k in ACTION_ORDER}


def to_iso_z(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat() + "Z"


def stable_uuid(rng: random.Random) -> str:
    return str(UUID(int=rng.getrandbits(128)))


def generate_order_id(rng: random.Random) -> str:
    date = datetime(2026, 4, 8, 12, 0, 0) + timedelta(minutes=rng.randint(0, 60 * 24 * 120))
    return f"ORD{date.strftime('%Y%m%d%H%M%S')}{rng.randint(1000, 9999)}"


def generate_tracking_no(rng: random.Random) -> str:
    date = datetime(2026, 4, 8, 12, 0, 0) + timedelta(minutes=rng.randint(0, 60 * 24 * 120))
    return f"TRK{date.strftime('%Y%m%d%H%M%S')}{rng.randint(1000, 9999)}"


def extract_order_id(text: str) -> str | None:
    match = ORDER_ID_RE.search(text or "")
    if not match:
        return None
    return match.group(1).upper()


def extract_reason(text: str) -> str | None:
    match = REASON_RE.search(text or "")
    if match and match.group(1).strip():
        return normalize_text(match.group(1), 150)
    return None


def detect_product_keyword(user_text: str) -> str:
    lower = user_text.lower()
    candidates = [
        ("laptop", ["laptop", "notebook", "笔记本"]),
        ("phone", ["phone", "mobile", "手机"]),
        ("headphone", ["headphone", "耳机"]),
        ("keyboard", ["keyboard", "键盘"]),
        ("camera", ["camera", "相机"]),
        ("shoes", ["shoes", "鞋"]),
    ]
    for keyword, hints in candidates:
        if any(h in lower for h in hints):
            return keyword
    return "ecommerce product"


def normalize_return_type(value: str) -> str:
    text = value.strip().lower()
    if text in {"exchange", "换货"}:
        return "exchange"
    return "return"


def default_action_input(action: str, candidate: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    user_text = str(candidate.get("user", ""))
    order_id = extract_order_id(user_text) or generate_order_id(rng)

    if action == "query_order_status":
        return {"order_id": order_id}
    if action == "query_logistics":
        payload: dict[str, Any] = {"user_id": "current_user", "limit": 3}
        if extract_order_id(user_text):
            payload["order_id"] = order_id
        return payload
    if action == "query_product_info":
        return {
            "keyword": detect_product_keyword(user_text),
            "page": 1,
            "page_size": 12,
            "sort_by": "newest",
            "in_stock": True,
        }
    if action == "create_return_request":
        request_type = "exchange" if "换" in user_text else "return"
        return {
            "order_id": order_id,
            "type": request_type,
            "reason": extract_reason(user_text) or "商品与描述不符",
        }
    if action == "query_refund_status":
        return {"user_id": "current_user", "limit": 5}
    if action == "query_orders_summary":
        return {"user_id": "current_user", "limit": 5}
    raise ValueError(f"Unsupported action: {action}")


def parse_json_object(text: str) -> dict[str, Any] | None:
    content = (text or "").strip()
    if not content:
        return None
    content = content.replace("```json", "").replace("```", "").strip()

    try:
        obj = json.loads(content)
        if isinstance(obj, dict):
            return obj
        if isinstance(obj, list):
            for item in obj:
                if isinstance(item, dict):
                    return item
    except json.JSONDecodeError:
        pass

    first = content.find("{")
    last = content.rfind("}")
    if first >= 0 and last > first:
        snippet = content[first : last + 1]
        try:
            obj = json.loads(snippet)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            return None
    return None


def maybe_parse_action_input(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        obj = parse_json_object(value)
        if isinstance(obj, dict):
            return obj
    return None


def sanitize_response_text(text: str) -> str:
    return normalize_text(text, max_chars=400)


def coerce_limit(value: Any, default: int) -> int:
    try:
        num = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(10, num))


def normalize_action_input(
    action: str,
    raw_action_input: dict[str, Any],
    fallback_input: dict[str, Any],
) -> dict[str, Any]:
    merged = copy.deepcopy(fallback_input)
    for k, v in raw_action_input.items():
        merged[k] = v

    if action in {"query_logistics", "query_refund_status", "query_orders_summary"}:
        merged["user_id"] = str(merged.get("user_id", "current_user")).strip() or "current_user"
        if "limit" in merged:
            merged["limit"] = coerce_limit(merged.get("limit"), fallback_input.get("limit", 5))
    if action == "query_order_status":
        merged["order_id"] = str(merged.get("order_id", "")).strip().upper()
    if action == "create_return_request":
        merged["order_id"] = str(merged.get("order_id", "")).strip().upper()
        merged["type"] = normalize_return_type(str(merged.get("type", "return")))
        merged["reason"] = normalize_text(str(merged.get("reason", "")), 180)
    if action == "query_product_info":
        if "page" in merged:
            try:
                merged["page"] = max(1, int(merged["page"]))
            except (TypeError, ValueError):
                merged["page"] = 1
        if "page_size" in merged:
            try:
                merged["page_size"] = max(1, min(50, int(merged["page_size"])))
            except (TypeError, ValueError):
                merged["page_size"] = 12
        merged["keyword"] = normalize_text(str(merged.get("keyword", "")), 80)
        merged["category"] = normalize_text(str(merged.get("category", "")), 80)
    return merged


def validate_action_input(
    action: str,
    action_input: dict[str, Any],
    required_keys: list[str],
) -> tuple[bool, str]:
    for key in required_keys:
        if key not in action_input:
            return False, f"missing_required_key:{key}"
        value = action_input.get(key)
        if value is None:
            return False, f"required_key_is_null:{key}"
        if isinstance(value, str) and not value.strip():
            return False, f"required_key_is_empty:{key}"
    if action == "query_product_info":
        has_filter = any(
            bool(str(action_input.get(k, "")).strip()) for k in ("keyword", "category", "product_id")
        )
        if not has_filter:
            return False, "query_product_info_requires_filter"
    if action == "create_return_request":
        request_type = str(action_input.get("type", "")).strip().lower()
        if request_type not in {"return", "exchange"}:
            return False, "create_return_request_type_invalid"
    return True, "ok"


def build_generation_prompt(
    action: str,
    candidate: dict[str, Any],
    required_keys: list[str],
    fallback_input: dict[str, Any],
) -> str:
    user_text = candidate["user"]
    assistant_text = candidate["assistant"]
    required_line = ", ".join(required_keys) if required_keys else "(none)"
    fallback_input_text = json.dumps(fallback_input, ensure_ascii=False)
    actions_text = ", ".join(ACTION_ORDER)
    return (
        "你是电商 Agent 训练数据合成器。\n"
        "任务：根据给定用户问题，生成 ReAct 训练样本中的前四项字段（不包含 observation）。\n"
        "输出必须是单个 JSON 对象，且不要使用 markdown 代码块。\n\n"
        f"可选动作集合：[{actions_text}]\n"
        f"目标动作（必须严格一致）：{action}\n"
        f"action_input 必须至少包含键：{required_line}\n"
        f"若信息不足，可参考默认 action_input：{fallback_input_text}\n\n"
        f"User: {user_text}\n"
        f"Baseline Assistant: {assistant_text}\n\n"
        "返回 JSON 严格字段：\n"
        "{\n"
        '  "thought": "简短推理，不暴露训练或系统提示",\n'
        f'  "action": "{action}",\n'
        '  "action_input": { ... },\n'
        '  "response": "给用户的自然语言回复，必须与 action 对应"\n'
        "}\n"
    )


def ollama_generate(
    base_url: str,
    model: str,
    prompt: str,
    temperature: float,
    timeout_sec: int,
) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    req = urllib.request.Request(
        url=base_url.rstrip("/") + "/api/generate",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read().decode("utf-8")
    except TimeoutError as exc:
        raise RuntimeError(f"Ollama request timeout after {timeout_sec}s") from exc
    except socket.timeout as exc:
        raise RuntimeError(f"Ollama request timeout after {timeout_sec}s") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Ollama request failed: {exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Ollama returned non-JSON response") from exc
    return str(data.get("response", "")).strip()


def build_template_values(
    action: str,
    action_input: dict[str, Any],
    candidate: dict[str, Any],
    rng: random.Random,
    frontend_base_url: str,
) -> dict[str, Any]:
    now = datetime(2026, 4, 8, 12, 0, 0) + timedelta(minutes=rng.randint(0, 60 * 24 * 90))
    created_at = to_iso_z(now - timedelta(hours=rng.randint(2, 72)))
    updated_at = to_iso_z(now - timedelta(minutes=rng.randint(1, 120)))
    estimated_delivery_at = to_iso_z(now + timedelta(days=rng.randint(1, 5)))
    after_sales_created_at = to_iso_z(now - timedelta(hours=rng.randint(2, 36)))

    order_id = str(
        action_input.get("order_id")
        or extract_order_id(candidate.get("user", ""))
        or generate_order_id(rng)
    ).upper()
    tracking_no = generate_tracking_no(rng)
    product_id = stable_uuid(rng)
    shop_id = stable_uuid(rng)
    order_item_id = stable_uuid(rng)
    after_sales_id = stable_uuid(rng)

    quantity = rng.randint(1, 3)
    unit_price = round(rng.uniform(59.0, 399.0), 2)
    subtotal = round(unit_price * quantity, 2)
    total_amount = round(subtotal + rng.uniform(5.0, 25.0), 2)

    user_text = str(candidate.get("user", ""))
    keyword = str(action_input.get("keyword", "")).strip() or detect_product_keyword(user_text)
    category = str(action_input.get("category", "")).strip() or "electronics"
    if keyword == "phone":
        product_name = "Smartphone Fast Charger"
    elif keyword == "laptop":
        product_name = "Ultra-light Laptop Sleeve"
    else:
        product_name = f"{keyword.title()} Accessory Set"

    order_status = rng.choice(["pending_shipment", "shipped"])
    logistics_status = "in_transit" if order_status == "shipped" else "pending"
    after_sales_type = normalize_return_type(str(action_input.get("type", "return")))
    after_sales_status = rng.choice(["submitted", "merchant_approved", "processing", "completed"])

    frontend = frontend_base_url.rstrip("/")
    order_link = f"{frontend}/orders?orderId={order_id}"
    product_link = f"{frontend}/products/{product_id}"

    return {
        "order_id": order_id,
        "order_status": order_status,
        "address": "上海市浦东新区世纪大道100号",
        "contact_email": "test1@example.com",
        "total_amount": total_amount,
        "created_at": created_at,
        "shop_id": shop_id,
        "shop_name": "EC Demo Shop",
        "order_item_id": order_item_id,
        "product_id": product_id,
        "product_name": product_name,
        "unit_price": unit_price,
        "quantity": quantity,
        "subtotal": subtotal,
        "product_link": product_link,
        "tracking_no": tracking_no,
        "logistics_status": logistics_status,
        "current_location": "上海转运中心",
        "estimated_delivery_at": estimated_delivery_at,
        "route_step_1": "上海转运中心",
        "route_step_2": "杭州分拨站",
        "updated_at": updated_at,
        "after_sales_id": after_sales_id,
        "after_sales_type": after_sales_type,
        "after_sales_reason": str(action_input.get("reason") or "商品与描述不符"),
        "after_sales_status": after_sales_status,
        "after_sales_created_at": after_sales_created_at,
        "order_link": order_link,
        "price": round(rng.uniform(69.0, 699.0), 2),
        "product_desc": f"{keyword} related product",
        "image_url": "https://example.com/images/product.jpg",
        "product_category": category,
        "is_active": True,
        "stock": rng.randint(5, 200),
        "product_created_at": created_at,
        "total": 1,
        "page": int(action_input.get("page") or 1),
        "page_size": int(action_input.get("page_size") or 12),
    }


def render_template(node: Any, values: dict[str, Any]) -> Any:
    if isinstance(node, dict):
        return {k: render_template(v, values) for k, v in node.items()}
    if isinstance(node, list):
        return [render_template(item, values) for item in node]
    if isinstance(node, str):
        full = FULL_PLACEHOLDER_RE.match(node)
        if full:
            key = full.group(1)
            return copy.deepcopy(values.get(key, node))

        def repl(match: re.Match[str]) -> str:
            key = match.group(1)
            value = values.get(key, match.group(0))
            return str(value)

        return PLACEHOLDER_RE.sub(repl, node)
    return node


def validate_observation_shape(observation: Any, template: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(template, dict):
        if not isinstance(observation, dict):
            return [f"{path}: expected object, got {type(observation).__name__}"]
        obs_keys = set(observation.keys())
        tpl_keys = set(template.keys())
        if obs_keys != tpl_keys:
            missing = sorted(tpl_keys - obs_keys)
            extra = sorted(obs_keys - tpl_keys)
            if missing:
                errors.append(f"{path}: missing_keys={missing}")
            if extra:
                errors.append(f"{path}: extra_keys={extra}")
        for key in sorted(tpl_keys & obs_keys):
            errors.extend(
                validate_observation_shape(observation[key], template[key], f"{path}.{key}")
            )
        return errors

    if isinstance(template, list):
        if not isinstance(observation, list):
            return [f"{path}: expected list, got {type(observation).__name__}"]
        if not template:
            return []
        if not observation:
            return [f"{path}: list is empty"]
        return validate_observation_shape(observation[0], template[0], f"{path}[0]")

    # Scalar type checks are intentionally relaxed (nullable/formatting flexibility).
    return errors


def build_observation(
    action: str,
    action_input: dict[str, Any],
    candidate: dict[str, Any],
    template: Any,
    rng: random.Random,
    frontend_base_url: str,
) -> tuple[dict[str, Any], list[str]]:
    values = build_template_values(action, action_input, candidate, rng, frontend_base_url)
    observation = render_template(template, values)
    if not isinstance(observation, dict):
        raise ValueError(f"Observation must be dict for action {action}.")
    errors = validate_observation_shape(observation, template)
    return observation, errors


def build_react_text(
    thought: str,
    action: str,
    action_input: dict[str, Any],
    observation: dict[str, Any],
    response: str,
) -> str:
    action_input_json = json.dumps(action_input, ensure_ascii=False, separators=(",", ":"))
    observation_json = json.dumps(observation, ensure_ascii=False, separators=(",", ":"))
    return "\n".join(
        [
            f"Thought: {normalize_text(thought, 240)}",
            f"Action: {action}",
            f"Action_Input: {action_input_json}",
            f"Observation: {observation_json}",
            f"Response: {sanitize_response_text(response)}",
        ]
    )


def validate_react_text(text: str) -> tuple[bool, str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    expected_prefixes = ["Thought:", "Action:", "Action_Input:", "Observation:", "Response:"]
    if len(lines) != 5:
        return False, "react_format_line_count_invalid"
    for line, prefix in zip(lines, expected_prefixes):
        if not line.startswith(prefix):
            return False, f"react_missing_prefix:{prefix}"

    try:
        json.loads(lines[2].split(":", 1)[1].strip())
    except json.JSONDecodeError:
        return False, "react_action_input_not_json"
    try:
        json.loads(lines[3].split(":", 1)[1].strip())
    except json.JSONDecodeError:
        return False, "react_observation_not_json"

    return True, "ok"


def fallback_generation(
    action: str,
    candidate: dict[str, Any],
    action_input: dict[str, Any],
) -> tuple[str, str]:
    user_text = str(candidate.get("user", ""))
    if action == "query_order_status":
        thought = "用户在询问订单状态，需要查询订单详情接口。"
        response = f"我已为你查询订单状态。{user_text[:50]}"
    elif action == "query_logistics":
        thought = "用户在询问物流进度，需要查询物流摘要接口。"
        response = "我已查询到最近物流进度，并给出最新节点。"
    elif action == "query_product_info":
        thought = "用户在咨询商品信息，需要查询商品列表接口。"
        response = "我已按你的需求筛选了可用商品并返回关键信息。"
    elif action == "create_return_request":
        thought = "用户希望发起退货/换货，需要调用售后创建接口。"
        response = "我已按你提供的信息生成售后申请草稿。"
    elif action == "query_refund_status":
        thought = "用户在询问退款/售后进度，需要查询售后摘要接口。"
        response = "我已查询你的售后进度并汇总最新状态。"
    else:
        thought = "用户在查看订单概览，需要查询订单摘要接口。"
        response = "我已汇总最近订单列表与关键状态。"

    if action == "create_return_request":
        action_input["type"] = normalize_return_type(str(action_input.get("type", "return")))
    return thought, response


def synthesize_records(
    selected: dict[str, list[dict[str, Any]]],
    schema_map: dict[str, dict[str, Any]],
    model_name: str,
    base_url: str,
    temperature: float,
    timeout_sec: int,
    max_retries: int,
    frontend_base_url: str,
    rng: random.Random,
    dry_run: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    tasks: list[tuple[str, dict[str, Any]]] = []
    for action in ACTION_ORDER:
        for candidate in selected[action]:
            tasks.append((action, candidate))
    rng.shuffle(tasks)

    records: list[dict[str, Any]] = []
    mode_counter: Counter[str] = Counter()
    action_counter: Counter[str] = Counter()
    generation_failure_reasons: Counter[str] = Counter()
    schema_error_counter: Counter[str] = Counter()
    react_format_error_counter: Counter[str] = Counter()

    for idx, (action, candidate) in enumerate(tasks):
        action_schema = schema_map[action]
        required_keys = list(action_schema.get("required_action_input_keys", []))
        observation_template = action_schema.get("observation_template", {})
        default_input = default_action_input(action, candidate, rng)

        thought = ""
        response = ""
        normalized_input = copy.deepcopy(default_input)
        mode = "fallback"

        if not dry_run:
            for _ in range(max_retries):
                prompt = build_generation_prompt(action, candidate, required_keys, default_input)
                try:
                    raw = ollama_generate(
                        base_url=base_url,
                        model=model_name,
                        prompt=prompt,
                        temperature=temperature,
                        timeout_sec=timeout_sec,
                    )
                except RuntimeError as exc:
                    err = str(exc).lower()
                    if "timeout" in err:
                        generation_failure_reasons["ollama_request_timeout"] += 1
                    elif "non-json" in err:
                        generation_failure_reasons["ollama_response_not_json"] += 1
                    else:
                        generation_failure_reasons["ollama_request_failed"] += 1
                    continue
                except Exception:
                    generation_failure_reasons["ollama_unexpected_error"] += 1
                    continue

                obj = parse_json_object(raw)
                if not obj:
                    generation_failure_reasons["llm_output_not_json"] += 1
                    continue

                model_action = str(obj.get("action", "")).strip()
                if model_action != action:
                    generation_failure_reasons["llm_action_mismatch"] += 1
                    continue

                thought_raw = normalize_text(str(obj.get("thought", "")), 240)
                response_raw = sanitize_response_text(str(obj.get("response", "")))
                model_action_input = maybe_parse_action_input(obj.get("action_input"))
                if not thought_raw:
                    generation_failure_reasons["llm_thought_empty"] += 1
                    continue
                if not response_raw:
                    generation_failure_reasons["llm_response_empty"] += 1
                    continue
                if model_action_input is None:
                    generation_failure_reasons["llm_action_input_invalid"] += 1
                    continue

                normalized_input = normalize_action_input(action, model_action_input, default_input)
                valid, reason = validate_action_input(action, normalized_input, required_keys)
                if not valid:
                    generation_failure_reasons[reason] += 1
                    continue

                thought = thought_raw
                response = response_raw
                mode = "llm"
                break

        if mode != "llm":
            normalized_input = normalize_action_input(action, {}, default_input)
            valid, reason = validate_action_input(action, normalized_input, required_keys)
            if not valid:
                generation_failure_reasons[f"fallback_input_invalid:{reason}"] += 1
                normalized_input = copy.deepcopy(default_input)
            thought, response = fallback_generation(action, candidate, normalized_input)

        observation, schema_errors = build_observation(
            action=action,
            action_input=normalized_input,
            candidate=candidate,
            template=observation_template,
            rng=rng,
            frontend_base_url=frontend_base_url,
        )
        for err in schema_errors:
            schema_error_counter[err] += 1

        react_text = build_react_text(
            thought=thought,
            action=action,
            action_input=normalized_input,
            observation=observation,
            response=response,
        )
        ok, react_reason = validate_react_text(react_text)
        if not ok:
            react_format_error_counter[react_reason] += 1
            # Do not drop the sample; keep deterministic output for target count.

        system_text = normalize_text(str(candidate.get("system", "")), 1200) or SYSTEM_PROMPT
        user_text = normalize_text(str(candidate.get("user", "")), 800)

        records.append(
            {
                "id": f"react-agent-{idx:07d}",
                "source": "react_synth",
                "category": "react_agent",
                "intent": f"react_{action}",
                "action": action,
                "generation_mode": mode,
                "origin_source": str(candidate.get("source", "unknown")),
                "messages": [
                    {"role": "system", "content": system_text},
                    {"role": "user", "content": user_text},
                    {"role": "assistant", "content": react_text},
                ],
            }
        )
        mode_counter[mode] += 1
        action_counter[action] += 1

    summary = {
        "num_generated": len(records),
        "generation_mode_distribution": dict(mode_counter),
        "action_distribution": dict(action_counter),
        "generation_failure_reasons": dict(generation_failure_reasons),
        "schema_validation_errors": {
            "num_errors": int(sum(schema_error_counter.values())),
            "top_errors": schema_error_counter.most_common(20),
        },
        "react_format_errors": {
            "num_errors": int(sum(react_format_error_counter.values())),
            "top_errors": react_format_error_counter.most_common(20),
        },
    }
    return records, summary


def split_records(
    rows: list[dict[str, Any]],
    seed: int,
    train_ratio: float,
    val_ratio: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    if not 0 < train_ratio < 1:
        raise ValueError("train_ratio must be in (0,1).")
    if not 0 <= val_ratio < 1:
        raise ValueError("val_ratio must be in [0,1).")
    if train_ratio + val_ratio >= 1:
        raise ValueError("train_ratio + val_ratio must be < 1.")

    data = list(rows)
    random.Random(seed).shuffle(data)
    n = len(data)
    train_end = int(n * train_ratio)
    val_end = train_end + int(n * val_ratio)
    return data[:train_end], data[train_end:val_end], data[val_end:]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def append_base_and_extra(base_file: Path, extra_rows: list[dict[str, Any]], out_file: Path) -> dict[str, int]:
    out_file.parent.mkdir(parents=True, exist_ok=True)
    base_count = 0
    with out_file.open("w", encoding="utf-8") as out:
        for line in iter_lines_with_fallback(base_file):
            text = line.rstrip("\n")
            if not text:
                continue
            out.write(text + "\n")
            base_count += 1
        for row in extra_rows:
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {
        "base_count": base_count,
        "extra_count": len(extra_rows),
        "combined_count": base_count + len(extra_rows),
    }


def compute_action_ratio_deviation(
    target_counts: dict[str, int],
    actual_counts: dict[str, int],
    total: int,
) -> dict[str, float]:
    out: dict[str, float] = {}
    if total <= 0:
        return {k: 0.0 for k in ACTION_ORDER}
    for action in ACTION_ORDER:
        target = target_counts.get(action, 0) / total * 100.0
        actual = actual_counts.get(action, 0) / total * 100.0
        out[action] = round(actual - target, 4)
    return out


def summarize_group_distribution(action_counts: dict[str, int], total: int) -> dict[str, dict[str, float]]:
    group_counts: dict[str, int] = {k: 0 for k in GROUP_TARGET_RATIOS}
    for action, count in action_counts.items():
        group = ACTION_TO_GROUP.get(action)
        if group:
            group_counts[group] += int(count)
    summary: dict[str, dict[str, float]] = {}
    for group, target_ratio in GROUP_TARGET_RATIOS.items():
        actual_ratio = (group_counts[group] / total * 100.0) if total > 0 else 0.0
        summary[group] = {
            "target_ratio_pct": float(target_ratio),
            "actual_ratio_pct": round(actual_ratio, 4),
            "deviation_pct_point": round(actual_ratio - target_ratio, 4),
        }
    return summary


def main() -> None:
    args = parse_args()
    rng = random.Random(args.seed)

    lora_root = Path(__file__).resolve().parent.parent
    env_map = load_env_file(lora_root / ".env")

    model_name = (args.ollama_model or env_map.get("OLLAMA_MODEL") or "qwen3.5:9b").strip()
    frontend_base_url = (
        env_map.get("FRONTEND_BASE_URL", "http://localhost:5173").strip()
        or "http://localhost:5173"
    )

    input_train = resolve_path(args.input_train, lora_root)
    input_val = resolve_path(args.input_val, lora_root)
    input_test = resolve_path(args.input_test, lora_root)
    schema_path = resolve_path(args.schema_config, lora_root)
    react_out_dir = resolve_path(args.react_out_dir, lora_root)
    combined_out_dir = resolve_path(args.combined_out_dir, lora_root)

    if args.sample_size <= 0:
        raise ValueError("--sample-size must be > 0")

    schema_map = load_schema_config(schema_path)
    target_counts = allocate_counts(args.sample_size, ACTION_TARGET_RATIOS)
    action_caps = {
        action: max(args.min_pool_size, target_counts[action] * max(1, args.pool_multiplier))
        for action in ACTION_ORDER
    }

    pools, pool_summary = collect_action_pools(
        input_paths=[input_train, input_val, input_test],
        action_caps=action_caps,
        rng=rng,
    )
    selected, shortages = pick_candidates_for_actions(pools, target_counts, rng)

    generated, synth_summary = synthesize_records(
        selected=selected,
        schema_map=schema_map,
        model_name=model_name,
        base_url=args.ollama_base_url,
        temperature=args.temperature,
        timeout_sec=args.timeout_sec,
        max_retries=args.max_retries,
        frontend_base_url=frontend_base_url,
        rng=rng,
        dry_run=bool(args.dry_run),
    )

    react_train, react_val, react_test = split_records(
        generated,
        seed=args.seed,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
    )
    write_jsonl(react_out_dir / "train.jsonl", react_train)
    write_jsonl(react_out_dir / "val.jsonl", react_val)
    write_jsonl(react_out_dir / "test.jsonl", react_test)

    combined_train_stats = append_base_and_extra(
        base_file=input_train,
        extra_rows=react_train,
        out_file=combined_out_dir / "train.jsonl",
    )
    combined_val_stats = append_base_and_extra(
        base_file=input_val,
        extra_rows=react_val,
        out_file=combined_out_dir / "val.jsonl",
    )
    combined_test_stats = append_base_and_extra(
        base_file=input_test,
        extra_rows=react_test,
        out_file=combined_out_dir / "test.jsonl",
    )

    actual_counts = synth_summary.get("action_distribution", {})
    ratio_deviation = compute_action_ratio_deviation(target_counts, actual_counts, len(generated))
    group_summary = summarize_group_distribution(actual_counts, len(generated))

    summary = {
        "sample_size_target": args.sample_size,
        "sample_size_generated": len(generated),
        "target_action_counts": target_counts,
        "actual_action_counts": actual_counts,
        "action_ratio_deviation_pct_point": ratio_deviation,
        "group_ratio_summary": group_summary,
        "selected_shortages_before_fill": shortages,
        "pool_summary": pool_summary,
        "synthesis_summary": synth_summary,
        "react_split_counts": {
            "train": len(react_train),
            "val": len(react_val),
            "test": len(react_test),
        },
        "combined_counts": {
            "train": combined_train_stats,
            "val": combined_val_stats,
            "test": combined_test_stats,
        },
        "paths": {
            "schema_config": str(schema_path),
            "react_out_dir": str(react_out_dir),
            "combined_out_dir": str(combined_out_dir),
        },
        "ollama": {
            "base_url": args.ollama_base_url,
            "model": model_name,
            "temperature": args.temperature,
            "timeout_sec": args.timeout_sec,
            "max_retries": args.max_retries,
            "dry_run": bool(args.dry_run),
        },
        "seed": args.seed,
    }

    summary_path = react_out_dir / "summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("ReAct synthesis completed.")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
