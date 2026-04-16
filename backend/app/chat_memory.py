from __future__ import annotations

import json
import logging
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession

from .cache import RedisCache
from .env import BACKEND_ROOT_DIR

logger = logging.getLogger(__name__)

DEFAULT_CHAT_SESSION_ID = "default"
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"
ROLE_SYSTEM = "system"
CHAT_MEMORY_DIR = BACKEND_ROOT_DIR / "data" / "chat_memory"

_ORDER_ID_PATTERN = re.compile(r"\b(ORD\d{10,})\b", flags=re.IGNORECASE)
_BUDGET_PATTERN = re.compile(
    r"(?:预算|价位|价格|控制在|不超过|低于)\s*([0-9]{2,6}(?:\.\d+)?)\s*(?:元|块|rmb)?",
    flags=re.IGNORECASE,
)
_SIZE_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:寸|英寸|in\b|inch\b|gb\b|g\b|tb\b|l\b|ml\b|w\b|hz\b|k\b)",
    flags=re.IGNORECASE,
)

_COLOR_KEYWORDS = [
    "白色",
    "黑色",
    "银色",
    "灰色",
    "蓝色",
    "绿色",
    "红色",
    "粉色",
    "紫色",
    "金色",
    "深空灰",
    "星光色",
    "午夜色",
]
_SCENARIO_KEYWORDS = [
    "通勤",
    "办公",
    "游戏",
    "出差",
    "拍照",
    "续航",
    "轻薄",
    "学生",
    "宿舍",
    "追剧",
    "剪视频",
    "运动",
    "家用",
    "直播",
    "会议",
    "便携",
    "户外",
]
_BRAND_KEYWORDS = [
    "Apple",
    "华为",
    "小米",
    "荣耀",
    "联想",
    "ThinkPad",
    "戴尔",
    "华硕",
    "惠普",
    "三星",
    "索尼",
    "OPPO",
    "vivo",
    "TCL",
    "海信",
    "美的",
    "格力",
    "JBL",
]
_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "product": ["商品", "推荐", "颜色", "尺寸", "屏幕", "手机", "电脑", "耳机", "显示器"],
    "order": ["订单", "下单", "购买"],
    "logistics": ["物流", "快递", "运单", "发货"],
    "after_sales": ["售后", "退款", "退货", "换货"],
    "price_protection": ["保价", "降价", "补差价"],
}


@dataclass(frozen=True)
class ChatMemoryConfig:
    root_dir: Path = CHAT_MEMORY_DIR
    compact_message_threshold: int = 12
    compact_char_threshold: int = 4000
    recent_window_messages: int = 8
    bundle_recent_messages: int = 6
    cache_ttl_sec: int = 180
    lock_ttl_sec: int = 30


@dataclass(frozen=True)
class ChatSessionRef:
    user_id: UUID
    session_id: str
    sender_id: str
    principal_id: str
    root_dir: Path

    @property
    def user_dir(self) -> Path:
        return self.root_dir / sanitize_path_segment(self.principal_id)

    @property
    def session_dir(self) -> Path:
        return self.user_dir / sanitize_path_segment(self.session_id)

    @property
    def context_markdown_path(self) -> Path:
        return self.session_dir / "context_memory.md"

    @property
    def global_markdown_path(self) -> Path:
        return self.user_dir / "global_memory.md"


@dataclass(frozen=True)
class PersistedChatMessage:
    message_id: str
    chat_session_id: str
    sequence_no: int


def can_use_db_session(session: Any) -> bool:
    return all(hasattr(session, attr) for attr in ("execute", "commit", "rollback"))


def sanitize_path_segment(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", (value or "").strip())
    cleaned = cleaned.strip("._")
    return cleaned or DEFAULT_CHAT_SESSION_ID


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str, separators=(",", ":"))


def ensure_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except Exception:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def ensure_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except Exception:
            return []
        return parsed if isinstance(parsed, list) else []
    return []


def truncate_text(value: str, limit: int = 120) -> str:
    text_value = (value or "").strip().replace("\n", " ")
    if len(text_value) <= limit:
        return text_value
    return text_value[: max(0, limit - 3)].rstrip() + "..."


def derive_session_title(text_value: str) -> str:
    cleaned = re.sub(r"\s+", " ", (text_value or "").strip())
    if not cleaned:
        return "新会话"
    return cleaned[:16] + ("..." if len(cleaned) > 16 else "")


