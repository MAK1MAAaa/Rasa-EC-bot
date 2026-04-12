from __future__ import annotations

import argparse
import asyncio
import csv
import json
import math
import random
import re
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = ROOT_DIR / "backend" / "benchmarks" / "experiment.yaml"
DEFAULT_PROMPT_ROOT = ROOT_DIR / "backend" / "benchmarks" / "prompts"
DEFAULT_SCENARIO_FAMILIES = (
    "recommendation",
    "order_query",
    "logistics_query",
    "after_sales_query",
    "knowledge_and_multimodal",
    "transactional_action",
)
CAPABILITY_KEYS = (
    "supports_auth_queries",
    "supports_kb_policy",
    "supports_kb_manual",
    "supports_pending_action",
    "supports_pending_decision",
    "supports_attachments",
    "supports_image_analysis",
    "supports_cards",
)
ORDER_ID_RE = re.compile(r"\bORD\d{6,}\b", flags=re.IGNORECASE)
LOGIN_REQUIRED_PATTERNS = ["请先登录", "先登录", "登录后", "请登录"]
EXPIRY_PATTERNS = ["已过期", "过期", "重新发起", "重新生成"]


@dataclass(frozen=True)
class TurnStep:
    turn_id: str
    kind: str
    message: str = ""
    image_case: str = ""
    decision: str = ""
    use_uploaded_attachments: bool = False
    sleep_seconds: float = 0.0


@dataclass(frozen=True)
class ExpectedOutcomes:
    required_any_text_keywords: list[str]
    forbidden_text_keywords: list[str]
    required_card_types: list[str]
    required_action_types: list[str]
    requires_confirmation_buttons: bool
    should_return_order_id: bool
    should_block_without_login: bool
    should_be_unsupported: bool
    must_avoid_hallucinated_order_id: bool
    allowed_order_ids: list[str]
    min_response_chars: int


@dataclass(frozen=True)
class ConversationSample:
    sample_id: str
    scenario_family: str
    scenario: str
    turns: list[TurnStep]
    account: str
    required_capabilities: list[str]
    preconditions: dict[str, Any]
    expected_outcomes: ExpectedOutcomes
    tags: list[str]
    tier: str
    repeatable: bool = True


@dataclass(frozen=True)
class SystemTarget:
    name: str
    kind: str
    base_url: str
    path: str
    model: str
    auth_mode: str
    sender_id: str
    upload_path: str
    pending_action_path: str
    login_url: str
    me_url: str
    capabilities: dict[str, bool]


@dataclass(frozen=True)
class AuthConfig:
    login_url: str
    me_url: str
    customer_email: str
    customer_password: str
    merchant_email: str
    merchant_password: str


@dataclass
class AuthContext:
    token: str = ""
    user_id: str = ""
    email: str = ""
    username: str = ""

    @property
    def bearer_headers(self) -> dict[str, str]:
        if not self.token:
            return {}
        return {"Authorization": f"Bearer {self.token}"}


@dataclass(frozen=True)
class KnowledgeSeedDocument:
    source_type: str
    title: str
    path: Path
    version: str
    status: str
    metadata: dict[str, Any]


@dataclass
class NormalizedReply:
    text: str = ""
    response_chars: int = 0
    card_count: int = 0
    action_count: int = 0
    card_types: list[str] = field(default_factory=list)
    action_types: list[str] = field(default_factory=list)
    order_ids: list[str] = field(default_factory=list)


@dataclass
class TurnEvent:
    timestamp: str
    system: str
    scenario_family: str
    scenario: str
    sample_id: str
    tier: str
    repeat: int
    concurrency: int
    conversation_index: int
    turn_index: int
    turn_id: str
    turn_kind: str
    requires_auth: bool
    required_capabilities: list[str]
    executed: bool
    unsupported: bool
    success: bool
    http_status: int | None
    error_type: str
    error_message: str
    latency_ms: float
    started_at: float
    finished_at: float
    response_text: str
    response_chars: int
    response_card_count: int
    response_action_count: int
    response_card_types: list[str] = field(default_factory=list)
    response_action_types: list[str] = field(default_factory=list)
    response_order_ids: list[str] = field(default_factory=list)


