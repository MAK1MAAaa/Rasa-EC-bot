
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta
from random import randint
from typing import Literal
from uuid import UUID

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Path, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, or_
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from .auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from .cache import RedisCache
from .database import get_session
from .models import (
    ChatAfterSalesSummaryItem,
    ChatAfterSalesSummaryResponse,
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
    ChatReplyMessage,
    ChatSendRequest,
    ChatSendResponse,
    CreateAfterSalesRequest,
    CreateOrderRequest,
    Logistics,
    LogisticsRead,
    LoginRequest,
    MerchantAfterSalesItem,
    MerchantAfterSalesListResponse,
    MerchantAfterSalesUpdateRequest,
    MerchantOrderListResponse,
    MerchantOrderShipRequest,
    MerchantProductCreate,
    MerchantProductUpdate,
    Order,
    OrderItem,
    OrderItemRead,
    OrderListItem,
    OrderListResponse,
    OrderRead,
    Product,
    ProductFilterMetaResponse,
    ProductListResponse,
    ProductRead,
    Shop,
    ShopAddress,
    ShopAddressCreate,
    ShopAddressRead,
    ShopAddressUpdate,
    ShopBrief,
    ShopRead,
    Token,
    TokenData,
    UpdateCartItemRequest,
    User,
    UserCreate,
    UserRead,
)

app = FastAPI(title="Rasa-EC-bot Backend", version="0.3.0")

RASA_SERVER_URL = os.getenv("RASA_SERVER_URL", "http://127.0.0.1:5005")
RASA_REST_WEBHOOK_PATH = os.getenv("RASA_REST_WEBHOOK_PATH", "/webhooks/rest/webhook")
RASA_REQUEST_TIMEOUT_SEC = float(os.getenv("RASA_REQUEST_TIMEOUT_SEC", "30"))
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")
RASA_INTERNAL_TOKEN = os.getenv("RASA_INTERNAL_TOKEN", "")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:9b")
OLLAMA_TIMEOUT_SEC = float(os.getenv("OLLAMA_TIMEOUT_SEC", "45"))
LOGISTICS_LLM_MAX_WAIT_SEC = float(os.getenv("LOGISTICS_LLM_MAX_WAIT_SEC", "12"))

REDIS_URL = os.getenv("REDIS_URL", "")
REDIS_CACHE_TTL_SEC = int(os.getenv("REDIS_CACHE_TTL_SEC", "180"))

ORDER_STATUS_PENDING_SHIPMENT = "pending_shipment"
ORDER_STATUS_SHIPPED = "shipped"

AFTER_SALES_TYPE_RETURN = "return"
AFTER_SALES_TYPE_EXCHANGE = "exchange"
AFTER_SALES_ALLOWED_TYPES = {AFTER_SALES_TYPE_RETURN, AFTER_SALES_TYPE_EXCHANGE}

AFTER_SALES_STATUS_SUBMITTED = "submitted"
AFTER_SALES_STATUS_MERCHANT_APPROVED = "merchant_approved"
AFTER_SALES_STATUS_PROCESSING = "processing"
AFTER_SALES_STATUS_MERCHANT_REJECTED = "merchant_rejected"
AFTER_SALES_STATUS_COMPLETED = "completed"
AFTER_SALES_STATUS_CANCELLED = "cancelled"

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

PRODUCT_FILTER_CACHE_KEY = "products:filters:v1"


@app.on_event("startup")
async def on_startup() -> None:
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


def build_fallback_route(ship_from: str, ship_to: str) -> tuple[str, list[str]]:
    origin = infer_region_label(ship_from, "始发地")
    destination = infer_region_label(ship_to, "目的地")
    if origin == destination:
        route = [
            f"{origin}揽收仓",
            f"{origin}同城分拨中心",
            f"{destination}配送站",
            "派送中",
        ]
    else:
        route = [
            f"{origin}揽收仓",
            f"{origin}转运中心",
            f"{destination}转运中心",
            f"{destination}配送站",
        ]
    return route[0], route