def merge_unique(existing: list[str], additions: list[str], *, limit: int | None = None) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for item in [*(existing or []), *(additions or [])]:
        cleaned = str(item or "").strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        merged.append(cleaned)
    if isinstance(limit, int) and limit > 0 and len(merged) > limit:
        return merged[-limit:]
    return merged


def infer_topic_tags(text_value: str) -> list[str]:
    cleaned = (text_value or "").strip()
    if not cleaned:
        return []
    tags: list[str] = []
    for topic, keywords in _TOPIC_KEYWORDS.items():
        if any(keyword in cleaned for keyword in keywords):
            tags.append(topic)
    return tags or ["general"]


def extract_memory_facts_from_texts(texts: list[str]) -> dict[str, list[str]]:
    facts = {
        "budgets": [],
        "colors": [],
        "sizes": [],
        "brands": [],
        "scenarios": [],
        "order_ids": [],
        "topics": [],
    }
    for raw_text in texts:
        text_value = (raw_text or "").strip()
        if not text_value:
            continue

        facts["topics"] = merge_unique(facts["topics"], infer_topic_tags(text_value))

        for matched in _ORDER_ID_PATTERN.findall(text_value):
            facts["order_ids"] = merge_unique(facts["order_ids"], [matched.upper()])

        for matched in _BUDGET_PATTERN.findall(text_value):
            facts["budgets"] = merge_unique(facts["budgets"], [f"{matched}元"])

        for matched in _SIZE_PATTERN.findall(text_value):
            facts["sizes"] = merge_unique(facts["sizes"], [matched])

        for keyword in _COLOR_KEYWORDS:
            if keyword in text_value:
                facts["colors"] = merge_unique(facts["colors"], [keyword])

        for keyword in _SCENARIO_KEYWORDS:
            if keyword in text_value:
                facts["scenarios"] = merge_unique(facts["scenarios"], [keyword])

        for keyword in _BRAND_KEYWORDS:
            if keyword.lower() in text_value.lower():
                facts["brands"] = merge_unique(facts["brands"], [keyword])

    return facts


def merge_memory_facts(existing: dict[str, Any], updates: dict[str, Any]) -> dict[str, list[str]]:
    keys = ["budgets", "colors", "sizes", "brands", "scenarios", "order_ids", "topics"]
    merged: dict[str, list[str]] = {}
    for key in keys:
        merged[key] = merge_unique(ensure_list(existing.get(key)), ensure_list(updates.get(key)))
    return merged