@dataclass
class ConversationEvent:
    timestamp: str
    system: str
    scenario_family: str
    scenario: str
    sample_id: str
    tier: str
    repeat: int
    concurrency: int
    conversation_index: int
    account: str
    required_capabilities: list[str]
    turn_count: int
    executed_turns: int
    unsupported: bool
    success: bool
    http_error_count: int
    latency_ms: float
    started_at: float
    finished_at: float
    quality_status: str
    conversation_success: bool
    passed: bool
    quality_flags: dict[str, Any] = field(default_factory=dict)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="客服链路多轮系统 benchmark。")
    parser.add_argument("--systems", default="", help="逗号分隔的系统名称列表")
    parser.add_argument("--scenarios", default=",".join(DEFAULT_SCENARIO_FAMILIES))
    parser.add_argument("--profile", default="quick")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--dataset", type=Path, default=None)
    parser.add_argument("--dataset-tier", default="")
    parser.add_argument("--results-root", type=Path, default=None)
    parser.add_argument("--requests-per-level", type=int, default=None)
    parser.add_argument("--repeats", type=int, default=None)
    parser.add_argument("--concurrency", default="")
    parser.add_argument("--timeout-sec", type=float, default=None)
    parser.add_argument("--warmup-requests", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def parse_csv_values(raw: str) -> list[str]:
    cleaned = raw.strip()
    if not cleaned:
        return []
    return [part.strip() for part in cleaned.split(",") if part.strip()]


def parse_concurrency_override(raw: str) -> list[int] | None:
    values = parse_csv_values(raw)
    if not values:
        return None
    parsed = [int(item) for item in values]
    if any(item <= 0 for item in parsed):
        raise ValueError("并发值必须大于 0。")
    return parsed


def load_config(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        import yaml  # type: ignore

        payload = yaml.safe_load(text)
    if not isinstance(payload, dict):
        raise RuntimeError("benchmark 配置必须是对象。")
    return payload


def require_string(mapping: dict[str, Any], key: str, *, default: str = "") -> str:
    value = mapping.get(key, default)
    return str(value or "").strip()


def resolve_auth_config(config: dict[str, Any]) -> AuthConfig:
    auth_cfg = config.get("auth")
    if not isinstance(auth_cfg, dict):
        raise RuntimeError("缺少 auth 配置。")
    customer = auth_cfg.get("customer")
    merchant = auth_cfg.get("merchant")
    if not isinstance(customer, dict):
        raise RuntimeError("缺少 auth.customer 配置。")
    if not isinstance(merchant, dict):
        raise RuntimeError("缺少 auth.merchant 配置。")
    return AuthConfig(
        login_url=require_string(auth_cfg, "login_url"),
        me_url=require_string(auth_cfg, "me_url"),
        customer_email=require_string(customer, "email"),
        customer_password=require_string(customer, "password"),
        merchant_email=require_string(merchant, "email"),
        merchant_password=require_string(merchant, "password"),
    )


def normalize_capabilities(item: dict[str, Any]) -> dict[str, bool]:
    raw_caps = item.get("capabilities") if isinstance(item.get("capabilities"), dict) else {}
    capabilities: dict[str, bool] = {}
    for key in CAPABILITY_KEYS:
        default_value = False
        if key == "supports_auth_queries":
            default_value = require_string(item, "auth_mode", default="none") in {"bearer", "metadata"}
        elif key == "supports_cards":
            default_value = bool(item.get("supports_cards", False))
        elif key == "supports_attachments":
            default_value = bool(item.get("supports_attachments", item.get("requires_upload_step", False)))
        elif key == "supports_image_analysis":
            default_value = bool(item.get("supports_image_analysis", item.get("supports_image", False)))
        capabilities[key] = bool(raw_caps.get(key, item.get(key, default_value)))
    return capabilities


def resolve_system_targets(config: dict[str, Any], requested_systems: list[str]) -> dict[str, SystemTarget]:
    systems_cfg = config.get("systems")
    if not isinstance(systems_cfg, dict):
        raise RuntimeError("缺少 systems 配置。")
    selected_names = requested_systems or list(systems_cfg.keys())
    targets: dict[str, SystemTarget] = {}
    for name in selected_names:
        item = systems_cfg.get(name)
        if not isinstance(item, dict):
            raise RuntimeError(f"system 未配置: {name}")
        target = SystemTarget(
            name=name,
            kind=require_string(item, "kind"),
            base_url=require_string(item, "base_url"),
            path=require_string(item, "path"),
            model=require_string(item, "model"),
            auth_mode=require_string(item, "auth_mode", default="none"),
            sender_id=require_string(item, "sender_id", default=f"benchmark-{name}"),
            upload_path=require_string(item, "upload_path"),
            pending_action_path=require_string(item, "pending_action_path", default="/api/v1/chat/pending-action/decision"),
            login_url=require_string(item, "login_url"),
            me_url=require_string(item, "me_url"),
            capabilities=normalize_capabilities(item),
        )
        if not target.kind or not target.base_url or not target.path:
            raise RuntimeError(f"system 配置不完整: {name}")
        targets[name] = target
    return targets


def resolve_knowledge_seed_documents(config: dict[str, Any]) -> list[KnowledgeSeedDocument]:
    seed_cfg = config.get("knowledge_seed")
    if not isinstance(seed_cfg, dict):
        return []
    documents = seed_cfg.get("documents")
    if not isinstance(documents, list):
        return []
    resolved: list[KnowledgeSeedDocument] = []
    for item in documents:
        if not isinstance(item, dict):
            continue
        path = Path(require_string(item, "path"))
        if not path.is_absolute():
            path = (ROOT_DIR / path).resolve()
        resolved.append(
            KnowledgeSeedDocument(
                source_type=require_string(item, "source_type"),
                title=require_string(item, "title"),
                path=path,
                version=require_string(item, "version", default="benchmark-v1"),
                status=require_string(item, "status", default="active"),
                metadata=dict(item.get("metadata") or {}),
            )
        )
    return resolved


def parse_turn(payload: dict[str, Any], index: int) -> TurnStep:
    return TurnStep(
        turn_id=str(payload.get("id") or f"turn-{index}"),
        kind=str(payload.get("kind") or "chat_send").strip(),
        message=str(payload.get("message") or "").strip(),
        image_case=str(payload.get("image_case") or "").strip(),
        decision=str(payload.get("decision") or "").strip().lower(),
        use_uploaded_attachments=bool(payload.get("use_uploaded_attachments", False)),
        sleep_seconds=float(payload.get("sleep_seconds") or 0.0),
    )


def parse_expected_outcomes(payload: dict[str, Any]) -> ExpectedOutcomes:
    if "expected_outcomes" in payload and isinstance(payload["expected_outcomes"], dict):
        raw = payload["expected_outcomes"]
    else:
        checks = dict(payload.get("checks") or {})
        raw = {
            "required_any_text_keywords": list(checks.get("required_any_keywords", [])),
            "forbidden_text_keywords": list(checks.get("forbidden_keywords", [])),
            "required_card_types": [],
            "required_action_types": [],
            "requires_confirmation_buttons": bool(checks.get("requires_confirmation", False)),
            "should_return_order_id": False,
            "should_block_without_login": False,
            "should_be_unsupported": False,
            "must_avoid_hallucinated_order_id": bool(checks.get("must_not_hallucinate_order_id", True)),
            "allowed_order_ids": [],
            "min_response_chars": int(checks.get("min_response_chars", 8)),
        }
    return ExpectedOutcomes(
        required_any_text_keywords=[str(item).strip() for item in raw.get("required_any_text_keywords", []) if str(item).strip()],
        forbidden_text_keywords=[str(item).strip() for item in raw.get("forbidden_text_keywords", []) if str(item).strip()],
        required_card_types=[str(item).strip() for item in raw.get("required_card_types", []) if str(item).strip()],
        required_action_types=[str(item).strip() for item in raw.get("required_action_types", []) if str(item).strip()],
        requires_confirmation_buttons=bool(raw.get("requires_confirmation_buttons", False)),
        should_return_order_id=bool(raw.get("should_return_order_id", False)),
        should_block_without_login=bool(raw.get("should_block_without_login", False)),
        should_be_unsupported=bool(raw.get("should_be_unsupported", False)),
        must_avoid_hallucinated_order_id=bool(raw.get("must_avoid_hallucinated_order_id", True)),
        allowed_order_ids=[str(item).strip() for item in raw.get("allowed_order_ids", []) if str(item).strip()],
        min_response_chars=int(raw.get("min_response_chars", 8)),
    )


def load_dataset_file(path: Path) -> list[ConversationSample]:
    records: list[ConversationSample] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_no, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                continue
            turns_payload = payload.get("turns")
            turns = (
                [parse_turn(item, index) for index, item in enumerate(turns_payload, start=1) if isinstance(item, dict)]
                if isinstance(turns_payload, list)
                else [TurnStep(turn_id="turn-1", kind="chat_send", message=str(payload.get("user_input") or "").strip())]
            )
            if not turns:
                continue
            records.append(
                ConversationSample(
                    sample_id=str(payload.get("id") or f"{path.stem}-{line_no}"),
                    scenario_family=str(payload.get("scenario_family") or payload.get("scenario") or path.stem).strip(),
                    scenario=str(payload.get("scenario") or path.stem).strip(),
                    turns=turns,
                    account=str(payload.get("account") or ("customer" if payload.get("requires_auth") else "anonymous")).strip(),
                    required_capabilities=[
                        str(item).strip() for item in payload.get("required_capabilities", []) if str(item).strip()
                    ],
                    preconditions=dict(payload.get("preconditions") or {}),
                    expected_outcomes=parse_expected_outcomes(payload),
                    tags=[str(item).strip() for item in payload.get("tags", []) if str(item).strip()],
                    tier=str(payload.get("tier") or "legacy").strip(),
                    repeatable=bool(payload.get("repeatable", True)),
                )
            )
    if not records:
        raise RuntimeError(f"数据集为空: {path}")
    return records


def resolve_dataset_files(
    dataset_arg: Path | None,
    dataset_tier: str,
    scenario_families: list[str],
) -> dict[str, Path]:
    if dataset_arg is None:
        base_dir = (DEFAULT_PROMPT_ROOT / dataset_tier).resolve()
        return {family: (base_dir / f"{family}.jsonl").resolve() for family in scenario_families}
    resolved = dataset_arg.resolve()
    if resolved.is_dir():
        tier_dir = resolved / dataset_tier
        base_dir = tier_dir if tier_dir.exists() else resolved
        return {family: (base_dir / f"{family}.jsonl").resolve() for family in scenario_families}
    if resolved.is_file() and len(scenario_families) == 1:
        return {scenario_families[0]: resolved}
    raise RuntimeError("--dataset 为文件时只能配合单场景族使用；多场景族请传目录。")


def compute_percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 2)
    rank = (len(ordered) - 1) * percentile
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return round(ordered[lower], 2)
    weight = rank - lower
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * weight, 2)


