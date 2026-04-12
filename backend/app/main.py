
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path as FsPath
from random import randint
from typing import Any, Literal
from uuid import UUID, uuid4

import httpx
from fastapi import Depends, FastAPI, File, Header, HTTPException, Path, Query, Request, UploadFile, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from sqlalchemy import String, cast, delete, func, or_, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from .env import BACKEND_ROOT_DIR, ENV_FILE_PATH, load_backend_env

load_backend_env()

from .auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from .cache import RedisCache
from .database import engine, get_session
from .models import (
    ChatAfterSalesSummaryItem,
    ChatAfterSalesSummaryResponse,
    ChatAction,
    ChatCard,
    ChatOrderLogisticsSummaryItem,
    ChatOrderLogisticsSummaryResponse,
    AfterSales,
    AfterSalesRead,
    AddCartItemRequest,
    CartItem,
    CartItemRead,
    CartResponse,
    ChatOrderSummaryItem,
    ChatOrderSummaryResponse,
    ChatPendingActionDecisionRequest,
    ChatReplyMessage,
    ChatSendRequest,
    ChatSendResponse,
    ChatUploadImageResponse,
    CreateAfterSalesRequest,
    CreateLogisticsComplaintRequest,
    CreateOrderRequest,
    KBIndexRequest,
    KBIndexResponse,
    GeoPointRead,
    GeoCache,
    Logistics,
    LogisticsComplaint,
    LogisticsComplaintRead,
    LogisticsRead,
    LoginRequest,
    MerchantAfterSalesItem,
    MerchantAfterSalesListResponse,
    MerchantAfterSalesUpdateRequest,
    MerchantLogisticsComplaintItem,
    MerchantLogisticsComplaintListResponse,
    MerchantLogisticsComplaintUpdateRequest,
    MerchantOrderListResponse,
    MerchantOrderShipRequest,
    MerchantProductCreate,
    MerchantProductUpdate,
    MerchantShopUpdate,
    Order,
    OrderItem,
    OrderItemRead,
    OrderListItem,
    OrderListResponse,
    OrderRead,
    Product,
    ProductFilterMetaResponse,
    ProductFilterShopOption,
    ProductRecommendationResponse,
    ProductListResponse,
    ProductRead,
    ProductViewHistory,
    ProductViewHistoryItem,
    ProductViewHistoryResponse,
    Shop,
    ShopAddress,
    ShopAddressCreate,
    ShopAddressListResponse,
    ShopAddressRead,
    ShopAddressUpdate,
    ShopBrief,
    ShopRead,
    Token,
    TokenData,
    UpdateOrderShippingRequest,
    UpdateCartItemRequest,
    User,
    UserCreate,
    UserRead,
)
from .nexau_orchestrator import NexAUAgentOrchestrator, infer_message_domains, is_complex_query

app = FastAPI(title="Rasa-EC-bot Backend", version="0.3.0")
logger = logging.getLogger("rasa_ec_bot.chat_router")

RASA_SERVER_URL = os.getenv("RASA_SERVER_URL", "http://127.0.0.1:5005")
RASA_REST_WEBHOOK_PATH = os.getenv("RASA_REST_WEBHOOK_PATH", "/webhooks/rest/webhook")
RASA_PARSE_PATH = os.getenv("RASA_PARSE_PATH", "/model/parse")
RASA_REQUEST_TIMEOUT_SEC = float(os.getenv("RASA_REQUEST_TIMEOUT_SEC", "30"))
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")
RASA_INTERNAL_TOKEN = os.getenv("RASA_INTERNAL_TOKEN", "")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:2b")
OLLAMA_TIMEOUT_SEC = float(os.getenv("OLLAMA_TIMEOUT_SEC", "45"))
_agent_provider_raw = os.getenv("AGENT_LLM_PROVIDER", "").strip().lower()
if _agent_provider_raw:
    AGENT_LLM_PROVIDER = _agent_provider_raw
elif os.getenv("AGENT_LLM_BASE_URL", "").strip():
    AGENT_LLM_PROVIDER = "openai_compat"
else:
    AGENT_LLM_PROVIDER = "ollama"
AGENT_LLM_BASE_URL = os.getenv(
    "AGENT_LLM_BASE_URL",
    "http://127.0.0.1:8002/v1" if AGENT_LLM_PROVIDER in {"openai", "openai_compat"} else OLLAMA_BASE_URL,
).strip()
AGENT_LLM_MODEL = os.getenv(
    "AGENT_LLM_MODEL",
    os.getenv("AGENT_OLLAMA_MODEL", "qwen3.5-2b-lora" if AGENT_LLM_PROVIDER in {"openai", "openai_compat"} else "qwen3.5:2b-lora"),
).strip()
AGENT_LLM_API_KEY = os.getenv("AGENT_LLM_API_KEY", "EMPTY").strip()
AGENT_LLM_TIMEOUT_SEC = float(
    os.getenv("AGENT_LLM_TIMEOUT_SEC", os.getenv("AGENT_OLLAMA_TIMEOUT_SEC", str(OLLAMA_TIMEOUT_SEC)))
)
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large")
OLLAMA_VLM_MODEL = os.getenv("OLLAMA_VLM_MODEL", "qwen3-vl:2b")
KB_EMBEDDING_DIM = int(os.getenv("KB_EMBEDDING_DIM", "1024"))
KB_RETRIEVAL_TOP_K = int(os.getenv("KB_RETRIEVAL_TOP_K", "4"))
KB_CHUNK_SIZE = int(os.getenv("KB_CHUNK_SIZE", "500"))
KB_CHUNK_OVERLAP = int(os.getenv("KB_CHUNK_OVERLAP", "80"))
CHAT_UPLOAD_DIR = os.getenv("CHAT_UPLOAD_DIR", "data/chat_uploads")
CHAT_UPLOAD_MAX_MB = int(os.getenv("CHAT_UPLOAD_MAX_MB", "8"))
CHAT_UPLOAD_MAX_BYTES = CHAT_UPLOAD_MAX_MB * 1024 * 1024
CHAT_UPLOAD_ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
AMAP_WEB_KEY = os.getenv("AMAP_WEB_KEY", "").strip()
AMAP_WEB_SIG = os.getenv("AMAP_WEB_SIG", "").strip()
AMAP_TIMEOUT_MS = int(os.getenv("AMAP_TIMEOUT_MS", "3000"))
AMAP_QPS_LIMIT = max(1, int(os.getenv("AMAP_QPS_LIMIT", "5")))
CHAT_ROUTER_ENABLE_AGENT = os.getenv("CHAT_ROUTER_ENABLE_AGENT", "true").strip().lower() not in {"0", "false", "no"}
CHAT_ROUTER_RASA_CONFIDENCE_THRESHOLD = float(os.getenv("CHAT_ROUTER_RASA_CONFIDENCE_THRESHOLD", "0.72"))
FAST_ROUTER_INTENTS = {
    "greet",
    "goodbye",
    "thanks",
    "ask_order_help",
    "ask_shipping_help",
    "ask_after_sales_help",
    "ask_product_recommendation",
    "bot_challenge",
}

REDIS_URL = os.getenv("REDIS_URL", "")
REDIS_CACHE_TTL_SEC = int(os.getenv("REDIS_CACHE_TTL_SEC", "180"))
APP_ROOT_DIR = BACKEND_ROOT_DIR
UPLOAD_ROOT_DIR = (
    FsPath(CHAT_UPLOAD_DIR).resolve()
    if FsPath(CHAT_UPLOAD_DIR).is_absolute()
    else (APP_ROOT_DIR / CHAT_UPLOAD_DIR).resolve()
)

ORDER_STATUS_PENDING_SHIPMENT = "pending_shipment"
ORDER_STATUS_SHIPPED = "shipped"
ORDER_STATUS_CANCELLED = "cancelled"
LOGISTICS_STATUS_IN_TRANSIT = "in_transit"
LOGISTICS_STATUS_DELIVERED = "delivered"

AFTER_SALES_TYPE_RETURN = "return"
AFTER_SALES_TYPE_EXCHANGE = "exchange"
AFTER_SALES_ALLOWED_TYPES = {AFTER_SALES_TYPE_RETURN, AFTER_SALES_TYPE_EXCHANGE}

AFTER_SALES_STATUS_SUBMITTED = "submitted"
AFTER_SALES_STATUS_MERCHANT_APPROVED = "merchant_approved"
AFTER_SALES_STATUS_PROCESSING = "processing"
AFTER_SALES_STATUS_MERCHANT_REJECTED = "merchant_rejected"
AFTER_SALES_STATUS_COMPLETED = "completed"
AFTER_SALES_STATUS_CANCELLED = "cancelled"

LOGISTICS_COMPLAINT_STATUS_SUBMITTED = "submitted"
LOGISTICS_COMPLAINT_STATUS_PROCESSING = "processing"
LOGISTICS_COMPLAINT_STATUS_RESOLVED = "resolved"
LOGISTICS_COMPLAINT_STATUS_REJECTED = "rejected"
LOGISTICS_COMPLAINT_STATUS_CANCELLED = "cancelled"

LOGISTICS_COMPLAINT_TERMINAL_STATUSES = {
    LOGISTICS_COMPLAINT_STATUS_RESOLVED,
    LOGISTICS_COMPLAINT_STATUS_REJECTED,
    LOGISTICS_COMPLAINT_STATUS_CANCELLED,
}

AFTER_SALES_TERMINAL_STATUSES = {
    AFTER_SALES_STATUS_MERCHANT_REJECTED,
    AFTER_SALES_STATUS_COMPLETED,
    AFTER_SALES_STATUS_CANCELLED,
}

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

cache = RedisCache(redis_url=REDIS_URL, default_ttl_sec=REDIS_CACHE_TTL_SEC)

PRODUCT_FILTER_CACHE_KEY = "products:filters:v2"
CHAT_ACTION_TTL_SEC = int(os.getenv("CHAT_ACTION_TTL_SEC", "300"))
CHAT_ACTION_TYPE_CHECKOUT = "checkout"
CHAT_ACTION_TYPE_AFTER_SALES = "after_sales"
CHAT_ACTION_TYPE_CANCEL_ORDER = "cancel_order"
CHAT_ACTION_TYPE_UPDATE_ORDER_SHIPPING = "update_order_shipping"
CHAT_ACTION_TYPE_LOGISTICS_COMPLAINT = "logistics_complaint"
PRODUCT_VIEW_HISTORY_MAX_ITEMS = 20
DEFAULT_PRODUCT_HISTORY_LIMIT = 8
DEFAULT_PRODUCT_RECOMMENDATION_LIMIT = 5
PENDING_CHAT_ACTION_MEMORY: dict[str, dict[str, Any]] = {}
_amap_throttle_lock = asyncio.Lock()
_amap_last_call_time = 0.0


@dataclass
class RealtimeConnection:
    connection_id: int
    websocket: WebSocket
    user_id: UUID | None
    role: str | None
    shop_id: UUID | None