def build_recent_window(messages: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    selected = messages[-max(1, limit) :]
    return [
        {
            "sequence_no": int(item.get("sequence_no") or 0),
            "role": str(item.get("sender_role") or ""),
            "text": str(item.get("message_text") or ""),
            "created_at": str(item.get("created_at") or ""),
        }
        for item in selected
    ]


def build_session_summary_markdown(
    *,
    ref: ChatSessionRef,
    snapshot_version: int,
    facts: dict[str, list[str]],
    messages: list[dict[str, Any]],
    recent_window: list[dict[str, Any]],
) -> str:
    user_messages = [str(item.get("message_text") or "") for item in messages if item.get("sender_role") == ROLE_USER]
    topic_counts = Counter(tag for message in user_messages for tag in infer_topic_tags(message))
    last_user = next((item for item in reversed(messages) if item.get("sender_role") == ROLE_USER), None)
    last_assistant = next(
        (item for item in reversed(messages) if item.get("sender_role") in {ROLE_ASSISTANT, ROLE_SYSTEM}),
        None,
    )
    lines = [
        "# 会话上下文记忆",
        "",
        f"- 用户: {ref.user_id}",
        f"- 会话: {ref.session_id}",
        f"- 快照版本: {snapshot_version}",
        f"- 更新时间: {datetime.utcnow().isoformat(timespec='seconds')}Z",
        "",
        "## 会话摘要",
    ]
    if topic_counts:
        lines.append(f"- 近期关注主题: {', '.join(tag for tag, _count in topic_counts.most_common(4))}")
    if facts["budgets"]:
        lines.append(f"- 预算偏好: {', '.join(facts['budgets'])}")
    if facts["colors"]:
        lines.append(f"- 颜色偏好: {', '.join(facts['colors'])}")
    if facts["sizes"]:
        lines.append(f"- 规格偏好: {', '.join(facts['sizes'])}")
    if facts["brands"]:
        lines.append(f"- 品牌线索: {', '.join(facts['brands'])}")
    if facts["scenarios"]:
        lines.append(f"- 场景偏好: {', '.join(facts['scenarios'])}")
    if facts["order_ids"]:
        lines.append(f"- 关联订单: {', '.join(facts['order_ids'])}")
    if not any(facts.values()) and not topic_counts:
        lines.append("- 当前还没有稳定的长期偏好。")

    lines.extend(["", "## 最近有效轮次"])
    if last_user:
        lines.append(f"- 最近用户诉求: {truncate_text(str(last_user.get('message_text') or ''))}")
    if last_assistant:
        lines.append(f"- 最近系统响应: {truncate_text(str(last_assistant.get('message_text') or ''))}")
    if not last_user and not last_assistant:
        lines.append("- 暂无最近轮次摘要。")

    lines.extend(["", "## 最近消息窗口"])
    if not recent_window:
        lines.append("- 暂无消息窗口。")
    else:
        for item in recent_window:
            role_label = {
                ROLE_USER: "用户",
                ROLE_ASSISTANT: "助手",
                ROLE_SYSTEM: "系统",
            }.get(str(item.get("role") or ""), "消息")
            lines.append(f"- {role_label}: {truncate_text(str(item.get('text') or ''))}")

    return "\n".join(lines).strip() + "\n"


def build_global_memory_markdown(
    *,
    user_id: UUID,
    facts: dict[str, list[str]],
    recent_topics: list[str],
) -> str:
    lines = [
        "# 用户全局记忆",
        "",
        f"- 用户: {user_id}",
        f"- 更新时间: {datetime.utcnow().isoformat(timespec='seconds')}Z",
        "",
        "## 长期偏好",
    ]
    if facts["brands"]:
        lines.append(f"- 品牌偏好: {', '.join(facts['brands'])}")
    if facts["budgets"]:
        lines.append(f"- 预算偏好: {', '.join(facts['budgets'])}")
    if facts["colors"]:
        lines.append(f"- 颜色偏好: {', '.join(facts['colors'])}")
    if facts["sizes"]:
        lines.append(f"- 规格偏好: {', '.join(facts['sizes'])}")
    if facts["scenarios"]:
        lines.append(f"- 使用场景: {', '.join(facts['scenarios'])}")
    if not any([facts["brands"], facts["budgets"], facts["colors"], facts["sizes"], facts["scenarios"]]):
        lines.append("- 目前还没有稳定的显式偏好。")

    lines.extend(["", "## 长期事实"])
    if facts["order_ids"]:
        lines.append(f"- 相关订单: {', '.join(facts['order_ids'])}")
    else:
        lines.append("- 暂无稳定订单事实。")

    lines.extend(["", "## 最近关注主题"])
    if recent_topics:
        for item in recent_topics:
            lines.append(f"- {item}")
    else:
        lines.append("- 暂无最近主题。")
    return "\n".join(lines).strip() + "\n"


def should_compact_history(
    *,
    latest_snapshot_end_sequence: int,
    all_messages: list[dict[str, Any]],
    config: ChatMemoryConfig,
    context_file_exists: bool,
) -> bool:
    if not all_messages:
        return False
    if latest_snapshot_end_sequence <= 0 or not context_file_exists:
        return True

    pending_messages = [
        item for item in all_messages if int(item.get("sequence_no") or 0) > int(latest_snapshot_end_sequence)
    ]
    if len(pending_messages) >= config.compact_message_threshold:
        return True
    pending_chars = sum(len(str(item.get("message_text") or "")) for item in pending_messages)
    return pending_chars >= config.compact_char_threshold


def bundle_cache_key(ref: ChatSessionRef) -> str:
    return f"chat:memory:bundle:{ref.user_id}:{ref.session_id}"


def bundle_lock_key(ref: ChatSessionRef) -> str:
    return f"chat:memory:lock:{ref.user_id}:{ref.session_id}"


def pending_action_cache_key(user_id: UUID) -> str:
    return f"chat:pending-action:{user_id}"


def attach_pending_action_context(payload: dict[str, Any], ref: ChatSessionRef | None) -> dict[str, Any]:
    normalized = dict(payload or {})
    if ref:
        normalized["_chat_session"] = {
            "session_id": ref.session_id,
            "sender_id": ref.sender_id,
        }
    return normalized


def extract_session_ref_from_pending_payload(
    *,
    user_id: UUID,
    payload: dict[str, Any] | None,
    config: ChatMemoryConfig,
) -> ChatSessionRef:
    chat_session = ensure_dict((payload or {}).get("_chat_session"))
    sender_id = str(chat_session.get("sender_id") or "").strip()
    if not sender_id:
        session_id = str(chat_session.get("session_id") or "").strip() or DEFAULT_CHAT_SESSION_ID
        sender_id = f"{user_id}:{session_id}"
    return resolve_chat_session_ref(user_id=user_id, sender_id=sender_id, config=config)


def resolve_chat_session_ref(
    *,
    user_id: UUID | None,
    sender_id: str,
    config: ChatMemoryConfig,
) -> ChatSessionRef | None:
    if user_id is None:
        return None

    principal_id = str(user_id)
    normalized_sender = (sender_id or "").strip()
    session_id = DEFAULT_CHAT_SESSION_ID

    if ":" in normalized_sender:
        sender_principal, sender_session_id = normalized_sender.split(":", 1)
        if sender_principal.strip() == principal_id and sender_session_id.strip():
            session_id = sender_session_id.strip()
    elif normalized_sender == principal_id:
        session_id = DEFAULT_CHAT_SESSION_ID

    cleaned_session_id = sanitize_path_segment(session_id)
    normalized_composite_sender = f"{principal_id}:{cleaned_session_id}"
    config.root_dir.mkdir(parents=True, exist_ok=True)
    return ChatSessionRef(
        user_id=user_id,
        session_id=cleaned_session_id,
        sender_id=normalized_composite_sender,
        principal_id=principal_id,
        root_dir=config.root_dir,
    )


def write_markdown_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.name + ".tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(path)


async def ensure_chat_memory_schema(engine: AsyncEngine) -> None:
    statements = [
        """
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            session_id VARCHAR(128) NOT NULL,
            sender_id VARCHAR(255) NOT NULL,
            title VARCHAR(255) NOT NULL DEFAULT '新会话',
            message_count INT NOT NULL DEFAULT 0 CHECK (message_count >= 0),
            current_snapshot_version INT NOT NULL DEFAULT 0 CHECK (current_snapshot_version >= 0),
            current_context_file_path TEXT,
            last_message_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, session_id)
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_last_message ON chat_sessions(user_id, last_message_at DESC)",
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            chat_session_id uuid NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            session_id VARCHAR(128) NOT NULL,
            sender_role VARCHAR(20) NOT NULL CHECK (sender_role IN ('user', 'assistant', 'system')),
            sequence_no INT NOT NULL CHECK (sequence_no > 0),
            message_text TEXT NOT NULL DEFAULT '',
            attachment_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
            route_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            cards JSONB NOT NULL DEFAULT '[]'::jsonb,
            actions JSONB NOT NULL DEFAULT '[]'::jsonb,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(chat_session_id, sequence_no)
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_chat_messages_session_sequence ON chat_messages(chat_session_id, sequence_no DESC)",
        "CREATE INDEX IF NOT EXISTS idx_chat_messages_user_created_at ON chat_messages(user_id, created_at DESC)",
        """
        CREATE TABLE IF NOT EXISTS chat_context_snapshots (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            chat_session_id uuid NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            session_id VARCHAR(128) NOT NULL,
            snapshot_version INT NOT NULL CHECK (snapshot_version > 0),
            start_sequence_no INT NOT NULL CHECK (start_sequence_no > 0),
            end_sequence_no INT NOT NULL CHECK (end_sequence_no >= start_sequence_no),
            summary_markdown TEXT NOT NULL,
            memory_facts JSONB NOT NULL DEFAULT '{}'::jsonb,
            recent_window JSONB NOT NULL DEFAULT '[]'::jsonb,
            context_file_path TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(chat_session_id, snapshot_version)
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_chat_context_snapshots_session_version ON chat_context_snapshots(chat_session_id, snapshot_version DESC)",
        """
        CREATE TABLE IF NOT EXISTS chat_user_global_memory (
            user_id uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            memory_markdown TEXT NOT NULL,
            memory_facts JSONB NOT NULL DEFAULT '{}'::jsonb,
            recent_topics JSONB NOT NULL DEFAULT '[]'::jsonb,
            context_file_path TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS chat_pending_actions (
            user_id uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_chat_pending_actions_expires_at ON chat_pending_actions(expires_at)",
    ]
    async with engine.begin() as conn:
        for statement in statements:
            await conn.execute(text(statement))


async def invalidate_memory_bundle_cache(*, cache: RedisCache, ref: ChatSessionRef | None) -> None:
    if ref is None:
        return
    await cache.delete_keys(bundle_cache_key(ref))


async def _load_or_create_chat_session_row(
    *,
    session: AsyncSession,
    ref: ChatSessionRef,
    first_message_text: str,
) -> dict[str, Any]:
    select_stmt = text(
        """
        SELECT id, title, message_count, current_snapshot_version, current_context_file_path
        FROM chat_sessions
        WHERE user_id = CAST(:user_id AS uuid) AND session_id = :session_id
        FOR UPDATE
        """
    )
    row = (await session.execute(select_stmt, {"user_id": str(ref.user_id), "session_id": ref.session_id})).mappings().first()
    if row:
        return dict(row)

    created_title = derive_session_title(first_message_text)
    insert_stmt = text(
        """
        INSERT INTO chat_sessions (
            user_id, session_id, sender_id, title, message_count, current_snapshot_version, current_context_file_path
        ) VALUES (
            CAST(:user_id AS uuid), :session_id, :sender_id, :title, 0, 0, :current_context_file_path
        )
        RETURNING id, title, message_count, current_snapshot_version, current_context_file_path
        """
    )
    created = await session.execute(
        insert_stmt,
        {
            "user_id": str(ref.user_id),
            "session_id": ref.session_id,
            "sender_id": ref.sender_id,
            "title": created_title,
            "current_context_file_path": str(ref.context_markdown_path),
        },
    )
    created_row = created.mappings().first()
    return dict(created_row or {})


async def persist_chat_message(
    *,
    session: AsyncSession,
    ref: ChatSessionRef | None,
    role: str,
    text_value: str,
    attachments: list[str] | None = None,
    route_metadata: dict[str, Any] | None = None,
    cards: list[dict[str, Any]] | None = None,
    actions: list[dict[str, Any]] | None = None,
) -> PersistedChatMessage | None:
    if ref is None or not can_use_db_session(session):
        return None

    normalized_role = (role or "").strip().lower()
    if normalized_role not in {ROLE_USER, ROLE_ASSISTANT, ROLE_SYSTEM}:
        raise ValueError(f"Unsupported chat role: {role}")

    normalized_text = (text_value or "").strip()
    normalized_attachments = [item for item in (attachments or []) if isinstance(item, str) and item.strip()]
    normalized_cards = [item for item in (cards or []) if isinstance(item, dict)]
    normalized_actions = [item for item in (actions or []) if isinstance(item, dict)]
    metadata = ensure_dict(route_metadata or {})

    try:
        row = await _load_or_create_chat_session_row(session=session, ref=ref, first_message_text=normalized_text)
        chat_session_id = str(row.get("id") or "")
        message_count = int(row.get("message_count") or 0)
        title = str(row.get("title") or "新会话")
        next_sequence = message_count + 1
        next_title = title
        if normalized_role == ROLE_USER and title == "新会话" and normalized_text:
            next_title = derive_session_title(normalized_text)

        insert_stmt = text(
            """
            INSERT INTO chat_messages (
                chat_session_id, user_id, session_id, sender_role, sequence_no, message_text,
                attachment_ids, route_metadata, cards, actions
            ) VALUES (
                CAST(:chat_session_id AS uuid),
                CAST(:user_id AS uuid),
                :session_id,
                :sender_role,
                :sequence_no,
                :message_text,
                CAST(:attachment_ids AS jsonb),
                CAST(:route_metadata AS jsonb),
                CAST(:cards AS jsonb),
                CAST(:actions AS jsonb)
            )
            RETURNING id
            """
        )
        inserted = await session.execute(
            insert_stmt,
            {
                "chat_session_id": chat_session_id,
                "user_id": str(ref.user_id),
                "session_id": ref.session_id,
                "sender_role": normalized_role,
                "sequence_no": next_sequence,
                "message_text": normalized_text,
                "attachment_ids": json_dumps(normalized_attachments),
                "route_metadata": json_dumps(metadata),
                "cards": json_dumps(normalized_cards),
                "actions": json_dumps(normalized_actions),
            },
        )
        message_row = inserted.mappings().first()
        update_stmt = text(
            """
            UPDATE chat_sessions
            SET sender_id = :sender_id,
                title = :title,
                message_count = :message_count,
                last_message_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = CAST(:chat_session_id AS uuid)
            """
        )
        await session.execute(
            update_stmt,
            {
                "sender_id": ref.sender_id,
                "title": next_title,
                "message_count": next_sequence,
                "chat_session_id": chat_session_id,
            },
        )
        await session.commit()
        return PersistedChatMessage(
            message_id=str((message_row or {}).get("id") or ""),
            chat_session_id=chat_session_id,
            sequence_no=next_sequence,
        )
    except Exception:
        await session.rollback()
        logger.exception("Failed to persist chat message. user_id=%s session_id=%s", ref.user_id, ref.session_id)
        return None


async def update_chat_message_route_metadata(
    *,
    session: AsyncSession,
    message_id: str,
    route_metadata: dict[str, Any],
) -> None:
    if not message_id or not can_use_db_session(session):
        return
    try:
        await session.execute(
            text(
                """
                UPDATE chat_messages
                SET route_metadata = CAST(:route_metadata AS jsonb)
                WHERE id = CAST(:message_id AS uuid)
                """
            ),
            {"message_id": message_id, "route_metadata": json_dumps(ensure_dict(route_metadata))},
        )
        await session.commit()
    except Exception:
        await session.rollback()
        logger.exception("Failed to update chat route metadata. message_id=%s", message_id)


async def get_pending_chat_action(
    *,
    session: AsyncSession,
    cache: RedisCache,
    user_id: UUID,
) -> dict[str, Any] | None:
    cache_key = pending_action_cache_key(user_id)
    raw = await cache.get_json(cache_key) if cache.enabled else None
    payload = ensure_dict(raw)
    if payload:
        expires_at_ts = int(payload.get("expires_at_ts") or 0)
        if expires_at_ts <= 0 or expires_at_ts > int(datetime.utcnow().timestamp()):
            return payload

    if not can_use_db_session(session):
        return None

    row = (
        await session.execute(
            text(
                """
                SELECT payload, expires_at
                FROM chat_pending_actions
                WHERE user_id = CAST(:user_id AS uuid)
                LIMIT 1
                """
            ),
            {"user_id": str(user_id)},
        )
    ).mappings().first()
    if not row:
        return None

    expires_at = row.get("expires_at")
    if isinstance(expires_at, str):
        try:
            expires_at = datetime.fromisoformat(expires_at)
        except Exception:
            expires_at = None
    if not isinstance(expires_at, datetime):
        await clear_pending_chat_action(session=session, cache=cache, user_id=user_id)
        return None
    if expires_at <= datetime.utcnow():
        await clear_pending_chat_action(session=session, cache=cache, user_id=user_id)
        return None

    payload = ensure_dict(row.get("payload"))
    payload["expires_at_ts"] = int(expires_at.timestamp())
    await cache.set_json(cache_key, payload, ttl_sec=max(1, int((expires_at - datetime.utcnow()).total_seconds())))
    return payload


async def set_pending_chat_action(
    *,
    session: AsyncSession,
    cache: RedisCache,
    user_id: UUID,
    payload: dict[str, Any],
    ttl_sec: int,
) -> dict[str, Any]:
    normalized = dict(payload or {})
    expires_at_ts = int(normalized.get("expires_at_ts") or 0)
    if expires_at_ts <= 0:
        expires_at_ts = int((datetime.utcnow() + timedelta(seconds=max(1, int(ttl_sec)))).timestamp())
        normalized["expires_at_ts"] = expires_at_ts
    expires_at = datetime.utcfromtimestamp(expires_at_ts)

    if can_use_db_session(session):
        try:
            await session.execute(
                text(
                    """
                    INSERT INTO chat_pending_actions (user_id, payload, expires_at)
                    VALUES (CAST(:user_id AS uuid), CAST(:payload AS jsonb), :expires_at)
                    ON CONFLICT (user_id) DO UPDATE
                    SET payload = EXCLUDED.payload,
                        expires_at = EXCLUDED.expires_at,
                        updated_at = CURRENT_TIMESTAMP
                    """
                ),
                {
                    "user_id": str(user_id),
                    "payload": json_dumps(normalized),
                    "expires_at": expires_at,
                },
            )
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("Failed to persist pending chat action. user_id=%s", user_id)

    await cache.set_json(
        pending_action_cache_key(user_id),
        normalized,
        ttl_sec=max(1, int((expires_at - datetime.utcnow()).total_seconds())),
    )
    return normalized


async def clear_pending_chat_action(
    *,
    session: AsyncSession,
    cache: RedisCache,
    user_id: UUID,
) -> None:
    if can_use_db_session(session):
        try:
            await session.execute(
                text("DELETE FROM chat_pending_actions WHERE user_id = CAST(:user_id AS uuid)"),
                {"user_id": str(user_id)},
            )
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("Failed to clear pending chat action. user_id=%s", user_id)
    await cache.delete_keys(pending_action_cache_key(user_id))


async def _load_session_messages(
    *,
    session: AsyncSession,
    ref: ChatSessionRef,
) -> list[dict[str, Any]]:
    rows = await session.execute(
        text(
            """
            SELECT id, chat_session_id, session_id, sender_role, sequence_no, message_text, route_metadata, created_at
            FROM chat_messages
            WHERE user_id = CAST(:user_id AS uuid) AND session_id = :session_id
            ORDER BY sequence_no ASC
            """
        ),
        {"user_id": str(ref.user_id), "session_id": ref.session_id},
    )
    return [dict(item) for item in rows.mappings().all()]


async def _load_session_snapshot_row(
    *,
    session: AsyncSession,
    ref: ChatSessionRef,
) -> dict[str, Any] | None:
    row = (
        await session.execute(
            text(
                """
                SELECT s.id, s.current_snapshot_version, s.current_context_file_path,
                       cs.end_sequence_no, cs.summary_markdown
                FROM chat_sessions s
                LEFT JOIN chat_context_snapshots cs
                    ON cs.chat_session_id = s.id AND cs.snapshot_version = s.current_snapshot_version
                WHERE s.user_id = CAST(:user_id AS uuid) AND s.session_id = :session_id
                LIMIT 1
                """
            ),
            {"user_id": str(ref.user_id), "session_id": ref.session_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def load_agent_memory_bundle(
    *,
    session: AsyncSession,
    cache: RedisCache,
    ref: ChatSessionRef | None,
    config: ChatMemoryConfig,
) -> dict[str, Any]:
    if ref is None or not can_use_db_session(session):
        return {
            "session_id": "",
            "recent_messages": [],
            "session_memory_markdown": "",
            "global_memory_markdown": "",
        }

    cache_key = bundle_cache_key(ref)
    cached = await cache.get_json(cache_key) if cache.enabled else None
    if isinstance(cached, dict) and cached.get("session_id") == ref.session_id:
        return cached

    session_snapshot = await _load_session_snapshot_row(session=session, ref=ref)
    messages = await _load_session_messages(session=session, ref=ref)
    global_row = (
        await session.execute(
            text(
                """
                SELECT memory_markdown
                FROM chat_user_global_memory
                WHERE user_id = CAST(:user_id AS uuid)
                LIMIT 1
                """
            ),
            {"user_id": str(ref.user_id)},
        )
    ).mappings().first()

    bundle = {
        "session_id": ref.session_id,
        "recent_messages": build_recent_window(messages, limit=config.bundle_recent_messages),
        "session_memory_markdown": str((session_snapshot or {}).get("summary_markdown") or ""),
        "global_memory_markdown": str((global_row or {}).get("memory_markdown") or ""),
    }
    await cache.set_json(cache_key, bundle, ttl_sec=config.cache_ttl_sec)
    return bundle


async def refresh_chat_memory_artifacts(
    *,
    session: AsyncSession,
    cache: RedisCache,
    ref: ChatSessionRef | None,
    config: ChatMemoryConfig,
) -> None:
    if ref is None or not can_use_db_session(session):
        return

    lock_key = bundle_lock_key(ref)
    lock_token = f"{ref.user_id}:{ref.session_id}:{datetime.utcnow().timestamp()}"
    acquired = await cache.acquire_lock(lock_key, token=lock_token, ttl_sec=config.lock_ttl_sec) if cache.enabled else True
    if not acquired:
        return

    try:
        snapshot_row = await _load_session_snapshot_row(session=session, ref=ref)
        messages = await _load_session_messages(session=session, ref=ref)
        if not messages:
            return

        latest_end_sequence = int((snapshot_row or {}).get("end_sequence_no") or 0)
        current_snapshot_version = int((snapshot_row or {}).get("current_snapshot_version") or 0)
        facts = extract_memory_facts_from_texts(
            [str(item.get("message_text") or "") for item in messages if item.get("sender_role") == ROLE_USER]
        )
        recent_window = build_recent_window(messages, limit=config.recent_window_messages)

        if should_compact_history(
            latest_snapshot_end_sequence=latest_end_sequence,
            all_messages=messages,
            config=config,
            context_file_exists=ref.context_markdown_path.is_file(),
        ):
            next_snapshot_version = current_snapshot_version + 1
            summary_markdown = build_session_summary_markdown(
                ref=ref,
                snapshot_version=next_snapshot_version,
                facts=facts,
                messages=messages,
                recent_window=recent_window,
            )
            write_markdown_file(ref.context_markdown_path, summary_markdown)
            end_sequence = int(messages[-1].get("sequence_no") or 0)
            await session.execute(
                text(
                    """
                    INSERT INTO chat_context_snapshots (
                        chat_session_id, user_id, session_id, snapshot_version, start_sequence_no,
                        end_sequence_no, summary_markdown, memory_facts, recent_window, context_file_path
                    )
                    SELECT
                        id,
                        CAST(:user_id AS uuid),
                        :session_id,
                        :snapshot_version,
                        1,
                        :end_sequence_no,
                        :summary_markdown,
                        CAST(:memory_facts AS jsonb),
                        CAST(:recent_window AS jsonb),
                        :context_file_path
                    FROM chat_sessions
                    WHERE user_id = CAST(:user_id AS uuid) AND session_id = :session_id
                    """
                ),
                {
                    "user_id": str(ref.user_id),
                    "session_id": ref.session_id,
                    "snapshot_version": next_snapshot_version,
                    "end_sequence_no": end_sequence,
                    "summary_markdown": summary_markdown,
                    "memory_facts": json_dumps(facts),
                    "recent_window": json_dumps(recent_window),
                    "context_file_path": str(ref.context_markdown_path),
                },
            )
            await session.execute(
                text(
                    """
                    UPDATE chat_sessions
                    SET current_snapshot_version = :snapshot_version,
                        current_context_file_path = :context_file_path,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = CAST(:user_id AS uuid) AND session_id = :session_id
                    """
                ),
                {
                    "user_id": str(ref.user_id),
                    "session_id": ref.session_id,
                    "snapshot_version": next_snapshot_version,
                    "context_file_path": str(ref.context_markdown_path),
                },
            )

        global_row = (
            await session.execute(
                text(
                    """
                    SELECT memory_facts, recent_topics
                    FROM chat_user_global_memory
                    WHERE user_id = CAST(:user_id AS uuid)
                    LIMIT 1
                    """
                ),
                {"user_id": str(ref.user_id)},
            )
        ).mappings().first()
        merged_facts = merge_memory_facts(
            ensure_dict((global_row or {}).get("memory_facts")),
            facts,
        )
        recent_topics = merge_unique(
            ensure_list((global_row or {}).get("recent_topics")),
            [
                f"{tag}: {truncate_text(str(messages[-1].get('message_text') or ''), 48)}"
                for tag in infer_topic_tags(str(messages[-1].get("message_text") or ""))
            ],
            limit=10,
        )
        global_markdown = build_global_memory_markdown(
            user_id=ref.user_id,
            facts=merged_facts,
            recent_topics=recent_topics,
        )
        write_markdown_file(ref.global_markdown_path, global_markdown)
        await session.execute(
            text(
                """
                INSERT INTO chat_user_global_memory (
                    user_id, memory_markdown, memory_facts, recent_topics, context_file_path
                ) VALUES (
                    CAST(:user_id AS uuid),
                    :memory_markdown,
                    CAST(:memory_facts AS jsonb),
                    CAST(:recent_topics AS jsonb),
                    :context_file_path
                )
                ON CONFLICT (user_id) DO UPDATE
                SET memory_markdown = EXCLUDED.memory_markdown,
                    memory_facts = EXCLUDED.memory_facts,
                    recent_topics = EXCLUDED.recent_topics,
                    context_file_path = EXCLUDED.context_file_path,
                    updated_at = CURRENT_TIMESTAMP
                """
            ),
            {
                "user_id": str(ref.user_id),
                "memory_markdown": global_markdown,
                "memory_facts": json_dumps(merged_facts),
                "recent_topics": json_dumps(recent_topics),
                "context_file_path": str(ref.global_markdown_path),
            },
        )
        await session.commit()

        bundle = {
            "session_id": ref.session_id,
            "recent_messages": build_recent_window(messages, limit=config.bundle_recent_messages),
            "session_memory_markdown": (
                ref.context_markdown_path.read_text(encoding="utf-8") if ref.context_markdown_path.is_file() else ""
            ),
            "global_memory_markdown": global_markdown,
        }
        await cache.set_json(bundle_cache_key(ref), bundle, ttl_sec=config.cache_ttl_sec)
    except Exception:
        await session.rollback()
        logger.exception("Failed to refresh chat memory artifacts. user_id=%s session_id=%s", ref.user_id, ref.session_id)
    finally:
        if cache.enabled:
            await cache.release_lock(lock_key, token=lock_token)