def contains_any(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords if keyword)


def extract_order_ids(value: Any) -> list[str]:
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    return sorted(set(match.group(0).upper() for match in ORDER_ID_RE.finditer(text)))


async def login_for_auth_context(
    client: httpx.AsyncClient,
    *,
    login_url: str,
    me_url: str,
    email: str,
    password: str,
) -> AuthContext:
    login_response = await client.post(login_url, json={"email": email, "password": password})
    login_response.raise_for_status()
    login_payload = login_response.json()
    token = str(login_payload.get("access_token") or "").strip() if isinstance(login_payload, dict) else ""
    if not token:
        raise RuntimeError("登录成功但未返回 access_token。")
    me_response = await client.get(me_url, headers={"Authorization": f"Bearer {token}"})
    me_response.raise_for_status()
    me_payload = me_response.json()
    if not isinstance(me_payload, dict):
        raise RuntimeError("auth/me 返回格式无效。")
    return AuthContext(
        token=token,
        user_id=str(me_payload.get("id") or "").strip(),
        email=str(me_payload.get("email") or "").strip(),
        username=str(me_payload.get("username") or "").strip(),
    )


def get_or_create_login_urls(auth_cfg: AuthConfig, system: SystemTarget) -> tuple[str, str]:
    login_url = system.login_url or auth_cfg.login_url
    me_url = system.me_url or auth_cfg.me_url
    if not login_url or not me_url:
        raise RuntimeError(f"system {system.name} 缺少登录配置。")
    return login_url, me_url


def build_rasa_metadata(account: str, auth_context: AuthContext) -> dict[str, Any]:
    metadata: dict[str, Any] = {"frontend_base_url": "http://localhost:5173"}
    if account == "customer":
        metadata.update(
            {
                "is_authenticated": True,
                "user_id": auth_context.user_id,
                "user_email": auth_context.email,
                "username": auth_context.username or "benchmark-user",
            }
        )
    else:
        metadata["is_authenticated"] = False
    return metadata


