from datetime import timedelta, datetime
from random import randint
from uuid import UUID

from fastapi import FastAPI, Depends, HTTPException, status, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, or_
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Literal

from .models import (
    User,
    UserCreate,
    UserRead,
    LoginRequest,
    Token,
    TokenData,
    Product,
    ProductRead,
    ProductListResponse,
    ProductFilterMetaResponse,
    CartItem,
    AddCartItemRequest,
    UpdateCartItemRequest,
    CartItemRead,
    CartResponse,
    Order,
    CreateOrderRequest,
    OrderItem,
    OrderItemRead,
    OrderRead,
    OrderListItem,
    OrderListResponse,
)
from .auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_user,
)
from .database import get_session

app = FastAPI(title="Rasa-EC-bot Backend", version="0.2.0")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def generate_order_id() -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    suffix = f"{randint(0, 9999):04d}"
    return f"ORD{timestamp}{suffix}"


def to_product_read(product: Product) -> ProductRead:
    return ProductRead(
        id=product.id,
        name=product.name,
        price=float(product.price),
        description=product.description,
        image_url=product.image_url,
        category=product.category,
        is_active=product.is_active,
        stock=product.stock,
        created_at=product.created_at,
    )


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

    return CartResponse(
        items=items,
        total_items=total_items,
        total_amount=round(total_amount, 2),
    )


async def fetch_cart_rows(session: AsyncSession, user_id: UUID) -> list[tuple[CartItem, Product]]:
    statement = (
        select(CartItem, Product)
        .join(Product, CartItem.product_id == Product.id)
        .where(CartItem.user_id == user_id)
        .order_by(CartItem.updated_at.desc())
    )
    result = await session.execute(statement)
    return result.all()


async def get_current_db_user(
    token_data: TokenData = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> User:
    email = normalize_email(token_data.email or "")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    statement = select(User).where(func.lower(User.email) == email)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    return user


async def get_active_product_or_404(session: AsyncSession, product_id: UUID) -> Product:
    product = await session.get(Product, product_id)
    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


async def build_order_detail(session: AsyncSession, order: Order) -> OrderRead:
    items_stmt = select(OrderItem).where(OrderItem.order_id == order.id).order_by(OrderItem.id)
    items_result = await session.execute(items_stmt)
    order_items = items_result.scalars().all()

    return OrderRead(
        id=order.id,
        status=order.status,
        address=order.address,
        contact_email=order.contact_email,
        total_amount=float(order.total_amount),
        created_at=order.created_at,
        items=[
            OrderItemRead(
                id=item.id,
                product_id=item.product_id,
                product_name=item.product_name,
                unit_price=float(item.unit_price),
                quantity=item.quantity,
                subtotal=float(item.subtotal),
            )
            for item in order_items
        ],
    )


# 配置 CORS
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


@app.get("/")
async def root():
    return {"message": "Welcome to Rasa-EC-bot API"}


@app.post("/api/v1/auth/register", response_model=UserRead)
async def register(user: UserCreate, session: AsyncSession = Depends(get_session)):
    normalized_email = normalize_email(user.email)

    statement = select(User).where(func.lower(User.email) == normalized_email)
    result = await session.execute(statement)
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user.password)
    new_user = User(
        username=user.username.strip(),
        email=normalized_email,
        hashed_password=hashed_password,
    )
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user


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
        data={"sub": user.email},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/v1/auth/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_db_user)):
    return current_user


@app.get("/api/v1/products/filters", response_model=ProductFilterMetaResponse)
async def get_product_filter_meta(session: AsyncSession = Depends(get_session)):
    active_filters = [Product.is_active == True]  # noqa: E712

    categories_statement = (
        select(Product.category)
        .where(
            *active_filters,
            Product.category.is_not(None),
            Product.category != "",
        )
        .distinct()
        .order_by(Product.category.asc())
    )
    categories_result = await session.execute(categories_statement)
    categories = [category for category in categories_result.scalars().all() if category]

    price_range_statement = select(func.min(Product.price), func.max(Product.price)).where(*active_filters)
    price_range_result = await session.execute(price_range_statement)
    price_min, price_max = price_range_result.one()

    return ProductFilterMetaResponse(
        categories=categories,
        price_min=float(price_min or 0),
        price_max=float(price_max or 0),
    )


@app.get("/api/v1/products", response_model=ProductListResponse)
async def list_products(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
    keyword: str = Query(default=""),
    category: str = Query(default=""),
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
        filters.append(
            or_(
                Product.name.ilike(pattern),
                Product.description.ilike(pattern),
            )
        )
    if cleaned_category:
        filters.append(Product.category == cleaned_category)
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
    statement = (
        select(Product)
        .where(*filters)
        .order_by(order_by)
        .offset(offset)
        .limit(page_size)
    )
    result = await session.execute(statement)
    products = result.scalars().all()

    return ProductListResponse(
        items=[to_product_read(product) for product in products],
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
    return to_product_read(product)


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
        session.add(
            CartItem(
                user_id=current_user.id,
                product_id=payload.product_id,
                quantity=payload.quantity,
            )
        )

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
    address = payload.address.strip()
    contact_email = normalize_email(payload.contact_email)
    if not address:
        raise HTTPException(status_code=400, detail="Address is required")
    if not contact_email:
        raise HTTPException(status_code=400, detail="Contact email is required")

    cart_rows = await fetch_cart_rows(session, current_user.id)
    if not cart_rows:
        raise HTTPException(status_code=400, detail="Cart is empty")

    for cart_item, product in cart_rows:
        if cart_item.quantity > product.stock:
            raise HTTPException(
                status_code=409,
                detail=f"Insufficient stock for {product.name}",
            )

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
        status="待发货",
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

    return await build_order_detail(session, new_order)


@app.get("/api/v1/orders", response_model=OrderListResponse)
async def list_orders(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_db_user),
):
    statement = (
        select(Order)
        .where(Order.user_id == current_user.id)
        .order_by(Order.created_at.desc())
    )
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
    item_count_map = {order_id: count for order_id, count in count_result.all()}

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
    order = await session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    return await build_order_detail(session, order)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
