from __future__ import annotations

import argparse
import asyncio
import hashlib
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

from .dataset import infer_layer_score_profile
from .io_utils import CONFIG_DIR, DATASET_DIR, ROOT_DIR, load_structured_file, render_markdown_table, write_csv, write_json, write_jsonl


DEFAULT_CONFIG_PATH = CONFIG_DIR / "experiment.yaml"
DEFAULT_PROMPT_ROOT = DATASET_DIR
DEFAULT_SCENARIO_FAMILIES = (
    "recommendation",
    "order_query",
    "logistics_query",
    "after_sales_query",
    "knowledge_and_multimodal",
    "transactional_action",
)
SUPPORTED_BENCHMARK_SUITES = ("shared_core", "agent_extension")
SELECTION_MODE_DEFAULTS = {
    "quick": "sampled",
    "standard": "all_unique",
    "paper": "all_unique",
}
PRIMARY_FAILURE_PRIORITY = (
    "unsupported",
    "technical_failure",
    "image_flow_failure",
    "pending_decision_failure",
    "hallucinated_order_id",
    "missing_order_id",
    "missing_required_cards",
    "missing_required_actions",
    "missing_confirmation_buttons",
    "login_block_failure",
    "contains_forbidden_keywords",
    "missing_required_keywords",
    "format_error",
)
PROMPT_VERSION_FILES = {
    "agent_final_answer": (ROOT_DIR / "backend" / "prompts" / "agent_final_answer.md").resolve(),
    "rasa_review": (ROOT_DIR / "backend" / "prompts" / "rasa_review.md").resolve(),
    "image_analysis": (ROOT_DIR / "backend" / "prompts" / "image_analysis.md").resolve(),
}
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
LOGIN_REQUIRED_PATTERNS = [
    "please log in",
    "login first",
    "sign in first",
    "authentication required",
]
EXPIRY_PATTERNS = [
    "expired",
    "request expired",
    "timed out",
    "no pending action",
]

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
    required_all_text_keywords: list[str]
    required_keyword_groups: list[list[str]]
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
    benchmark_suite: str
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
    layer: str = "business"
    score_profile: str = "structured_business"


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
    benchmark_suite: str
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
    benchmark_suite: str
    tier: str
    repeat: int
    concurrency: int
    conversation_index: int
    account: str
    layer: str
    score_profile: str
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
    parser = argparse.ArgumentParser(description="���� benchmark �����̡�")
    parser.add_argument("--systems", default="", help="���ŷָ��ϵͳ�����б��Ĭ�϶�ȡ�����е�ȫ��ϵͳ��")
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
        raise ValueError("����ֵ������� 0��")
    return parsed


def resolve_selection_mode(profile: str, profile_cfg: dict[str, Any]) -> str:
    raw_mode = str(profile_cfg.get("selection_mode") or "").strip().lower()
    if raw_mode in {"sampled", "all_unique"}:
        return raw_mode
    return SELECTION_MODE_DEFAULTS.get(profile, "all_unique")


def select_primary_failure_reason(flags: dict[str, Any]) -> str:
    for reason in PRIMARY_FAILURE_PRIORITY:
        if bool(flags.get(reason)):
            return reason
    return ""


def load_config(path: Path) -> dict[str, Any]:
    payload = load_structured_file(path)
    if not isinstance(payload, dict):
        raise RuntimeError(f"Benchmark ���ñ����Ƕ���{path}")
    return payload


def require_string(mapping: dict[str, Any], key: str, *, default: str = "") -> str:
    value = mapping.get(key, default)
    return str(value or "").strip()


def resolve_auth_config(config: dict[str, Any]) -> AuthConfig:
    auth_cfg = config.get("auth")
    if not isinstance(auth_cfg, dict):
        raise RuntimeError("ȱ�� auth ���á�")
    customer = auth_cfg.get("customer")
    merchant = auth_cfg.get("merchant")
    if not isinstance(customer, dict):
        raise RuntimeError("ȱ�� auth.customer ���á�")
    if not isinstance(merchant, dict):
        raise RuntimeError("ȱ�� auth.merchant ���á�")
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
        capabilities[key] = bool(raw_caps.get(key, item.get(key, default_value)))
    return capabilities