def normalize_card_types(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []
    types: list[str] = []
    for item in items:
        if isinstance(item, dict):
            card_type = str(item.get("type") or "").strip()
            if card_type:
                types.append(card_type)
    return types


def normalize_action_types(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []
    types: list[str] = []
    for item in items:
        if isinstance(item, dict):
            action_type = str(item.get("type") or "").strip()
            if action_type:
                types.append(action_type)
    return types


def normalize_rasa_messages(payload: Any) -> NormalizedReply:
    reply = NormalizedReply()
    if not isinstance(payload, list):
        return reply
    texts: list[str] = []
    all_cards: list[dict[str, Any]] = []
    all_actions: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if text:
            texts.append(text)
        custom = item.get("custom")
        if isinstance(custom, dict):
            cards = custom.get("cards")
            actions = custom.get("actions")
            if isinstance(cards, list):
                all_cards.extend([card for card in cards if isinstance(card, dict)])
            if isinstance(actions, list):
                all_actions.extend([action for action in actions if isinstance(action, dict)])
    reply.text = "\n".join(texts).strip()
    reply.response_chars = len(reply.text)
    reply.card_count = len(all_cards)
    reply.action_count = len(all_actions)
    reply.card_types = normalize_card_types(all_cards)
    reply.action_types = normalize_action_types(all_actions)
    reply.order_ids = extract_order_ids({"text": reply.text, "cards": all_cards, "actions": all_actions})
    return reply


def normalize_backend_messages(payload: Any) -> NormalizedReply:
    reply = NormalizedReply()
    if not isinstance(payload, dict):
        return reply
    messages = payload.get("messages")
    if not isinstance(messages, list):
        return reply
    texts: list[str] = []
    all_cards: list[dict[str, Any]] = []
    all_actions: list[dict[str, Any]] = []
    for item in messages:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if text:
            texts.append(text)
        cards = item.get("cards")
        actions = item.get("actions")
        if isinstance(cards, list):
            all_cards.extend([card for card in cards if isinstance(card, dict)])
        if isinstance(actions, list):
            all_actions.extend([action for action in actions if isinstance(action, dict)])
    reply.text = "\n".join(texts).strip()
    reply.response_chars = len(reply.text)
    reply.card_count = len(all_cards)
    reply.action_count = len(all_actions)
    reply.card_types = normalize_card_types(all_cards)
    reply.action_types = normalize_action_types(all_actions)
    reply.order_ids = extract_order_ids({"text": reply.text, "cards": all_cards, "actions": all_actions})
    return reply


def normalize_ollama_message(payload: Any) -> NormalizedReply:
    reply = NormalizedReply()
    if not isinstance(payload, dict):
        return reply
    message = payload.get("message")
    if isinstance(message, dict):
        reply.text = str(message.get("content") or "").strip()
    reply.response_chars = len(reply.text)
    reply.order_ids = extract_order_ids(reply.text)
    return reply


def build_ollama_messages(sample: ConversationSample, message: str) -> list[dict[str, str]]:
    system_prompt = (
        f"你是电商平台客服。当前场景族是 {sample.scenario_family}。"
        "禁止编造订单号、物流状态、退款结果。回答要简洁明确。"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message},
    ]


def system_supports_sample(system: SystemTarget, sample: ConversationSample) -> tuple[bool, list[str]]:
    missing = [capability for capability in sample.required_capabilities if not system.capabilities.get(capability, False)]
    return not missing, missing


def infer_input_order_ids(sample: ConversationSample) -> list[str]:
    payload = {
        "turns": [turn.message for turn in sample.turns if turn.message],
        "allowed_order_ids": sample.expected_outcomes.allowed_order_ids,
        "preconditions": sample.preconditions,
    }
    return extract_order_ids(payload)


def score_conversation(
    *,
    sample: ConversationSample,
    turn_events: list[TurnEvent],
    unsupported: bool,
) -> tuple[str, bool, bool, dict[str, Any]]:
    if unsupported:
        flags = {
            "supported": False,
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
        }
        return "na", False, False, flags

    combined_text = "\n".join(event.response_text for event in turn_events if event.response_text).strip()
    card_types = {card_type for event in turn_events for card_type in event.response_card_types}
    action_types = {action_type for event in turn_events for action_type in event.response_action_types}
    output_order_ids = {order_id for event in turn_events for order_id in event.response_order_ids}
    allowed_order_ids = set(sample.expected_outcomes.allowed_order_ids or infer_input_order_ids(sample))

    missing_required_keywords = bool(sample.expected_outcomes.required_any_text_keywords) and not contains_any(
        combined_text,
        sample.expected_outcomes.required_any_text_keywords,
    )
    contains_forbidden_keywords = contains_any(combined_text, sample.expected_outcomes.forbidden_text_keywords)
    missing_required_cards = any(card_type not in card_types for card_type in sample.expected_outcomes.required_card_types)
    missing_required_actions = any(action_type not in action_types for action_type in sample.expected_outcomes.required_action_types)
    missing_confirmation_buttons = sample.expected_outcomes.requires_confirmation_buttons and (
        "pending_action" not in card_types or "pending_action_decision" not in action_types
    )
    missing_order_id = sample.expected_outcomes.should_return_order_id and not bool(output_order_ids.intersection(allowed_order_ids))
    hallucinated_order_id = sample.expected_outcomes.must_avoid_hallucinated_order_id and bool(
        output_order_ids.difference(allowed_order_ids) if allowed_order_ids else output_order_ids.difference(infer_input_order_ids(sample))
    )
    login_block_failure = sample.expected_outcomes.should_block_without_login and not contains_any(
        combined_text,
        LOGIN_REQUIRED_PATTERNS,
    )
    image_turns = [event for event in turn_events if event.turn_kind == "upload_image"]
    image_flow_failure = bool(image_turns) and not all(event.success for event in image_turns)
    pending_turns = [event for event in turn_events if event.turn_kind == "pending_decision"]
    pending_decision_failure = bool(pending_turns) and not all(event.success for event in pending_turns)
    format_error = len(combined_text) < max(sample.expected_outcomes.min_response_chars, 1)
    if sample.expected_outcomes.required_card_types:
        format_error = False
    technical_success = all(event.success for event in turn_events if event.executed)
    passed = technical_success and not any(
        [
            missing_required_keywords,
            contains_forbidden_keywords,
            missing_required_cards,
            missing_required_actions,
            missing_confirmation_buttons,
            missing_order_id,
            hallucinated_order_id,
            login_block_failure,
            image_flow_failure,
            pending_decision_failure,
            format_error,
        ]
    )
    flags = {
        "supported": True,
        "missing_required_keywords": missing_required_keywords,
        "contains_forbidden_keywords": contains_forbidden_keywords,
        "missing_required_cards": missing_required_cards,
        "missing_required_actions": missing_required_actions,
        "missing_confirmation_buttons": missing_confirmation_buttons,
        "missing_order_id": missing_order_id,
        "hallucinated_order_id": hallucinated_order_id,
        "login_block_failure": login_block_failure,
        "image_flow_failure": image_flow_failure,
        "pending_decision_failure": pending_decision_failure,
        "format_error": format_error,
        "expired_pending_action_ok": contains_any(combined_text, EXPIRY_PATTERNS),
    }
    return ("pass" if passed else "fail"), technical_success, passed, flags


async def seed_knowledge_for_system(
    client: httpx.AsyncClient,
    system: SystemTarget,
    auth_cfg: AuthConfig,
    config: dict[str, Any],
) -> dict[str, Any]:
    seed_documents = resolve_knowledge_seed_documents(config)
    if not seed_documents:
        return {}
    if not (system.capabilities.get("supports_kb_policy") or system.capabilities.get("supports_kb_manual")):
        return {}
    if system.kind != "backend_chat":
        return {}

    login_url, me_url = get_or_create_login_urls(auth_cfg, system)
    merchant_auth = await login_for_auth_context(
        client,
        login_url=login_url,
        me_url=me_url,
        email=auth_cfg.merchant_email,
        password=auth_cfg.merchant_password,
    )
    seed_cfg = config.get("knowledge_seed") if isinstance(config.get("knowledge_seed"), dict) else {}
    index_path = require_string(seed_cfg, "index_path", default="/api/v1/kb/index")
    items: list[dict[str, Any]] = []
    for document in seed_documents:
        if document.source_type == "policy" and not system.capabilities.get("supports_kb_policy", False):
            continue
        if document.source_type == "manual" and not system.capabilities.get("supports_kb_manual", False):
            continue
        items.append(
            {
                "source_type": document.source_type,
                "title": document.title,
                "content": document.path.read_text(encoding="utf-8"),
                "version": document.version,
                "status": document.status,
                "metadata": document.metadata,
            }
        )
    if not items:
        return {}
    response = await client.post(
        f"{system.base_url.rstrip('/')}/{index_path.lstrip('/')}",
        json={"items": items},
        headers=merchant_auth.bearer_headers,
    )
    response.raise_for_status()
    payload = response.json() if response.content else {}
    return payload if isinstance(payload, dict) else {}


async def execute_turn(
    *,
    client: httpx.AsyncClient,
    system: SystemTarget,
    sample: ConversationSample,
    turn: TurnStep,
    turn_index: int,
    repeat: int,
    concurrency: int,
    conversation_index: int,
    config: dict[str, Any],
    auth_cfg: AuthConfig,
    auth_context: AuthContext,
    uploaded_attachments: list[str],
) -> tuple[TurnEvent, AuthContext, list[str]]:
    timestamp = now_iso()
    started_at = time.time()
    perf_started = time.perf_counter()
    status_code: int | None = None
    error_type = ""
    error_message = ""
    reply = NormalizedReply()
    success = False
    current_auth = auth_context
    current_attachments = list(uploaded_attachments)

    try:
        if turn.kind == "login":
            login_url, me_url = get_or_create_login_urls(auth_cfg, system)
            if sample.account != "customer":
                success = True
            else:
                current_auth = await login_for_auth_context(
                    client,
                    login_url=login_url,
                    me_url=me_url,
                    email=auth_cfg.customer_email,
                    password=auth_cfg.customer_password,
                )
                success = True
        elif turn.kind == "sleep_until_expired":
            await asyncio.sleep(turn.sleep_seconds)
            success = True
        elif turn.kind == "upload_image":
            if not system.capabilities.get("supports_attachments", False):
                raise RuntimeError("system does not support attachment upload")
            image_assets_dir = require_string(config, "image_assets_dir")
            image_case_map = config.get("image_case_map") if isinstance(config.get("image_case_map"), dict) else {}
            filename = str(image_case_map.get(turn.image_case) or "").strip()
            if not image_assets_dir or not filename:
                raise RuntimeError(f"missing image asset config for case {turn.image_case}")
            image_path = (ROOT_DIR / image_assets_dir / filename).resolve()
            upload_url = f"{system.base_url.rstrip('/')}/{system.upload_path.lstrip('/')}"
            headers = current_auth.bearer_headers if sample.account == "customer" else {}
            response = await client.post(
                upload_url,
                files={"file": (image_path.name, image_path.read_bytes(), "image/png")},
                headers=headers,
            )
            status_code = response.status_code
            response.raise_for_status()
            payload = response.json()
            attachment_id = str(payload.get("attachment_id") or "").strip() if isinstance(payload, dict) else ""
            if not attachment_id:
                raise RuntimeError("image upload succeeded but attachment_id is empty")
            current_attachments.append(attachment_id)
            success = True
        elif turn.kind == "chat_send":
            if system.kind == "rasa_rest":
                response = await client.post(
                    f"{system.base_url.rstrip('/')}/{system.path.lstrip('/')}",
                    json={
                        "sender": system.sender_id,
                        "message": turn.message,
                        "metadata": build_rasa_metadata(sample.account, current_auth),
                    },
                )
                status_code = response.status_code
                response.raise_for_status()
                reply = normalize_rasa_messages(response.json())
                success = True
            elif system.kind == "ollama_chat":
                response = await client.post(
                    f"{system.base_url.rstrip('/')}/{system.path.lstrip('/')}",
                    json={
                        "model": system.model,
                        "stream": False,
                        "messages": build_ollama_messages(sample, turn.message),
                        "options": {"temperature": 0},
                    },
                )
                status_code = response.status_code
                response.raise_for_status()
                reply = normalize_ollama_message(response.json())
                success = True
            elif system.kind == "backend_chat":
                attachments = current_attachments if turn.use_uploaded_attachments else []
                headers = current_auth.bearer_headers if sample.account == "customer" else {}
                response = await client.post(
                    f"{system.base_url.rstrip('/')}/{system.path.lstrip('/')}",
                    json={"message": turn.message, "sender_id": system.sender_id, "attachments": attachments},
                    headers=headers,
                )
                status_code = response.status_code
                response.raise_for_status()
                reply = normalize_backend_messages(response.json())
                success = True
            else:
                raise RuntimeError(f"unsupported system.kind: {system.kind}")
        elif turn.kind == "pending_decision":
            response = await client.post(
                f"{system.base_url.rstrip('/')}/{system.pending_action_path.lstrip('/')}",
                json={"decision": turn.decision},
                headers=current_auth.bearer_headers,
            )
            status_code = response.status_code
            response.raise_for_status()
            reply = normalize_backend_messages(response.json())
            success = True
        else:
            raise RuntimeError(f"unsupported turn.kind: {turn.kind}")
    except httpx.TimeoutException:
        error_type = "timeout"
        error_message = "request timeout"
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        error_type = "http_error"
        error_message = exc.response.text[:300]
    except Exception as exc:  # noqa: BLE001
        error_type = "runtime_error"
        error_message = str(exc)

    finished_at = time.time()
    latency_ms = round((time.perf_counter() - perf_started) * 1000, 2)
    event = TurnEvent(
        timestamp=timestamp,
        system=system.name,
        scenario_family=sample.scenario_family,
        scenario=sample.scenario,
        sample_id=sample.sample_id,
        tier=sample.tier,
        repeat=repeat,
        concurrency=concurrency,
        conversation_index=conversation_index,
        turn_index=turn_index,
        turn_id=turn.turn_id,
        turn_kind=turn.kind,
        requires_auth=sample.account == "customer",
        required_capabilities=list(sample.required_capabilities),
        executed=True,
        unsupported=False,
        success=success,
        http_status=status_code,
        error_type=error_type,
        error_message=error_message,
        latency_ms=latency_ms,
        started_at=started_at,
        finished_at=finished_at,
        response_text=reply.text,
        response_chars=reply.response_chars,
        response_card_count=reply.card_count,
        response_action_count=reply.action_count,
        response_card_types=reply.card_types,
        response_action_types=reply.action_types,
        response_order_ids=reply.order_ids,
    )
    return event, current_auth, current_attachments


async def execute_conversation(
    *,
    client: httpx.AsyncClient,
    system: SystemTarget,
    sample: ConversationSample,
    auth_cfg: AuthConfig,
    config: dict[str, Any],
    repeat: int,
    concurrency: int,
    conversation_index: int,
) -> tuple[ConversationEvent, list[TurnEvent]]:
    timestamp = now_iso()
    started_at = time.time()
    supported, missing_caps = system_supports_sample(system, sample)
    if not supported:
        turn_events = [
            TurnEvent(
                timestamp=timestamp,
                system=system.name,
                scenario_family=sample.scenario_family,
                scenario=sample.scenario,
                sample_id=sample.sample_id,
                tier=sample.tier,
                repeat=repeat,
                concurrency=concurrency,
                conversation_index=conversation_index,
                turn_index=index,
                turn_id=turn.turn_id,
                turn_kind=turn.kind,
                requires_auth=sample.account == "customer",
                required_capabilities=list(sample.required_capabilities),
                executed=False,
                unsupported=True,
                success=False,
                http_status=None,
                error_type="unsupported_capability",
                error_message="missing capabilities: " + ",".join(missing_caps),
                latency_ms=0.0,
                started_at=started_at,
                finished_at=started_at,
                response_text="",
                response_chars=0,
                response_card_count=0,
                response_action_count=0,
            )
            for index, turn in enumerate(sample.turns, start=1)
        ]
        quality_status, conversation_success, passed, flags = score_conversation(
            sample=sample,
            turn_events=turn_events,
            unsupported=True,
        )
        return (
            ConversationEvent(
                timestamp=timestamp,
                system=system.name,
                scenario_family=sample.scenario_family,
                scenario=sample.scenario,
                sample_id=sample.sample_id,
                tier=sample.tier,
                repeat=repeat,
                concurrency=concurrency,
                conversation_index=conversation_index,
                account=sample.account,
                required_capabilities=list(sample.required_capabilities),
                turn_count=len(sample.turns),
                executed_turns=0,
                unsupported=True,
                success=False,
                http_error_count=0,
                latency_ms=0.0,
                started_at=started_at,
                finished_at=started_at,
                quality_status=quality_status,
                conversation_success=conversation_success,
                passed=passed,
                quality_flags=flags,
            ),
            turn_events,
        )

    auth_context = AuthContext()
    uploaded_attachments: list[str] = []
    turn_events: list[TurnEvent] = []
    for turn_index, turn in enumerate(sample.turns, start=1):
        turn_event, auth_context, uploaded_attachments = await execute_turn(
            client=client,
            system=system,
            sample=sample,
            turn=turn,
            turn_index=turn_index,
            repeat=repeat,
            concurrency=concurrency,
            conversation_index=conversation_index,
            config=config,
            auth_cfg=auth_cfg,
            auth_context=auth_context,
            uploaded_attachments=uploaded_attachments,
        )
        turn_events.append(turn_event)
    finished_at = max((event.finished_at for event in turn_events), default=started_at)
    quality_status, conversation_success, passed, flags = score_conversation(
        sample=sample,
        turn_events=turn_events,
        unsupported=False,
    )
    return (
        ConversationEvent(
            timestamp=timestamp,
            system=system.name,
            scenario_family=sample.scenario_family,
            scenario=sample.scenario,
            sample_id=sample.sample_id,
            tier=sample.tier,
            repeat=repeat,
            concurrency=concurrency,
            conversation_index=conversation_index,
            account=sample.account,
            required_capabilities=list(sample.required_capabilities),
            turn_count=len(sample.turns),
            executed_turns=sum(1 for event in turn_events if event.executed),
            unsupported=False,
            success=all(event.success for event in turn_events if event.executed),
            http_error_count=sum(1 for event in turn_events if event.error_type == "http_error"),
            latency_ms=round((finished_at - started_at) * 1000, 2),
            started_at=started_at,
            finished_at=finished_at,
            quality_status=quality_status,
            conversation_success=conversation_success,
            passed=passed,
            quality_flags=flags,
        ),
        turn_events,
    )


def pick_samples(samples: list[ConversationSample], requests_per_level: int, seed: int) -> list[ConversationSample]:
    if requests_per_level <= 0 or requests_per_level >= len(samples):
        return list(samples)
    rng = random.Random(seed)
    repeatable = [sample for sample in samples if sample.repeatable]
    nonrepeatable = [sample for sample in samples if not sample.repeatable]
    rng.shuffle(repeatable)
    rng.shuffle(nonrepeatable)
    selected: list[ConversationSample] = []
    selected.extend(nonrepeatable[: min(len(nonrepeatable), requests_per_level)])
    remaining = max(0, requests_per_level - len(selected))
    if remaining <= 0:
        return selected[:requests_per_level]
    if not repeatable:
        rng.shuffle(samples)
        return samples[:requests_per_level]
    while len(selected) < requests_per_level:
        selected.append(repeatable[(len(selected) - len(nonrepeatable)) % len(repeatable)])
    rng.shuffle(selected)
    return selected


async def warmup_system(
    client: httpx.AsyncClient,
    system: SystemTarget,
    sample: ConversationSample,
    auth_cfg: AuthConfig,
    config: dict[str, Any],
    warmup_requests: int,
) -> None:
    for _ in range(max(0, warmup_requests)):
        try:
            await execute_conversation(
                client=client,
                system=system,
                sample=sample,
                auth_cfg=auth_cfg,
                config=config,
                repeat=0,
                concurrency=1,
                conversation_index=0,
            )
        except Exception:
            return


async def execute_batch(
    *,
    client: httpx.AsyncClient,
    system: SystemTarget,
    samples: list[ConversationSample],
    auth_cfg: AuthConfig,
    config: dict[str, Any],
    repeat: int,
    concurrency: int,
) -> tuple[list[ConversationEvent], list[TurnEvent]]:
    semaphore = asyncio.Semaphore(concurrency)

    async def guarded(item: tuple[int, ConversationSample]) -> tuple[ConversationEvent, list[TurnEvent]]:
        conversation_index, sample = item
        async with semaphore:
            return await execute_conversation(
                client=client,
                system=system,
                sample=sample,
                auth_cfg=auth_cfg,
                config=config,
                repeat=repeat,
                concurrency=concurrency,
                conversation_index=conversation_index,
            )

    results = await asyncio.gather(*(guarded(item) for item in enumerate(samples, start=1)))
    conversation_events = [item[0] for item in results]
    turn_events = [turn for _, turns in results for turn in turns]
    return conversation_events, turn_events


def write_jsonl(path: Path, records: list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def build_summary_rows(conversations: list[ConversationEvent]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, int, int], list[ConversationEvent]] = {}
    for event in conversations:
        groups.setdefault((event.system, event.scenario_family, event.concurrency, event.repeat), []).append(event)
    rows: list[dict[str, Any]] = []
    for key in sorted(groups.keys()):
        system, scenario_family, concurrency, repeat = key
        batch = groups[key]
        eligible = [event for event in batch if not event.unsupported]
        successful = [event for event in eligible if event.success]
        throughput_rps = 0.0
        if batch:
            started_at = min(event.started_at for event in batch)
            finished_at = max(event.finished_at for event in batch)
            elapsed = max(finished_at - started_at, 1e-6)
            throughput_rps = round(len(batch) / elapsed, 4)
        rows.append(
            {
                "system": system,
                "scenario_family": scenario_family,
                "concurrency": concurrency,
                "repeat": repeat,
                "conversations": len(batch),
                "eligible_conversations": len(eligible),
                "successful_conversations": len(successful),
                "unsupported_rate": round(sum(1 for event in batch if event.unsupported) / max(1, len(batch)), 4),
                "conversation_success_rate": round(
                    sum(1 for event in eligible if event.conversation_success) / max(1, len(eligible)),
                    4,
                ),
                "quality_pass_rate": round(sum(1 for event in eligible if event.passed) / max(1, len(eligible)), 4),
                "p50_ms": compute_percentile([event.latency_ms for event in batch], 0.50),
                "p95_ms": compute_percentile([event.latency_ms for event in batch], 0.95),
                "p99_ms": compute_percentile([event.latency_ms for event in batch], 0.99),
                "throughput_rps": throughput_rps,
                "avg_turn_count": round(statistics.mean(event.turn_count for event in batch), 2) if batch else 0.0,
            }
        )
    return rows


def build_quality_rows(conversations: list[ConversationEvent]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[ConversationEvent]] = {}
    for event in conversations:
        groups.setdefault((event.system, event.scenario_family), []).append(event)
    rows: list[dict[str, Any]] = []
    for key in sorted(groups.keys()):
        system, scenario_family = key
        batch = groups[key]
        eligible = [event for event in batch if not event.unsupported]
        rows.append(
            {
                "system": system,
                "scenario_family": scenario_family,
                "conversations": len(batch),
                "eligible_conversations": len(eligible),
                "unsupported_conversations": sum(1 for event in batch if event.unsupported),
                "conversation_success": sum(1 for event in eligible if event.conversation_success),
                "quality_pass": sum(1 for event in eligible if event.passed),
                "missing_required_keywords": sum(
                    1 for event in eligible if bool(event.quality_flags.get("missing_required_keywords"))
                ),
                "contains_forbidden_keywords": sum(
                    1 for event in eligible if bool(event.quality_flags.get("contains_forbidden_keywords"))
                ),
                "missing_required_cards": sum(
                    1 for event in eligible if bool(event.quality_flags.get("missing_required_cards"))
                ),
                "missing_required_actions": sum(
                    1 for event in eligible if bool(event.quality_flags.get("missing_required_actions"))
                ),
                "missing_confirmation_buttons": sum(
                    1 for event in eligible if bool(event.quality_flags.get("missing_confirmation_buttons"))
                ),
                "missing_order_id": sum(1 for event in eligible if bool(event.quality_flags.get("missing_order_id"))),
                "hallucinated_order_id": sum(
                    1 for event in eligible if bool(event.quality_flags.get("hallucinated_order_id"))
                ),
                "login_block_failures": sum(
                    1 for event in eligible if bool(event.quality_flags.get("login_block_failure"))
                ),
                "image_flow_failures": sum(
                    1 for event in eligible if bool(event.quality_flags.get("image_flow_failure"))
                ),
                "pending_decision_failures": sum(
                    1 for event in eligible if bool(event.quality_flags.get("pending_decision_failure"))
                ),
            }
        )
    return rows


def build_conversation_summary_rows(conversations: list[ConversationEvent]) -> list[dict[str, Any]]:
    return [asdict(event) for event in conversations]


def build_capability_coverage_rows(conversations: list[ConversationEvent]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[ConversationEvent]] = {}
    for event in conversations:
        for capability in event.required_capabilities:
            groups.setdefault((event.system, capability), []).append(event)
    rows: list[dict[str, Any]] = []
    for key in sorted(groups.keys()):
        system, capability = key
        batch = groups[key]
        eligible = [event for event in batch if not event.unsupported]
        rows.append(
            {
                "system": system,
                "capability": capability,
                "required_conversations": len(batch),
                "supported_conversations": len(eligible),
                "support_rate": round(len(eligible) / max(1, len(batch)), 4),
                "conversation_success_rate": round(
                    sum(1 for event in eligible if event.conversation_success) / max(1, len(eligible)),
                    4,
                ),
                "quality_pass_rate": round(sum(1 for event in eligible if event.passed) / max(1, len(eligible)), 4),
            }
        )
    return rows


def build_system_matrix(conversations: list[ConversationEvent], scenario_families: list[str]) -> list[dict[str, Any]]:
    systems = sorted({event.system for event in conversations})
    rows: list[dict[str, Any]] = []
    for system in systems:
        row: dict[str, Any] = {"system": system}
        for family in scenario_families:
            scoped = [event for event in conversations if event.system == system and event.scenario_family == family]
            eligible = [event for event in scoped if not event.unsupported]
            row[f"{family}_quality_pass_rate"] = round(sum(1 for event in eligible if event.passed) / max(1, len(eligible)), 4)
            row[f"{family}_conversation_success_rate"] = round(
                sum(1 for event in eligible if event.conversation_success) / max(1, len(eligible)),
                4,
            )
            row[f"{family}_unsupported_rate"] = round(sum(1 for event in scoped if event.unsupported) / max(1, len(scoped)), 4)
            row[f"{family}_p95_ms"] = compute_percentile([event.latency_ms for event in scoped], 0.95)
        rows.append(row)
    return rows


def render_markdown_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "_无数据_"
    headers = list(rows[0].keys())
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(header, "")) for header in headers) + " |")
    return "\n".join(lines)