def should_replace_with_fallback_route(route_points: list[str]) -> bool:
    if not route_points:
        return True
    route_text = " ".join(route_points).lower()
    generic_tokens = [
        "origin warehouse",
        "transit center",
        "destination city",
        "out for delivery",
        "picked up",
        "warehouse",
    ]
    if any(token in route_text for token in generic_tokens):
        return True
    return not any(re.search(r"[\u4e00-\u9fff]", item) for item in route_points)


def should_replace_with_fallback_location(current_location: str) -> bool:
    text = (current_location or "").strip()
    if not text:
        return True
    lowered = text.lower()
    generic_tokens = [
        "origin warehouse",
        "transit center",
        "destination city",
        "out for delivery",
        "picked up",
    ]
    if any(token in lowered for token in generic_tokens):
        return True
    return not bool(re.search(r"[\u4e00-\u9fff]", text))


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


def to_product_read(product: Product, shop_name: str) -> ProductRead:
    return ProductRead(
        id=product.id,
        shop_id=product.shop_id,
        shop_name=shop_name,
        name=product.name,
        price=float(product.price),
        description=product.description,
        image_url=product.image_url,
        category=product.category,
        is_active=product.is_active,
        stock=product.stock,
        created_at=product.created_at,
    )


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


def to_after_sales_read(item: AfterSales) -> AfterSalesRead:
    return AfterSalesRead(
        id=item.id,
        order_id=item.order_id,
        type=item.type,
        reason=item.reason,
        status=item.status,
        created_at=item.created_at,
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
    logistics_read = None
    if logistics:
        logistics_read = LogisticsRead(
            tracking_no=logistics.tracking_no,
            status=logistics.status,
            current_location=logistics.current_location,
            estimated_delivery_at=logistics.estimated_delivery_at,
            route_plan=list(logistics.route_plan or []),
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
    )


def parse_ollama_json(content: str) -> dict:
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", content)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        return {}
    return {}


async def predict_logistics(
    ship_from: str,
    ship_to: str,
    now: datetime,
) -> tuple[datetime, str, list[str], str]:
    fallback_eta = now + timedelta(hours=72)
    fallback_location, fallback_route = build_fallback_route(ship_from, ship_to)
    fallback_raw = "fallback"

    system_prompt = (
        "You are a logistics planning assistant. "
        "Return strict JSON with keys: eta_hours (int), current_location (string), route_points (array of strings), summary (string). "
        "No markdown, no extra keys."
    )
    user_prompt = (
        f"Shipment time: {now.isoformat()} UTC\n"
        f"Ship from: {ship_from}\n"
        f"Ship to: {ship_to}\n"
        "Estimate route and delivery ETA."
    )

    try:
        timeout_sec = max(1.0, min(OLLAMA_TIMEOUT_SEC, LOGISTICS_LLM_MAX_WAIT_SEC))
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "stream": False,
                    "format": "json",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
        response.raise_for_status()
        payload = response.json()
        content = payload.get("message", {}).get("content", "") if isinstance(payload, dict) else ""
        if not isinstance(content, str) or not content.strip():
            return fallback_eta, fallback_location, fallback_route, fallback_raw

        parsed = parse_ollama_json(content)
        eta_hours_raw = parsed.get("eta_hours")
        eta_hours = 72
        if isinstance(eta_hours_raw, (int, float)):
            eta_hours = int(eta_hours_raw)
        eta_hours = max(4, min(240, eta_hours))

        current_location = parsed.get("current_location")
        if not isinstance(current_location, str) or not current_location.strip():
            current_location = fallback_location

        route_points = parsed.get("route_points")
        cleaned_route: list[str] = []
        if isinstance(route_points, list):
            for item in route_points:
                if isinstance(item, str) and item.strip():
                    cleaned_route.append(item.strip())
        if should_replace_with_fallback_route(cleaned_route):
            cleaned_route = fallback_route

        if should_replace_with_fallback_location(current_location):
            current_location = cleaned_route[0]

        return now + timedelta(hours=eta_hours), current_location, cleaned_route, content.strip()
    except Exception:
        return fallback_eta, fallback_location, fallback_route, fallback_raw


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


def append_merchant_note(reason: str | None, note: str) -> str:
    cleaned_note = note.strip()
    if not cleaned_note:
        return (reason or "").strip()

    prefix = (reason or "").strip()
    stamped = f"[merchant_note {datetime.utcnow().isoformat(timespec='seconds')} UTC] {cleaned_note}"
    return f"{prefix}\n{stamped}".strip() if prefix else stamped


@app.get("/")
async def root():
    return {"message": "Welcome to Rasa-EC-bot API"}


@app.post("/api/v1/chat/send", response_model=ChatSendResponse)
async def chat_send(
    payload: ChatSendRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message cannot be empty")

    current_user = await get_current_db_user_optional(request, session)
    sender_id = (payload.sender_id or "").strip() or (f"user-{current_user.id}" if current_user else "web_user")
    metadata = {
        "is_authenticated": bool(current_user),
        "user_id": str(current_user.id) if current_user else "",
        "user_email": current_user.email if current_user else "",
        "username": current_user.username if current_user else "",
        "frontend_base_url": FRONTEND_BASE_URL,
    }

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

    messages: list[ChatReplyMessage] = []
    for item in data:
        if isinstance(item, dict):
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                messages.append(ChatReplyMessage(text=text.strip()))

    if not messages:
        messages.append(ChatReplyMessage(text="Sorry, no reply was generated. Please try again later."))
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
            status=order.status,
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

    price_range_statement = select(func.min(Product.price), func.max(Product.price)).where(*active_filters)
    price_range_result = await session.execute(price_range_statement)
    price_min, price_max = price_range_result.one()

    response = ProductFilterMetaResponse(
        categories=categories,
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
    shop_id: UUID | None = Query(default=None),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    in_stock: bool = Query(default=False),
    sort_by: Literal["newest", "price_asc", "price_desc"] = Query(default="newest"),
    session: AsyncSession = Depends(get_session),
):
    filters = [Product.is_active == True]  # noqa: E712
    cleaned_keyword = keyword.strip()
    cleaned_category = category.strip()

    if cleaned_keyword:
        pattern = f"%{cleaned_keyword}%"
        filters.append(or_(Product.name.ilike(pattern), Product.description.ilike(pattern)))
    if cleaned_category:
        filters.append(Product.category == cleaned_category)
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
        order_by = Product.price.asc()
    elif sort_by == "price_desc":
        order_by = Product.price.desc()
    else:
        order_by = Product.created_at.desc()

    count_statement = select(func.count()).select_from(Product).where(*filters)
    count_result = await session.execute(count_statement)
    total = int(count_result.scalar_one() or 0)

    offset = (page - 1) * page_size
    statement = select(Product).where(*filters).order_by(order_by).offset(offset).limit(page_size)
    result = await session.execute(statement)
    products = result.scalars().all()

    shop_name_map = await get_shop_name_map(session, [product.shop_id for product in products])
    return ProductListResponse(
        items=[to_product_read(product, shop_name_map.get(product.shop_id, "Unknown Shop")) for product in products],
        total=total,
        page=page,
        page_size=page_size,
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
    return to_product_read(product, shop.name)


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
    return await build_order_detail(session, new_order)


@app.get("/api/v1/orders", response_model=OrderListResponse)
async def list_orders(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_db_user),
):
    statement = select(Order).where(Order.user_id == current_user.id).order_by(Order.created_at.desc())
    result = await session.execute(statement)
    orders = result.scalars().all()

    if not orders:
        return OrderListResponse(items=[])

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
        ]
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
    if order.status != ORDER_STATUS_SHIPPED:
        raise HTTPException(status_code=400, detail="After-sales is available after shipment")

    request_type = normalize_after_sales_type(payload.type)
    if request_type not in AFTER_SALES_ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="type must be return or exchange")

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
    return to_after_sales_read(item)