class RealtimeConnectionManager:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._counter = 0
        self._connections: dict[int, RealtimeConnection] = {}

    async def connect(
        self,
        websocket: WebSocket,
        *,
        user_id: UUID | None,
        role: str | None,
        shop_id: UUID | None,
    ) -> int:
        await websocket.accept()
        async with self._lock:
            self._counter += 1
            connection_id = self._counter
            self._connections[connection_id] = RealtimeConnection(
                connection_id=connection_id,
                websocket=websocket,
                user_id=user_id,
                role=role,
                shop_id=shop_id,
            )
            return connection_id

    async def disconnect(self, connection_id: int) -> None:
        async with self._lock:
            self._connections.pop(connection_id, None)

    async def broadcast(
        self,
        *,
        event: str,
        data: dict[str, Any],
        user_id: UUID | None = None,
        role: str | None = None,
        shop_id: UUID | None = None,
    ) -> None:
        async with self._lock:
            candidates = list(self._connections.values())

        stale_connection_ids: list[int] = []
        normalized_role = normalize_role(role) if role else None
        payload = {
            "event": event,
            "data": data,
            "sent_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }

        for connection in candidates:
            if user_id is not None and connection.user_id != user_id:
                continue
            if normalized_role is not None and normalize_role(connection.role) != normalized_role:
                continue
            if shop_id is not None and connection.shop_id != shop_id:
                continue

            try:
                await connection.websocket.send_json(payload)
            except Exception:
                stale_connection_ids.append(connection.connection_id)

        if stale_connection_ids:
            async with self._lock:
                for connection_id in stale_connection_ids:
                    self._connections.pop(connection_id, None)


realtime_manager = RealtimeConnectionManager()


async def ensure_logistics_geo_schema() -> None:
    statements = [
        'CREATE EXTENSION IF NOT EXISTS "pgcrypto"',
        """
        CREATE TABLE IF NOT EXISTS geo_cache (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            source_text VARCHAR(512) NOT NULL UNIQUE,
            lng DOUBLE PRECISION NOT NULL,
            lat DOUBLE PRECISION NOT NULL,
            provider VARCHAR(32) NOT NULL DEFAULT 'amap',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_geo_cache_updated_at ON geo_cache(updated_at DESC)",
        "ALTER TABLE logistics ADD COLUMN IF NOT EXISTS current_lng DOUBLE PRECISION",
        "ALTER TABLE logistics ADD COLUMN IF NOT EXISTS current_lat DOUBLE PRECISION",
        "ALTER TABLE logistics ADD COLUMN IF NOT EXISTS route_geo JSONB NOT NULL DEFAULT '[]'::jsonb",
    ]
    async with engine.begin() as conn:
        for statement in statements:
            await conn.execute(text(statement))


async def ensure_catalog_schema() -> None:
    statements = [
        "ALTER TABLE shops ADD COLUMN IF NOT EXISTS logo_url TEXT",
        "ALTER TABLE shops ADD COLUMN IF NOT EXISTS rating DOUBLE PRECISION",
        "ALTER TABLE shops ADD COLUMN IF NOT EXISTS service_score DOUBLE PRECISION",
        "ALTER TABLE shops ADD COLUMN IF NOT EXISTS logistics_score DOUBLE PRECISION",
        "ALTER TABLE shops ADD COLUMN IF NOT EXISTS after_sales_score DOUBLE PRECISION",
        "ALTER TABLE shops ADD COLUMN IF NOT EXISTS shipping_city VARCHAR(120)",
        "ALTER TABLE shops ADD COLUMN IF NOT EXISTS featured_categories JSONB NOT NULL DEFAULT '[]'::jsonb",
        "ALTER TABLE shops ADD COLUMN IF NOT EXISTS service_tags JSONB NOT NULL DEFAULT '[]'::jsonb",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS brand VARCHAR(120)",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS model VARCHAR(160)",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS sku_code VARCHAR(120)",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS original_price DECIMAL(10, 2)",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS rating DOUBLE PRECISION",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS review_count INT NOT NULL DEFAULT 0",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS monthly_sales INT NOT NULL DEFAULT 0",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS ship_in_hours INT NOT NULL DEFAULT 0",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS warranty_days INT NOT NULL DEFAULT 0",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS tags JSONB NOT NULL DEFAULT '[]'::jsonb",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS spec_highlights JSONB NOT NULL DEFAULT '[]'::jsonb",
        "CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand)",
        "CREATE INDEX IF NOT EXISTS idx_products_monthly_sales ON products(monthly_sales DESC)",
        "CREATE INDEX IF NOT EXISTS idx_products_rating ON products(rating DESC)",
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'chk_products_original_price'
            ) THEN
                ALTER TABLE products
                ADD CONSTRAINT chk_products_original_price
                CHECK (original_price IS NULL OR original_price >= price);
            END IF;
        END $$;
        """,
    ]
    async with engine.begin() as conn:
        for statement in statements:
            await conn.execute(text(statement))


async def ensure_product_view_history_schema() -> None:
    statements = [
        """
        CREATE TABLE IF NOT EXISTS product_view_history (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            product_id uuid NOT NULL REFERENCES products(id) ON DELETE CASCADE,
            view_count INT NOT NULL DEFAULT 1 CHECK (view_count > 0),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            last_viewed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_product_view_history_user_product
        ON product_view_history(user_id, product_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_product_view_history_user_last_viewed_at
        ON product_view_history(user_id, last_viewed_at DESC)
        """,
    ]
    async with engine.begin() as conn:
        for statement in statements:
            await conn.execute(text(statement))


async def ensure_order_service_schema() -> None:
    statements = [
        """
        CREATE TABLE IF NOT EXISTS logistics_complaints (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            order_id VARCHAR(50) NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            reason TEXT NOT NULL,
            status VARCHAR(50) NOT NULL,
            resolution_note TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_logistics_complaints_order_id ON logistics_complaints(order_id)",
        """
        CREATE INDEX IF NOT EXISTS idx_logistics_complaints_status_updated_at
        ON logistics_complaints(status, updated_at DESC)
        """,
    ]
    async with engine.begin() as conn:
        for statement in statements:
            await conn.execute(text(statement))


@app.on_event("startup")
async def on_startup() -> None:
    logger.info(
        "Backend config loaded. env_file=%s exists=%s amap_web_key=%s amap_sig=%s",
        ENV_FILE_PATH,
        ENV_FILE_PATH.is_file(),
        mask_secret_for_log(AMAP_WEB_KEY),
        "configured" if AMAP_WEB_SIG else "not_configured",
    )
    if not AMAP_WEB_KEY:
        logger.warning(
            "AMAP_WEB_KEY is empty. Shipping route geocode will fall back to text-only logistics until backend/.env is configured."
        )
    UPLOAD_ROOT_DIR.mkdir(parents=True, exist_ok=True)
    await ensure_logistics_geo_schema()
    await ensure_catalog_schema()
    await ensure_product_view_history_schema()
    await ensure_order_service_schema()
    await cache.connect()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await cache.close()


def dump_response_model(model: object) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")  # type: ignore[attr-defined]
    return json.loads(model.json())  # type: ignore[attr-defined]


def parse_response_model(model_cls, payload: dict):
    if hasattr(model_cls, "model_validate"):
        return model_cls.model_validate(payload)  # type: ignore[attr-defined]
    return model_cls.parse_obj(payload)


def clean_kb_source_type(source_type: str) -> str:
    normalized = (source_type or "").strip().lower()
    if normalized not in {"policy", "manual"}:
        raise HTTPException(status_code=400, detail="source_type must be policy or manual")
    return normalized


def split_text_into_chunks(text: str, *, chunk_size: int, overlap: int) -> list[str]:
    cleaned = (text or "").strip()
    if not cleaned:
        return []
    normalized_chunk_size = max(150, chunk_size)
    normalized_overlap = max(0, min(overlap, normalized_chunk_size - 1))
    step = max(1, normalized_chunk_size - normalized_overlap)
    chunks: list[str] = []
    for start in range(0, len(cleaned), step):
        chunk = cleaned[start : start + normalized_chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        if start + normalized_chunk_size >= len(cleaned):
            break
    return chunks


def compute_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def infer_image_size(content: bytes) -> tuple[int | None, int | None]:
    try:
        with Image.open(BytesIO(content)) as image:
            width, height = image.size
            return int(width), int(height)
    except Exception:
        return None, None


def build_vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{item:.9f}" for item in vector) + "]"


def safe_parse_json_object(raw_text: str) -> dict[str, Any]:
    text = (raw_text or "").strip()
    if not text:
        return {}
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {}
    except Exception:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return {}
    try:
        value = json.loads(match.group(0))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


async def generate_embedding(text_content: str) -> list[float]:
    payload_embed = {
        "model": OLLAMA_EMBED_MODEL,
        "input": [text_content],
    }
    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT_SEC) as client:
            response = await client.post(f"{OLLAMA_BASE_URL}/api/embed", json=payload_embed)
        response.raise_for_status()
        payload = response.json()
        embeddings = payload.get("embeddings") if isinstance(payload, dict) else None
        if isinstance(embeddings, list) and embeddings and isinstance(embeddings[0], list):
            vector = [float(item) for item in embeddings[0]]
            if len(vector) != KB_EMBEDDING_DIM:
                raise HTTPException(
                    status_code=500,
                    detail=f"Embedding dimension mismatch: expected {KB_EMBEDDING_DIM}, got {len(vector)}",
                )
            return vector
    except HTTPException:
        raise
    except Exception:
        pass

    payload_legacy = {
        "model": OLLAMA_EMBED_MODEL,
        "prompt": text_content,
    }
    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT_SEC) as client:
            response = await client.post(f"{OLLAMA_BASE_URL}/api/embeddings", json=payload_legacy)
        response.raise_for_status()
        payload = response.json()
        embedding = payload.get("embedding") if isinstance(payload, dict) else None
        if isinstance(embedding, list):
            vector = [float(item) for item in embedding]
            if len(vector) != KB_EMBEDDING_DIM:
                raise HTTPException(
                    status_code=500,
                    detail=f"Embedding dimension mismatch: expected {KB_EMBEDDING_DIM}, got {len(vector)}",
                )
            return vector
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Embedding service unavailable: {exc}") from exc

    raise HTTPException(status_code=503, detail="Embedding service returned invalid payload")


async def retrieve_kb_knowledge(
    *,
    session: AsyncSession,
    source_type: str,
    query_text: str,
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    cleaned_query = (query_text or "").strip()
    if not cleaned_query:
        return []

    vector = await generate_embedding(cleaned_query)
    vector_literal = build_vector_literal(vector)
    limit = max(1, min(top_k or KB_RETRIEVAL_TOP_K, 10))
    normalized_source_type = clean_kb_source_type(source_type)

    vector_statement = text(
        """
        SELECT
            c.id AS chunk_id,
            c.chunk_text AS chunk_text,
            c.metadata AS metadata,
            d.title AS title,
            d.version AS version,
            d.source_type AS source_type,
            (1 - (c.embedding <=> CAST(:embedding AS vector))) AS score
        FROM kb_chunks c
        JOIN kb_documents d ON d.id = c.document_id
        WHERE d.source_type = :source_type AND d.status = 'active'
        ORDER BY c.embedding <=> CAST(:embedding AS vector)
        LIMIT :limit
        """
    )
    vector_rows = (await session.execute(
        vector_statement,
        {"embedding": vector_literal, "source_type": normalized_source_type, "limit": limit},
    )).mappings().all()

    keyword_statement = text(
        """
        SELECT
            c.id AS chunk_id,
            c.chunk_text AS chunk_text,
            c.metadata AS metadata,
            d.title AS title,
            d.version AS version,
            d.source_type AS source_type,
            ts_rank(to_tsvector('simple', c.chunk_text), plainto_tsquery('simple', :query)) AS score
        FROM kb_chunks c
        JOIN kb_documents d ON d.id = c.document_id
        WHERE d.source_type = :source_type
          AND d.status = 'active'
          AND to_tsvector('simple', c.chunk_text) @@ plainto_tsquery('simple', :query)
        ORDER BY score DESC
        LIMIT :limit
        """
    )
    keyword_rows = (await session.execute(
        keyword_statement,
        {"query": cleaned_query, "source_type": normalized_source_type, "limit": limit},
    )).mappings().all()

    merged: list[dict[str, Any]] = []
    seen_chunk_ids: set[str] = set()
    for row in [*vector_rows, *keyword_rows]:
        chunk_id = str(row.get("chunk_id") or "")
        if not chunk_id or chunk_id in seen_chunk_ids:
            continue
        seen_chunk_ids.add(chunk_id)
        merged.append(
            {
                "chunk_id": chunk_id,
                "chunk_text": str(row.get("chunk_text") or ""),
                "title": str(row.get("title") or ""),
                "version": str(row.get("version") or ""),
                "source_type": str(row.get("source_type") or ""),
                "score": float(row.get("score") or 0.0),
                "metadata": row.get("metadata") if isinstance(row.get("metadata"), dict) else {},
            }
        )
        if len(merged) >= limit:
            break
    return merged


def normalize_image_analysis(raw: dict[str, Any]) -> dict[str, Any]:
    confidence_raw = raw.get("confidence")
    try:
        confidence = float(confidence_raw)
    except Exception:
        confidence = 0.0
    confidence = max(0.0, min(confidence, 1.0))
    return {
        "issue_type": str(raw.get("issue_type") or "unknown").strip() or "unknown",
        "severity": str(raw.get("severity") or "medium").strip() or "medium",
        "evidence": str(raw.get("evidence") or "").strip(),
        "suggested_action": str(raw.get("suggested_action") or "").strip(),
        "confidence": confidence,
    }


async def analyze_uploaded_image_vlm(
    *,
    session: AsyncSession,
    attachment_id: str,
    current_user: User | None,
) -> dict[str, Any]:
    query_statement = text(
        """
        SELECT id, user_id, local_path, mime
        FROM chat_attachments
        WHERE id = CAST(:attachment_id AS uuid)
        LIMIT 1
        """
    )
    row = (await session.execute(query_statement, {"attachment_id": attachment_id})).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Attachment not found")

    row_user_id = row.get("user_id")
    if current_user and row_user_id and str(row_user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Attachment does not belong to current user")

    local_path = FsPath(str(row.get("local_path") or ""))
    if not local_path.exists() or not local_path.is_file():
        raise HTTPException(status_code=404, detail="Attachment file not found")

    image_bytes = local_path.read_bytes()
    encoded_image = base64.b64encode(image_bytes).decode("ascii")
    system_prompt = (
        "你是电商售后图像分析助手。"
        "请只输出 JSON 对象，字段必须为：issue_type,severity,evidence,suggested_action,confidence。"
        "confidence 范围 0 到 1。"
    )
    user_prompt = "请识别图像中的售后问题，并给出结构化分析结果。"
    payload = {
        "model": OLLAMA_VLM_MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": user_prompt,
                "images": [encoded_image],
            },
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT_SEC) as client:
            response = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
        response.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"VLM service unavailable: {exc}") from exc

    response_payload = response.json() if response.content else {}
    raw_content = ""
    if isinstance(response_payload, dict):
        message_payload = response_payload.get("message")
        if isinstance(message_payload, dict):
            raw_content = str(message_payload.get("content") or "")
    parsed = normalize_image_analysis(safe_parse_json_object(raw_content))
    return {
        "attachment_id": attachment_id,
        "analysis": parsed,
    }


def chat_orders_summary_cache_prefix(user_id: UUID) -> str:
    return f"chat:orders-summary:{user_id}:"


def chat_orders_summary_cache_key(user_id: UUID, limit: int) -> str:
    return f"{chat_orders_summary_cache_prefix(user_id)}{limit}"


def chat_logistics_summary_cache_prefix(user_id: UUID) -> str:
    return f"chat:orders-logistics-summary:{user_id}:"


def chat_logistics_summary_cache_key(user_id: UUID, limit: int, order_id: str | None) -> str:
    order_segment = (order_id or "").strip() or "all"
    return f"{chat_logistics_summary_cache_prefix(user_id)}{limit}:{order_segment}"


def chat_after_sales_summary_cache_prefix(user_id: UUID) -> str:
    return f"chat:after-sales-summary:{user_id}:"


def chat_after_sales_summary_cache_key(user_id: UUID, limit: int) -> str:
    return f"{chat_after_sales_summary_cache_prefix(user_id)}{limit}"


async def invalidate_product_filter_cache() -> None:
    await cache.delete_keys(PRODUCT_FILTER_CACHE_KEY)


async def invalidate_chat_cache_for_user(
    user_id: UUID,
    *,
    orders: bool = False,
    logistics: bool = False,
    after_sales: bool = False,
) -> None:
    if orders:
        await cache.delete_prefix(chat_orders_summary_cache_prefix(user_id))
    if logistics:
        await cache.delete_prefix(chat_logistics_summary_cache_prefix(user_id))
    if after_sales:
        await cache.delete_prefix(chat_after_sales_summary_cache_prefix(user_id))


def chat_pending_action_cache_key(user_id: UUID) -> str:
    return f"chat:pending-action:{user_id}"


def now_unix_ts() -> int:
    return int(datetime.utcnow().timestamp())


async def get_pending_chat_action(user_id: UUID) -> dict[str, Any] | None:
    key = chat_pending_action_cache_key(user_id)
    payload: dict[str, Any] | None = None

    if cache.enabled:
        raw = await cache.get_json(key)
        if isinstance(raw, dict):
            payload = raw
    else:
        raw = PENDING_CHAT_ACTION_MEMORY.get(key)
        if isinstance(raw, dict):
            payload = raw

    if not payload:
        return None

    expires_at = int(payload.get("expires_at_ts") or 0)
    if expires_at > 0 and expires_at <= now_unix_ts():
        await clear_pending_chat_action(user_id)
        return None

    return payload


async def set_pending_chat_action(user_id: UUID, payload: dict[str, Any]) -> None:
    key = chat_pending_action_cache_key(user_id)
    if cache.enabled:
        await cache.set_json(key, payload, ttl_sec=CHAT_ACTION_TTL_SEC)
    else:
        PENDING_CHAT_ACTION_MEMORY[key] = payload


async def clear_pending_chat_action(user_id: UUID) -> None:
    key = chat_pending_action_cache_key(user_id)
    if cache.enabled:
        await cache.delete_keys(key)
    else:
        PENDING_CHAT_ACTION_MEMORY.pop(key, None)


def normalize_chat_cards(raw_cards: Any) -> list[ChatCard]:
    if not isinstance(raw_cards, list):
        return []

    cards: list[ChatCard] = []
    for raw_card in raw_cards:
        if not isinstance(raw_card, dict):
            continue
        card_type = str(raw_card.get("type") or "").strip()
        if not card_type:
            continue
        data = raw_card.get("data")
        cards.append(ChatCard(type=card_type, data=data if isinstance(data, dict) else {}))
    return cards


def normalize_chat_actions(raw_actions: Any) -> list[ChatAction]:
    if not isinstance(raw_actions, list):
        return []

    actions: list[ChatAction] = []
    for raw_action in raw_actions:
        if not isinstance(raw_action, dict):
            continue
        action_type = str(raw_action.get("type") or "").strip()
        label = str(raw_action.get("label") or "").strip()
        if not action_type or not label:
            continue
        payload = raw_action.get("payload")
        style = raw_action.get("style")
        actions.append(
            ChatAction(
                type=action_type,
                label=label,
                payload=payload if isinstance(payload, dict) else {},
                style=str(style).strip() if isinstance(style, str) and style.strip() else None,
            )
        )
    return actions


def build_chat_message(
    text: str,
    *,
    cards: Any = None,
    actions: Any = None,
) -> ChatReplyMessage:
    return ChatReplyMessage(
        text=(text or "").strip(),
        cards=normalize_chat_cards(cards),
        actions=normalize_chat_actions(actions),
    )


def parse_confirmation_command(message: str) -> str | None:
    text = (message or "").strip()
    if not text:
        return None

    match = re.match(r"^(确认|取消|confirm|cancel)\s*[。.!！]?$", text, flags=re.IGNORECASE)
    if not match:
        return None

    action_raw = (match.group(1) or "").strip().lower()
    return "confirm" if action_raw in {"确认", "confirm"} else "cancel"


def build_pending_action_card(pending: dict[str, Any]) -> dict[str, Any]:
    action_type = str(pending.get("type") or "").strip()
    summary = pending.get("summary") if isinstance(pending.get("summary"), dict) else {}
    details_raw = summary.get("details") if isinstance(summary.get("details"), list) else []
    details: list[dict[str, str]] = []

    for raw_item in details_raw:
        if not isinstance(raw_item, dict):
            continue
        label = str(raw_item.get("label") or "").strip()
        value = str(raw_item.get("value") or "").strip()
        if label and value:
            details.append({"label": label, "value": value})

    return {
        "action_type": action_type,
        "title": str(summary.get("title") or "待确认操作"),
        "description": str(summary.get("description") or ""),
        "details": details,
        "created_at": str(pending.get("created_at") or ""),
        "expires_at_ts": int(pending.get("expires_at_ts") or 0),
    }


def build_pending_action_buttons() -> list[dict[str, Any]]:
    return [
        {
            "type": "pending_action_decision",
            "label": "确认执行",
            "style": "primary",
            "payload": {"decision": "confirm"},
        },
        {
            "type": "pending_action_decision",
            "label": "取消操作",
            "style": "danger",
            "payload": {"decision": "cancel"},
        },
    ]


def extract_email_from_message(message: str) -> str | None:
    match = re.search(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", message or "")
    if not match:
        return None
    return normalize_email(match.group(0))


def extract_order_id_from_message(message: str) -> str | None:
    match = re.search(r"(ORD\d{10,})", (message or "").upper())
    if not match:
        return None
    return match.group(1)


def extract_reason_from_message(message: str) -> str | None:
    text = (message or "").strip()
    if not text:
        return None
    for pattern in [r"(?:原因|理由)[:：]\s*(.+)$", r"(?:because|reason)[:：]?\s*(.+)$"]:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match and match.group(1).strip():
            return match.group(1).strip()
    return None


def extract_address_from_message(message: str) -> str | None:
    text = (message or "").strip()
    if not text:
        return None
    match = re.search(r"(?:收货地址|地址)[:：]\s*(.+)$", text, flags=re.IGNORECASE)
    if not match:
        return None
    value = match.group(1).strip()
    value = re.split(r"(?:邮箱|email)[:：]", value, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    return value or None


def extract_logistics_complaint_reason_from_message(message: str) -> str | None:
    reason = extract_reason_from_message(message)
    if reason:
        return reason
    text = (message or "").strip()
    if not text:
        return None
    for pattern in [r"(?:投诉|抱怨|问题)[:：]\s*(.+)$", r"(?:太慢了|一直没动静|一直未更新)\s*(.+)$"]:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match and match.group(1).strip():
            return match.group(1).strip()
    return None


def contains_action_marker(text: str) -> bool:
    markers = ["帮我", "给我", "代我", "立即", "马上", "现在", "直接", "自动", "提交", "发起"]
    return any(marker in text for marker in markers)


def is_checkout_request(message: str) -> bool:
    text = (message or "").strip()
    if not text:
        return False
    lowered = text.lower()
    keywords = ["下单", "购买", "结算", "买单", "checkout", "place order", "buy for me"]
    if not any(keyword in text or keyword in lowered for keyword in keywords):
        return False
    if text.startswith(("如何", "怎么", "怎样", "可以", "请问")):
        return False
    explicit_commands = ["帮我下单", "代我下单", "直接下单", "自动下单", "帮我购买", "帮我结算"]
    return any(command in text for command in explicit_commands) or contains_action_marker(text)


def is_after_sales_request(message: str) -> bool:
    text = (message or "").strip()
    if not text:
        return False
    lowered = text.lower()
    keywords = ["退款", "退货", "换货", "售后", "refund", "return", "exchange"]
    if not any(keyword in text or keyword in lowered for keyword in keywords):
        return False
    if text.startswith(("如何", "怎么", "怎样", "可以", "请问")):
        return False
    explicit_commands = ["帮我退款", "申请退款", "申请退货", "申请换货", "发起售后", "提交售后"]
    return any(command in text for command in explicit_commands) or contains_action_marker(text)


def is_cancel_order_request(message: str) -> bool:
    text = (message or "").strip()
    if not text:
        return False
    lowered = text.lower()
    keywords = ["取消订单", "撤销订单", "cancel order", "cancel my order"]
    if not any(keyword in text or keyword in lowered for keyword in keywords):
        return False
    if text.startswith(("如何", "怎么", "怎样", "可以", "请问")):
        return False
    return True


def is_update_shipping_request(message: str) -> bool:
    text = (message or "").strip()
    if not text:
        return False
    lowered = text.lower()
    keywords = ["修改地址", "修改收货地址", "更新地址", "改地址", "change address", "update address"]
    if not any(keyword in text or keyword in lowered for keyword in keywords):
        return False
    if text.startswith(("如何", "怎么", "怎样", "可以", "请问")):
        return False
    return True


def is_logistics_complaint_request(message: str) -> bool:
    text = (message or "").strip()
    if not text:
        return False
    lowered = text.lower()
    keywords = ["投诉物流", "物流投诉", "投诉快递", "快递投诉", "complain logistics", "delivery complaint"]
    if not any(keyword in text or keyword in lowered for keyword in keywords):
        return False
    if text.startswith(("如何", "怎么", "怎样", "可以", "请问")):
        return False
    return True


async def get_latest_order_for_user(session: AsyncSession, user_id: UUID) -> Order | None:
    statement = select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc()).limit(1)
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def has_active_after_sales_request(session: AsyncSession, order_id: str) -> bool:
    statement = (
        select(AfterSales)
        .where(
            AfterSales.order_id == order_id,
            ~AfterSales.status.in_(tuple(AFTER_SALES_TERMINAL_STATUSES)),
        )
        .limit(1)
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none() is not None


async def has_active_logistics_complaint(session: AsyncSession, order_id: str) -> bool:
    statement = (
        select(LogisticsComplaint)
        .where(
            LogisticsComplaint.order_id == order_id,
            ~LogisticsComplaint.status.in_(tuple(LOGISTICS_COMPLAINT_TERMINAL_STATUSES)),
        )
        .limit(1)
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none() is not None


async def prepare_checkout_chat_action(message: str, current_user: User, session: AsyncSession) -> ChatReplyMessage:
    rows = await fetch_cart_rows(session, current_user.id)
    if not rows:
        return build_chat_message("购物车是空的，先去加购商品后我再帮你下单。")

    shop_ids = {product.shop_id for _, product in rows}
    if len(shop_ids) > 1:
        return build_chat_message("当前购物车包含多个店铺商品，暂时只能同店铺下单。请先整理购物车后再试。")

    for cart_item, product in rows:
        if cart_item.quantity > product.stock:
            return build_chat_message(f"商品「{product.name}」库存不足，请先调整购物车数量。")

    address = extract_address_from_message(message)
    if not address:
        latest_order = await get_latest_order_for_user(session, current_user.id)
        if latest_order and latest_order.address:
            address = latest_order.address.strip()

    contact_email = extract_email_from_message(message) or normalize_email(current_user.email)

    if not address:
        return build_chat_message("可以帮你自动下单。请补充收货地址，例如：下单 地址: 上海市浦东新区XX路88号。")
    if not contact_email:
        return build_chat_message("请补充联系邮箱，例如：下单 邮箱: your@email.com。")

    item_count = sum(cart_item.quantity for cart_item, _ in rows)
    total_amount = round(sum(float(product.price) * cart_item.quantity for cart_item, product in rows), 2)
    preview_names = "、".join(product.name for _, product in rows[:3])
    if len(rows) > 3:
        preview_names = f"{preview_names} 等"

    pending_payload = {
        "type": CHAT_ACTION_TYPE_CHECKOUT,
        "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "expires_at_ts": now_unix_ts() + CHAT_ACTION_TTL_SEC,
        "payload": {
            "address": address,
            "contact_email": contact_email,
        },
        "summary": {
            "title": "自动下单草案",
            "description": "请在弹窗中确认或取消。",
            "details": [
                {"label": "商品", "value": preview_names},
                {"label": "件数", "value": str(item_count)},
                {"label": "总额", "value": f"¥ {total_amount:.2f}"},
                {"label": "收货地址", "value": address},
                {"label": "联系邮箱", "value": contact_email},
            ],
        },
    }
    await set_pending_chat_action(current_user.id, pending_payload)

    return build_chat_message(
        "已生成下单草案，请在下方卡片中确认或取消（5分钟内有效）。",
        cards=[{"type": "pending_action", "data": build_pending_action_card(pending_payload)}],
        actions=build_pending_action_buttons(),
    )


async def prepare_after_sales_chat_action(message: str, current_user: User, session: AsyncSession) -> ChatReplyMessage:
    order_id = extract_order_id_from_message(message)
    if not order_id:
        return build_chat_message("请提供订单号后我才能帮你发起退款/换货，例如：申请退款 ORD202604010001 原因: 尺寸不合适。")

    reason = extract_reason_from_message(message)
    if not reason:
        return build_chat_message("请补充售后原因，例如：申请退款 ORD202604010001 原因: 商品与描述不符。")

    request_type = AFTER_SALES_TYPE_EXCHANGE if "换货" in message else AFTER_SALES_TYPE_RETURN
    order = await get_order_or_404(session, order_id)
    if order.user_id != current_user.id:
        return build_chat_message("该订单不属于当前登录账号，无法为你发起售后。")
    logistics = await get_logistics_by_order(session, order.id)
    stage = resolve_after_sales_stage(order=order, logistics=logistics)
    if stage == ORDER_STATUS_PENDING_SHIPMENT and request_type != AFTER_SALES_TYPE_RETURN:
        return build_chat_message("订单未发货时仅支持申请退货，换货请在签收后发起。")
    if stage == LOGISTICS_STATUS_IN_TRANSIT:
        return build_chat_message("订单物流运输中，暂不支持申请退货/换货。请等待签收后再申请更多售后帮助。")
    if stage == "unsupported":
        return build_chat_message("当前订单状态暂不支持发起售后。")
    if await has_active_after_sales_request(session, order.id):
        return build_chat_message("该订单已有进行中的售后申请，请等待商家处理。")

    pending_payload = {
        "type": CHAT_ACTION_TYPE_AFTER_SALES,
        "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "expires_at_ts": now_unix_ts() + CHAT_ACTION_TTL_SEC,
        "payload": {
            "order_id": order.id,
            "request_type": request_type,
            "reason": reason,
        },
        "summary": {
            "title": "自动售后草案",
            "description": "请在弹窗中确认或取消。",
            "details": [
                {"label": "订单号", "value": order.id},
                {"label": "类型", "value": "换货" if request_type == AFTER_SALES_TYPE_EXCHANGE else "退款/退货"},
                {"label": "原因", "value": reason},
            ],
        },
    }
    await set_pending_chat_action(current_user.id, pending_payload)

    return build_chat_message(
        "已生成售后申请草案，请在下方卡片中确认或取消（5分钟内有效）。",
        cards=[{"type": "pending_action", "data": build_pending_action_card(pending_payload)}],
        actions=build_pending_action_buttons(),
    )


async def prepare_cancel_order_chat_action(message: str, current_user: User, session: AsyncSession) -> ChatReplyMessage:
    order_id = extract_order_id_from_message(message)
    if not order_id:
        return build_chat_message("请提供订单号后我才能帮你取消订单，例如：取消订单 ORD202604010001。")

    order = await get_order_or_404(session, order_id)
    if order.user_id != current_user.id:
        return build_chat_message("该订单不属于当前登录账号，无法为你取消。")
    if order.status == ORDER_STATUS_CANCELLED:
        return build_chat_message("该订单已经取消，无需重复操作。")
    if order.status != ORDER_STATUS_PENDING_SHIPMENT:
        return build_chat_message("只有待发货订单支持取消。订单已发货后请改走售后流程。")
    if await has_active_after_sales_request(session, order.id):
        return build_chat_message("该订单已有进行中的售后申请，请先处理售后记录。")

    pending_payload = {
        "type": CHAT_ACTION_TYPE_CANCEL_ORDER,
        "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "expires_at_ts": now_unix_ts() + CHAT_ACTION_TTL_SEC,
        "payload": {
            "order_id": order.id,
        },
        "summary": {
            "title": "取消订单草案",
            "description": "取消后会恢复商品库存，请确认是否继续。",
            "details": [
                {"label": "订单号", "value": order.id},
                {"label": "当前状态", "value": "待发货"},
                {"label": "订单金额", "value": f"¥ {float(order.total_amount):.2f}"},
            ],
        },
    }
    await set_pending_chat_action(current_user.id, pending_payload)
    return build_chat_message(
        "已生成取消订单草案，请在下方卡片中确认或取消（5分钟内有效）。",
        cards=[{"type": "pending_action", "data": build_pending_action_card(pending_payload)}],
        actions=build_pending_action_buttons(),
    )


async def prepare_update_shipping_chat_action(message: str, current_user: User, session: AsyncSession) -> ChatReplyMessage:
    order_id = extract_order_id_from_message(message)
    if not order_id:
        return build_chat_message(
            "请提供订单号和新地址后我才能帮你修改收货信息，例如：修改地址 ORD202604010001 地址: 上海市浦东新区XX路88号。"
        )

    address = extract_address_from_message(message)
    if not address:
        return build_chat_message("请补充新的收货地址，例如：修改地址 ORD202604010001 地址: 上海市浦东新区XX路88号。")

    order = await get_order_or_404(session, order_id)
    if order.user_id != current_user.id:
        return build_chat_message("该订单不属于当前登录账号，无法为你修改收货信息。")
    if order.status == ORDER_STATUS_CANCELLED:
        return build_chat_message("该订单已经取消，不能再修改收货信息。")
    if order.status != ORDER_STATUS_PENDING_SHIPMENT:
        return build_chat_message("只有待发货订单支持修改收货信息。订单发货后请联系人工处理。")

    next_contact_email = extract_email_from_message(message) or normalize_email(order.contact_email)
    pending_payload = {
        "type": CHAT_ACTION_TYPE_UPDATE_ORDER_SHIPPING,
        "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "expires_at_ts": now_unix_ts() + CHAT_ACTION_TTL_SEC,
        "payload": {
            "order_id": order.id,
            "address": address,
            "contact_email": next_contact_email,
        },
        "summary": {
            "title": "修改收货信息草案",
            "description": "请确认新的收货地址与联系邮箱。",
            "details": [
                {"label": "订单号", "value": order.id},
                {"label": "新地址", "value": address},
                {"label": "联系邮箱", "value": next_contact_email},
            ],
        },
    }
    await set_pending_chat_action(current_user.id, pending_payload)
    return build_chat_message(
        "已生成收货信息修改草案，请在下方卡片中确认或取消（5分钟内有效）。",
        cards=[{"type": "pending_action", "data": build_pending_action_card(pending_payload)}],
        actions=build_pending_action_buttons(),
    )


async def prepare_logistics_complaint_chat_action(message: str, current_user: User, session: AsyncSession) -> ChatReplyMessage:
    order_id = extract_order_id_from_message(message)
    if not order_id:
        return build_chat_message("请提供订单号后我才能帮你发起物流投诉，例如：投诉物流 ORD202604010001 原因: 包裹长时间未更新。")

    reason = extract_logistics_complaint_reason_from_message(message)
    if not reason:
        return build_chat_message("请补充投诉原因，例如：投诉物流 ORD202604010001 原因: 包裹长时间未更新。")

    order = await get_order_or_404(session, order_id)
    if order.user_id != current_user.id:
        return build_chat_message("该订单不属于当前登录账号，无法为你发起物流投诉。")
    if order.status != ORDER_STATUS_SHIPPED:
        return build_chat_message("只有已发货订单支持物流投诉。未发货订单建议先联系商家或直接取消。")
    if not await get_logistics_by_order(session, order.id):
        return build_chat_message("该订单还没有有效物流信息，暂时无法发起物流投诉。")
    if await has_active_logistics_complaint(session, order.id):
        return build_chat_message("该订单已有进行中的物流投诉，请等待处理结果。")

    pending_payload = {
        "type": CHAT_ACTION_TYPE_LOGISTICS_COMPLAINT,
        "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "expires_at_ts": now_unix_ts() + CHAT_ACTION_TTL_SEC,
        "payload": {
            "order_id": order.id,
            "reason": reason,
        },
        "summary": {
            "title": "物流投诉草案",
            "description": "请确认投诉内容，提交后将进入处理队列。",
            "details": [
                {"label": "订单号", "value": order.id},
                {"label": "投诉原因", "value": reason},
            ],
        },
    }
    await set_pending_chat_action(current_user.id, pending_payload)
    return build_chat_message(
        "已生成物流投诉草案，请在下方卡片中确认或取消（5分钟内有效）。",
        cards=[{"type": "pending_action", "data": build_pending_action_card(pending_payload)}],
        actions=build_pending_action_buttons(),
    )


async def execute_pending_checkout_action(
    current_user: User,
    session: AsyncSession,
    payload: dict[str, Any],
) -> ChatReplyMessage:
    address = (payload.get("address") or "").strip()
    contact_email = normalize_email((payload.get("contact_email") or "").strip())
    if not address or not contact_email:
        raise HTTPException(status_code=400, detail="Pending checkout payload is incomplete")

    order_detail = await create_order(
        payload=CreateOrderRequest(address=address, contact_email=contact_email),
        session=session,
        current_user=current_user,
    )
    base_url = FRONTEND_BASE_URL.rstrip("/")
    item_count = sum(int(item.quantity) for item in order_detail.items)
    return build_chat_message(
        "下单成功，订单已创建。",
        cards=[
            {
                "type": "order",
                "data": {
                    "id": order_detail.id,
                    "status": order_detail.status,
                    "total_amount": float(order_detail.total_amount),
                    "item_count": item_count,
                    "created_at": order_detail.created_at.isoformat(),
                    "order_link": f"{base_url}/order/{order_detail.id}",
                },
            }
        ],
    )


async def execute_pending_after_sales_action(
    current_user: User,
    session: AsyncSession,
    payload: dict[str, Any],
) -> ChatReplyMessage:
    order_id = (payload.get("order_id") or "").strip()
    request_type = normalize_after_sales_type(str(payload.get("request_type") or AFTER_SALES_TYPE_RETURN))
    reason = (payload.get("reason") or "").strip()
    if not order_id or request_type not in AFTER_SALES_ALLOWED_TYPES or not reason:
        raise HTTPException(status_code=400, detail="Pending after-sales payload is incomplete")

    result = await create_after_sales_request(
        payload=CreateAfterSalesRequest(type=request_type, reason=reason),
        order_id=order_id,
        session=session,
        current_user=current_user,
    )
    order = await get_order_or_404(session, order_id)
    count_result = await session.execute(select(func.count(OrderItem.id)).where(OrderItem.order_id == order_id))
    item_count = int(count_result.scalar_one() or 0)
    base_url = FRONTEND_BASE_URL.rstrip("/")
    type_label = "换货" if request_type == AFTER_SALES_TYPE_EXCHANGE else "退款/退货"
    order_link = f"{base_url}/order/{order_id}"
    return build_chat_message(
        f"{type_label}申请已提交。",
        cards=[
            {
                "type": "after_sales",
                "data": {
                    "id": str(result.id),
                    "order_id": order_id,
                    "type": request_type,
                    "status": result.status,
                    "created_at": result.created_at.isoformat(),
                    "reason": reason,
                    "order_link": order_link,
                },
            },
            {
                "type": "order",
                "data": {
                    "id": order.id,
                    "status": order.status,
                    "total_amount": float(order.total_amount),
                    "item_count": item_count,
                    "created_at": order.created_at.isoformat(),
                    "order_link": order_link,
                },
            },
        ],
    )


async def execute_pending_cancel_order_action(
    current_user: User,
    session: AsyncSession,
    payload: dict[str, Any],
) -> ChatReplyMessage:
    order_id = (payload.get("order_id") or "").strip()
    if not order_id:
        raise HTTPException(status_code=400, detail="Pending cancel-order payload is incomplete")

    order_detail = await cancel_order(order_id=order_id, session=session, current_user=current_user)
    return build_chat_message(
        "订单已取消。",
        cards=[
            {
                "type": "order",
                "data": {
                    "id": order_detail.id,
                    "status": order_detail.status,
                    "total_amount": float(order_detail.total_amount),
                    "item_count": len(order_detail.items),
                    "created_at": order_detail.created_at.isoformat(),
                    "order_link": f"{FRONTEND_BASE_URL.rstrip('/')}/order/{order_detail.id}",
                },
            }
        ],
    )


async def execute_pending_update_order_shipping_action(
    current_user: User,
    session: AsyncSession,
    payload: dict[str, Any],
) -> ChatReplyMessage:
    order_id = (payload.get("order_id") or "").strip()
    address = (payload.get("address") or "").strip()
    contact_email = normalize_email((payload.get("contact_email") or "").strip())
    if not order_id or not address:
        raise HTTPException(status_code=400, detail="Pending update-shipping payload is incomplete")

    order_detail = await update_order_shipping(
        order_id=order_id,
        payload=UpdateOrderShippingRequest(address=address, contact_email=contact_email or None),
        session=session,
        current_user=current_user,
    )
    return build_chat_message(
        "收货信息已更新。",
        cards=[
            {
                "type": "order",
                "data": {
                    "id": order_detail.id,
                    "status": order_detail.status,
                    "total_amount": float(order_detail.total_amount),
                    "item_count": len(order_detail.items),
                    "created_at": order_detail.created_at.isoformat(),
                    "order_link": f"{FRONTEND_BASE_URL.rstrip('/')}/order/{order_detail.id}",
                },
            }
        ],
    )


async def execute_pending_logistics_complaint_action(
    current_user: User,
    session: AsyncSession,
    payload: dict[str, Any],
) -> ChatReplyMessage:
    order_id = (payload.get("order_id") or "").strip()
    reason = (payload.get("reason") or "").strip()
    if not order_id or not reason:
        raise HTTPException(status_code=400, detail="Pending logistics-complaint payload is incomplete")

    complaint = await create_logistics_complaint(
        payload=CreateLogisticsComplaintRequest(reason=reason),
        order_id=order_id,
        session=session,
        current_user=current_user,
    )
    return build_chat_message(
        "物流投诉已提交。",
        cards=[
            {
                "type": "logistics_complaint",
                "data": {
                    "id": str(complaint.id),
                    "order_id": complaint.order_id,
                    "status": complaint.status,
                    "reason": complaint.reason,
                    "resolution_note": complaint.resolution_note,
                    "created_at": complaint.created_at.isoformat(),
                    "updated_at": complaint.updated_at.isoformat(),
                    "order_link": f"{FRONTEND_BASE_URL.rstrip('/')}/order/{complaint.order_id}",
                },
            }
        ],
    )


async def decide_pending_chat_action(
    decision: str,
    current_user: User,
    session: AsyncSession,
) -> ChatReplyMessage:
    normalized_decision = (decision or "").strip().lower()
    if normalized_decision not in {"confirm", "cancel"}:
        raise HTTPException(status_code=400, detail="decision must be confirm or cancel")

    pending = await get_pending_chat_action(current_user.id)
    if not pending:
        return build_chat_message("当前没有待确认的自动操作。")

    if normalized_decision == "cancel":
        await clear_pending_chat_action(current_user.id)
        return build_chat_message("已取消本次自动操作。")

    action_type = str(pending.get("type") or "").strip()
    action_payload = pending.get("payload") if isinstance(pending.get("payload"), dict) else {}

    try:
        if action_type == CHAT_ACTION_TYPE_CHECKOUT:
            result_message = await execute_pending_checkout_action(current_user, session, action_payload)
        elif action_type == CHAT_ACTION_TYPE_AFTER_SALES:
            result_message = await execute_pending_after_sales_action(current_user, session, action_payload)
        elif action_type == CHAT_ACTION_TYPE_CANCEL_ORDER:
            result_message = await execute_pending_cancel_order_action(current_user, session, action_payload)
        elif action_type == CHAT_ACTION_TYPE_UPDATE_ORDER_SHIPPING:
            result_message = await execute_pending_update_order_shipping_action(current_user, session, action_payload)
        elif action_type == CHAT_ACTION_TYPE_LOGISTICS_COMPLAINT:
            result_message = await execute_pending_logistics_complaint_action(current_user, session, action_payload)
        else:
            raise HTTPException(status_code=400, detail="Unsupported pending action type")
    except HTTPException as exc:
        await clear_pending_chat_action(current_user.id)
        return build_chat_message(f"自动执行失败：{exc.detail}。本次待确认操作已清除，请重新发起。")
    except Exception:
        await clear_pending_chat_action(current_user.id)
        return build_chat_message("自动执行失败：服务出现异常。本次待确认操作已清除，请稍后重试。")

    await clear_pending_chat_action(current_user.id)
    return result_message


async def handle_chat_transaction_action(message: str, current_user: User, session: AsyncSession) -> ChatReplyMessage | None:
    if normalize_role(current_user.role) != "customer":
        return None

    pending = await get_pending_chat_action(current_user.id)
    command = parse_confirmation_command(message)

    if command:
        return await decide_pending_chat_action(command, current_user, session)

    if pending and (
        is_checkout_request(message)
        or is_after_sales_request(message)
        or is_cancel_order_request(message)
        or is_update_shipping_request(message)
        or is_logistics_complaint_request(message)
    ):
        return build_chat_message(
            "你有待确认操作，请先在下方卡片中确认或取消。",
            cards=[{"type": "pending_action", "data": build_pending_action_card(pending)}],
            actions=build_pending_action_buttons(),
        )

    if is_checkout_request(message):
        return await prepare_checkout_chat_action(message, current_user, session)

    if is_after_sales_request(message):
        return await prepare_after_sales_chat_action(message, current_user, session)

    if is_cancel_order_request(message):
        return await prepare_cancel_order_chat_action(message, current_user, session)

    if is_update_shipping_request(message):
        return await prepare_update_shipping_chat_action(message, current_user, session)

    if is_logistics_complaint_request(message):
        return await prepare_logistics_complaint_chat_action(message, current_user, session)

    return None


def normalize_rasa_response_messages(raw_data: Any) -> list[ChatReplyMessage]:
    if not isinstance(raw_data, list):
        return []

    messages: list[ChatReplyMessage] = []
    for item in raw_data:
        if not isinstance(item, dict):
            continue
        custom_payload = item.get("custom") if isinstance(item.get("custom"), dict) else {}
        text = item.get("text")
        if not isinstance(text, str):
            custom_text = custom_payload.get("text")
            text = custom_text if isinstance(custom_text, str) else ""

        cards = item.get("cards")
        actions = item.get("actions")
        if cards is None:
            cards = custom_payload.get("cards")
        if actions is None:
            actions = custom_payload.get("actions")

        parsed = build_chat_message(text or "", cards=cards, actions=actions)
        if parsed.text or parsed.cards or parsed.actions:
            messages.append(parsed)
    return messages


async def parse_rasa_intent(message: str) -> tuple[str, float]:
    parse_url = f"{RASA_SERVER_URL.rstrip('/')}{RASA_PARSE_PATH}"
    try:
        async with httpx.AsyncClient(timeout=RASA_REQUEST_TIMEOUT_SEC) as client:
            response = await client.post(parse_url, json={"text": message})
        response.raise_for_status()
        payload = response.json()
        intent = payload.get("intent") if isinstance(payload, dict) else {}
        intent_name = str(intent.get("name") or "").strip()
        confidence = float(intent.get("confidence") or 0.0)
        return intent_name, confidence
    except Exception:
        return "", 0.0


def decide_chat_route(*, message: str, intent_name: str, intent_confidence: float) -> str:
    if not CHAT_ROUTER_ENABLE_AGENT:
        return "rule"
    if intent_name == "nlu_fallback":
        return "agent"
    if intent_confidence < CHAT_ROUTER_RASA_CONFIDENCE_THRESHOLD:
        return "agent"
    if is_complex_query(message):
        return "agent"
    if intent_name in FAST_ROUTER_INTENTS:
        return "rule"
    return "agent"


async def call_rasa_webhook(*, sender_id: str, message: str, metadata: dict[str, Any]) -> list[ChatReplyMessage]:
    webhook_url = f"{RASA_SERVER_URL.rstrip('/')}{RASA_REST_WEBHOOK_PATH}"
    try:
        async with httpx.AsyncClient(timeout=RASA_REQUEST_TIMEOUT_SEC) as client:
            response = await client.post(
                webhook_url,
                json={"sender": sender_id, "message": message, "metadata": metadata},
            )
        response.raise_for_status()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Rasa response timeout")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Rasa request failed with status {exc.response.status_code}",
        )
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="Rasa service unavailable")

    data = response.json()
    if not isinstance(data, list):
        raise HTTPException(status_code=502, detail="Invalid response from Rasa")
    messages = normalize_rasa_response_messages(data)
    if not messages:
        messages.append(build_chat_message("暂时没有生成有效回复，请稍后重试。"))
    return messages


async def query_price_protection_candidates(
    *,
    user_id: UUID,
    session: AsyncSession,
    order_limit: int = 3,
) -> dict[str, Any]:
    statement = (
        select(Order)
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .limit(max(1, min(order_limit, 10)))
    )
    order_result = await session.execute(statement)
    orders = order_result.scalars().all()
    if not orders:
        return {"orders": [], "eligible_items": [], "total_refund_diff": 0.0}

    order_ids = [order.id for order in orders]
    item_result = await session.execute(select(OrderItem).where(OrderItem.order_id.in_(order_ids)))
    order_items = item_result.scalars().all()
    product_ids = {item.product_id for item in order_items}
    product_map: dict[UUID, Product] = {}
    if product_ids:
        product_result = await session.execute(select(Product).where(Product.id.in_(tuple(product_ids))))
        products = product_result.scalars().all()
        product_map = {product.id: product for product in products}

    order_briefs: list[dict[str, Any]] = []
    eligible_items: list[dict[str, Any]] = []
    total_refund_diff = 0.0
    for order in orders:
        order_briefs.append(
            {
                "order_id": order.id,
                "created_at": order.created_at.isoformat(),
                "status": order.status,
            }
        )
        for item in order_items:
            if item.order_id != order.id:
                continue
            product = product_map.get(item.product_id)
            if not product:
                continue
            old_unit_price = float(item.unit_price)
            new_unit_price = float(product.price)
            unit_diff = round(old_unit_price - new_unit_price, 2)
            if unit_diff <= 0:
                continue
            quantity = int(item.quantity)
            refund_diff = round(unit_diff * quantity, 2)
            total_refund_diff = round(total_refund_diff + refund_diff, 2)
            eligible_items.append(
                {
                    "order_id": item.order_id,
                    "product_id": str(item.product_id),
                    "product_name": item.product_name,
                    "old_unit_price": old_unit_price,
                    "new_unit_price": new_unit_price,
                    "quantity": quantity,
                    "refund_diff": refund_diff,
                }
            )

    return {
        "orders": order_briefs,
        "eligible_items": eligible_items,
        "total_refund_diff": total_refund_diff,
    }


def serialize_chat_cards(cards: list[ChatCard]) -> list[dict[str, Any]]:
    return [{"type": card.type, "data": dict(card.data)} for card in cards]


def serialize_chat_actions(actions: list[ChatAction]) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for action in actions:
        item: dict[str, Any] = {"type": action.type, "label": action.label, "payload": dict(action.payload)}
        if action.style:
            item["style"] = action.style
        serialized.append(item)
    return serialized


async def run_nexau_agent_orchestrator(
    *,
    message: str,
    current_user: User | None,
    session: AsyncSession,
    attachments: list[str] | None = None,
) -> tuple[ChatReplyMessage, list[dict[str, Any]]]:
    orchestrator = NexAUAgentOrchestrator(
        llm_provider=AGENT_LLM_PROVIDER,
        llm_base_url=AGENT_LLM_BASE_URL,
        llm_model=AGENT_LLM_MODEL,
        llm_timeout_sec=AGENT_LLM_TIMEOUT_SEC,
        llm_api_key=AGENT_LLM_API_KEY,
        frontend_base_url=FRONTEND_BASE_URL,
    )

    async def tool_query_orders_summary(user_id: str, limit: int = 5) -> dict[str, Any]:
        response = await chat_internal_orders_summary(
            user_id=UUID(user_id),
            limit=max(1, min(limit, 10)),
            x_rasa_token=(RASA_INTERNAL_TOKEN or None),
            session=session,
        )
        cards = [
            {
                "type": "order",
                "data": {
                    "id": item.id,
                    "status": item.status,
                    "total_amount": item.total_amount,
                    "item_count": item.item_count,
                    "created_at": item.created_at.isoformat(),
                    "order_link": item.order_link,
                },
            }
            for item in response.items
        ]
        return {"observation": dump_response_model(response), "cards": cards}

    async def tool_query_logistics_summary(user_id: str, order_id: str | None = None, limit: int = 5) -> dict[str, Any]:
        response = await chat_internal_orders_logistics_summary(
            user_id=UUID(user_id),
            order_id=order_id,
            limit=max(1, min(limit, 10)),
            x_rasa_token=(RASA_INTERNAL_TOKEN or None),
            session=session,
        )
        cards = [
            {
                "type": "logistics",
                "data": {
                    "id": item.id,
                    "status": item.status,
                    "created_at": item.created_at.isoformat(),
                    "order_link": item.order_link,
                    "tracking_no": item.tracking_no,
                    "current_location": item.current_location,
                    "estimated_delivery_at": (
                        item.estimated_delivery_at.isoformat() if item.estimated_delivery_at else None
                    ),
                    "route_plan": list(item.route_plan),
                },
            }
            for item in response.items
        ]
        return {"observation": dump_response_model(response), "cards": cards}

    async def tool_query_after_sales_summary(user_id: str, limit: int = 5) -> dict[str, Any]:
        response = await chat_internal_after_sales_summary(
            user_id=UUID(user_id),
            limit=max(1, min(limit, 10)),
            x_rasa_token=(RASA_INTERNAL_TOKEN or None),
            session=session,
        )
        cards = [
            {
                "type": "after_sales",
                "data": {
                    "id": str(item.id),
                    "order_id": item.order_id,
                    "type": item.type,
                    "status": item.status,
                    "created_at": item.created_at.isoformat(),
                    "reason": item.reason,
                    "order_link": item.order_link,
                },
            }
            for item in response.items
        ]
        return {"observation": dump_response_model(response), "cards": cards}

    async def tool_query_price_protection(user_id: str) -> dict[str, Any]:
        observation = await query_price_protection_candidates(user_id=UUID(user_id), session=session)
        return {"observation": observation}

    async def tool_query_product_recommendations(
        query: str,
        user_id: str = "",
        category: str = "",
        limit: int = DEFAULT_PRODUCT_RECOMMENDATION_LIMIT,
    ) -> dict[str, Any]:
        parsed_user_id = UUID(user_id) if user_id.strip() else None
        response = await get_personalized_product_recommendations(
            session,
            user_id=parsed_user_id,
            query=query,
            category=category,
            limit=max(1, min(limit, 20)),
        )
        cards = [product_read_to_chat_card(item) for item in response.items]
        return {"observation": dump_response_model(response), "cards": cards}

    async def tool_retrieve_policy_knowledge(query: str) -> dict[str, Any]:
        matches = await retrieve_kb_knowledge(
            session=session,
            source_type="policy",
            query_text=query,
            top_k=KB_RETRIEVAL_TOP_K,
        )
        observation = {
            "source_type": "policy",
            "query": query,
            "matches": [
                {
                    "title": item["title"],
                    "version": item["version"],
                    "score": item["score"],
                    "chunk_text": item["chunk_text"],
                }
                for item in matches
            ],
        }
        return {"observation": observation}

    async def tool_retrieve_manual_knowledge(query: str) -> dict[str, Any]:
        matches = await retrieve_kb_knowledge(
            session=session,
            source_type="manual",
            query_text=query,
            top_k=KB_RETRIEVAL_TOP_K,
        )
        observation = {
            "source_type": "manual",
            "query": query,
            "matches": [
                {
                    "title": item["title"],
                    "version": item["version"],
                    "score": item["score"],
                    "chunk_text": item["chunk_text"],
                }
                for item in matches
            ],
        }
        return {"observation": observation}

    async def tool_analyze_uploaded_image_vlm(attachment_id: str) -> dict[str, Any]:
        result = await analyze_uploaded_image_vlm(
            session=session,
            attachment_id=attachment_id,
            current_user=current_user,
        )
        analysis = result["analysis"]
        return {
            "observation": result,
            "cards": [
                {
                    "type": "image_analysis",
                    "data": {
                        "attachment_id": attachment_id,
                        "issue_type": analysis.get("issue_type"),
                        "severity": analysis.get("severity"),
                        "evidence": analysis.get("evidence"),
                        "suggested_action": analysis.get("suggested_action"),
                        "confidence": analysis.get("confidence"),
                    },
                }
            ],
        }

    async def tool_draft_after_sales_request(order_id: str, request_type: str, reason: str) -> dict[str, Any]:
        if not current_user:
            raise HTTPException(status_code=401, detail="Unauthenticated user cannot create draft action")
        action_text = "换货" if request_type == AFTER_SALES_TYPE_EXCHANGE else "退款"
        synthetic_message = f"申请{action_text} {order_id} 原因: {reason}"
        reply = await prepare_after_sales_chat_action(synthetic_message, current_user, session)
        return {
            "observation": {
                "draft_text": reply.text,
                "cards_count": len(reply.cards),
                "actions_count": len(reply.actions),
            },
            "cards": serialize_chat_cards(reply.cards),
            "actions": serialize_chat_actions(reply.actions),
        }

    orchestrator.register_tool(
        name="query_orders_summary",
        mode="read",
        description="查询当前用户最近订单汇总",
        handler=tool_query_orders_summary,
    )
    orchestrator.register_tool(
        name="query_logistics_summary",
        mode="read",
        description="查询当前用户物流汇总",
        handler=tool_query_logistics_summary,
    )
    orchestrator.register_tool(
        name="query_after_sales_summary",
        mode="read",
        description="查询当前用户售后汇总",
        handler=tool_query_after_sales_summary,
    )
    orchestrator.register_tool(
        name="query_price_protection",
        mode="read",
        description="基于订单与当前商品价格计算可补差价信息",
        handler=tool_query_price_protection,
    )
    orchestrator.register_tool(
        name="query_product_recommendations",
        mode="read",
        description="基于用户最近浏览历史、显式类目和关键词获取商品推荐",
        handler=tool_query_product_recommendations,
    )
    orchestrator.register_tool(
        name="retrieve_policy_knowledge",
        mode="read",
        description="检索售后政策知识库内容",
        handler=tool_retrieve_policy_knowledge,
    )
    orchestrator.register_tool(
        name="retrieve_manual_knowledge",
        mode="read",
        description="检索商品说明书知识库内容",
        handler=tool_retrieve_manual_knowledge,
    )
    orchestrator.register_tool(
        name="analyze_uploaded_image_vlm",
        mode="read",
        description="使用视觉模型分析用户上传图片并输出结构化结论",
        handler=tool_analyze_uploaded_image_vlm,
    )
    orchestrator.register_tool(
        name="draft_after_sales_request",
        mode="write",
        description="生成待确认售后草案，不直接执行写入",
        handler=tool_draft_after_sales_request,
    )

    result = await orchestrator.run(
        message=message,
        user_id=str(current_user.id) if current_user else "",
        is_authenticated=bool(current_user),
        attachments=attachments or [],
    )
    reply = build_chat_message(result.text, cards=result.cards, actions=result.actions)
    tool_call_logs = [
        {
            "name": call.name,
            "mode": call.mode,
            "success": call.success,
            "args": call.args,
            "error": call.error,
        }
        for call in result.tool_calls
    ]
    return reply, tool_call_logs


def normalize_email(email: str) -> str:
    return email.strip().lower()


def generate_order_id() -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    suffix = f"{randint(0, 9999):04d}"
    return f"ORD{timestamp}{suffix}"


def generate_tracking_no() -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    suffix = f"{randint(1000, 9999)}"
    return f"TRK{timestamp}{suffix}"


def normalize_role(role: str | None) -> str:
    normalized = (role or "").strip().lower()
    return normalized if normalized in {"customer", "merchant"} else "customer"


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def normalize_string_list(values: list[str] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_value in values or []:
        if not isinstance(raw_value, str):
            continue
        cleaned = raw_value.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
    return normalized


def normalize_original_price(*, price: float, original_price: float | None) -> float | None:
    if original_price is None:
        return None
    normalized = round(float(original_price), 2)
    if normalized < round(float(price), 2):
        raise HTTPException(status_code=400, detail="original_price cannot be lower than price")
    return normalized


def build_full_address(address: ShopAddress) -> str:
    return f"{address.province} {address.city} {address.district} {address.address_line}".strip()


def infer_region_label(address_text: str, fallback: str) -> str:
    text = (address_text or "").strip()
    if not text:
        return fallback

    patterns = [
        r"([\u4e00-\u9fff]{2,}(?:特别行政区|自治区|自治州|地区|盟|市))",
        r"([\u4e00-\u9fff]{2,}(?:省))",
        r"([A-Za-z][A-Za-z\s\-]{1,30})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()

    token = re.split(r"[\s,，;/|]+", text)[0].strip()
    return token[:18] if token else fallback


@dataclass
class LogisticsRouteStep:
    name: str
    amap_query: str
    stage: str | None = None


@dataclass
class AmapGeocodeResult:
    formatted_address: str
    province: str
    city: str
    district: str
    adcode: str
    lng: float
    lat: float


def normalize_amap_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.strip():
                return item.strip()
    return ""


def resolve_city_label(detail: AmapGeocodeResult | None, fallback_text: str) -> str:
    if detail:
        if detail.city:
            return detail.city
        if detail.province:
            return detail.province
        if detail.district:
            return detail.district
    return infer_region_label(fallback_text, "站点")


def resolve_station_label(detail: AmapGeocodeResult | None, fallback_text: str, city_label: str) -> str:
    if detail and detail.district and detail.district not in {detail.city, detail.province}:
        return detail.district
    if city_label:
        return city_label
    return infer_region_label(fallback_text, "站点")


def build_hub_query(detail: AmapGeocodeResult | None, city_label: str, fallback_text: str) -> str:
    if detail and detail.city and detail.district and detail.district not in {detail.city, detail.province}:
        return f"{detail.city}{detail.district}"
    if city_label:
        return city_label
    return fallback_text


def haversine_distance_km(lng1: float, lat1: float, lng2: float, lat2: float) -> float:
    radius_km = 6371.0
    lng1_rad = math.radians(lng1)
    lat1_rad = math.radians(lat1)
    lng2_rad = math.radians(lng2)
    lat2_rad = math.radians(lat2)
    d_lng = lng2_rad - lng1_rad
    d_lat = lat2_rad - lat1_rad
    a = math.sin(d_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(d_lng / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return radius_km * c


def estimate_logistics_eta_hours(origin: AmapGeocodeResult | None, destination: AmapGeocodeResult | None) -> int:
    if not origin or not destination:
        return 72

    distance_km = haversine_distance_km(origin.lng, origin.lat, destination.lng, destination.lat)
    if distance_km <= 30:
        return 12
    if distance_km <= 120:
        return 18
    if distance_km <= 300:
        return 24
    if distance_km <= 800:
        return 36
    if distance_km <= 1500:
        return 48
    return 72


def build_deterministic_route_steps(
    ship_from: str,
    ship_to: str,
    origin: AmapGeocodeResult | None,
    destination: AmapGeocodeResult | None,
) -> list[LogisticsRouteStep]:
    origin_city_label = resolve_city_label(origin, ship_from)
    destination_city_label = resolve_city_label(destination, ship_to)
    destination_station_label = resolve_station_label(destination, ship_to, destination_city_label)

    origin_city_key = origin.city if origin and origin.city else (origin.province if origin else "")
    destination_city_key = destination.city if destination and destination.city else (destination.province if destination else "")
    same_city = bool(origin_city_key and destination_city_key and origin_city_key == destination_city_key)

    if same_city:
        return [
            LogisticsRouteStep(name=f"{origin_city_label}揽收仓", amap_query=ship_from, stage="pickup"),
            LogisticsRouteStep(
                name=f"{destination_station_label}同城分拨中心",
                amap_query=build_hub_query(destination, destination_city_label, ship_to),
                stage="sorting",
            ),
            LogisticsRouteStep(name=f"{destination_station_label}配送站", amap_query=ship_to, stage="delivery_station"),
        ]

    return [
        LogisticsRouteStep(name=f"{origin_city_label}揽收仓", amap_query=ship_from, stage="pickup"),
        LogisticsRouteStep(
            name=f"{origin_city_label}转运中心",
            amap_query=build_hub_query(origin, origin_city_label, ship_from),
            stage="origin_hub",
        ),
        LogisticsRouteStep(
            name=f"{destination_city_label}转运中心",
            amap_query=build_hub_query(destination, destination_city_label, ship_to),
            stage="destination_hub",
        ),
        LogisticsRouteStep(name=f"{destination_station_label}配送站", amap_query=ship_to, stage="delivery_station"),
    ]


def build_fallback_route_steps(ship_from: str, ship_to: str) -> list[LogisticsRouteStep]:
    origin = infer_region_label(ship_from, "始发地")
    destination = infer_region_label(ship_to, "目的地")
    if origin == destination:
        return [
            LogisticsRouteStep(name=f"{origin}揽收仓", amap_query=ship_from, stage="pickup"),
            LogisticsRouteStep(name=f"{origin}同城分拨中心", amap_query=f"{origin} 分拨中心", stage="sorting"),
            LogisticsRouteStep(name=f"{destination}配送站", amap_query=ship_to, stage="delivery_station"),
            LogisticsRouteStep(name="派送中", amap_query=ship_to, stage="last_mile"),
        ]
    return [
        LogisticsRouteStep(name=f"{origin}揽收仓", amap_query=ship_from, stage="pickup"),
        LogisticsRouteStep(name=f"{origin}转运中心", amap_query=f"{origin} 转运中心", stage="origin_hub"),
        LogisticsRouteStep(name=f"{destination}转运中心", amap_query=f"{destination} 转运中心", stage="destination_hub"),
        LogisticsRouteStep(name=f"{destination}配送站", amap_query=ship_to, stage="delivery_station"),
    ]


def build_fallback_route(ship_from: str, ship_to: str) -> tuple[str, list[str]]:
    steps = build_fallback_route_steps(ship_from, ship_to)
    route = [step.name for step in steps]
    return route[0], route


def normalize_route_steps(raw_steps: Any) -> list[LogisticsRouteStep]:
    if not isinstance(raw_steps, list):
        return []
    normalized: list[LogisticsRouteStep] = []
    for item in raw_steps:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        amap_query = str(item.get("amap_query") or item.get("address") or item.get("query") or "").strip()
        stage = str(item.get("stage") or "").strip() or None
        if not name:
            continue
        normalized.append(LogisticsRouteStep(name=name, amap_query=amap_query or name, stage=stage))
    return normalized


def build_route_steps_from_route_points(route_points: Any) -> list[LogisticsRouteStep]:
    if not isinstance(route_points, list):
        return []
    route_steps: list[LogisticsRouteStep] = []
    for item in route_points:
        if not isinstance(item, str):
            continue
        cleaned = item.strip()
        if not cleaned:
            continue
        route_steps.append(LogisticsRouteStep(name=cleaned, amap_query=cleaned))
    return route_steps


def route_steps_to_plan(route_steps: list[LogisticsRouteStep]) -> list[str]:
    return [step.name for step in route_steps if step.name]


def extract_route_steps(route_geo: Any, route_plan: list[str] | None = None) -> list[LogisticsRouteStep]:
    route_steps = normalize_route_steps(route_geo)
    if route_steps:
        return route_steps
    return build_route_steps_from_route_points(route_plan or [])


def find_route_step(route_steps: list[LogisticsRouteStep], location: str) -> LogisticsRouteStep | None:
    cleaned_location = (location or "").strip()
    if not cleaned_location:
        return None
    for step in route_steps:
        if step.name == cleaned_location:
            return step
    return None


def build_route_geo_queries(step: LogisticsRouteStep) -> list[str]:
    def _push(values: list[str], candidate: str | None) -> None:
        cleaned = re.sub(r"\s+", " ", (candidate or "").strip())
        if cleaned and cleaned not in values:
            values.append(cleaned)

    queries: list[str] = []
    _push(queries, step.amap_query)
    _push(queries, step.name)

    stripped_name = re.sub(r"(揽收仓|转运中心|同城分拨中心|配送站|派送中)$", "", step.name).strip()
    _push(queries, stripped_name)

    stripped_query = re.sub(r"(揽收仓|转运中心|同城分拨中心|配送站|派送中)$", "", step.amap_query).strip()
    _push(queries, stripped_query)

    if stripped_name:
        _push(queries, infer_region_label(stripped_name, ""))
    if stripped_query:
        _push(queries, infer_region_label(stripped_query, ""))
    return queries


def normalize_geo_cache_text(address_text: str) -> str:
    cleaned = re.sub(r"\s+", " ", (address_text or "").strip())
    return cleaned[:512]


def mask_secret_for_log(secret: str, visible: int = 4) -> str:
    cleaned = (secret or "").strip()
    if not cleaned:
        return "<empty>"
    if len(cleaned) <= visible:
        return "*" * len(cleaned)
    return f"{'*' * max(0, len(cleaned) - visible)}{cleaned[-visible:]}"


def summarize_text_for_log(value: str, max_len: int = 80) -> str:
    cleaned = normalize_geo_cache_text(value)
    if len(cleaned) <= max_len:
        return cleaned
    return f"{cleaned[: max_len - 3]}..."


def to_valid_coordinate(value: Any) -> float | None:
    try:
        converted = float(value)
    except Exception:
        return None
    if converted < -180 or converted > 180:
        return None
    return round(converted, 6)


def normalize_route_geo(raw_points: Any) -> list[GeoPointRead]:
    if not isinstance(raw_points, list):
        return []
    normalized: list[GeoPointRead] = []
    for item in raw_points:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        lng = to_valid_coordinate(item.get("lng"))
        lat = to_valid_coordinate(item.get("lat"))
        if not name or lng is None or lat is None:
            continue
        normalized.append(GeoPointRead(name=name, lng=lng, lat=lat))
    return normalized


async def throttle_amap_requests() -> None:
    global _amap_last_call_time
    min_interval = 1.0 / float(AMAP_QPS_LIMIT)
    async with _amap_throttle_lock:
        loop = asyncio.get_running_loop()
        now = loop.time()
        wait_time = (_amap_last_call_time + min_interval) - now
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        _amap_last_call_time = loop.time()


async def request_amap_geocode_payload(address_text: str) -> dict[str, Any] | None:
    query = normalize_geo_cache_text(address_text)
    if not query:
        logger.warning("AMap geocode skipped because query is empty.")
        return None
    if not AMAP_WEB_KEY:
        logger.warning("AMap geocode skipped because AMAP_WEB_KEY is empty. query=%s", summarize_text_for_log(query))
        return None

    await throttle_amap_requests()
    params: dict[str, Any] = {
        "key": AMAP_WEB_KEY,
        "address": query,
        "output": "JSON",
    }
    if AMAP_WEB_SIG:
        params["sig"] = AMAP_WEB_SIG

    timeout_sec = max(1.0, AMAP_TIMEOUT_MS / 1000.0)
    try:
        logger.info("AMap geocode request. query=%s timeout=%.2fs", summarize_text_for_log(query), timeout_sec)
        async with httpx.AsyncClient(timeout=timeout_sec, trust_env=False) as client:
            response = await client.get("https://restapi.amap.com/v3/geocode/geo", params=params)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            logger.warning("AMap geocode returned non-dict payload. query=%s", summarize_text_for_log(query))
            return None
        status_value = str(payload.get("status") or "")
        info_value = summarize_text_for_log(str(payload.get("info") or ""))
        infocode_value = str(payload.get("infocode") or "")
        geocodes = payload.get("geocodes")
        geocode_count = len(geocodes) if isinstance(geocodes, list) else 0
        if status_value != "1":
            logger.warning(
                "AMap geocode rejected query=%s status=%s info=%s infocode=%s",
                summarize_text_for_log(query),
                status_value,
                info_value,
                infocode_value,
            )
            return None
        if geocode_count == 0:
            logger.warning(
                "AMap geocode returned empty result. query=%s info=%s infocode=%s",
                summarize_text_for_log(query),
                info_value,
                infocode_value,
            )
            return None
        logger.info("AMap geocode success. query=%s geocodes=%s", summarize_text_for_log(query), geocode_count)
        return payload
    except Exception as exc:
        logger.warning("AMap geocode request failed. query=%s error=%s", summarize_text_for_log(query), exc)
        return None


def parse_amap_geocode_result(payload: dict[str, Any]) -> AmapGeocodeResult | None:
    geocodes = payload.get("geocodes")
    if not isinstance(geocodes, list) or not geocodes:
        return None
    first = geocodes[0]
    if not isinstance(first, dict):
        return None
    location_text = str(first.get("location") or "").strip()
    if "," not in location_text:
        return None
    lng_text, lat_text = location_text.split(",", 1)
    lng = to_valid_coordinate(lng_text)
    lat = to_valid_coordinate(lat_text)
    if lng is None or lat is None:
        return None
    return AmapGeocodeResult(
        formatted_address=str(first.get("formatted_address") or "").strip(),
        province=normalize_amap_text(first.get("province")),
        city=normalize_amap_text(first.get("city")),
        district=normalize_amap_text(first.get("district")),
        adcode=str(first.get("adcode") or "").strip(),
        lng=lng,
        lat=lat,
    )


async def call_amap_geocode_detail(address_text: str) -> AmapGeocodeResult | None:
    payload = await request_amap_geocode_payload(address_text)
    if not payload:
        return None
    detail = parse_amap_geocode_result(payload)
    if not detail:
        logger.warning("AMap geocode parse failed. query=%s", summarize_text_for_log(address_text))
        return None
    logger.info(
        "AMap geocode resolved. query=%s address=%s lng=%s lat=%s",
        summarize_text_for_log(address_text),
        summarize_text_for_log(detail.formatted_address),
        detail.lng,
        detail.lat,
    )
    return detail


async def call_amap_geocode(address_text: str) -> tuple[float, float] | None:
    detail = await call_amap_geocode_detail(address_text)
    if not detail:
        return None
    return detail.lng, detail.lat


async def get_geo_cache_entry(session: AsyncSession, source_text: str) -> GeoCache | None:
    statement = select(GeoCache).where(GeoCache.source_text == source_text)
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def upsert_geo_cache_entry(session: AsyncSession, source_text: str, lng: float, lat: float) -> None:
    await session.execute(
        text(
            """
            INSERT INTO geo_cache (source_text, lng, lat, provider, created_at, updated_at)
            VALUES (:source_text, :lng, :lat, 'amap', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (source_text)
            DO UPDATE SET
                lng = EXCLUDED.lng,
                lat = EXCLUDED.lat,
                provider = EXCLUDED.provider,
                updated_at = CURRENT_TIMESTAMP
            """
        ),
        {"source_text": source_text, "lng": lng, "lat": lat},
    )


async def geocode_with_cache(session: AsyncSession, address_text: str) -> tuple[float, float] | None:
    normalized_text = normalize_geo_cache_text(address_text)
    if not normalized_text:
        return None

    cached = await get_geo_cache_entry(session, normalized_text)
    if cached:
        lng = to_valid_coordinate(cached.lng)
        lat = to_valid_coordinate(cached.lat)
        if lng is not None and lat is not None:
            return lng, lat

    coords = await call_amap_geocode(normalized_text)
    if not coords:
        return None

    await upsert_geo_cache_entry(session, normalized_text, coords[0], coords[1])
    return coords


async def build_route_geo(session: AsyncSession, route_steps: list[LogisticsRouteStep]) -> list[dict[str, Any]]:
    geo_points: list[dict[str, Any]] = []
    for step in route_steps:
        coords: tuple[float, float] | None = None
        attempted_queries = build_route_geo_queries(step)
        for query in attempted_queries:
            coords = await geocode_with_cache(session, query)
            if coords:
                break
        point_payload: dict[str, Any] = {
            "name": step.name,
            "amap_query": step.amap_query,
        }
        if step.stage:
            point_payload["stage"] = step.stage
        if coords:
            point_payload["lng"] = coords[0]
            point_payload["lat"] = coords[1]
            logger.info(
                "Route geo resolved. step=%s stage=%s query=%s lng=%s lat=%s",
                step.name,
                step.stage or "",
                summarize_text_for_log(query),
                coords[0],
                coords[1],
            )
        else:
            logger.warning(
                "Route geo missing. step=%s stage=%s tried=%s",
                step.name,
                step.stage or "",
                [summarize_text_for_log(item) for item in attempted_queries],
            )
        geo_points.append(point_payload)
    return geo_points


def pick_geo_from_route(route_geo: list[GeoPointRead], location: str) -> tuple[float, float] | None:
    cleaned_location = (location or "").strip()
    if not cleaned_location:
        return None
    for item in route_geo:
        if item.name == cleaned_location:
            return item.lng, item.lat
    return None


async def get_user_shop(session: AsyncSession, user_id: UUID) -> Shop | None:
    statement = select(Shop).where(Shop.owner_user_id == user_id, Shop.is_active == True)  # noqa: E712
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_current_db_user(
    token_data: TokenData = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> User:
    email = normalize_email(token_data.email or "")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

    statement = select(User).where(func.lower(User.email) == email)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    return user


async def get_current_db_user_optional(request: Request, session: AsyncSession) -> User | None:
    authorization = (request.headers.get("Authorization") or "").strip()
    if not authorization.lower().startswith("bearer "):
        return None

    token = authorization[7:].strip()
    if not token:
        return None

    try:
        token_data = await get_current_user(token)
    except HTTPException:
        return None

    email = normalize_email(token_data.email or "")
    if not email:
        return None

    statement = select(User).where(func.lower(User.email) == email)
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def resolve_realtime_identity(token: str | None) -> tuple[UUID | None, str | None, UUID | None]:
    cleaned_token = (token or "").strip()
    if not cleaned_token:
        return None, None, None

    token_data = await get_current_user(cleaned_token)
    email = normalize_email(token_data.email or "")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

    async with AsyncSession(engine) as session:
        statement = select(User).where(func.lower(User.email) == email)
        result = await session.execute(statement)
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

        role = normalize_role(user.role)
        shop_id: UUID | None = None
        if role == "merchant":
            shop = await get_user_shop(session, user.id)
            if shop:
                shop_id = shop.id

        return user.id, role, shop_id


async def publish_inventory_changed(
    *,
    reason: str,
    shop_id: UUID | None = None,
    product_ids: list[UUID] | None = None,
) -> None:
    await realtime_manager.broadcast(
        event="inventory_changed",
        data={
            "reason": reason,
            "shop_id": str(shop_id) if shop_id else None,
            "product_ids": [str(product_id) for product_id in (product_ids or [])],
        },
    )


async def publish_cart_changed(*, user_id: UUID, reason: str) -> None:
    await realtime_manager.broadcast(
        event="cart_changed",
        data={
            "reason": reason,
            "user_id": str(user_id),
        },
        user_id=user_id,
    )


async def publish_order_changed(
    *,
    order_id: str,
    user_id: UUID,
    shop_id: UUID,
    status: str,
    reason: str,
) -> None:
    payload = {
        "reason": reason,
        "order_id": order_id,
        "status": status,
        "user_id": str(user_id),
        "shop_id": str(shop_id),
    }
    await realtime_manager.broadcast(event="order_changed", data=payload, user_id=user_id)
    await realtime_manager.broadcast(event="order_changed", data=payload, role="merchant", shop_id=shop_id)


async def publish_after_sales_changed(
    *,
    after_sales_id: UUID,
    order_id: str,
    user_id: UUID,
    shop_id: UUID,
    status: str,
    reason: str,
) -> None:
    payload = {
        "reason": reason,
        "after_sales_id": str(after_sales_id),
        "order_id": order_id,
        "status": status,
        "user_id": str(user_id),
        "shop_id": str(shop_id),
    }
    await realtime_manager.broadcast(event="after_sales_changed", data=payload, user_id=user_id)
    await realtime_manager.broadcast(event="after_sales_changed", data=payload, role="merchant", shop_id=shop_id)


async def publish_logistics_complaint_changed(
    *,
    complaint_id: UUID,
    order_id: str,
    user_id: UUID,
    shop_id: UUID,
    status: str,
    reason: str,
) -> None:
    payload = {
        "reason": reason,
        "complaint_id": str(complaint_id),
        "order_id": order_id,
        "status": status,
        "user_id": str(user_id),
        "shop_id": str(shop_id),
    }
    await realtime_manager.broadcast(event="logistics_complaint_changed", data=payload, user_id=user_id)
    await realtime_manager.broadcast(event="logistics_complaint_changed", data=payload, role="merchant", shop_id=shop_id)


async def get_current_merchant_shop(
    current_user: User = Depends(get_current_db_user),
    session: AsyncSession = Depends(get_session),
) -> Shop:
    if normalize_role(current_user.role) != "merchant":
        raise HTTPException(status_code=403, detail="Merchant permission required")

    shop = await get_user_shop(session, current_user.id)
    if not shop:
        raise HTTPException(status_code=404, detail="Merchant shop not found")
    return shop


def to_shop_read(shop: Shop) -> ShopRead:
    return ShopRead(
        id=shop.id,
        name=shop.name,
        description=shop.description,
        contact_email=shop.contact_email,
        contact_phone=shop.contact_phone,
        logo_url=shop.logo_url,
        rating=shop.rating,
        service_score=shop.service_score,
        logistics_score=shop.logistics_score,
        after_sales_score=shop.after_sales_score,
        shipping_city=shop.shipping_city,
        featured_categories=list(shop.featured_categories or []),
        service_tags=list(shop.service_tags or []),
        is_active=shop.is_active,
        created_at=shop.created_at,
    )


def to_product_read(product: Product, shop: Shop | None = None, shop_name: str | None = None) -> ProductRead:
    resolved_shop_name = shop.name if shop else (shop_name or "Unknown Shop")
    return ProductRead(
        id=product.id,
        shop_id=product.shop_id,
        shop_name=resolved_shop_name,
        shop_description=shop.description if shop else None,
        shop_logo_url=shop.logo_url if shop else None,
        shop_rating=shop.rating if shop else None,
        shop_service_score=shop.service_score if shop else None,
        shop_logistics_score=shop.logistics_score if shop else None,
        shop_after_sales_score=shop.after_sales_score if shop else None,
        shop_shipping_city=shop.shipping_city if shop else None,
        shop_featured_categories=list(shop.featured_categories or []) if shop else [],
        shop_service_tags=list(shop.service_tags or []) if shop else [],
        name=product.name,
        price=float(product.price),
        description=product.description,
        image_url=product.image_url,
        category=product.category,
        brand=product.brand,
        model=product.model,
        sku_code=product.sku_code,
        original_price=float(product.original_price) if product.original_price is not None else None,
        rating=product.rating,
        review_count=product.review_count,
        monthly_sales=product.monthly_sales,
        ship_in_hours=product.ship_in_hours,
        warranty_days=product.warranty_days,
        tags=list(product.tags or []),
        spec_highlights=list(product.spec_highlights or []),
        is_active=product.is_active,
        stock=product.stock,
        created_at=product.created_at,
    )


@dataclass
class RecommendationHistoryProfile:
    recent_product_ids: list[UUID]
    category_scores: dict[str, int]
    brand_scores: dict[str, int]
    tag_scores: dict[str, int]
    shop_scores: dict[UUID, int]


def to_product_view_history_item(
    history: ProductViewHistory,
    product: Product,
    *,
    shop: Shop | None = None,
    shop_name: str | None = None,
) -> ProductViewHistoryItem:
    product_read = to_product_read(product, shop=shop, shop_name=shop_name)
    return ProductViewHistoryItem(
        **dump_response_model(product_read),
        view_count=history.view_count,
        last_viewed_at=history.last_viewed_at,
    )


def product_read_to_chat_card(product: ProductRead) -> dict[str, Any]:
    base_url = FRONTEND_BASE_URL.rstrip("/")
    return {
        "type": "product",
        "data": {
            "id": str(product.id),
            "name": product.name,
            "category": product.category or "未分类",
            "brand": product.brand or "",
            "model": product.model or "",
            "price": float(product.price),
            "original_price": float(product.original_price) if product.original_price is not None else None,
            "stock": int(product.stock),
            "rating": float(product.rating) if product.rating is not None else None,
            "review_count": int(product.review_count),
            "monthly_sales": int(product.monthly_sales),
            "ship_in_hours": int(product.ship_in_hours),
            "tags": list(product.tags or []),
            "shop_name": product.shop_name,
            "product_link": f"{base_url}/products/{product.id}",
            "image_url": product.image_url or "",
        },
    }


def normalize_match_text(value: str | None) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", "", value.strip().lower())


def extract_recommendation_query_terms(query: str) -> list[str]:
    cleaned = (query or "").strip().lower()
    if not cleaned:
        return []

    normalized = cleaned
    for marker in [
        "给我",
        "帮我",
        "推荐",
        "几款",
        "看看",
        "想买",
        "适合",
        "有没有",
        "哪些",
        "什么",
        "哪个",
        "比较",
        "一下",
        "请问",
        "可以",
        "用于",
        "一款",
        "一个",
    ]:
        normalized = normalized.replace(marker, " ")

    tokens = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", normalized)
    unique_terms: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        term = token.strip()
        if len(term) < 2 or term in seen:
            continue
        seen.add(term)
        unique_terms.append(term)
    return unique_terms[:8]


def infer_explicit_category_from_query(query: str, categories: list[str]) -> str:
    normalized_query = normalize_match_text(query)
    if not normalized_query:
        return ""

    sorted_categories = sorted(
        [item.strip() for item in categories if isinstance(item, str) and item.strip()],
        key=len,
        reverse=True,
    )
    for category in sorted_categories:
        if normalize_match_text(category) in normalized_query:
            return category
    return ""


def build_recommendation_history_profile(rows: list[tuple[ProductViewHistory, Product]]) -> RecommendationHistoryProfile:
    category_scores: Counter[str] = Counter()
    brand_scores: Counter[str] = Counter()
    tag_scores: Counter[str] = Counter()
    shop_scores: Counter[UUID] = Counter()
    recent_product_ids: list[UUID] = []

    for index, (history, product) in enumerate(rows):
        recent_product_ids.append(product.id)
        recency_weight = max(1, PRODUCT_VIEW_HISTORY_MAX_ITEMS - index)
        view_bonus = max(0, min(int(history.view_count), 5) - 1)
        weight = recency_weight + view_bonus

        category_key = normalize_match_text(product.category)
        brand_key = normalize_match_text(product.brand)
        if category_key:
            category_scores[category_key] += weight
        if brand_key:
            brand_scores[brand_key] += weight
        shop_scores[product.shop_id] += weight
        for tag in list(product.tags or []):
            tag_key = normalize_match_text(tag)
            if tag_key:
                tag_scores[tag_key] += weight

    return RecommendationHistoryProfile(
        recent_product_ids=recent_product_ids,
        category_scores=dict(category_scores),
        brand_scores=dict(brand_scores),
        tag_scores=dict(tag_scores),
        shop_scores=dict(shop_scores),
    )


def compute_product_query_score(
    product: ProductRead,
    *,
    query: str,
    query_terms: list[str],
    explicit_category: str,
) -> int:
    score = 0
    normalized_query = normalize_match_text(query)
    normalized_category = normalize_match_text(product.category)
    normalized_brand = normalize_match_text(product.brand)
    normalized_model = normalize_match_text(product.model)
    normalized_name = normalize_match_text(product.name)
    normalized_description = normalize_match_text(product.description)
    normalized_tags = [normalize_match_text(item) for item in list(product.tags or [])]

    if explicit_category and normalized_category == normalize_match_text(explicit_category):
        score += 1200

    text_fields = [normalized_name, normalized_category, normalized_brand, normalized_model, normalized_description, *normalized_tags]
    if normalized_query and any(normalized_query in field for field in text_fields if field):
        score += 280

    for term in query_terms:
        normalized_term = normalize_match_text(term)
        if not normalized_term:
            continue
        if normalized_term in normalized_name:
            score += 130
        elif normalized_term in normalized_brand or normalized_term in normalized_model:
            score += 105
        elif normalized_term in normalized_category:
            score += 95
        elif any(normalized_term in tag for tag in normalized_tags):
            score += 80
        elif normalized_term in normalized_description:
            score += 45

    return score


def compute_product_history_score(product: ProductRead, profile: RecommendationHistoryProfile) -> int:
    score = 0
    normalized_category = normalize_match_text(product.category)
    normalized_brand = normalize_match_text(product.brand)
    if normalized_category:
        score += profile.category_scores.get(normalized_category, 0) * 50
    if normalized_brand:
        score += profile.brand_scores.get(normalized_brand, 0) * 38
    score += profile.shop_scores.get(product.shop_id, 0) * 24
    for tag in list(product.tags or []):
        score += profile.tag_scores.get(normalize_match_text(tag), 0) * 14
    return score


async def fetch_recent_product_view_rows(
    session: AsyncSession,
    *,
    user_id: UUID,
    limit: int,
) -> list[tuple[ProductViewHistory, Product]]:
    statement = (
        select(ProductViewHistory, Product)
        .join(Product, ProductViewHistory.product_id == Product.id)
        .where(ProductViewHistory.user_id == user_id, Product.is_active == True)  # noqa: E712
        .order_by(ProductViewHistory.last_viewed_at.desc(), ProductViewHistory.created_at.desc())
        .limit(max(1, min(limit, PRODUCT_VIEW_HISTORY_MAX_ITEMS)))
    )
    result = await session.execute(statement)
    return result.all()


async def build_product_view_history_response(
    session: AsyncSession,
    *,
    user_id: UUID,
    limit: int,
) -> ProductViewHistoryResponse:
    rows = await fetch_recent_product_view_rows(session, user_id=user_id, limit=limit)
    if not rows:
        return ProductViewHistoryResponse(items=[])

    shop_map = await get_shop_map(session, [product.shop_id for _history, product in rows])
    items = [
        to_product_view_history_item(
            history,
            product,
            shop=shop_map.get(product.shop_id),
            shop_name="Unknown Shop",
        )
        for history, product in rows
    ]
    return ProductViewHistoryResponse(items=items)


async def record_product_view(session: AsyncSession, *, user_id: UUID, product_id: UUID) -> None:
    now = datetime.utcnow()
    table = ProductViewHistory.__table__
    upsert_statement = (
        insert(table)
        .values(
            user_id=user_id,
            product_id=product_id,
            view_count=1,
            created_at=now,
            last_viewed_at=now,
        )
        .on_conflict_do_update(
            index_elements=[table.c.user_id, table.c.product_id],
            set_={
                "view_count": table.c.view_count + 1,
                "last_viewed_at": now,
            },
        )
    )
    await session.execute(upsert_statement)

    stale_id_statement = (
        select(ProductViewHistory.id)
        .where(ProductViewHistory.user_id == user_id)
        .order_by(ProductViewHistory.last_viewed_at.desc(), ProductViewHistory.created_at.desc())
        .offset(PRODUCT_VIEW_HISTORY_MAX_ITEMS)
    )
    stale_ids = list((await session.execute(stale_id_statement)).scalars().all())
    if stale_ids:
        await session.execute(delete(ProductViewHistory).where(ProductViewHistory.id.in_(stale_ids)))

    await session.commit()


async def list_active_product_categories(session: AsyncSession) -> list[str]:
    statement = (
        select(Product.category)
        .where(Product.is_active == True, Product.stock > 0, Product.category.is_not(None), Product.category != "")  # noqa: E712
        .distinct()
        .order_by(Product.category.asc())
    )
    result = await session.execute(statement)
    return [item for item in result.scalars().all() if isinstance(item, str) and item.strip()]


async def get_personalized_product_recommendations(
    session: AsyncSession,
    *,
    user_id: UUID | None,
    query: str = "",
    category: str = "",
    limit: int = DEFAULT_PRODUCT_RECOMMENDATION_LIMIT,
) -> ProductRecommendationResponse:
    safe_limit = max(1, min(limit, PRODUCT_VIEW_HISTORY_MAX_ITEMS))
    cleaned_query = (query or "").strip()
    cleaned_category = (category or "").strip()

    history_rows: list[tuple[ProductViewHistory, Product]] = []
    history_profile = RecommendationHistoryProfile(
        recent_product_ids=[],
        category_scores={},
        brand_scores={},
        tag_scores={},
        shop_scores={},
    )
    if user_id is not None:
        history_rows = await fetch_recent_product_view_rows(
            session,
            user_id=user_id,
            limit=PRODUCT_VIEW_HISTORY_MAX_ITEMS,
        )
        history_profile = build_recommendation_history_profile(history_rows)

    resolved_category = cleaned_category
    if not resolved_category and cleaned_query:
        resolved_category = infer_explicit_category_from_query(cleaned_query, await list_active_product_categories(session))

    async def load_candidates(category_filter: str) -> list[Product]:
        filters = [Product.is_active == True, Product.stock > 0]  # noqa: E712
        if category_filter:
            filters.append(Product.category == category_filter)
        statement = (
            select(Product)
            .where(*filters)
            .order_by(Product.monthly_sales.desc(), Product.rating.desc().nullslast(), Product.created_at.desc())
            .limit(200)
        )
        return list((await session.execute(statement)).scalars().all())

    products = await load_candidates(resolved_category)
    if not products and resolved_category:
        products = await load_candidates("")

    if not products:
        return ProductRecommendationResponse(items=[], personalized=bool(history_profile.recent_product_ids))

    shop_map = await get_shop_map(session, [product.shop_id for product in products])
    query_terms = extract_recommendation_query_terms(cleaned_query)
    recent_product_id_set = set(history_profile.recent_product_ids)

    scored_items: list[tuple[ProductRead, int, int, int, float, float, datetime, bool]] = []
    for product in products:
        product_read = to_product_read(product, shop=shop_map.get(product.shop_id), shop_name="Unknown Shop")
        query_score = compute_product_query_score(
            product_read,
            query=cleaned_query,
            query_terms=query_terms,
            explicit_category=resolved_category,
        )
        history_score = compute_product_history_score(product_read, history_profile)
        sales_score = int(product.monthly_sales or 0)
        rating_score = float(product.rating or 0.0)
        review_score = float(product.review_count or 0)
        scored_items.append(
            (
                product_read,
                query_score,
                history_score,
                sales_score,
                rating_score,
                review_score,
                product.created_at,
                product.id in recent_product_id_set,
            )
        )

    scored_items.sort(
        key=lambda item: (
            1 if item[1] > 0 else 0,
            item[1],
            item[2],
            item[3],
            item[4],
            item[5],
            item[6],
        ),
        reverse=True,
    )

    selected: list[ProductRead] = []
    seen_product_ids: set[UUID] = set()
    for include_recent in (False, True):
        for product_read, *_rest, is_recent in scored_items:
            if include_recent != is_recent:
                continue
            if product_read.id in seen_product_ids:
                continue
            selected.append(product_read)
            seen_product_ids.add(product_read.id)
            if len(selected) >= safe_limit:
                break
        if len(selected) >= safe_limit:
            break

    return ProductRecommendationResponse(items=selected, personalized=bool(history_profile.recent_product_ids))


async def get_shop_map(session: AsyncSession, shop_ids: list[UUID]) -> dict[UUID, Shop]:
    unique_ids = list({shop_id for shop_id in shop_ids})
    if not unique_ids:
        return {}

    statement = select(Shop).where(Shop.id.in_(unique_ids))
    result = await session.execute(statement)
    shops = result.scalars().all()
    return {shop.id: shop for shop in shops}


async def get_shop_name_map(session: AsyncSession, shop_ids: list[UUID]) -> dict[UUID, str]:
    unique_ids = list({shop_id for shop_id in shop_ids})
    if not unique_ids:
        return {}

    statement = select(Shop.id, Shop.name).where(Shop.id.in_(unique_ids))
    result = await session.execute(statement)
    return {shop_id: name for shop_id, name in result.all()}


async def fetch_cart_rows(session: AsyncSession, user_id: UUID) -> list[tuple[CartItem, Product]]:
    statement = (
        select(CartItem, Product)
        .join(Product, CartItem.product_id == Product.id)
        .where(CartItem.user_id == user_id)
        .order_by(CartItem.updated_at.desc())
    )
    result = await session.execute(statement)
    return result.all()


def build_cart_response(rows: list[tuple[CartItem, Product]]) -> CartResponse:
    items: list[CartItemRead] = []
    total_items = 0
    total_amount = 0.0

    for cart_item, product in rows:
        unit_price = float(product.price)
        subtotal = round(unit_price * cart_item.quantity, 2)
        total_items += cart_item.quantity
        total_amount += subtotal
        items.append(
            CartItemRead(
                id=cart_item.id,
                product_id=product.id,
                product_name=product.name,
                product_image_url=product.image_url,
                unit_price=unit_price,
                quantity=cart_item.quantity,
                subtotal=subtotal,
            )
        )

    return CartResponse(items=items, total_items=total_items, total_amount=round(total_amount, 2))


async def get_active_product_or_404(session: AsyncSession, product_id: UUID) -> Product:
    product = await session.get(Product, product_id)
    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


async def get_order_or_404(session: AsyncSession, order_id: str) -> Order:
    order = await session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


async def get_logistics_by_order(session: AsyncSession, order_id: str) -> Logistics | None:
    statement = select(Logistics).where(Logistics.order_id == order_id)
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_after_sales_by_order(session: AsyncSession, order_id: str) -> list[AfterSales]:
    statement = (
        select(AfterSales)
        .where(AfterSales.order_id == order_id)
        .order_by(AfterSales.created_at.desc())
    )
    result = await session.execute(statement)
    return result.scalars().all()


async def get_logistics_complaints_by_order(session: AsyncSession, order_id: str) -> list[LogisticsComplaint]:
    statement = (
        select(LogisticsComplaint)
        .where(LogisticsComplaint.order_id == order_id)
        .order_by(LogisticsComplaint.updated_at.desc(), LogisticsComplaint.created_at.desc())
    )
    result = await session.execute(statement)
    return result.scalars().all()


def normalize_route_points(route_plan: list[str] | None) -> list[str]:
    if not isinstance(route_plan, list):
        return []
    points: list[str] = []
    for item in route_plan:
        if not isinstance(item, str):
            continue
        cleaned = item.strip()
        if cleaned:
            points.append(cleaned)
    return points


def compute_next_logistics_state(logistics: Logistics) -> tuple[str, str]:
    route_points = normalize_route_points(list(logistics.route_plan or []))
    if not route_points:
        raise HTTPException(status_code=400, detail="No logistics route available for this order")

    current_location = (logistics.current_location or "").strip()
    if not current_location:
        if len(route_points) == 1:
            return route_points[0], LOGISTICS_STATUS_DELIVERED
        return route_points[0], LOGISTICS_STATUS_IN_TRANSIT

    if current_location in route_points:
        current_idx = route_points.index(current_location)
        if current_idx >= len(route_points) - 1:
            return route_points[-1], LOGISTICS_STATUS_DELIVERED
        next_idx = current_idx + 1
        next_status = LOGISTICS_STATUS_DELIVERED if next_idx == len(route_points) - 1 else LOGISTICS_STATUS_IN_TRANSIT
        return route_points[next_idx], next_status

    if len(route_points) == 1:
        return route_points[0], LOGISTICS_STATUS_DELIVERED
    return route_points[0], LOGISTICS_STATUS_IN_TRANSIT


def resolve_after_sales_stage(*, order: Order, logistics: Logistics | None) -> str:
    if order.status == ORDER_STATUS_PENDING_SHIPMENT:
        return ORDER_STATUS_PENDING_SHIPMENT
    if order.status != ORDER_STATUS_SHIPPED:
        return "unsupported"

    logistics_status = (logistics.status or "").strip().lower() if logistics else ""
    if logistics_status == LOGISTICS_STATUS_DELIVERED:
        return LOGISTICS_STATUS_DELIVERED
    return LOGISTICS_STATUS_IN_TRANSIT


def allowed_after_sales_types(stage: str) -> set[str]:
    if stage == ORDER_STATUS_PENDING_SHIPMENT:
        return {AFTER_SALES_TYPE_RETURN}
    if stage == LOGISTICS_STATUS_DELIVERED:
        return set(AFTER_SALES_ALLOWED_TYPES)
    return set()


def validate_after_sales_rule(*, request_type: str, stage: str) -> None:
    allowed_types = allowed_after_sales_types(stage)
    if not allowed_types:
        if stage == LOGISTICS_STATUS_IN_TRANSIT:
            raise HTTPException(status_code=400, detail="Order is in transit; please apply after-sales after delivery")
        raise HTTPException(status_code=400, detail="Current order status does not support after-sales request")
    if request_type not in allowed_types:
        if stage == ORDER_STATUS_PENDING_SHIPMENT:
            raise HTTPException(status_code=400, detail="Before shipment, only return request is supported")
        raise HTTPException(status_code=400, detail="This after-sales type is not allowed at current stage")


def to_after_sales_read(item: AfterSales) -> AfterSalesRead:
    return AfterSalesRead(
        id=item.id,
        order_id=item.order_id,
        type=item.type,
        reason=item.reason,
        status=item.status,
        created_at=item.created_at,
    )


def to_logistics_complaint_read(item: LogisticsComplaint) -> LogisticsComplaintRead:
    return LogisticsComplaintRead(
        id=item.id,
        order_id=item.order_id,
        reason=item.reason,
        status=item.status,
        resolution_note=item.resolution_note,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def to_merchant_after_sales_item(item: AfterSales, order: Order) -> MerchantAfterSalesItem:
    base_url = FRONTEND_BASE_URL.rstrip("/")
    return MerchantAfterSalesItem(
        id=item.id,
        order_id=item.order_id,
        type=item.type,
        reason=item.reason,
        status=item.status,
        created_at=item.created_at,
        order_status=order.status,
        contact_email=order.contact_email,
        order_link=f"{base_url}/orders?orderId={item.order_id}",
    )


def to_merchant_logistics_complaint_item(item: LogisticsComplaint, order: Order) -> MerchantLogisticsComplaintItem:
    base_url = FRONTEND_BASE_URL.rstrip("/")
    return MerchantLogisticsComplaintItem(
        id=item.id,
        order_id=item.order_id,
        reason=item.reason,
        status=item.status,
        resolution_note=item.resolution_note,
        created_at=item.created_at,
        updated_at=item.updated_at,
        order_status=order.status,
        contact_email=order.contact_email,
        order_link=f"{base_url}/orders?orderId={item.order_id}",
    )


async def build_order_detail(session: AsyncSession, order: Order) -> OrderRead:
    items_stmt = select(OrderItem).where(OrderItem.order_id == order.id).order_by(OrderItem.id)
    items_result = await session.execute(items_stmt)
    order_items = items_result.scalars().all()

    shop = await session.get(Shop, order.shop_id)
    if not shop:
        raise HTTPException(status_code=500, detail="Shop not found for order")

    base_url = FRONTEND_BASE_URL.rstrip("/")
    logistics = await get_logistics_by_order(session, order.id)
    after_sales = await get_after_sales_by_order(session, order.id)
    logistics_complaints = await get_logistics_complaints_by_order(session, order.id)
    logistics_read = None
    if logistics:
        route_plan_value = list(logistics.route_plan or [])
        route_geo_payload = list(logistics.route_geo or [])
        normalized_route_geo = normalize_route_geo(route_geo_payload)
        if not normalized_route_geo:
            route_steps = extract_route_steps(route_geo_payload, route_plan_value)
            if logistics.shipped_from_address_id:
                shipped_from_address = await session.get(ShopAddress, logistics.shipped_from_address_id)
                if shipped_from_address:
                    _, _, route_steps, _ = await predict_logistics(
                        build_full_address(shipped_from_address),
                        order.address,
                        logistics.updated_at,
                    )
                    route_plan_value = route_steps_to_plan(route_steps)
            if route_steps:
                rebuilt_route_geo = await build_route_geo(session, route_steps)
                normalized_route_geo = normalize_route_geo(rebuilt_route_geo)
                if normalized_route_geo:
                    route_geo_payload = rebuilt_route_geo

        current_lng = to_valid_coordinate(logistics.current_lng)
        current_lat = to_valid_coordinate(logistics.current_lat)
        if current_lng is None or current_lat is None:
            current_geo = pick_geo_from_route(normalized_route_geo, logistics.current_location or "")
            if not current_geo and normalized_route_geo:
                current_geo = (normalized_route_geo[0].lng, normalized_route_geo[0].lat)
            if current_geo:
                current_lng = current_geo[0]
                current_lat = current_geo[1]

        logistics_read = LogisticsRead(
            tracking_no=logistics.tracking_no,
            status=logistics.status,
            current_location=logistics.current_location,
            current_lng=current_lng,
            current_lat=current_lat,
            estimated_delivery_at=logistics.estimated_delivery_at,
            route_plan=route_plan_value,
            route_geo=normalized_route_geo,
            updated_at=logistics.updated_at,
        )

    return OrderRead(
        id=order.id,
        status=order.status,
        address=order.address,
        contact_email=order.contact_email,
        total_amount=float(order.total_amount),
        created_at=order.created_at,
        shop_id=order.shop_id,
        shop_name=shop.name,
        items=[
            OrderItemRead(
                id=item.id,
                product_id=item.product_id,
                product_name=item.product_name,
                unit_price=float(item.unit_price),
                quantity=item.quantity,
                subtotal=float(item.subtotal),
                product_link=f"{base_url}/products/{item.product_id}",
            )
            for item in order_items
        ],
        logistics=logistics_read,
        after_sales=[to_after_sales_read(item) for item in after_sales],
        logistics_complaints=[to_logistics_complaint_read(item) for item in logistics_complaints],
    )


async def predict_logistics(
    ship_from: str,
    ship_to: str,
    now: datetime,
) -> tuple[datetime, str, list[LogisticsRouteStep], str]:
    fallback_eta = now + timedelta(hours=72)
    fallback_steps = build_fallback_route_steps(ship_from, ship_to)
    fallback_route = route_steps_to_plan(fallback_steps)
    fallback_location = fallback_route[0]
    origin_detail = await call_amap_geocode_detail(ship_from)
    destination_detail = await call_amap_geocode_detail(ship_to)
    logger.info(
        "Predict logistics geocode result. ship_from=%s origin_ok=%s ship_to=%s destination_ok=%s",
        summarize_text_for_log(ship_from),
        bool(origin_detail),
        summarize_text_for_log(ship_to),
        bool(destination_detail),
    )
    if not origin_detail and not destination_detail:
        fallback_raw = json.dumps(
            {
                "provider": "deterministic_fallback",
                "eta_hours": 72,
                "current_location": fallback_location,
                "route_steps": [
                    {
                        "name": step.name,
                        "amap_query": step.amap_query,
                        "stage": step.stage,
                    }
                    for step in fallback_steps
                ],
                "summary": "amap geocode unavailable, use text fallback",
            },
            ensure_ascii=False,
        )
        logger.warning(
            "Predict logistics fell back to text route because both AMap geocode lookups failed. ship_from=%s ship_to=%s",
            summarize_text_for_log(ship_from),
            summarize_text_for_log(ship_to),
        )
        return fallback_eta, fallback_location, fallback_steps, fallback_raw

    route_steps = build_deterministic_route_steps(ship_from, ship_to, origin_detail, destination_detail)
    eta_hours = estimate_logistics_eta_hours(origin_detail, destination_detail)
    current_location = route_steps[0].name
    raw_payload = {
        "provider": "deterministic_geocode",
        "eta_hours": eta_hours,
        "current_location": current_location,
        "route_steps": [
            {
                "name": step.name,
                "amap_query": step.amap_query,
                "stage": step.stage,
            }
            for step in route_steps
        ],
        "origin": (
            {
                "formatted_address": origin_detail.formatted_address,
                "province": origin_detail.province,
                "city": origin_detail.city,
                "district": origin_detail.district,
                "location": [origin_detail.lng, origin_detail.lat],
            }
            if origin_detail
            else None
        ),
        "destination": (
            {
                "formatted_address": destination_detail.formatted_address,
                "province": destination_detail.province,
                "city": destination_detail.city,
                "district": destination_detail.district,
                "location": [destination_detail.lng, destination_detail.lat],
            }
            if destination_detail
            else None
        ),
        "summary": "generated from ship-from and ship-to addresses via AMap geocode",
    }
    logger.info(
        "Predict logistics generated deterministic route. current_location=%s steps=%s eta_hours=%s",
        current_location,
        len(route_steps),
        eta_hours,
    )
    return now + timedelta(hours=eta_hours), current_location, route_steps, json.dumps(raw_payload, ensure_ascii=False)


async def to_user_read(session: AsyncSession, user: User) -> UserRead:
    shop_brief = None
    if normalize_role(user.role) == "merchant":
        shop = await get_user_shop(session, user.id)
        if shop:
            shop_brief = ShopBrief(id=shop.id, name=shop.name)
    return UserRead(
        id=user.id,
        username=user.username,
        email=user.email,
        role=normalize_role(user.role),
        created_at=user.created_at,
        shop=shop_brief,
    )


def to_shop_address_read(address: ShopAddress) -> ShopAddressRead:
    return ShopAddressRead(
        id=address.id,
        shop_id=address.shop_id,
        label=address.label,
        contact_name=address.contact_name,
        contact_phone=address.contact_phone,
        province=address.province,
        city=address.city,
        district=address.district,
        address_line=address.address_line,
        postal_code=address.postal_code,
        is_default=address.is_default,
        created_at=address.created_at,
    )


def build_product_create_values(payload: MerchantProductCreate) -> dict[str, Any]:
    cleaned_name = (payload.name or "").strip()
    if not cleaned_name:
        raise HTTPException(status_code=400, detail="name is required")

    normalized_price = round(float(payload.price), 2)
    normalized_original_price = normalize_original_price(
        price=normalized_price,
        original_price=payload.original_price,
    )
    return {
        "name": cleaned_name,
        "description": normalize_optional_text(payload.description),
        "image_url": normalize_optional_text(payload.image_url),
        "category": normalize_optional_text(payload.category),
        "brand": normalize_optional_text(payload.brand),
        "model": normalize_optional_text(payload.model),
        "sku_code": normalize_optional_text(payload.sku_code),
        "price": normalized_price,
        "original_price": normalized_original_price,
        "rating": payload.rating,
        "review_count": payload.review_count,
        "monthly_sales": payload.monthly_sales,
        "ship_in_hours": payload.ship_in_hours,
        "warranty_days": payload.warranty_days,
        "tags": normalize_string_list(payload.tags),
        "spec_highlights": normalize_string_list(payload.spec_highlights),
        "stock": payload.stock,
        "is_active": payload.is_active,
    }


def apply_product_update_payload(product: Product, payload: MerchantProductUpdate) -> None:
    if payload.name is not None:
        cleaned_name = payload.name.strip()
        if not cleaned_name:
            raise HTTPException(status_code=400, detail="name is required")
        product.name = cleaned_name
    if payload.description is not None:
        product.description = normalize_optional_text(payload.description)
    if payload.image_url is not None:
        product.image_url = normalize_optional_text(payload.image_url)
    if payload.category is not None:
        product.category = normalize_optional_text(payload.category)
    if payload.brand is not None:
        product.brand = normalize_optional_text(payload.brand)
    if payload.model is not None:
        product.model = normalize_optional_text(payload.model)
    if payload.sku_code is not None:
        product.sku_code = normalize_optional_text(payload.sku_code)
    if payload.price is not None:
        product.price = round(float(payload.price), 2)
    if payload.original_price is not None:
        product.original_price = normalize_original_price(
            price=float(product.price),
            original_price=payload.original_price,
        )
    elif payload.price is not None and product.original_price is not None:
        product.original_price = normalize_original_price(
            price=float(product.price),
            original_price=float(product.original_price),
        )
    if payload.rating is not None:
        product.rating = payload.rating
    if payload.review_count is not None:
        product.review_count = payload.review_count
    if payload.monthly_sales is not None:
        product.monthly_sales = payload.monthly_sales
    if payload.ship_in_hours is not None:
        product.ship_in_hours = payload.ship_in_hours
    if payload.warranty_days is not None:
        product.warranty_days = payload.warranty_days
    if payload.tags is not None:
        product.tags = normalize_string_list(payload.tags)
    if payload.spec_highlights is not None:
        product.spec_highlights = normalize_string_list(payload.spec_highlights)
    if payload.stock is not None:
        product.stock = payload.stock
    if payload.is_active is not None:
        product.is_active = payload.is_active


def apply_shop_update_payload(shop: Shop, payload: MerchantShopUpdate) -> None:
    if payload.logo_url is not None:
        shop.logo_url = normalize_optional_text(payload.logo_url)
    if payload.description is not None:
        shop.description = normalize_optional_text(payload.description)
    if payload.contact_email is not None:
        normalized_email = normalize_optional_text(payload.contact_email)
        shop.contact_email = normalize_email(normalized_email) if normalized_email else None
    if payload.contact_phone is not None:
        shop.contact_phone = normalize_optional_text(payload.contact_phone)
    if payload.shipping_city is not None:
        shop.shipping_city = normalize_optional_text(payload.shipping_city)
    if payload.featured_categories is not None:
        shop.featured_categories = normalize_string_list(payload.featured_categories)
    if payload.service_tags is not None:
        shop.service_tags = normalize_string_list(payload.service_tags)


def normalize_after_sales_type(raw: str) -> str:
    return (raw or "").strip().lower()


def normalize_after_sales_action(raw: str) -> str:
    return (raw or "").strip().lower()


def resolve_after_sales_next_status(current_status: str, action: str) -> str | None:
    transition_map: dict[str, dict[str, str]] = {
        AFTER_SALES_STATUS_SUBMITTED: {
            "approve": AFTER_SALES_STATUS_MERCHANT_APPROVED,
            "reject": AFTER_SALES_STATUS_MERCHANT_REJECTED,
        },
        AFTER_SALES_STATUS_MERCHANT_APPROVED: {
            "processing": AFTER_SALES_STATUS_PROCESSING,
            "complete": AFTER_SALES_STATUS_COMPLETED,
            "reject": AFTER_SALES_STATUS_MERCHANT_REJECTED,
        },
        AFTER_SALES_STATUS_PROCESSING: {
            "complete": AFTER_SALES_STATUS_COMPLETED,
        },
    }
    return transition_map.get(current_status, {}).get(action)


def normalize_logistics_complaint_action(raw: str) -> str:
    return (raw or "").strip().lower()


def resolve_logistics_complaint_next_status(current_status: str, action: str) -> str | None:
    transition_map: dict[str, dict[str, str]] = {
        LOGISTICS_COMPLAINT_STATUS_SUBMITTED: {
            "processing": LOGISTICS_COMPLAINT_STATUS_PROCESSING,
            "resolve": LOGISTICS_COMPLAINT_STATUS_RESOLVED,
            "reject": LOGISTICS_COMPLAINT_STATUS_REJECTED,
            "cancel": LOGISTICS_COMPLAINT_STATUS_CANCELLED,
        },
        LOGISTICS_COMPLAINT_STATUS_PROCESSING: {
            "resolve": LOGISTICS_COMPLAINT_STATUS_RESOLVED,
            "reject": LOGISTICS_COMPLAINT_STATUS_REJECTED,
            "cancel": LOGISTICS_COMPLAINT_STATUS_CANCELLED,
        },
    }
    return transition_map.get(current_status, {}).get(action)


def append_merchant_note(reason: str | None, note: str) -> str:
    cleaned_note = note.strip()
    if not cleaned_note:
        return (reason or "").strip()

    prefix = (reason or "").strip()
    stamped = f"[merchant_note {datetime.utcnow().isoformat(timespec='seconds')} UTC] {cleaned_note}"
    return f"{prefix}\n{stamped}".strip() if prefix else stamped


@app.websocket("/ws/realtime")
async def realtime_websocket(websocket: WebSocket, token: str | None = Query(default=None)):
    try:
        user_id, role, shop_id = await resolve_realtime_identity(token)
    except HTTPException:
        await websocket.close(code=1008)
        return

    connection_id = await realtime_manager.connect(
        websocket,
        user_id=user_id,
        role=role,
        shop_id=shop_id,
    )
    await websocket.send_json(
        {
            "event": "connected",
            "data": {
                "user_id": str(user_id) if user_id else None,
                "role": role,
                "shop_id": str(shop_id) if shop_id else None,
            },
            "sent_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }
    )

    try:
        while True:
            message = await websocket.receive_text()
            if message.strip().lower() == "ping":
                await websocket.send_json(
                    {
                        "event": "pong",
                        "data": {},
                        "sent_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                    }
                )
    except WebSocketDisconnect:
        await realtime_manager.disconnect(connection_id)
    except Exception:
        await realtime_manager.disconnect(connection_id)


@app.get("/")
async def root():
    return {"message": "Welcome to Rasa-EC-bot API"}


def normalize_attachment_ids(raw_ids: list[str]) -> list[str]:
    cleaned_ids: list[str] = []
    for raw_id in raw_ids:
        value = (raw_id or "").strip()
        if not value:
            continue
        try:
            normalized = str(UUID(value))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"Invalid attachment id: {value}") from exc
        if normalized not in cleaned_ids:
            cleaned_ids.append(normalized)
    return cleaned_ids


async def validate_chat_attachments(
    *,
    session: AsyncSession,
    attachment_ids: list[str],
    current_user: User | None,
) -> None:
    for attachment_id in attachment_ids:
        statement = text(
            """
            SELECT id, user_id
            FROM chat_attachments
            WHERE id = CAST(:attachment_id AS uuid)
            LIMIT 1
            """
        )
        row = (await session.execute(statement, {"attachment_id": attachment_id})).mappings().first()
        if not row:
            raise HTTPException(status_code=400, detail=f"Attachment not found: {attachment_id}")

        owner_user_id = row.get("user_id")
        if owner_user_id and not current_user:
            raise HTTPException(status_code=403, detail=f"Attachment login required: {attachment_id}")
        if current_user and owner_user_id and str(owner_user_id) != str(current_user.id):
            raise HTTPException(status_code=403, detail=f"Attachment forbidden: {attachment_id}")


@app.post("/api/v1/chat/upload-image", response_model=ChatUploadImageResponse)
async def chat_upload_image(
    request: Request,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    current_user = await get_current_db_user_optional(request, session)
    if current_user and normalize_role(current_user.role) == "merchant":
        raise HTTPException(status_code=403, detail="Merchant accounts cannot access chat support")

    content_type = (file.content_type or "").strip().lower()
    if content_type not in CHAT_UPLOAD_ALLOWED_MIME:
        raise HTTPException(status_code=400, detail="Only jpeg/png/webp image is supported")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded image is empty")
    if len(content) > CHAT_UPLOAD_MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"Image exceeds {CHAT_UPLOAD_MAX_MB}MB")

    width, height = infer_image_size(content)
    if width is None or height is None:
        raise HTTPException(status_code=400, detail="Invalid image file")

    attachment_uuid = uuid4()
    extension_map = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }
    extension = extension_map.get(content_type, ".bin")
    bucket_dir = UPLOAD_ROOT_DIR / datetime.utcnow().strftime("%Y%m%d")
    bucket_dir.mkdir(parents=True, exist_ok=True)
    local_path = bucket_dir / f"{attachment_uuid}{extension}"
    local_path.write_bytes(content)

    sender_id = f"user-{current_user.id}" if current_user else "guest-upload"
    insert_stmt = text(
        """
        INSERT INTO chat_attachments (
            id, user_id, sender_id, local_path, mime, sha256, width, height, size_bytes
        ) VALUES (
            CAST(:id AS uuid), :user_id, :sender_id, :local_path, :mime, :sha256, :width, :height, :size_bytes
        )
        """
    )
    await session.execute(
        insert_stmt,
        {
            "id": str(attachment_uuid),
            "user_id": str(current_user.id) if current_user else None,
            "sender_id": sender_id,
            "local_path": str(local_path),
            "mime": content_type,
            "sha256": compute_sha256(content),
            "width": width,
            "height": height,
            "size_bytes": len(content),
        },
    )
    await session.commit()

    return ChatUploadImageResponse(
        attachment_id=str(attachment_uuid),
        mime=content_type,
        size_bytes=len(content),
        width=width,
        height=height,
    )


@app.post("/api/v1/kb/index", response_model=KBIndexResponse)
async def kb_index(
    payload: KBIndexRequest,
    current_user: User = Depends(get_current_db_user),
    session: AsyncSession = Depends(get_session),
):
    if normalize_role(current_user.role) != "merchant":
        raise HTTPException(status_code=403, detail="Only merchant account can index knowledge")
    if not payload.items:
        raise HTTPException(status_code=400, detail="items cannot be empty")

    indexed_documents = 0
    indexed_chunks = 0
    for item in payload.items:
        source_type = clean_kb_source_type(item.source_type)
        title = (item.title or "").strip()
        content = (item.content or "").strip()
        if not title or not content:
            raise HTTPException(status_code=400, detail="title and content are required")

        checksum = compute_sha256(content.encode("utf-8"))
        upsert_document_stmt = text(
            """
            INSERT INTO kb_documents (source_type, title, version, status, checksum, updated_at)
            VALUES (:source_type, :title, :version, :status, :checksum, CURRENT_TIMESTAMP)
            ON CONFLICT (checksum)
            DO UPDATE SET
                source_type = EXCLUDED.source_type,
                title = EXCLUDED.title,
                version = EXCLUDED.version,
                status = EXCLUDED.status,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
            """
        )
        document_id = (
            await session.execute(
                upsert_document_stmt,
                {
                    "source_type": source_type,
                    "title": title,
                    "version": (item.version or "").strip() or None,
                    "status": (item.status or "").strip() or "active",
                    "checksum": checksum,
                },
            )
        ).scalar_one()
        indexed_documents += 1

        await session.execute(
            text("DELETE FROM kb_chunks WHERE document_id = CAST(:document_id AS uuid)"),
            {"document_id": str(document_id)},
        )

        chunks = split_text_into_chunks(content, chunk_size=KB_CHUNK_SIZE, overlap=KB_CHUNK_OVERLAP)
        for chunk_order, chunk_text in enumerate(chunks):
            embedding = await generate_embedding(chunk_text)
            await session.execute(
                text(
                    """
                    INSERT INTO kb_chunks (document_id, chunk_order, chunk_text, embedding, metadata)
                    VALUES (
                        CAST(:document_id AS uuid),
                        :chunk_order,
                        :chunk_text,
                        CAST(:embedding AS vector),
                        CAST(:metadata AS jsonb)
                    )
                    """
                ),
                {
                    "document_id": str(document_id),
                    "chunk_order": chunk_order,
                    "chunk_text": chunk_text,
                    "embedding": build_vector_literal(embedding),
                    "metadata": json.dumps(item.metadata if isinstance(item.metadata, dict) else {}, ensure_ascii=False),
                },
            )
            indexed_chunks += 1

    await session.commit()
    return KBIndexResponse(indexed_documents=indexed_documents, indexed_chunks=indexed_chunks)


@app.post("/api/v1/chat/pending-action/decision", response_model=ChatSendResponse)
async def chat_pending_action_decision(
    payload: ChatPendingActionDecisionRequest,
    current_user: User = Depends(get_current_db_user),
    session: AsyncSession = Depends(get_session),
):
    if normalize_role(current_user.role) != "customer":
        raise HTTPException(status_code=403, detail="Only customer accounts can decide pending chat actions")

    reply = await decide_pending_chat_action(payload.decision, current_user, session)
    return ChatSendResponse(messages=[reply])


@app.post("/api/v1/chat/send", response_model=ChatSendResponse)
async def chat_send(
    payload: ChatSendRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    message = payload.message.strip()
    attachment_ids = normalize_attachment_ids(payload.attachments or [])
    if not message and not attachment_ids:
        raise HTTPException(status_code=400, detail="message or attachments cannot be empty")

    current_user = await get_current_db_user_optional(request, session)
    if current_user and normalize_role(current_user.role) == "merchant":
        raise HTTPException(status_code=403, detail="Merchant accounts cannot access chat support")

    await validate_chat_attachments(session=session, attachment_ids=attachment_ids, current_user=current_user)

    if current_user and message and not attachment_ids:
        transaction_reply = await handle_chat_transaction_action(message, current_user, session)
        if transaction_reply:
            return ChatSendResponse(messages=[transaction_reply])

    trace_id = uuid4().hex
    sender_id = (payload.sender_id or "").strip() or (f"user-{current_user.id}" if current_user else "web_user")
    metadata = {
        "is_authenticated": bool(current_user),
        "user_id": str(current_user.id) if current_user else "",
        "user_email": current_user.email if current_user else "",
        "username": current_user.username if current_user else "",
        "frontend_base_url": FRONTEND_BASE_URL,
        "trace_id": trace_id,
        "attachments": attachment_ids,
    }

    intent_name = ""
    intent_confidence = 0.0
    if message:
        intent_name, intent_confidence = await parse_rasa_intent(message)
    route = (
        "agent"
        if attachment_ids
        else decide_chat_route(message=message, intent_name=intent_name, intent_confidence=intent_confidence)
    )
    domains = sorted(infer_message_domains(message))
    logger.info(
        "chat_route trace_id=%s route=%s intent=%s confidence=%.3f domains=%s sender_id=%s attachments=%d",
        trace_id,
        route,
        intent_name or "unknown",
        intent_confidence,
        ",".join(domains),
        sender_id,
        len(attachment_ids),
    )

    metadata["route"] = route
    if route == "agent":
        try:
            reply, tool_call_logs = await run_nexau_agent_orchestrator(
                message=message,
                current_user=current_user,
                session=session,
                attachments=attachment_ids,
            )
            logger.info(
                "agent_route trace_id=%s tool_calls=%s",
                trace_id,
                json.dumps(tool_call_logs, ensure_ascii=False, default=str),
            )
            return ChatSendResponse(messages=[reply])
        except Exception as exc:  # noqa: BLE001
            logger.exception("agent_route_failed trace_id=%s error=%s fallback=rule", trace_id, str(exc))
            metadata["route"] = "rule"

    if not message:
        raise HTTPException(status_code=400, detail="attachments request must route to agent")

    messages = await call_rasa_webhook(sender_id=sender_id, message=message, metadata=metadata)
    return ChatSendResponse(messages=messages)


@app.get("/api/v1/chat/internal/orders-summary", response_model=ChatOrderSummaryResponse)
async def chat_internal_orders_summary(
    user_id: UUID = Query(...),
    limit: int = Query(default=5, ge=1, le=10),
    x_rasa_token: str | None = Header(default=None, alias="X-Rasa-Token"),
    session: AsyncSession = Depends(get_session),
):
    expected_token = (RASA_INTERNAL_TOKEN or "").strip()
    provided_token = (x_rasa_token or "").strip()
    if expected_token and provided_token != expected_token:
        raise HTTPException(status_code=403, detail="Forbidden")

    cache_key = chat_orders_summary_cache_key(user_id, limit)
    cached_payload = await cache.get_json(cache_key)
    if isinstance(cached_payload, dict):
        try:
            return parse_response_model(ChatOrderSummaryResponse, cached_payload)
        except Exception:
            pass

    statement = select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc()).limit(limit)
    result = await session.execute(statement)
    orders = result.scalars().all()
    if not orders:
        response = ChatOrderSummaryResponse(items=[])
        await cache.set_json(cache_key, dump_response_model(response))
        return response

    order_ids = [order.id for order in orders]
    count_statement = (
        select(OrderItem.order_id, func.count(OrderItem.id))
        .where(OrderItem.order_id.in_(order_ids))
        .group_by(OrderItem.order_id)
    )
    count_result = await session.execute(count_statement)
    item_count_map = {order_id: int(count) for order_id, count in count_result.all()}

    base_url = FRONTEND_BASE_URL.rstrip("/")
    items = [
        ChatOrderSummaryItem(
            id=order.id,
            status=order.status,
            total_amount=float(order.total_amount),
            item_count=int(item_count_map.get(order.id, 0)),
            created_at=order.created_at,
            order_link=f"{base_url}/orders?orderId={order.id}",
        )
        for order in orders
    ]
    response = ChatOrderSummaryResponse(items=items)
    await cache.set_json(cache_key, dump_response_model(response))
    return response


@app.get("/api/v1/chat/internal/orders-logistics-summary", response_model=ChatOrderLogisticsSummaryResponse)
async def chat_internal_orders_logistics_summary(
    user_id: UUID = Query(...),
    order_id: str | None = Query(default=None),
    limit: int = Query(default=5, ge=1, le=10),
    x_rasa_token: str | None = Header(default=None, alias="X-Rasa-Token"),
    session: AsyncSession = Depends(get_session),
):
    expected_token = (RASA_INTERNAL_TOKEN or "").strip()
    provided_token = (x_rasa_token or "").strip()
    if expected_token and provided_token != expected_token:
        raise HTTPException(status_code=403, detail="Forbidden")

    cleaned_order_id = (order_id or "").strip()
    cache_key = chat_logistics_summary_cache_key(user_id, limit, cleaned_order_id)
    cached_payload = await cache.get_json(cache_key)
    if isinstance(cached_payload, dict):
        try:
            return parse_response_model(ChatOrderLogisticsSummaryResponse, cached_payload)
        except Exception:
            pass

    statement = (
        select(Order, Logistics)
        .join(Logistics, Logistics.order_id == Order.id, isouter=True)
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
    )

    if cleaned_order_id:
        statement = statement.where(Order.id == cleaned_order_id).limit(1)
    else:
        statement = statement.limit(limit)

    result = await session.execute(statement)
    rows = result.all()
    if not rows:
        response = ChatOrderLogisticsSummaryResponse(items=[])
        await cache.set_json(cache_key, dump_response_model(response))
        return response

    base_url = FRONTEND_BASE_URL.rstrip("/")
    items = [
        ChatOrderLogisticsSummaryItem(
            id=order.id,
            status=(logistics.status if logistics and (logistics.status or "").strip() else order.status),
            created_at=order.created_at,
            order_link=f"{base_url}/orders?orderId={order.id}",
            tracking_no=(logistics.tracking_no if logistics else None),
            current_location=(logistics.current_location if logistics else None),
            estimated_delivery_at=(logistics.estimated_delivery_at if logistics else None),
            route_plan=(list(logistics.route_plan or []) if logistics else []),
        )
        for order, logistics in rows
    ]
    response = ChatOrderLogisticsSummaryResponse(items=items)
    await cache.set_json(cache_key, dump_response_model(response))
    return response


@app.get("/api/v1/chat/internal/after-sales-summary", response_model=ChatAfterSalesSummaryResponse)
async def chat_internal_after_sales_summary(
    user_id: UUID = Query(...),
    limit: int = Query(default=5, ge=1, le=10),
    x_rasa_token: str | None = Header(default=None, alias="X-Rasa-Token"),
    session: AsyncSession = Depends(get_session),
):
    expected_token = (RASA_INTERNAL_TOKEN or "").strip()
    provided_token = (x_rasa_token or "").strip()
    if expected_token and provided_token != expected_token:
        raise HTTPException(status_code=403, detail="Forbidden")

    cache_key = chat_after_sales_summary_cache_key(user_id, limit)
    cached_payload = await cache.get_json(cache_key)
    if isinstance(cached_payload, dict):
        try:
            return parse_response_model(ChatAfterSalesSummaryResponse, cached_payload)
        except Exception:
            pass

    statement = (
        select(AfterSales, Order)
        .join(Order, AfterSales.order_id == Order.id)
        .where(Order.user_id == user_id)
        .order_by(AfterSales.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(statement)
    rows = result.all()
    if not rows:
        response = ChatAfterSalesSummaryResponse(items=[])
        await cache.set_json(cache_key, dump_response_model(response))
        return response

    base_url = FRONTEND_BASE_URL.rstrip("/")
    items = [
        ChatAfterSalesSummaryItem(
            id=item.id,
            order_id=item.order_id,
            type=item.type,
            status=item.status,
            created_at=item.created_at,
            reason=item.reason,
            order_link=f"{base_url}/orders?orderId={item.order_id}",
        )
        for item, _order in rows
    ]
    response = ChatAfterSalesSummaryResponse(items=items)
    await cache.set_json(cache_key, dump_response_model(response))
    return response


@app.get("/api/v1/chat/internal/product-recommendations", response_model=ProductRecommendationResponse)
async def chat_internal_product_recommendations(
    user_id: str | None = Query(default=None),
    category: str = Query(default=""),
    query: str = Query(default=""),
    limit: int = Query(default=DEFAULT_PRODUCT_RECOMMENDATION_LIMIT, ge=1, le=20),
    x_rasa_token: str | None = Header(default=None, alias="X-Rasa-Token"),
    session: AsyncSession = Depends(get_session),
):
    expected_token = (RASA_INTERNAL_TOKEN or "").strip()
    provided_token = (x_rasa_token or "").strip()
    if expected_token and provided_token != expected_token:
        raise HTTPException(status_code=403, detail="Forbidden")

    parsed_user_id: UUID | None = None
    if isinstance(user_id, str) and user_id.strip():
        try:
            parsed_user_id = UUID(user_id.strip())
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail="Invalid user_id") from exc

    return await get_personalized_product_recommendations(
        session,
        user_id=parsed_user_id,
        query=query,
        category=category,
        limit=limit,
    )


@app.post("/api/v1/auth/register", response_model=UserRead)
async def register(user: UserCreate, session: AsyncSession = Depends(get_session)):
    normalized_email = normalize_email(user.email)

    statement = select(User).where(func.lower(User.email) == normalized_email)
    result = await session.execute(statement)
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        username=user.username.strip(),
        email=normalized_email,
        hashed_password=get_password_hash(user.password),
        role="customer",
    )
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return await to_user_read(session, new_user)


@app.post("/api/v1/auth/login", response_model=Token)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_session)):
    normalized_email = normalize_email(payload.email)
    statement = select(User).where(func.lower(User.email) == normalized_email)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": normalize_role(user.role)},
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token)


@app.get("/api/v1/auth/me", response_model=UserRead)
async def me(
    current_user: User = Depends(get_current_db_user),
    session: AsyncSession = Depends(get_session),
):
    return await to_user_read(session, current_user)


@app.get("/api/v1/products/filters", response_model=ProductFilterMetaResponse)
async def get_product_filter_meta(session: AsyncSession = Depends(get_session)):
    cached_payload = await cache.get_json(PRODUCT_FILTER_CACHE_KEY)
    if isinstance(cached_payload, dict):
        try:
            return parse_response_model(ProductFilterMetaResponse, cached_payload)
        except Exception:
            pass

    active_filters = [Product.is_active == True]  # noqa: E712

    categories_statement = (
        select(Product.category)
        .where(*active_filters, Product.category.is_not(None), Product.category != "")
        .distinct()
        .order_by(Product.category.asc())
    )
    categories_result = await session.execute(categories_statement)
    categories = [category for category in categories_result.scalars().all() if category]

    brands_statement = (
        select(Product.brand)
        .where(*active_filters, Product.brand.is_not(None), Product.brand != "")
        .distinct()
        .order_by(Product.brand.asc())
    )
    brands_result = await session.execute(brands_statement)
    brands = [brand for brand in brands_result.scalars().all() if brand]

    price_range_statement = select(func.min(Product.price), func.max(Product.price)).where(*active_filters)
    price_range_result = await session.execute(price_range_statement)
    price_min, price_max = price_range_result.one()

    shop_statement = (
        select(
            Shop.id,
            Shop.name,
            Shop.rating,
            Shop.shipping_city,
            func.count(Product.id).label("active_product_count"),
        )
        .join(Product, Product.shop_id == Shop.id)
        .where(Product.is_active == True, Shop.is_active == True)  # noqa: E712
        .group_by(Shop.id, Shop.name, Shop.rating, Shop.shipping_city)
        .order_by(func.count(Product.id).desc(), Shop.rating.desc().nullslast(), Shop.name.asc())
    )
    shop_result = await session.execute(shop_statement)
    shops = [
        ProductFilterShopOption(
            id=shop_id,
            name=name,
            rating=rating,
            shipping_city=shipping_city,
            active_product_count=int(active_product_count or 0),
        )
        for shop_id, name, rating, shipping_city, active_product_count in shop_result.all()
    ]

    response = ProductFilterMetaResponse(
        categories=categories,
        brands=brands,
        shops=shops,
        price_min=float(price_min or 0),
        price_max=float(price_max or 0),
    )
    await cache.set_json(PRODUCT_FILTER_CACHE_KEY, dump_response_model(response))
    return response


@app.get("/api/v1/products", response_model=ProductListResponse)
async def list_products(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
    keyword: str = Query(default=""),
    category: str = Query(default=""),
    brand: str = Query(default=""),
    shop_id: UUID | None = Query(default=None),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    in_stock: bool = Query(default=False),
    sort_by: Literal["newest", "price_asc", "price_desc", "rating_desc", "sales_desc"] = Query(default="newest"),
    session: AsyncSession = Depends(get_session),
):
    filters = [Product.is_active == True]  # noqa: E712
    cleaned_keyword = keyword.strip()
    cleaned_category = category.strip()
    cleaned_brand = brand.strip()

    if cleaned_keyword:
        pattern = f"%{cleaned_keyword}%"
        filters.append(
            or_(
                Product.name.ilike(pattern),
                Product.brand.ilike(pattern),
                Product.model.ilike(pattern),
                Product.sku_code.ilike(pattern),
                Product.description.ilike(pattern),
                cast(Product.tags, String).ilike(pattern),
            )
        )
    if cleaned_category:
        filters.append(Product.category == cleaned_category)
    if cleaned_brand:
        filters.append(Product.brand == cleaned_brand)
    if shop_id is not None:
        filters.append(Product.shop_id == shop_id)
    if min_price is not None:
        filters.append(Product.price >= min_price)
    if max_price is not None:
        filters.append(Product.price <= max_price)
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status_code=400, detail="min_price cannot be greater than max_price")
    if in_stock:
        filters.append(Product.stock > 0)

    if sort_by == "price_asc":
        order_by = (Product.price.asc(), Product.created_at.desc())
    elif sort_by == "price_desc":
        order_by = (Product.price.desc(), Product.created_at.desc())
    elif sort_by == "rating_desc":
        order_by = (Product.rating.desc().nullslast(), Product.review_count.desc(), Product.created_at.desc())
    elif sort_by == "sales_desc":
        order_by = (Product.monthly_sales.desc(), Product.rating.desc().nullslast(), Product.created_at.desc())
    else:
        order_by = (Product.created_at.desc(),)

    count_statement = select(func.count()).select_from(Product).where(*filters)
    count_result = await session.execute(count_statement)
    total = int(count_result.scalar_one() or 0)

    offset = (page - 1) * page_size
    statement = select(Product).where(*filters).order_by(*order_by).offset(offset).limit(page_size)
    result = await session.execute(statement)
    products = result.scalars().all()

    shop_map = await get_shop_map(session, [product.shop_id for product in products])
    return ProductListResponse(
        items=[
            to_product_read(product, shop=shop_map.get(product.shop_id), shop_name="Unknown Shop")
            for product in products
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@app.get("/api/v1/products/history", response_model=ProductViewHistoryResponse)
async def get_product_view_history(
    limit: int = Query(default=DEFAULT_PRODUCT_HISTORY_LIMIT, ge=1, le=PRODUCT_VIEW_HISTORY_MAX_ITEMS),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_db_user),
):
    if normalize_role(current_user.role) != "customer":
        raise HTTPException(status_code=403, detail="Only customer accounts can view product history")

    return await build_product_view_history_response(
        session,
        user_id=current_user.id,
        limit=limit,
    )


@app.get("/api/v1/products/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: UUID = Path(...),
    session: AsyncSession = Depends(get_session),
):
    product = await get_active_product_or_404(session, product_id)
    shop = await session.get(Shop, product.shop_id)
    if not shop:
        raise HTTPException(status_code=500, detail="Shop not found for product")
    return to_product_read(product, shop=shop)


@app.post("/api/v1/products/{product_id}/history", status_code=status.HTTP_204_NO_CONTENT)
async def create_product_view_history(
    product_id: UUID = Path(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_db_user),
):
    if normalize_role(current_user.role) != "customer":
        raise HTTPException(status_code=403, detail="Only customer accounts can record product history")

    await get_active_product_or_404(session, product_id)
    await record_product_view(session, user_id=current_user.id, product_id=product_id)
    return None


@app.get("/api/v1/cart", response_model=CartResponse)
async def get_cart(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_db_user),
):
    rows = await fetch_cart_rows(session, current_user.id)
    return build_cart_response(rows)


@app.post("/api/v1/cart/items", response_model=CartResponse)
async def add_cart_item(
    payload: AddCartItemRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_db_user),
):
    if normalize_role(current_user.role) != "customer":
        raise HTTPException(status_code=403, detail="Only customer accounts can use cart")

    product = await get_active_product_or_404(session, payload.product_id)
    if payload.quantity > product.stock:
        raise HTTPException(status_code=409, detail="Insufficient stock")

    statement = select(CartItem).where(
        CartItem.user_id == current_user.id,
        CartItem.product_id == payload.product_id,
    )
    result = await session.execute(statement)
    existing_item = result.scalar_one_or_none()

    if existing_item:
        new_quantity = existing_item.quantity + payload.quantity
        if new_quantity > product.stock:
            raise HTTPException(status_code=409, detail="Insufficient stock")
        existing_item.quantity = new_quantity
        existing_item.updated_at = datetime.utcnow()
    else:
        session.add(CartItem(user_id=current_user.id, product_id=payload.product_id, quantity=payload.quantity))

    await session.commit()
    await publish_cart_changed(user_id=current_user.id, reason="item_added")
    rows = await fetch_cart_rows(session, current_user.id)
    return build_cart_response(rows)


@app.patch("/api/v1/cart/items/{item_id}", response_model=CartResponse)
async def update_cart_item(
    payload: UpdateCartItemRequest,
    item_id: UUID = Path(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_db_user),
):
    item = await session.get(CartItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    if item.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    if payload.quantity == 0:
        await session.delete(item)
    else:
        product = await get_active_product_or_404(session, item.product_id)
        if payload.quantity > product.stock:
            raise HTTPException(status_code=409, detail="Insufficient stock")
        item.quantity = payload.quantity
        item.updated_at = datetime.utcnow()

    await session.commit()
    await publish_cart_changed(
        user_id=current_user.id,
        reason="item_removed" if payload.quantity == 0 else "item_updated",
    )
    rows = await fetch_cart_rows(session, current_user.id)
    return build_cart_response(rows)


@app.delete("/api/v1/cart/items/{item_id}", response_model=CartResponse)
async def delete_cart_item(
    item_id: UUID = Path(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_db_user),
):
    item = await session.get(CartItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    if item.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    await session.delete(item)
    await session.commit()
    await publish_cart_changed(user_id=current_user.id, reason="item_removed")
    rows = await fetch_cart_rows(session, current_user.id)
    return build_cart_response(rows)


@app.post("/api/v1/orders", response_model=OrderRead)
async def create_order(
    payload: CreateOrderRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_db_user),
):
    if normalize_role(current_user.role) != "customer":
        raise HTTPException(status_code=403, detail="Only customer accounts can place orders")

    address = payload.address.strip()
    contact_email = normalize_email(payload.contact_email)
    if not address:
        raise HTTPException(status_code=400, detail="Address is required")
    if not contact_email:
        raise HTTPException(status_code=400, detail="Contact email is required")

    cart_rows = await fetch_cart_rows(session, current_user.id)
    if not cart_rows:
        raise HTTPException(status_code=400, detail="Cart is empty")

    shop_ids = {product.shop_id for _, product in cart_rows}
    if len(shop_ids) > 1:
        raise HTTPException(
            status_code=400,
            detail="Current checkout supports one shop at a time. Please select products from the same shop.",
        )
    shop_id = next(iter(shop_ids))

    product_ids = [product.id for _, product in cart_rows]
    for cart_item, product in cart_rows:
        if cart_item.quantity > product.stock:
            raise HTTPException(status_code=409, detail=f"Insufficient stock for {product.name}")

    order_id = generate_order_id()
    for _ in range(5):
        if not await session.get(Order, order_id):
            break
        order_id = generate_order_id()
    else:
        raise HTTPException(status_code=500, detail="Failed to generate order id")

    total_amount = 0.0
    new_order = Order(
        id=order_id,
        user_id=current_user.id,
        shop_id=shop_id,
        status=ORDER_STATUS_PENDING_SHIPMENT,
        address=address,
        contact_email=contact_email,
        total_amount=0.0,
    )

    try:
        session.add(new_order)
        for cart_item, product in cart_rows:
            unit_price = float(product.price)
            subtotal = round(unit_price * cart_item.quantity, 2)
            total_amount += subtotal

            product.stock = product.stock - cart_item.quantity
            session.add(
                OrderItem(
                    order_id=order_id,
                    product_id=product.id,
                    product_name=product.name,
                    unit_price=unit_price,
                    quantity=cart_item.quantity,
                    subtotal=subtotal,
                )
            )
            await session.delete(cart_item)

        new_order.total_amount = round(total_amount, 2)
        await session.commit()
        await session.refresh(new_order)
    except HTTPException:
        await session.rollback()
        raise
    except Exception:
        await session.rollback()
        raise HTTPException(status_code=500, detail="Failed to create order")

    await invalidate_product_filter_cache()
    await invalidate_chat_cache_for_user(current_user.id, orders=True, logistics=True)
    await publish_inventory_changed(
        reason="order_created",
        shop_id=new_order.shop_id,
        product_ids=product_ids,
    )
    await publish_cart_changed(user_id=current_user.id, reason="checked_out")
    await publish_order_changed(
        order_id=new_order.id,
        user_id=current_user.id,
        shop_id=new_order.shop_id,
        status=new_order.status,
        reason="created",
    )
    return await build_order_detail(session, new_order)


@app.post("/api/v1/orders/{order_id}/cancel", response_model=OrderRead)
async def cancel_order(
    order_id: str = Path(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_db_user),
):
    if normalize_role(current_user.role) != "customer":
        raise HTTPException(status_code=403, detail="Only customer accounts can cancel orders")

    order = await get_order_or_404(session, order_id)
    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if order.status == ORDER_STATUS_CANCELLED:
        raise HTTPException(status_code=400, detail="Order is already cancelled")
    if order.status != ORDER_STATUS_PENDING_SHIPMENT:
        raise HTTPException(status_code=400, detail="Only pending shipment orders can be cancelled")
    if await has_active_after_sales_request(session, order.id):
        raise HTTPException(status_code=409, detail="Order has an active after-sales request")

    items_result = await session.execute(select(OrderItem).where(OrderItem.order_id == order.id))
    order_items = items_result.scalars().all()
    product_ids = [item.product_id for item in order_items]

    if product_ids:
        product_result = await session.execute(select(Product).where(Product.id.in_(tuple(product_ids))))
        products = product_result.scalars().all()
        product_map = {product.id: product for product in products}
        for item in order_items:
            product = product_map.get(item.product_id)
            if product:
                product.stock = int(product.stock) + int(item.quantity)

    order.status = ORDER_STATUS_CANCELLED
    await session.commit()
    await session.refresh(order)
    await invalidate_product_filter_cache()
    await invalidate_chat_cache_for_user(current_user.id, orders=True, logistics=True)
    if product_ids:
        await publish_inventory_changed(reason="order_cancelled", shop_id=order.shop_id, product_ids=product_ids)
    await publish_order_changed(
        order_id=order.id,
        user_id=order.user_id,
        shop_id=order.shop_id,
        status=order.status,
        reason="cancelled",
    )
    return await build_order_detail(session, order)


@app.patch("/api/v1/orders/{order_id}/shipping", response_model=OrderRead)
async def update_order_shipping(
    payload: UpdateOrderShippingRequest,
    order_id: str = Path(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_db_user),
):
    if normalize_role(current_user.role) != "customer":
        raise HTTPException(status_code=403, detail="Only customer accounts can update shipping info")

    order = await get_order_or_404(session, order_id)
    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if order.status == ORDER_STATUS_CANCELLED:
        raise HTTPException(status_code=400, detail="Cancelled order cannot update shipping info")
    if order.status != ORDER_STATUS_PENDING_SHIPMENT:
        raise HTTPException(status_code=400, detail="Only pending shipment orders can update shipping info")

    address = (payload.address or "").strip()
    if not address:
        raise HTTPException(status_code=400, detail="Address is required")

    order.address = address
    if payload.contact_email is not None:
        normalized_email = normalize_email(payload.contact_email)
        if not normalized_email:
            raise HTTPException(status_code=400, detail="Contact email is invalid")
        order.contact_email = normalized_email

    await session.commit()
    await session.refresh(order)
    await invalidate_chat_cache_for_user(current_user.id, orders=True, logistics=True)
    await publish_order_changed(
        order_id=order.id,
        user_id=order.user_id,
        shop_id=order.shop_id,
        status=order.status,
        reason="shipping_updated",
    )
    return await build_order_detail(session, order)


@app.get("/api/v1/orders", response_model=OrderListResponse)
async def list_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=8, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_db_user),
):
    filters = [Order.user_id == current_user.id]
    count_statement = select(func.count()).select_from(Order).where(*filters)
    count_result = await session.execute(count_statement)
    total = int(count_result.scalar_one() or 0)

    offset = (page - 1) * page_size
    statement = (
        select(Order)
        .where(*filters)
        .order_by(Order.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await session.execute(statement)
    orders = result.scalars().all()

    if not orders:
        return OrderListResponse(items=[], total=total, page=page, page_size=page_size)

    order_ids = [order.id for order in orders]
    count_statement = (
        select(OrderItem.order_id, func.count(OrderItem.id))
        .where(OrderItem.order_id.in_(order_ids))
        .group_by(OrderItem.order_id)
    )
    count_result = await session.execute(count_statement)
    item_count_map = {order_id: int(count) for order_id, count in count_result.all()}
    shop_name_map = await get_shop_name_map(session, [order.shop_id for order in orders])

    return OrderListResponse(
        items=[
            OrderListItem(
                id=order.id,
                status=order.status,
                address=order.address,
                contact_email=order.contact_email,
                total_amount=float(order.total_amount),
                item_count=int(item_count_map.get(order.id, 0)),
                created_at=order.created_at,
                shop_id=order.shop_id,
                shop_name=shop_name_map.get(order.shop_id, "Unknown Shop"),
            )
            for order in orders
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@app.get("/api/v1/orders/{order_id}", response_model=OrderRead)
async def get_order_detail(
    order_id: str = Path(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_db_user),
):
    order = await get_order_or_404(session, order_id)
    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return await build_order_detail(session, order)


@app.get("/api/v1/orders/{order_id}/after-sales", response_model=list[AfterSalesRead])
async def list_order_after_sales(
    order_id: str = Path(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_db_user),
):
    order = await get_order_or_404(session, order_id)
    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    items = await get_after_sales_by_order(session, order.id)
    return [to_after_sales_read(item) for item in items]


@app.get("/api/v1/orders/{order_id}/logistics-complaints", response_model=list[LogisticsComplaintRead])
async def list_order_logistics_complaints(
    order_id: str = Path(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_db_user),
):
    order = await get_order_or_404(session, order_id)
    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    items = await get_logistics_complaints_by_order(session, order.id)
    return [to_logistics_complaint_read(item) for item in items]


@app.post("/api/v1/orders/{order_id}/after-sales", response_model=AfterSalesRead, status_code=201)
async def create_after_sales_request(
    payload: CreateAfterSalesRequest,
    order_id: str = Path(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_db_user),
):
    if normalize_role(current_user.role) != "customer":
        raise HTTPException(status_code=403, detail="Only customer accounts can create after-sales requests")

    order = await get_order_or_404(session, order_id)
    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    request_type = normalize_after_sales_type(payload.type)
    if request_type not in AFTER_SALES_ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="type must be return or exchange")
    logistics = await get_logistics_by_order(session, order.id)
    stage = resolve_after_sales_stage(order=order, logistics=logistics)
    validate_after_sales_rule(request_type=request_type, stage=stage)

    reason = (payload.reason or "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="reason is required")

    active_stmt = (
        select(AfterSales)
        .where(
            AfterSales.order_id == order.id,
            ~AfterSales.status.in_(tuple(AFTER_SALES_TERMINAL_STATUSES)),
        )
        .limit(1)
    )
    active_result = await session.execute(active_stmt)
    active_request = active_result.scalar_one_or_none()
    if active_request:
        raise HTTPException(status_code=409, detail="There is already an active after-sales request for this order")

    item = AfterSales(
        order_id=order.id,
        type=request_type,
        reason=reason,
        status=AFTER_SALES_STATUS_SUBMITTED,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    await invalidate_chat_cache_for_user(current_user.id, after_sales=True)
    await publish_after_sales_changed(
        after_sales_id=item.id,
        order_id=order.id,
        user_id=order.user_id,
        shop_id=order.shop_id,
        status=item.status,
        reason="created",
    )
    await publish_order_changed(
        order_id=order.id,
        user_id=order.user_id,
        shop_id=order.shop_id,
        status=order.status,
        reason="after_sales_created",
    )
    return to_after_sales_read(item)


@app.post("/api/v1/orders/{order_id}/logistics-complaints", response_model=LogisticsComplaintRead, status_code=201)
async def create_logistics_complaint(
    payload: CreateLogisticsComplaintRequest,
    order_id: str = Path(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_db_user),
):
    if normalize_role(current_user.role) != "customer":
        raise HTTPException(status_code=403, detail="Only customer accounts can create logistics complaints")

    order = await get_order_or_404(session, order_id)
    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if order.status != ORDER_STATUS_SHIPPED:
        raise HTTPException(status_code=400, detail="Only shipped orders can create logistics complaints")

    logistics = await get_logistics_by_order(session, order.id)
    if not logistics:
        raise HTTPException(status_code=400, detail="Order has no logistics record")

    reason = (payload.reason or "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="reason is required")
    if await has_active_logistics_complaint(session, order.id):
        raise HTTPException(status_code=409, detail="There is already an active logistics complaint for this order")

    item = LogisticsComplaint(
        order_id=order.id,
        reason=reason,
        status=LOGISTICS_COMPLAINT_STATUS_SUBMITTED,
        updated_at=datetime.utcnow(),
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    await publish_logistics_complaint_changed(
        complaint_id=item.id,
        order_id=order.id,
        user_id=order.user_id,
        shop_id=order.shop_id,
        status=item.status,
        reason="created",
    )
    await publish_order_changed(
        order_id=order.id,
        user_id=order.user_id,
        shop_id=order.shop_id,
        status=order.status,
        reason="logistics_complaint_created",
    )
    return to_logistics_complaint_read(item)


@app.get("/api/v1/merchant/after-sales", response_model=MerchantAfterSalesListResponse)
async def merchant_list_after_sales(
    status_filter: str = Query(default="open"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=8, ge=1, le=100),
    shop: Shop = Depends(get_current_merchant_shop),
    session: AsyncSession = Depends(get_session),
):
    normalized_filter = status_filter.strip().lower() or "open"

    statement = (
        select(AfterSales, Order)
        .join(Order, AfterSales.order_id == Order.id)
        .where(Order.shop_id == shop.id)
    )

    if normalized_filter == "open":
        statement = statement.where(
            AfterSales.status.in_(
                (
                    AFTER_SALES_STATUS_SUBMITTED,
                    AFTER_SALES_STATUS_MERCHANT_APPROVED,
                    AFTER_SALES_STATUS_PROCESSING,
                )
            )
        )
    elif normalized_filter != "all":
        statement = statement.where(AfterSales.status == normalized_filter)

    count_statement = select(func.count()).select_from(statement.subquery())
    count_result = await session.execute(count_statement)
    total = int(count_result.scalar_one() or 0)

    offset = (page - 1) * page_size
    statement = statement.order_by(AfterSales.created_at.desc()).offset(offset).limit(page_size)
    result = await session.execute(statement)
    rows = result.all()

    return MerchantAfterSalesListResponse(
        items=[to_merchant_after_sales_item(after_sales, order) for after_sales, order in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@app.patch("/api/v1/merchant/after-sales/{after_sales_id}", response_model=MerchantAfterSalesItem)
async def merchant_update_after_sales(
    payload: MerchantAfterSalesUpdateRequest,
    after_sales_id: UUID = Path(...),
    shop: Shop = Depends(get_current_merchant_shop),
    session: AsyncSession = Depends(get_session),
):
    item = await session.get(AfterSales, after_sales_id)
    if not item:
        raise HTTPException(status_code=404, detail="After-sales request not found")

    order = await get_order_or_404(session, item.order_id)
    if order.shop_id != shop.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    action = normalize_after_sales_action(payload.action)
    next_status = resolve_after_sales_next_status(item.status, action)
    if not next_status:
        raise HTTPException(status_code=400, detail="Invalid action for current after-sales status")

    item.status = next_status
    if payload.note:
        item.reason = append_merchant_note(item.reason, payload.note)

    await session.commit()
    await session.refresh(item)
    await invalidate_chat_cache_for_user(order.user_id, after_sales=True)
    await publish_after_sales_changed(
        after_sales_id=item.id,
        order_id=order.id,
        user_id=order.user_id,
        shop_id=order.shop_id,
        status=item.status,
        reason=f"merchant_{action}",
    )
    await publish_order_changed(
        order_id=order.id,
        user_id=order.user_id,
        shop_id=order.shop_id,
        status=order.status,
        reason="after_sales_updated",
    )
    return to_merchant_after_sales_item(item, order)


@app.get("/api/v1/merchant/logistics-complaints", response_model=MerchantLogisticsComplaintListResponse)
async def merchant_list_logistics_complaints(
    status_filter: str = Query(default="open"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=8, ge=1, le=100),
    shop: Shop = Depends(get_current_merchant_shop),
    session: AsyncSession = Depends(get_session),
):
    normalized_filter = status_filter.strip().lower() or "open"

    statement = (
        select(LogisticsComplaint, Order)
        .join(Order, LogisticsComplaint.order_id == Order.id)
        .where(Order.shop_id == shop.id)
    )

    if normalized_filter == "open":
        statement = statement.where(
            LogisticsComplaint.status.in_(
                (
                    LOGISTICS_COMPLAINT_STATUS_SUBMITTED,
                    LOGISTICS_COMPLAINT_STATUS_PROCESSING,
                )
            )
        )
    elif normalized_filter != "all":
        statement = statement.where(LogisticsComplaint.status == normalized_filter)

    count_statement = select(func.count()).select_from(statement.subquery())
    count_result = await session.execute(count_statement)
    total = int(count_result.scalar_one() or 0)

    offset = (page - 1) * page_size
    statement = statement.order_by(LogisticsComplaint.updated_at.desc()).offset(offset).limit(page_size)
    result = await session.execute(statement)
    rows = result.all()

    return MerchantLogisticsComplaintListResponse(
        items=[to_merchant_logistics_complaint_item(item, order) for item, order in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@app.patch("/api/v1/merchant/logistics-complaints/{complaint_id}", response_model=MerchantLogisticsComplaintItem)
async def merchant_update_logistics_complaint(
    payload: MerchantLogisticsComplaintUpdateRequest,
    complaint_id: UUID = Path(...),
    shop: Shop = Depends(get_current_merchant_shop),
    session: AsyncSession = Depends(get_session),
):
    item = await session.get(LogisticsComplaint, complaint_id)
    if not item:
        raise HTTPException(status_code=404, detail="Logistics complaint not found")

    order = await get_order_or_404(session, item.order_id)
    if order.shop_id != shop.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    action = normalize_logistics_complaint_action(payload.action)
    next_status = resolve_logistics_complaint_next_status(item.status, action)
    if not next_status:
        raise HTTPException(status_code=400, detail="Invalid action for current logistics complaint status")

    item.status = next_status
    if payload.note:
        item.resolution_note = append_merchant_note(item.resolution_note, payload.note)
    item.updated_at = datetime.utcnow()

    await session.commit()
    await session.refresh(item)
    await publish_logistics_complaint_changed(
        complaint_id=item.id,
        order_id=order.id,
        user_id=order.user_id,
        shop_id=order.shop_id,
        status=item.status,
        reason=f"merchant_{action}",
    )
    await publish_order_changed(
        order_id=order.id,
        user_id=order.user_id,
        shop_id=order.shop_id,
        status=order.status,
        reason="logistics_complaint_updated",
    )
    return to_merchant_logistics_complaint_item(item, order)


@app.get("/api/v1/merchant/shop", response_model=ShopRead)
async def merchant_get_shop(shop: Shop = Depends(get_current_merchant_shop)):
    return to_shop_read(shop)


@app.patch("/api/v1/merchant/shop", response_model=ShopRead)
async def merchant_update_shop(
    payload: MerchantShopUpdate,
    shop: Shop = Depends(get_current_merchant_shop),
    session: AsyncSession = Depends(get_session),
):
    apply_shop_update_payload(shop, payload)
    await session.commit()
    await session.refresh(shop)
    await invalidate_product_filter_cache()
    await publish_inventory_changed(reason="shop_updated", shop_id=shop.id)
    return to_shop_read(shop)


@app.get("/api/v1/merchant/addresses", response_model=ShopAddressListResponse)
async def merchant_list_addresses(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=8, ge=1, le=100),
    shop: Shop = Depends(get_current_merchant_shop),
    session: AsyncSession = Depends(get_session),
):
    filters = [ShopAddress.shop_id == shop.id]
    count_statement = select(func.count()).select_from(ShopAddress).where(*filters)
    count_result = await session.execute(count_statement)
    total = int(count_result.scalar_one() or 0)

    offset = (page - 1) * page_size
    statement = (
        select(ShopAddress)
        .where(*filters)
        .order_by(ShopAddress.is_default.desc(), ShopAddress.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await session.execute(statement)
    addresses = result.scalars().all()
    return ShopAddressListResponse(
        items=[to_shop_address_read(address) for address in addresses],
        total=total,
        page=page,
        page_size=page_size,
    )


@app.post("/api/v1/merchant/addresses", response_model=ShopAddressRead)
async def merchant_create_address(
    payload: ShopAddressCreate,
    shop: Shop = Depends(get_current_merchant_shop),
    session: AsyncSession = Depends(get_session),
):
    statement = select(ShopAddress).where(ShopAddress.shop_id == shop.id)
    result = await session.execute(statement)
    existing = result.scalars().all()

    make_default = payload.is_default or len(existing) == 0
    if make_default:
        for item in existing:
            item.is_default = False

    address = ShopAddress(
        shop_id=shop.id,
        label=payload.label.strip(),
        contact_name=payload.contact_name.strip(),
        contact_phone=payload.contact_phone.strip(),
        province=payload.province.strip(),
        city=payload.city.strip(),
        district=payload.district.strip(),
        address_line=payload.address_line.strip(),
        postal_code=(payload.postal_code or "").strip() or None,
        is_default=make_default,
    )
    session.add(address)
    await session.commit()
    await session.refresh(address)
    return to_shop_address_read(address)


@app.patch("/api/v1/merchant/addresses/{address_id}", response_model=ShopAddressRead)
async def merchant_update_address(
    payload: ShopAddressUpdate,
    address_id: UUID = Path(...),
    shop: Shop = Depends(get_current_merchant_shop),
    session: AsyncSession = Depends(get_session),
):
    address = await session.get(ShopAddress, address_id)
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
    if address.shop_id != shop.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    if payload.label is not None:
        address.label = payload.label.strip()
    if payload.contact_name is not None:
        address.contact_name = payload.contact_name.strip()
    if payload.contact_phone is not None:
        address.contact_phone = payload.contact_phone.strip()
    if payload.province is not None:
        address.province = payload.province.strip()
    if payload.city is not None:
        address.city = payload.city.strip()
    if payload.district is not None:
        address.district = payload.district.strip()
    if payload.address_line is not None:
        address.address_line = payload.address_line.strip()
    if payload.postal_code is not None:
        address.postal_code = payload.postal_code.strip() or None

    if payload.is_default is True:
        statement = select(ShopAddress).where(ShopAddress.shop_id == shop.id)
        result = await session.execute(statement)
        peers = result.scalars().all()
        for peer in peers:
            peer.is_default = peer.id == address.id
    elif payload.is_default is False:
        address.is_default = False

    await session.commit()
    await session.refresh(address)
    return to_shop_address_read(address)


@app.get("/api/v1/merchant/products", response_model=ProductListResponse)
async def merchant_list_products(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str = Query(default=""),
    shop: Shop = Depends(get_current_merchant_shop),
    session: AsyncSession = Depends(get_session),
):
    filters = [Product.shop_id == shop.id]
    cleaned_keyword = keyword.strip()
    if cleaned_keyword:
        pattern = f"%{cleaned_keyword}%"
        filters.append(
            or_(
                Product.name.ilike(pattern),
                Product.brand.ilike(pattern),
                Product.model.ilike(pattern),
                Product.sku_code.ilike(pattern),
                Product.description.ilike(pattern),
            )
        )

    count_statement = select(func.count()).select_from(Product).where(*filters)
    count_result = await session.execute(count_statement)
    total = int(count_result.scalar_one() or 0)

    offset = (page - 1) * page_size
    statement = (
        select(Product)
        .where(*filters)
        .order_by(Product.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await session.execute(statement)
    products = result.scalars().all()

    return ProductListResponse(
        items=[to_product_read(product, shop=shop) for product in products],
        total=total,
        page=page,
        page_size=page_size,
    )


@app.post("/api/v1/merchant/products", response_model=ProductRead)
async def merchant_create_product(
    payload: MerchantProductCreate,
    shop: Shop = Depends(get_current_merchant_shop),
    session: AsyncSession = Depends(get_session),
):
    product = Product(shop_id=shop.id, **build_product_create_values(payload))
    session.add(product)
    await session.commit()
    await session.refresh(product)
    await invalidate_product_filter_cache()
    await publish_inventory_changed(
        reason="product_created",
        shop_id=shop.id,
        product_ids=[product.id],
    )
    return to_product_read(product, shop=shop)


@app.patch("/api/v1/merchant/products/{product_id}", response_model=ProductRead)
async def merchant_update_product(
    payload: MerchantProductUpdate,
    product_id: UUID = Path(...),
    shop: Shop = Depends(get_current_merchant_shop),
    session: AsyncSession = Depends(get_session),
):
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.shop_id != shop.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    apply_product_update_payload(product, payload)

    await session.commit()
    await session.refresh(product)
    await invalidate_product_filter_cache()
    await publish_inventory_changed(
        reason="product_updated",
        shop_id=shop.id,
        product_ids=[product.id],
    )
    return to_product_read(product, shop=shop)


@app.get("/api/v1/merchant/orders", response_model=MerchantOrderListResponse)
async def merchant_list_orders(
    status_filter: Literal["all", "pending_shipment", "shipped"] = Query(default="pending_shipment"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=8, ge=1, le=100),
    shop: Shop = Depends(get_current_merchant_shop),
    session: AsyncSession = Depends(get_session),
):
    filters = [Order.shop_id == shop.id]
    if status_filter != "all":
        filters.append(Order.status == status_filter)

    count_statement = select(func.count()).select_from(Order).where(*filters)
    count_result = await session.execute(count_statement)
    total = int(count_result.scalar_one() or 0)

    offset = (page - 1) * page_size
    statement = (
        select(Order)
        .where(*filters)
        .order_by(Order.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await session.execute(statement)
    orders = result.scalars().all()

    details: list[OrderRead] = []
    for order in orders:
        details.append(await build_order_detail(session, order))
    return MerchantOrderListResponse(items=details, total=total, page=page, page_size=page_size)


@app.post("/api/v1/merchant/orders/{order_id}/ship", response_model=OrderRead)
async def merchant_ship_order(
    payload: MerchantOrderShipRequest,
    order_id: str = Path(...),
    shop: Shop = Depends(get_current_merchant_shop),
    session: AsyncSession = Depends(get_session),
):
    order = await get_order_or_404(session, order_id)
    if order.shop_id != shop.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if order.status == ORDER_STATUS_SHIPPED:
        return await build_order_detail(session, order)
    if order.status != ORDER_STATUS_PENDING_SHIPMENT:
        raise HTTPException(status_code=400, detail="Order is not pending shipment")

    target_address_id = payload.ship_from_address_id
    if target_address_id is None:
        default_stmt = (
            select(ShopAddress)
            .where(ShopAddress.shop_id == shop.id, ShopAddress.is_default == True)  # noqa: E712
            .limit(1)
        )
        default_result = await session.execute(default_stmt)
        default_address = default_result.scalar_one_or_none()
        if not default_address:
            any_stmt = select(ShopAddress).where(ShopAddress.shop_id == shop.id).limit(1)
            any_result = await session.execute(any_stmt)
            default_address = any_result.scalar_one_or_none()
        if not default_address:
            raise HTTPException(status_code=400, detail="No ship-from address available for this shop")
        target_address_id = default_address.id

    address = await session.get(ShopAddress, target_address_id)
    if not address:
        raise HTTPException(status_code=404, detail="Ship-from address not found")
    if address.shop_id != shop.id:
        raise HTTPException(status_code=403, detail="Address does not belong to current shop")

    now = datetime.utcnow()
    ship_from_text = build_full_address(address)
    ship_to_text = order.address
    eta, current_location, route_steps, llm_raw_text = await predict_logistics(ship_from_text, ship_to_text, now)
    current_location_value = (payload.current_location or "").strip() or current_location
    route_points = route_steps_to_plan(route_steps)
    route_geo_payload = await build_route_geo(session, route_steps)
    route_geo_points = normalize_route_geo(route_geo_payload)
    current_geo = pick_geo_from_route(route_geo_points, current_location_value)
    if not current_geo:
        current_geo = await geocode_with_cache(session, current_location_value)
    if not current_geo and route_geo_points:
        current_geo = (route_geo_points[0].lng, route_geo_points[0].lat)
    current_lng = current_geo[0] if current_geo else None
    current_lat = current_geo[1] if current_geo else None

    logistics = await get_logistics_by_order(session, order.id)
    tracking_no = generate_tracking_no()

    if logistics:
        logistics.shipped_from_address_id = address.id
        logistics.status = LOGISTICS_STATUS_IN_TRANSIT
        logistics.current_location = current_location_value
        logistics.current_lng = current_lng
        logistics.current_lat = current_lat
        logistics.estimated_delivery_at = eta
        logistics.route_plan = route_points
        logistics.route_geo = route_geo_payload
        logistics.llm_raw_text = llm_raw_text
        logistics.updated_at = now
        if not logistics.tracking_no:
            logistics.tracking_no = tracking_no
    else:
        logistics = Logistics(
            order_id=order.id,
            shipped_from_address_id=address.id,
            tracking_no=tracking_no,
            status=LOGISTICS_STATUS_IN_TRANSIT,
            current_location=current_location_value,
            current_lng=current_lng,
            current_lat=current_lat,
            estimated_delivery_at=eta,
            route_plan=route_points,
            route_geo=route_geo_payload,
            llm_raw_text=llm_raw_text,
            updated_at=now,
        )
        session.add(logistics)

    order.status = ORDER_STATUS_SHIPPED
    try:
        await session.commit()
    except IntegrityError:
        # Handle duplicated concurrent shipping attempts as idempotent success.
        await session.rollback()
        latest_order = await get_order_or_404(session, order_id)
        await invalidate_chat_cache_for_user(latest_order.user_id, orders=True, logistics=True)
        await publish_order_changed(
            order_id=latest_order.id,
            user_id=latest_order.user_id,
            shop_id=latest_order.shop_id,
            status=latest_order.status,
            reason="shipped",
        )
        return await build_order_detail(session, latest_order)
    await session.refresh(order)
    await invalidate_chat_cache_for_user(order.user_id, orders=True, logistics=True)
    await publish_order_changed(
        order_id=order.id,
        user_id=order.user_id,
        shop_id=order.shop_id,
        status=order.status,
        reason="shipped",
    )

    return await build_order_detail(session, order)


@app.post("/api/v1/merchant/orders/{order_id}/logistics/advance", response_model=OrderRead)
async def merchant_advance_order_logistics(
    order_id: str = Path(...),
    shop: Shop = Depends(get_current_merchant_shop),
    session: AsyncSession = Depends(get_session),
):
    order = await get_order_or_404(session, order_id)
    if order.shop_id != shop.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if order.status != ORDER_STATUS_SHIPPED:
        raise HTTPException(status_code=400, detail="Order must be shipped before advancing logistics")

    logistics = await get_logistics_by_order(session, order.id)
    if not logistics:
        raise HTTPException(status_code=404, detail="Logistics not found for this order")
    if (logistics.status or "").strip().lower() == LOGISTICS_STATUS_DELIVERED:
        raise HTTPException(status_code=400, detail="Logistics is already delivered")

    now = datetime.utcnow()
    next_location, next_status = compute_next_logistics_state(logistics)
    route_steps = extract_route_steps(list(logistics.route_geo or []), list(logistics.route_plan or []))
    route_geo_payload = list(logistics.route_geo or [])
    route_geo_points = normalize_route_geo(route_geo_payload)
    if not route_steps and logistics.shipped_from_address_id:
        shipped_from_address = await session.get(ShopAddress, logistics.shipped_from_address_id)
        if shipped_from_address:
            _, _, route_steps, _ = await predict_logistics(
                build_full_address(shipped_from_address),
                order.address,
                logistics.updated_at,
            )
    if not route_geo_points:
        route_geo_payload = await build_route_geo(session, route_steps)
        route_geo_points = normalize_route_geo(route_geo_payload)
        logistics.route_geo = route_geo_payload
    current_geo = pick_geo_from_route(route_geo_points, next_location)
    if not current_geo:
        next_step = find_route_step(route_steps, next_location)
        if next_step:
            current_geo = await geocode_with_cache(session, next_step.amap_query)
        if not current_geo:
            current_geo = await geocode_with_cache(session, next_location)
    if not current_geo and route_geo_points:
        current_geo = (route_geo_points[-1].lng, route_geo_points[-1].lat)

    logistics.current_location = next_location
    logistics.current_lng = current_geo[0] if current_geo else None
    logistics.current_lat = current_geo[1] if current_geo else None
    logistics.status = next_status
    logistics.updated_at = now
    if next_status == LOGISTICS_STATUS_DELIVERED:
        logistics.estimated_delivery_at = now

    await session.commit()
    await invalidate_chat_cache_for_user(order.user_id, orders=True, logistics=True)
    await publish_order_changed(
        order_id=order.id,
        user_id=order.user_id,
        shop_id=order.shop_id,
        status=order.status,
        reason=f"logistics_advanced:{next_status}",
    )

    return await build_order_detail(session, order)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