def build_paper_tables(
    *,
    matrix_rows: list[dict[str, Any]],
    capability_rows: list[dict[str, Any]],
    summary_rows: list[dict[str, Any]],
) -> str:
    lines = ["# 论文可引用表", "", "## 主表：系统形态对照", render_markdown_table(matrix_rows), "", "## 补充表：能力覆盖率", render_markdown_table(capability_rows), "", "## 补充表：批次摘要", render_markdown_table(summary_rows), "", "## 威胁说明", "- `unsupported_rate` 表示系统不具备该场景所需能力，而不是模型回答失败。", "- `conversation_success_rate` 反映多轮流程层面的完成情况。", "- `quality_pass_rate` 同时受内容、结构与流程规则约束。"]
    return "\n".join(lines)


def build_report(
    *,
    output_dir: Path,
    config_path: Path,
    dataset_files: dict[str, Path],
    systems: list[str],
    scenario_families: list[str],
    profile: str,
    dataset_tier: str,
    auth_cfg: AuthConfig,
    summary_rows: list[dict[str, Any]],
    quality_rows: list[dict[str, Any]],
    matrix_rows: list[dict[str, Any]],
    capability_rows: list[dict[str, Any]],
) -> str:
    lines = [
        "# 客服链路 Benchmark 报告",
        "",
        f"- 生成时间：{now_iso()}",
        f"- profile：{profile}",
        f"- dataset_tier：{dataset_tier}",
        f"- 配置文件：{config_path}",
        f"- 结果目录：{output_dir}",
        f"- Python：{sys.version.split()[0]}",
        f"- 系统矩阵：{', '.join(systems)}",
        f"- 场景族：{', '.join(scenario_families)}",
        f"- 客户测试账号：{auth_cfg.customer_email}",
        f"- 商家知识库建索引账号：{auth_cfg.merchant_email}",
        "",
        "## 数据集",
        render_markdown_table([{"scenario_family": family, "path": path} for family, path in dataset_files.items()]),
        "",
        "## 系统主表",
        render_markdown_table(matrix_rows),
        "",
        "## 批次摘要",
        render_markdown_table(summary_rows),
        "",
        "## 质量统计",
        render_markdown_table(quality_rows),
        "",
        "## 能力覆盖率",
        render_markdown_table(capability_rows),
        "",
        "## 说明",
        "- `unsupported_rate` 仅统计系统能力缺失，不计为接口失败。",
        "- `conversation_success_rate` 反映多轮流程层面是否完整执行。",
        "- `quality_pass_rate` 同时约束文本内容、卡片结构和流程动作。",
    ]
    return "\n".join(lines)