@app.get("/api/v1/merchant/after-sales", response_model=MerchantAfterSalesListResponse)
async def merchant_list_after_sales(
    status_filter: str = Query(default="open"),
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

    statement = statement.order_by(AfterSales.created_at.desc())
    result = await session.execute(statement)
    rows = result.all()

    return MerchantAfterSalesListResponse(
        items=[to_merchant_after_sales_item(after_sales, order) for after_sales, order in rows]
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
    return to_merchant_after_sales_item(item, order)


@app.get("/api/v1/merchant/shop", response_model=ShopRead)
async def merchant_get_shop(shop: Shop = Depends(get_current_merchant_shop)):
    return ShopRead(
        id=shop.id,
        name=shop.name,
        description=shop.description,
        contact_email=shop.contact_email,
        contact_phone=shop.contact_phone,
        is_active=shop.is_active,
        created_at=shop.created_at,
    )


@app.get("/api/v1/merchant/addresses", response_model=list[ShopAddressRead])
async def merchant_list_addresses(
    shop: Shop = Depends(get_current_merchant_shop),
    session: AsyncSession = Depends(get_session),
):
    statement = (
        select(ShopAddress)
        .where(ShopAddress.shop_id == shop.id)
        .order_by(ShopAddress.is_default.desc(), ShopAddress.created_at.desc())
    )
    result = await session.execute(statement)
    addresses = result.scalars().all()
    return [to_shop_address_read(address) for address in addresses]


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
        filters.append(or_(Product.name.ilike(pattern), Product.description.ilike(pattern)))

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
        items=[to_product_read(product, shop.name) for product in products],
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
    product = Product(
        shop_id=shop.id,
        name=payload.name.strip(),
        description=(payload.description or "").strip() or None,
        image_url=(payload.image_url or "").strip() or None,
        category=(payload.category or "").strip() or None,
        price=payload.price,
        stock=payload.stock,
        is_active=payload.is_active,
    )
    session.add(product)
    await session.commit()
    await session.refresh(product)
    await invalidate_product_filter_cache()
    return to_product_read(product, shop.name)


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

    if payload.name is not None:
        product.name = payload.name.strip()
    if payload.description is not None:
        product.description = payload.description.strip() or None
    if payload.image_url is not None:
        product.image_url = payload.image_url.strip() or None
    if payload.category is not None:
        product.category = payload.category.strip() or None
    if payload.price is not None:
        product.price = payload.price
    if payload.stock is not None:
        product.stock = payload.stock
    if payload.is_active is not None:
        product.is_active = payload.is_active

    await session.commit()
    await session.refresh(product)
    await invalidate_product_filter_cache()
    return to_product_read(product, shop.name)


@app.get("/api/v1/merchant/orders", response_model=MerchantOrderListResponse)
async def merchant_list_orders(
    status_filter: Literal["all", "pending_shipment", "shipped"] = Query(default="pending_shipment"),
    shop: Shop = Depends(get_current_merchant_shop),
    session: AsyncSession = Depends(get_session),
):
    filters = [Order.shop_id == shop.id]
    if status_filter != "all":
        filters.append(Order.status == status_filter)

    statement = select(Order).where(*filters).order_by(Order.created_at.desc())
    result = await session.execute(statement)
    orders = result.scalars().all()

    details: list[OrderRead] = []
    for order in orders:
        details.append(await build_order_detail(session, order))
    return MerchantOrderListResponse(items=details)


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
    eta, current_location, route_points, llm_raw_text = await predict_logistics(ship_from_text, ship_to_text, now)

    logistics = await get_logistics_by_order(session, order.id)
    tracking_no = generate_tracking_no()

    if logistics:
        logistics.shipped_from_address_id = address.id
        logistics.status = "in_transit"
        logistics.current_location = (payload.current_location or "").strip() or current_location
        logistics.estimated_delivery_at = eta
        logistics.route_plan = route_points
        logistics.llm_raw_text = llm_raw_text
        logistics.updated_at = now
        if not logistics.tracking_no:
            logistics.tracking_no = tracking_no
    else:
        logistics = Logistics(
            order_id=order.id,
            shipped_from_address_id=address.id,
            tracking_no=tracking_no,
            status="in_transit",
            current_location=(payload.current_location or "").strip() or current_location,
            estimated_delivery_at=eta,
            route_plan=route_points,
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
        return await build_order_detail(session, latest_order)
    await session.refresh(order)
    await invalidate_chat_cache_for_user(order.user_id, orders=True, logistics=True)

    return await build_order_detail(session, order)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