def resolve_system_targets(config: dict[str, Any], requested_systems: list[str]) -> dict[str, SystemTarget]:
    systems_cfg = config.get("systems")
    if not isinstance(systems_cfg, dict):
        raise RuntimeError("ȱ�� systems ���á�")
    selected_names = requested_systems or list(systems_cfg.keys())
    targets: dict[str, SystemTarget] = {}
    for name in selected_names:
        item = systems_cfg.get(name)
        if not isinstance(item, dict):
            raise RuntimeError(f"δ�ҵ�ϵͳ���ã�{name}")
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
            raise RuntimeError(f"ϵͳ���ò�������{name}")
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
    raw = payload.get("expected_outcomes")
    if not isinstance(raw, dict):
        raw = dict(payload.get("checks") or {})
    return ExpectedOutcomes(
        required_any_text_keywords=[str(item).strip() for item in raw.get("required_any_text_keywords", raw.get("required_any_keywords", [])) if str(item).strip()],
        required_all_text_keywords=[str(item).strip() for item in raw.get("required_all_text_keywords", []) if str(item).strip()],
        required_keyword_groups=[
            [str(keyword).strip() for keyword in group if str(keyword).strip()]
            for group in raw.get("required_keyword_groups", [])
            if isinstance(group, list)
        ],
        forbidden_text_keywords=[str(item).strip() for item in raw.get("forbidden_text_keywords", raw.get("forbidden_keywords", [])) if str(item).strip()],
        required_card_types=[str(item).strip() for item in raw.get("required_card_types", []) if str(item).strip()],
        required_action_types=[str(item).strip() for item in raw.get("required_action_types", []) if str(item).strip()],
        requires_confirmation_buttons=bool(raw.get("requires_confirmation_buttons", raw.get("requires_confirmation", False))),
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
            scenario_family = str(payload.get("scenario_family") or payload.get("scenario") or path.stem).strip()
            layer, score_profile = infer_layer_score_profile(scenario_family)
            records.append(
                ConversationSample(
                    sample_id=str(payload.get("id") or f"{path.stem}-{line_no}"),
                    benchmark_suite=str(payload.get("benchmark_suite") or "shared_core").strip(),
                    scenario_family=scenario_family,
                    scenario=str(payload.get("scenario") or path.stem).strip(),
                    turns=turns,
                    account=str(payload.get("account") or ("customer" if payload.get("requires_auth") else "anonymous")).strip(),
                    required_capabilities=[str(item).strip() for item in payload.get("required_capabilities", []) if str(item).strip()],
                    preconditions=dict(payload.get("preconditions") or {}),
                    expected_outcomes=parse_expected_outcomes(payload),
                    tags=[str(item).strip() for item in payload.get("tags", []) if str(item).strip()],
                    tier=str(payload.get("tier") or "legacy").strip(),
                    repeatable=bool(payload.get("repeatable", True)),
                    layer=str(payload.get("layer") or layer).strip(),
                    score_profile=str(payload.get("score_profile") or score_profile).strip(),
                )
            )
    if not records:
        raise RuntimeError(f"���ݼ�Ϊ�գ�{path}")
    return records


def resolve_dataset_files(dataset_arg: Path | None, dataset_tier: str, scenario_families: list[str]) -> dict[str, Path]:
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
    raise RuntimeError("--dataset can point to a file only when exactly one scenario family is selected.")


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


def contains_all(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return all(keyword.lower() in lowered for keyword in keywords if keyword)


def matches_keyword_groups(text: str, keyword_groups: list[list[str]]) -> bool:
    lowered = text.lower()
    for group in keyword_groups:
        normalized_group = [keyword.lower() for keyword in group if keyword]
        if normalized_group and not any(keyword in lowered for keyword in normalized_group):
            return False
    return True


def extract_order_ids(value: Any) -> list[str]:
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    return sorted(set(match.group(0).upper() for match in ORDER_ID_RE.finditer(text)))


def collect_prompt_versions() -> list[dict[str, str]]:
    versions: list[dict[str, str]] = []
    for name, path in PROMPT_VERSION_FILES.items():
        content = path.read_text(encoding="utf-8-sig")
        versions.append(
            {
                "name": name,
                "path": str(path),
                "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            }
        )
    return versions


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
        raise RuntimeError("��¼�ɹ���δ���� access_token��")
    me_response = await client.get(me_url, headers={"Authorization": f"Bearer {token}"})
    me_response.raise_for_status()
    me_payload = me_response.json()
    if not isinstance(me_payload, dict):
        raise RuntimeError("auth/me ���ظ�ʽ��Ч��")
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
        raise RuntimeError(f"ϵͳȱ�ٵ�¼���ã�{system.name}")
    return login_url, me_url


def build_rasa_metadata(account: str, auth_context: AuthContext, sender_id: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {"frontend_base_url": "http://localhost:5173", "benchmark_sender_id": sender_id}
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
    output: list[str] = []
    for item in items:
        if isinstance(item, dict):
            card_type = str(item.get("type") or "").strip()
            if card_type:
                output.append(card_type)
    return output


def normalize_action_types(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []
    output: list[str] = []
    for item in items:
        if isinstance(item, dict):
            action_type = str(item.get("type") or "").strip()
            if action_type:
                output.append(action_type)
    return output


def _collect_cards_actions(item: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cards: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    for key in ("cards", "actions"):
        value = item.get(key)
        if isinstance(value, list):
            if key == "cards":
                cards.extend([entry for entry in value if isinstance(entry, dict)])
            else:
                actions.extend([entry for entry in value if isinstance(entry, dict)])
    custom = item.get("custom")
    if isinstance(custom, dict):
        custom_cards = custom.get("cards")
        custom_actions = custom.get("actions")
        if isinstance(custom_cards, list):
            cards.extend([entry for entry in custom_cards if isinstance(entry, dict)])
        if isinstance(custom_actions, list):
            actions.extend([entry for entry in custom_actions if isinstance(entry, dict)])
    return cards, actions


def _finalize_reply(texts: list[str], cards: list[dict[str, Any]], actions: list[dict[str, Any]]) -> NormalizedReply:
    text = "\n".join(texts).strip()
    return NormalizedReply(
        text=text,
        response_chars=len(text),
        card_count=len(cards),
        action_count=len(actions),
        card_types=normalize_card_types(cards),
        action_types=normalize_action_types(actions),
        order_ids=extract_order_ids({"text": text, "cards": cards, "actions": actions}),
    )


def normalize_rasa_messages(payload: Any) -> NormalizedReply:
    if not isinstance(payload, list):
        return NormalizedReply()
    texts: list[str] = []
    cards: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if text:
            texts.append(text)
        extra_cards, extra_actions = _collect_cards_actions(item)
        cards.extend(extra_cards)
        actions.extend(extra_actions)
    return _finalize_reply(texts, cards, actions)


def normalize_backend_messages(payload: Any) -> NormalizedReply:
    if isinstance(payload, list):
        return normalize_rasa_messages(payload)
    if not isinstance(payload, dict):
        return NormalizedReply()
    messages = payload.get("messages")
    if not isinstance(messages, list):
        text = str(payload.get("text") or payload.get("message") or "").strip()
        cards, actions = _collect_cards_actions(payload)
        return _finalize_reply([text] if text else [], cards, actions)
    texts: list[str] = []
    cards: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    for item in messages:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if text:
            texts.append(text)
        extra_cards, extra_actions = _collect_cards_actions(item)
        cards.extend(extra_cards)
        actions.extend(extra_actions)
    return _finalize_reply(texts, cards, actions)


def normalize_ollama_message(payload: Any) -> NormalizedReply:
    if not isinstance(payload, dict):
        return NormalizedReply()
    text = ""
    message = payload.get("message")
    if isinstance(message, dict):
        text = str(message.get("content") or "").strip()
    if not text:
        text = str(payload.get("response") or "").strip()
    return _finalize_reply([text] if text else [], [], [])


def build_ollama_messages(sample: ConversationSample, message: str) -> list[dict[str, str]]:
    system_prompt = (
        "You are participating in a benchmark. Answer the user request directly and do not invent order ids, "
        "logistics numbers, cards, buttons, or backend state."
    )
    if sample.account == "customer":
        system_prompt += " The current user is already authenticated."
    else:
        system_prompt += " The current user is anonymous."
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message},
    ]


def infer_input_order_ids(sample: ConversationSample) -> list[str]:
    from_turns = extract_order_ids(" ".join(turn.message for turn in sample.turns))
    from_preconditions = [str(item).strip().upper() for item in sample.preconditions.get("allowed_order_ids", []) if str(item).strip()]
    return sorted(set(from_turns + from_preconditions))


def build_conversation_session_id(run_id: str, sample: ConversationSample, repeat: int, concurrency: int, conversation_index: int) -> str:
    return (
        f"benchmark_{run_id}_sample_{sample.sample_id}_repeat_{repeat}_"
        f"concurrency_{concurrency}_conversation_{conversation_index}"
    )


def make_conversation_sender_id(
    *,
    system: SystemTarget,
    sample: ConversationSample,
    repeat: int,
    concurrency: int,
    conversation_index: int,
    run_id: str,
    auth_context: AuthContext | None = None,
) -> str:
    session_id = build_conversation_session_id(run_id, sample, repeat, concurrency, conversation_index)
    if system.kind == "backend_chat" and sample.account == "customer" and auth_context and auth_context.user_id:
        return f"{auth_context.user_id}:{session_id}"
    return f"{system.sender_id}:{session_id}"


def score_conversation(
    *,
    sample: ConversationSample,
    turn_events: list[TurnEvent],
    unsupported: bool,
) -> tuple[str, bool, bool, dict[str, Any]]:
    if unsupported:
        flags = {
            "supported": False,
            "unsupported": True,
            "technical_failure": False,
            "format_error": False,
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
            "expired_pending_action": False,
        }
        flags["primary_failure_reason"] = select_primary_failure_reason(flags)
        return "na", False, False, flags

    combined_text = "\n".join(event.response_text for event in turn_events if event.response_text).strip()
    card_types = {card_type for event in turn_events for card_type in event.response_card_types}
    action_types = {action_type for event in turn_events for action_type in event.response_action_types}
    output_order_ids = {order_id for event in turn_events for order_id in event.response_order_ids}
    allowed_order_ids = set(sample.expected_outcomes.allowed_order_ids or infer_input_order_ids(sample))
    technical_success = all(event.success for event in turn_events if event.executed)
    technical_failure = not technical_success
    missing_required_keywords = (
        (bool(sample.expected_outcomes.required_any_text_keywords) and not contains_any(combined_text, sample.expected_outcomes.required_any_text_keywords))
        or (bool(sample.expected_outcomes.required_all_text_keywords) and not contains_all(combined_text, sample.expected_outcomes.required_all_text_keywords))
        or (bool(sample.expected_outcomes.required_keyword_groups) and not matches_keyword_groups(combined_text, sample.expected_outcomes.required_keyword_groups))
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
    expired_pending_action = bool(pending_turns) and contains_any(combined_text, EXPIRY_PATTERNS)
    format_error = len(combined_text) < max(sample.expected_outcomes.min_response_chars, 1)
    if sample.expected_outcomes.required_card_types or sample.expected_outcomes.required_action_types:
        format_error = False

    failure_flags = {
        "unsupported": False,
        "technical_failure": technical_failure,
        "image_flow_failure": image_flow_failure,
        "pending_decision_failure": pending_decision_failure,
        "hallucinated_order_id": hallucinated_order_id,
        "missing_order_id": missing_order_id,
        "missing_required_cards": missing_required_cards,
        "missing_required_actions": missing_required_actions,
        "missing_confirmation_buttons": missing_confirmation_buttons,
        "login_block_failure": login_block_failure,
        "contains_forbidden_keywords": contains_forbidden_keywords,
        "missing_required_keywords": missing_required_keywords,
        "format_error": format_error,
    }
    passed = not any(failure_flags.values())
    flags = {
        "supported": True,
        **failure_flags,
        "expired_pending_action": expired_pending_action,
    }
    primary_failure_reason = "" if passed else select_primary_failure_reason(flags)
    if not passed and not primary_failure_reason:
        flags["format_error"] = True
        primary_failure_reason = "format_error"
    flags["primary_failure_reason"] = primary_failure_reason
    return ("pass" if passed else "fail"), technical_success, passed, flags


def check_system_supports_sample(system: SystemTarget, sample: ConversationSample) -> bool:
    if sample.expected_outcomes.should_be_unsupported:
        return False
    for capability in sample.required_capabilities:
        if not system.capabilities.get(capability, False):
            return False
    return True


async def execute_turn(
    *,
    client: httpx.AsyncClient,
    system: SystemTarget,
    sample: ConversationSample,
    sender_id: str,
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
            if sample.account == "customer":
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
            if not system.capabilities.get("supports_attachments", False) or not system.upload_path:
                raise RuntimeError("��ǰϵͳ��֧��ͼƬ�ϴ���")
            image_assets_dir = require_string(config, "image_assets_dir")
            image_case_map = config.get("image_case_map") if isinstance(config.get("image_case_map"), dict) else {}
            filename = str(image_case_map.get(turn.image_case) or "").strip()
            if not image_assets_dir or not filename:
                raise RuntimeError(f"ȱ��ͼƬ�ز����ã�{turn.image_case}")
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
                raise RuntimeError("ͼƬ�ϴ��ɹ���δ���� attachment_id��")
            current_attachments.append(attachment_id)
            success = True
        elif turn.kind == "chat_send":
            if system.kind == "rasa_rest":
                response = await client.post(
                    f"{system.base_url.rstrip('/')}/{system.path.lstrip('/')}",
                    json={
                        "sender": sender_id,
                        "message": turn.message,
                        "metadata": build_rasa_metadata(sample.account, current_auth, sender_id),
                    },
                )
                status_code = response.status_code
                response.raise_for_status()
                reply = normalize_rasa_messages(response.json())
                success = True
            elif system.kind == "backend_chat":
                attachments = current_attachments if turn.use_uploaded_attachments else []
                headers = current_auth.bearer_headers if sample.account == "customer" else {}
                response = await client.post(
                    f"{system.base_url.rstrip('/')}/{system.path.lstrip('/')}",
                    json={"message": turn.message, "sender_id": sender_id, "attachments": attachments},
                    headers=headers,
                )
                status_code = response.status_code
                response.raise_for_status()
                reply = normalize_backend_messages(response.json())
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
            else:
                raise RuntimeError(f"��֧�ֵ� system.kind��{system.kind}")
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
            raise RuntimeError(f"��֧�ֵ� turn.kind��{turn.kind}")
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
        benchmark_suite=sample.benchmark_suite,
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


async def seed_knowledge_for_system(
    client: httpx.AsyncClient,
    system: SystemTarget,
    auth_cfg: AuthConfig,
    config: dict[str, Any],
) -> None:
    if system.kind != "backend_chat":
        return
    seed_cfg = config.get("knowledge_seed")
    if not isinstance(seed_cfg, dict):
        return
    index_path = require_string(seed_cfg, "index_path")
    documents = resolve_knowledge_seed_documents(config)
    if not index_path or not documents:
        return
    login_url, me_url = get_or_create_login_urls(auth_cfg, system)
    merchant_auth = await login_for_auth_context(
        client,
        login_url=login_url,
        me_url=me_url,
        email=auth_cfg.merchant_email,
        password=auth_cfg.merchant_password,
    )
    for document in documents:
        payload = {
            "items": [
                {
                    "source_type": document.source_type,
                    "title": document.title,
                    "content": document.path.read_text(encoding="utf-8-sig"),
                    "version": document.version,
                    "status": document.status,
                    "metadata": document.metadata,
                }
            ]
        }
        response = await client.post(
            f"{system.base_url.rstrip('/')}/{index_path.lstrip('/')}",
            json=payload,
            headers=merchant_auth.bearer_headers,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            response_text = response.text.strip()
            detail = response_text[:500] if response_text else "<empty response>"
            raise RuntimeError(
                f"Knowledge seed failed for system '{system.name}' with status {response.status_code}: {detail}"
            ) from exc


async def warmup_system(
    client: httpx.AsyncClient,
    system: SystemTarget,
    sample: ConversationSample,
    auth_cfg: AuthConfig,
    config: dict[str, Any],
    warmup_requests: int,
    run_id: str,
) -> None:
    if warmup_requests <= 0:
        return
    for index in range(1, warmup_requests + 1):
        auth_context = AuthContext()
        attachments: list[str] = []
        for turn_index, turn in enumerate(sample.turns[:1], start=1):
            sender_id = make_conversation_sender_id(
                system=system,
                sample=sample,
                repeat=0,
                concurrency=1,
                conversation_index=index,
                run_id=run_id,
                auth_context=auth_context,
            )
            _, auth_context, attachments = await execute_turn(
                client=client,
                system=system,
                sample=sample,
                sender_id=sender_id,
                turn=turn,
                turn_index=turn_index,
                repeat=0,
                concurrency=1,
                conversation_index=index,
                config=config,
                auth_cfg=auth_cfg,
                auth_context=auth_context,
                uploaded_attachments=attachments,
            )


def pick_samples(
    samples: list[ConversationSample],
    count: int,
    seed: int,
    *,
    selection_mode: str,
    repeat: int,
) -> list[ConversationSample]:
    if not samples:
        return []

    repeatable = [sample for sample in samples if sample.repeatable]
    fixed = [sample for sample in samples if not sample.repeatable and repeat == 1]
    rng = random.Random(seed)

    if selection_mode == "all_unique":
        planned = list(repeatable) + list(fixed)
        rng.shuffle(planned)
        return planned

    if count <= 0:
        return []

    population = list(repeatable) + list(fixed)
    rng.shuffle(population)
    selected = population[: min(count, len(population))]
    if len(selected) >= count or not repeatable:
        return selected

    repeatable_pool = list(repeatable)
    rng.shuffle(repeatable_pool)
    cursor = 0
    while len(selected) < count:
        selected.append(repeatable_pool[cursor % len(repeatable_pool)])
        cursor += 1
    return selected


def sample_allowed_for_profile(sample: ConversationSample, profile: str) -> bool:
    tags = {tag.strip().lower() for tag in sample.tags if tag.strip()}
    return not ("paper_only" in tags and profile != "paper")


def build_sample_metadata_row(sample: ConversationSample) -> dict[str, Any]:
    return {
        "sample_id": sample.sample_id,
        "benchmark_suite": sample.benchmark_suite,
        "scenario_family": sample.scenario_family,
        "scenario": sample.scenario,
        "tier": sample.tier,
        "repeatable": sample.repeatable,
        "layer": sample.layer,
        "score_profile": sample.score_profile,
        "tags": list(sample.tags),
    }


def build_expected_sample_row(
    *,
    system: str,
    sample: ConversationSample,
    repeat: int,
    concurrency: int,
    selection_mode: str,
) -> dict[str, Any]:
    row = build_sample_metadata_row(sample)
    row.update(
        {
            "system": system,
            "repeat": repeat,
            "concurrency": concurrency,
            "selection_mode": selection_mode,
        }
    )
    return row


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
    run_id: str,
) -> tuple[ConversationEvent, list[TurnEvent]]:
    timestamp = now_iso()
    started_at = time.time()
    if not check_system_supports_sample(system, sample):
        event = ConversationEvent(
            timestamp=timestamp,
            system=system.name,
            scenario_family=sample.scenario_family,
            scenario=sample.scenario,
            sample_id=sample.sample_id,
            benchmark_suite=sample.benchmark_suite,
            tier=sample.tier,
            repeat=repeat,
            concurrency=concurrency,
            conversation_index=conversation_index,
            account=sample.account,
            layer=sample.layer,
            score_profile=sample.score_profile,
            required_capabilities=list(sample.required_capabilities),
            turn_count=len(sample.turns),
            executed_turns=0,
            unsupported=True,
            success=False,
            http_error_count=0,
            latency_ms=0.0,
            started_at=started_at,
            finished_at=started_at,
            quality_status="na",
            conversation_success=False,
            passed=False,
            quality_flags={
                "supported": False,
                "unsupported": True,
                "technical_failure": False,
                "format_error": False,
                "primary_failure_reason": "unsupported",
            },
        )
        return event, []

    auth_context = AuthContext()
    attachments: list[str] = []
    turn_events: list[TurnEvent] = []
    for turn_index, turn in enumerate(sample.turns, start=1):
        sender_id = make_conversation_sender_id(
            system=system,
            sample=sample,
            repeat=repeat,
            concurrency=concurrency,
            conversation_index=conversation_index,
            run_id=run_id,
            auth_context=auth_context,
        )
        turn_event, auth_context, attachments = await execute_turn(
            client=client,
            system=system,
            sample=sample,
            sender_id=sender_id,
            turn=turn,
            turn_index=turn_index,
            repeat=repeat,
            concurrency=concurrency,
            conversation_index=conversation_index,
            config=config,
            auth_cfg=auth_cfg,
            auth_context=auth_context,
            uploaded_attachments=attachments,
        )
        turn_events.append(turn_event)

    finished_at = time.time()
    quality_status, technical_success, passed, flags = score_conversation(sample=sample, turn_events=turn_events, unsupported=False)
    event = ConversationEvent(
        timestamp=timestamp,
        system=system.name,
        scenario_family=sample.scenario_family,
        scenario=sample.scenario,
        sample_id=sample.sample_id,
        benchmark_suite=sample.benchmark_suite,
        tier=sample.tier,
        repeat=repeat,
        concurrency=concurrency,
        conversation_index=conversation_index,
        account=sample.account,
        layer=sample.layer,
        score_profile=sample.score_profile,
        required_capabilities=list(sample.required_capabilities),
        turn_count=len(sample.turns),
        executed_turns=sum(1 for item in turn_events if item.executed),
        unsupported=False,
        success=technical_success,
        http_error_count=sum(1 for item in turn_events if item.error_type == "http_error"),
        latency_ms=round((finished_at - started_at) * 1000, 2),
        started_at=started_at,
        finished_at=finished_at,
        quality_status=quality_status,
        conversation_success=technical_success,
        passed=passed,
        quality_flags=flags,
    )
    return event, turn_events


async def execute_batch(
    *,
    client: httpx.AsyncClient,
    system: SystemTarget,
    samples: list[ConversationSample],
    auth_cfg: AuthConfig,
    config: dict[str, Any],
    repeat: int,
    concurrency: int,
    run_id: str,
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
                run_id=run_id,
            )

    results = await asyncio.gather(*(guarded(item) for item in enumerate(samples, start=1)))
    conversation_events = [item[0] for item in results]
    turn_events = [turn for _, turns in results for turn in turns]
    return conversation_events, turn_events


def build_summary_rows(conversations: list[ConversationEvent]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, int, int], list[ConversationEvent]] = {}
    for event in conversations:
        groups.setdefault((event.system, event.benchmark_suite, event.scenario_family, event.concurrency, event.repeat), []).append(event)
    rows: list[dict[str, Any]] = []
    for key in sorted(groups.keys()):
        system, benchmark_suite, scenario_family, concurrency, repeat = key
        batch = groups[key]
        eligible = [event for event in batch if not event.unsupported]
        duration_sec = max(0.001, max(event.finished_at for event in batch) - min(event.started_at for event in batch))
        layer = batch[0].layer if batch else ""
        score_profile = batch[0].score_profile if batch else ""
        business_eligible = [event for event in eligible if event.layer == "business"]
        boundary_eligible = [event for event in eligible if event.layer == "boundary"]
        rows.append(
            {
                "system": system,
                "benchmark_suite": benchmark_suite,
                "scenario_family": scenario_family,
                "layer": layer,
                "score_profile": score_profile,
                "concurrency": concurrency,
                "repeat": repeat,
                "conversations": len(batch),
                "eligible_conversations": len(eligible),
                "unsupported_conversations": sum(1 for event in batch if event.unsupported),
                "unsupported_rate": round(sum(1 for event in batch if event.unsupported) / max(1, len(batch)), 4),
                "technical_success_rate": round(sum(1 for event in eligible if event.success) / max(1, len(eligible)), 4),
                "conversation_success_rate": round(sum(1 for event in eligible if event.conversation_success) / max(1, len(eligible)), 4),
                "quality_pass_rate": round(sum(1 for event in eligible if event.passed) / max(1, len(eligible)), 4),
                "hallucination_free_rate": round(
                    sum(1 for event in eligible if not bool(event.quality_flags.get("hallucinated_order_id"))) / max(1, len(eligible)),
                    4,
                ),
                "business_pass_rate": round(sum(1 for event in business_eligible if event.passed) / max(1, len(business_eligible)), 4),
                "boundary_safety_pass_rate": round(sum(1 for event in boundary_eligible if event.passed) / max(1, len(boundary_eligible)), 4),
                "p50_ms": compute_percentile([event.latency_ms for event in batch], 0.50),
                "p95_ms": compute_percentile([event.latency_ms for event in batch], 0.95),
                "p99_ms": compute_percentile([event.latency_ms for event in batch], 0.99),
                "throughput_rps": round(len(batch) / duration_sec, 4),
                "avg_turn_count": round(statistics.mean(event.turn_count for event in batch), 2) if batch else 0.0,
            }
        )
    return rows


def build_quality_rows(conversations: list[ConversationEvent]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[ConversationEvent]] = {}
    for event in conversations:
        groups.setdefault((event.system, event.benchmark_suite, event.scenario_family), []).append(event)
    rows: list[dict[str, Any]] = []
    for key in sorted(groups.keys()):
        system, benchmark_suite, scenario_family = key
        batch = groups[key]
        eligible = [event for event in batch if not event.unsupported]
        layer = batch[0].layer if batch else ""
        score_profile = batch[0].score_profile if batch else ""
        rows.append(
            {
                "system": system,
                "benchmark_suite": benchmark_suite,
                "scenario_family": scenario_family,
                "layer": layer,
                "score_profile": score_profile,
                "conversations": len(batch),
                "eligible_conversations": len(eligible),
                "unsupported_conversations": sum(1 for event in batch if event.unsupported),
                "conversation_success": sum(1 for event in eligible if event.conversation_success),
                "quality_pass": sum(1 for event in eligible if event.passed),
                "missing_required_keywords": sum(1 for event in eligible if bool(event.quality_flags.get("missing_required_keywords"))),
                "contains_forbidden_keywords": sum(1 for event in eligible if bool(event.quality_flags.get("contains_forbidden_keywords"))),
                "missing_required_cards": sum(1 for event in eligible if bool(event.quality_flags.get("missing_required_cards"))),
                "missing_required_actions": sum(1 for event in eligible if bool(event.quality_flags.get("missing_required_actions"))),
                "missing_confirmation_buttons": sum(1 for event in eligible if bool(event.quality_flags.get("missing_confirmation_buttons"))),
                "missing_order_id": sum(1 for event in eligible if bool(event.quality_flags.get("missing_order_id"))),
                "hallucinated_order_id": sum(1 for event in eligible if bool(event.quality_flags.get("hallucinated_order_id"))),
                "technical_failures": sum(1 for event in eligible if bool(event.quality_flags.get("technical_failure"))),
                "format_errors": sum(1 for event in eligible if bool(event.quality_flags.get("format_error"))),
                "login_block_failures": sum(1 for event in eligible if bool(event.quality_flags.get("login_block_failure"))),
                "image_flow_failures": sum(1 for event in eligible if bool(event.quality_flags.get("image_flow_failure"))),
                "pending_decision_failures": sum(1 for event in eligible if bool(event.quality_flags.get("pending_decision_failure"))),
            }
        )
    return rows


def build_conversation_summary_rows(conversations: list[ConversationEvent]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in conversations:
        row = asdict(event)
        flags = dict(event.quality_flags)
        row["supported"] = bool(flags.get("supported", not event.unsupported))
        row["hallucination_free"] = not bool(flags.get("hallucinated_order_id"))
        row["missing_required_keywords"] = bool(flags.get("missing_required_keywords"))
        row["contains_forbidden_keywords"] = bool(flags.get("contains_forbidden_keywords"))
        row["missing_required_cards"] = bool(flags.get("missing_required_cards"))
        row["missing_required_actions"] = bool(flags.get("missing_required_actions"))
        row["missing_confirmation_buttons"] = bool(flags.get("missing_confirmation_buttons"))
        row["missing_order_id"] = bool(flags.get("missing_order_id"))
        row["hallucinated_order_id"] = bool(flags.get("hallucinated_order_id"))
        row["technical_failure"] = bool(flags.get("technical_failure"))
        row["format_error"] = bool(flags.get("format_error"))
        row["login_block_failure"] = bool(flags.get("login_block_failure"))
        row["image_flow_failure"] = bool(flags.get("image_flow_failure"))
        row["pending_decision_failure"] = bool(flags.get("pending_decision_failure"))
        row["primary_failure_reason"] = str(flags.get("primary_failure_reason") or "")
        rows.append(row)
    return rows


def build_capability_coverage_rows(conversations: list[ConversationEvent]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[ConversationEvent]] = {}
    for event in conversations:
        for capability in event.required_capabilities:
            groups.setdefault((event.system, event.benchmark_suite, capability), []).append(event)
    rows: list[dict[str, Any]] = []
    for key in sorted(groups.keys()):
        system, benchmark_suite, capability = key
        batch = groups[key]
        eligible = [event for event in batch if not event.unsupported]
        rows.append(
            {
                "system": system,
                "benchmark_suite": benchmark_suite,
                "capability": capability,
                "required_conversations": len(batch),
                "supported_conversations": len(eligible),
                "support_rate": round(len(eligible) / max(1, len(batch)), 4),
                "conversation_success_rate": round(sum(1 for event in eligible if event.conversation_success) / max(1, len(eligible)), 4),
                "quality_pass_rate": round(sum(1 for event in eligible if event.passed) / max(1, len(eligible)), 4),
            }
        )
    return rows


def build_system_matrix(conversations: list[ConversationEvent], scenario_families: list[str]) -> list[dict[str, Any]]:
    systems = sorted({event.system for event in conversations})
    rows: list[dict[str, Any]] = []
    for system in systems:
        row: dict[str, Any] = {"system": system}
        scoped_all = [event for event in conversations if event.system == system and not event.unsupported]
        business_events = [event for event in scoped_all if event.layer == "business"]
        boundary_events = [event for event in scoped_all if event.layer == "boundary"]
        row["technical_success_rate"] = round(sum(1 for event in scoped_all if event.success) / max(1, len(scoped_all)), 4)
        row["hallucination_free_rate"] = round(
            sum(1 for event in scoped_all if not bool(event.quality_flags.get("hallucinated_order_id"))) / max(1, len(scoped_all)),
            4,
        )
        row["business_pass_rate"] = round(sum(1 for event in business_events if event.passed) / max(1, len(business_events)), 4)
        row["boundary_safety_pass_rate"] = round(sum(1 for event in boundary_events if event.passed) / max(1, len(boundary_events)), 4)
        for family in scenario_families:
            scoped = [event for event in conversations if event.system == system and event.scenario_family == family]
            eligible = [event for event in scoped if not event.unsupported]
            row[f"{family}_quality_pass_rate"] = round(sum(1 for event in eligible if event.passed) / max(1, len(eligible)), 4)
            row[f"{family}_conversation_success_rate"] = round(sum(1 for event in eligible if event.conversation_success) / max(1, len(eligible)), 4)
            row[f"{family}_unsupported_rate"] = round(sum(1 for event in scoped if event.unsupported) / max(1, len(scoped)), 4)
            row[f"{family}_p95_ms"] = compute_percentile([event.latency_ms for event in scoped], 0.95)
        rows.append(row)
    return rows


def build_paper_tables(*, matrix_rows: list[dict[str, Any]], capability_rows: list[dict[str, Any]], summary_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Raw Appendix Tables",
        "",
        "## System Matrix (Non-Ranking)",
        render_markdown_table(matrix_rows),
        "",
        "## Capability Coverage",
        render_markdown_table(capability_rows),
        "",
        "## Summary",
        render_markdown_table(summary_rows),
        "",
        "## Metric Notes",
        "- Use `analysis/report.md` for the formal `shared_core` and `agent_extension` rankings.",
        "- `unsupported_rate` means the system lacks a required capability for the task, not that the answer content was wrong.",
        "- `conversation_success_rate` measures whether the end-to-end flow completed successfully.",
        "- `quality_pass_rate` additionally enforces content, structure, and workflow requirements.",
    ]
    return "\n".join(lines)


def _build_report_legacy_unused(
    *,
    output_dir: Path,
    config_path: Path,
    dataset_files: dict[str, Path],
    systems: list[str],
    scenario_families: list[str],
    profile: str,
    dataset_tier: str,
    selection_mode: str,
    auth_cfg: AuthConfig,
    summary_rows: list[dict[str, Any]],
    quality_rows: list[dict[str, Any]],
    matrix_rows: list[dict[str, Any]],
    capability_rows: list[dict[str, Any]],
    prompt_versions: list[dict[str, str]],
    expected_sample_rows: list[dict[str, Any]],
) -> str:
    lines = [
        "# �ͷ���· Benchmark ����",
        "",
        f"- ����ʱ�䣺{now_iso()}",
        f"- Profile��{profile}",
        f"- ���ݼ��㼶��{dataset_tier}",
        f"- �����ļ���`{config_path}`",
        f"- ���Ŀ¼��`{output_dir}`",
        f"- Python��{sys.version.split()[0]}",
        f"- ϵͳ���ϣ�{', '.join(systems)}",
        f"- �������ϣ�{', '.join(scenario_families)}",
        f"- �ͻ��˺ţ�`{auth_cfg.customer_email}`",
        f"- �̼��˺ţ�`{auth_cfg.merchant_email}`",
        "- �ٷ�Ĭ�ϲ�����`1`",
        "- ��ʽ����ֻ��˫������ָ�꣬��ʹ��ʱ�ӺͲ�����Ϊ����������",
        "",
        "## ���ݼ��ļ�",
        render_markdown_table([{"scenario_family": family, "path": str(path)} for family, path in dataset_files.items()]),
        "",
        "## Prompt �汾",
        render_markdown_table(prompt_versions),
        "",
        "## ԭʼϵͳ���󣨷���ʽ���У�",
        render_markdown_table(matrix_rows),
        "",
        "## ����ժҪ",
        render_markdown_table(summary_rows),
        "",
        "## ��������",
        render_markdown_table(quality_rows),
        "",
        "## ��������",
        render_markdown_table(capability_rows),
    ]
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
    selection_mode: str,
    auth_cfg: AuthConfig,
    summary_rows: list[dict[str, Any]],
    quality_rows: list[dict[str, Any]],
    matrix_rows: list[dict[str, Any]],
    capability_rows: list[dict[str, Any]],
    prompt_versions: list[dict[str, str]],
    expected_sample_rows: list[dict[str, Any]],
) -> str:
    expected_unique_rows: list[dict[str, Any]] = []
    seen_expected: set[tuple[str, str]] = set()
    for row in expected_sample_rows:
        key = (str(row.get("benchmark_suite") or ""), str(row.get("sample_id") or ""))
        if key in seen_expected:
            continue
        seen_expected.add(key)
        expected_unique_rows.append(
            {
                "benchmark_suite": row.get("benchmark_suite", ""),
                "scenario_family": row.get("scenario_family", ""),
                "sample_id": row.get("sample_id", ""),
                "repeatable": row.get("repeatable", True),
                "tier": row.get("tier", ""),
            }
        )
    lines = [
        "# Benchmark Raw Report",
        "",
        f"- Generated At: {now_iso()}",
        f"- Profile: {profile}",
        f"- Dataset Tier: {dataset_tier}",
        f"- Selection Mode: {selection_mode}",
        f"- Config: `{config_path}`",
        f"- Output Dir: `{output_dir}`",
        f"- Python: {sys.version.split()[0]}",
        f"- Systems: {', '.join(systems)}",
        f"- Scenario Families: {', '.join(scenario_families)}",
        f"- Customer Seed Account: `{auth_cfg.customer_email}`",
        f"- Merchant Seed Account: `{auth_cfg.merchant_email}`",
        "",
        "## Dataset Files",
        render_markdown_table([{"scenario_family": family, "path": str(path)} for family, path in dataset_files.items()]),
        "",
        "## Expected Unique Samples",
        render_markdown_table(expected_unique_rows),
        "",
        "## Prompt Versions",
        render_markdown_table(prompt_versions),
        "",
        "## System Matrix",
        render_markdown_table(matrix_rows),
        "",
        "## Summary",
        render_markdown_table(summary_rows),
        "",
        "## Scenario Quality",
        render_markdown_table(quality_rows),
        "",
        "## Capability Coverage",
        render_markdown_table(capability_rows),
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
        raise RuntimeError(f"Profile �����ڣ�{args.profile}")
    dataset_tier = (args.dataset_tier or str(profile_cfg.get("dataset_tier") or "core")).strip()
    selection_mode = resolve_selection_mode(args.profile, profile_cfg)
    scenario_families = list(profile_cfg.get("scenarios") or selected_families)
    if args.scenarios.strip():
        scenario_families = selected_families
    system_targets = resolve_system_targets(config, selected_systems)
    dataset_files = resolve_dataset_files(args.dataset, dataset_tier, scenario_families)
    dataset_map = {
        family: [sample for sample in load_dataset_file(path) if sample_allowed_for_profile(sample, args.profile)]
        for family, path in dataset_files.items()
    }
    concurrency_levels = parse_concurrency_override(args.concurrency) or [int(item) for item in profile_cfg.get("concurrency", []) if int(item) > 0]
    requests_per_level = int(args.requests_per_level) if args.requests_per_level is not None else int(profile_cfg.get("requests_per_level", 1))
    repeats = int(args.repeats) if args.repeats is not None else int(profile_cfg.get("repeats", 1))
    timeout_sec = float(args.timeout_sec) if args.timeout_sec is not None else float(config.get("timeout_sec", 60))
    warmup_requests = int(args.warmup_requests) if args.warmup_requests is not None else int(config.get("warmup_requests", 0))
    seed = int(args.seed) if args.seed is not None else int(config.get("seed", 20260412))
    configured_results_root = str(config.get("results_dir") or "benchmark/results")
    results_root = args.results_root if args.results_root is not None else (ROOT_DIR / configured_results_root)
    if not results_root.is_absolute():
        results_root = (ROOT_DIR / results_root).resolve()
    run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{args.profile}_system_benchmark"
    output_dir = results_root / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    prompt_versions = collect_prompt_versions()
    sample_universe_rows = [build_sample_metadata_row(sample) for family in scenario_families for sample in dataset_map.get(family, [])]
    expected_sample_rows: list[dict[str, Any]] = []

    all_conversations: list[ConversationEvent] = []
    all_turns: list[TurnEvent] = []
    async with httpx.AsyncClient(timeout=timeout_sec, trust_env=False) as client:
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
            await warmup_system(client, system, warmup_sample, auth_cfg, config, warmup_requests, run_id)
            for family in scenario_families:
                samples = dataset_map[family]
                for repeat in range(1, repeats + 1):
                    for concurrency in concurrency_levels:
                        planned = pick_samples(
                            samples,
                            requests_per_level,
                            seed + repeat * 97 + concurrency * 17 + sum(ord(ch) for ch in system_name + family),
                            selection_mode=selection_mode,
                            repeat=repeat,
                        )
                        expected_sample_rows.extend(
                            [
                                build_expected_sample_row(
                                    system=system_name,
                                    sample=sample,
                                    repeat=repeat,
                                    concurrency=concurrency,
                                    selection_mode=selection_mode,
                                )
                                for sample in planned
                            ]
                        )
                        batch_conversations, batch_turns = await execute_batch(
                            client=client,
                            system=system,
                            samples=planned,
                            auth_cfg=auth_cfg,
                            config=config,
                            repeat=repeat,
                            concurrency=concurrency,
                            run_id=run_id,
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
    write_jsonl(output_dir / "raw_events.jsonl", [asdict(item) for item in all_conversations])
    write_jsonl(output_dir / "turn_events.jsonl", [asdict(item) for item in all_turns])
    write_csv(output_dir / "summary.csv", summary_rows)
    write_csv(output_dir / "scenario_quality.csv", quality_rows)
    write_csv(output_dir / "conversation_summary.csv", conversation_rows)
    write_csv(output_dir / "capability_coverage.csv", capability_rows)
    write_csv(output_dir / "system_matrix.csv", matrix_rows)
    write_json(output_dir / "prompt_versions.json", {"items": prompt_versions}, indent=2)
    write_json(
        output_dir / "run_metadata.json",
        {
            "profile": args.profile,
            "selection_mode": selection_mode,
            "dataset_tier": dataset_tier,
            "scenario_families": scenario_families,
            "dataset_files": {family: str(path) for family, path in dataset_files.items()},
            "systems": list(system_targets.keys()),
            "repeats": repeats,
            "requests_per_level": requests_per_level,
            "concurrency_levels": concurrency_levels,
            "sample_universe": sample_universe_rows,
            "expected_samples": expected_sample_rows,
        },
        indent=2,
    )
    (output_dir / "report.md").write_text(
        build_report(
            output_dir=output_dir,
            config_path=config_path,
            dataset_files=dataset_files,
            systems=list(system_targets.keys()),
            scenario_families=scenario_families,
            profile=args.profile,
            dataset_tier=dataset_tier,
            selection_mode=selection_mode,
            auth_cfg=auth_cfg,
            summary_rows=summary_rows,
            quality_rows=quality_rows,
            matrix_rows=matrix_rows,
            capability_rows=capability_rows,
            prompt_versions=prompt_versions,
            expected_sample_rows=expected_sample_rows,
        ),
        encoding="utf-8",
    )
    (output_dir / "paper_tables.md").write_text(
        build_paper_tables(matrix_rows=matrix_rows, capability_rows=capability_rows, summary_rows=summary_rows),
        encoding="utf-8",
    )
    print(json.dumps({"output_dir": str(output_dir), "conversations": len(all_conversations), "turns": len(all_turns)}, ensure_ascii=False))
    return output_dir


def main() -> None:
    args = parse_args()
    asyncio.run(execute_benchmark(args))


if __name__ == "__main__":
    main()