async def execute_benchmark(args: argparse.Namespace) -> Path:
    config_path = args.config.resolve()
    config = load_config(config_path)
    auth_cfg = resolve_auth_config(config)
    selected_systems = parse_csv_values(args.systems)
    selected_families = parse_csv_values(args.scenarios) or list(DEFAULT_SCENARIO_FAMILIES)

    profile_cfg = config.get("profiles", {}).get(args.profile)
    if not isinstance(profile_cfg, dict):
        raise RuntimeError(f"profile 不存在: {args.profile}")
    dataset_tier = (args.dataset_tier or str(profile_cfg.get("dataset_tier") or "core")).strip()
    scenario_families = list(profile_cfg.get("scenarios") or selected_families)
    if args.scenarios.strip():
        scenario_families = selected_families

    system_targets = resolve_system_targets(config, selected_systems)
    dataset_files = resolve_dataset_files(args.dataset, dataset_tier, scenario_families)
    dataset_map = {family: load_dataset_file(path) for family, path in dataset_files.items()}

    concurrency_levels = parse_concurrency_override(args.concurrency) or [
        int(item) for item in profile_cfg.get("concurrency", []) if int(item) > 0
    ]
    requests_per_level = (
        int(args.requests_per_level)
        if args.requests_per_level is not None
        else int(profile_cfg.get("requests_per_level", 1))
    )
    repeats = int(args.repeats) if args.repeats is not None else int(profile_cfg.get("repeats", 1))
    timeout_sec = float(args.timeout_sec) if args.timeout_sec is not None else float(config.get("timeout_sec", 60))
    warmup_requests = int(args.warmup_requests) if args.warmup_requests is not None else int(config.get("warmup_requests", 0))
    seed = int(args.seed) if args.seed is not None else int(config.get("seed", 20260412))

    configured_results_root = str(config.get("results_dir") or "backend/benchmarks/results")
    results_root = args.results_root if args.results_root is not None else (ROOT_DIR / configured_results_root)
    if not results_root.is_absolute():
        results_root = (ROOT_DIR / results_root).resolve()
    output_dir = results_root / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{args.profile}_system_benchmark"
    output_dir.mkdir(parents=True, exist_ok=True)

    all_conversations: list[ConversationEvent] = []
    all_turns: list[TurnEvent] = []
    async with httpx.AsyncClient(timeout=timeout_sec) as client:
        for system_name, system in system_targets.items():
            if args.verbose:
                print(f"[benchmark] system={system_name}")
            await seed_knowledge_for_system(client, system, auth_cfg, config)
            warmup_sample = next(
                (
                    sample
                    for sample in dataset_map.get("recommendation", [])
                    if sample.account == "anonymous" and not sample.required_capabilities
                ),
                next(iter(dataset_map.values()))[0],
            )
            await warmup_system(client, system, warmup_sample, auth_cfg, config, warmup_requests)
            for family in scenario_families:
                samples = dataset_map[family]
                for repeat in range(1, repeats + 1):
                    for concurrency in concurrency_levels:
                        planned = pick_samples(
                            samples,
                            requests_per_level,
                            seed + repeat * 97 + concurrency * 17 + sum(ord(ch) for ch in system_name + family),
                        )
                        batch_conversations, batch_turns = await execute_batch(
                            client=client,
                            system=system,
                            samples=planned,
                            auth_cfg=auth_cfg,
                            config=config,
                            repeat=repeat,
                            concurrency=concurrency,
                        )
                        all_conversations.extend(batch_conversations)
                        all_turns.extend(batch_turns)
                        if args.verbose:
                            print(
                                f"[benchmark] system={system_name} family={family} "
                                f"repeat={repeat} concurrency={concurrency} conversations={len(batch_conversations)}"
                            )

    summary_rows = build_summary_rows(all_conversations)
    quality_rows = build_quality_rows(all_conversations)
    conversation_rows = build_conversation_summary_rows(all_conversations)
    capability_rows = build_capability_coverage_rows(all_conversations)
    matrix_rows = build_system_matrix(all_conversations, scenario_families)

    raw_events_path = output_dir / "raw_events.jsonl"
    turn_events_path = output_dir / "turn_events.jsonl"
    summary_path = output_dir / "summary.csv"
    quality_path = output_dir / "scenario_quality.csv"
    matrix_path = output_dir / "system_matrix.csv"
    conversation_path = output_dir / "conversation_summary.csv"
    capability_path = output_dir / "capability_coverage.csv"
    report_path = output_dir / "report.md"
    paper_tables_path = output_dir / "paper_tables.md"

    write_jsonl(raw_events_path, all_conversations)
    write_jsonl(turn_events_path, all_turns)
    write_csv(summary_path, summary_rows)
    write_csv(quality_path, quality_rows)
    write_csv(matrix_path, matrix_rows)
    write_csv(conversation_path, conversation_rows)
    write_csv(capability_path, capability_rows)
    report_path.write_text(
        build_report(
            output_dir=output_dir,
            config_path=config_path,
            dataset_files=dataset_files,
            systems=list(system_targets.keys()),
            scenario_families=scenario_families,
            profile=args.profile,
            dataset_tier=dataset_tier,
            auth_cfg=auth_cfg,
            summary_rows=summary_rows,
            quality_rows=quality_rows,
            matrix_rows=matrix_rows,
            capability_rows=capability_rows,
        ),
        encoding="utf-8",
    )
    paper_tables_path.write_text(
        build_paper_tables(
            matrix_rows=matrix_rows,
            capability_rows=capability_rows,
            summary_rows=summary_rows,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"output_dir": str(output_dir), "conversations": len(all_conversations), "turns": len(all_turns)}, ensure_ascii=False))
    return output_dir


def main() -> None:
    args = parse_args()
    asyncio.run(execute_benchmark(args))


if __name__ == "__main__":
    main()
