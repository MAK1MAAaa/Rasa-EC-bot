from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class ShopBrief(SQLModel):
    id: UUID
    name: str


class UserBase(SQLModel):
    username: str = Field(index=True)
    email: str = Field(unique=True, index=True)


class User(UserBase, table=True):
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    hashed_password: str
    role: str = Field(default="customer")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: UUID
    role: str
    created_at: datetime
    shop: Optional[ShopBrief] = None


class LoginRequest(SQLModel):
    email: str
    password: str


class Shop(SQLModel, table=True):
    __tablename__ = "shops"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    owner_user_id: UUID = Field(foreign_key="users.id", index=True)
    name: str
    description: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ShopRead(SQLModel):
    id: UUID
    name: str
    description: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    is_active: bool
    created_at: datetime


class ShopAddress(SQLModel, table=True):
    __tablename__ = "shop_addresses"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    shop_id: UUID = Field(foreign_key="shops.id", index=True)
    label: str
    contact_name: str
    contact_phone: str
    province: str
    city: str
    district: str
    address_line: str
    postal_code: Optional[str] = None
    is_default: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ShopAddressCreate(SQLModel):
    label: str
    contact_name: str
    contact_phone: str
    province: str
    city: str
    district: str
    address_line: str
    postal_code: Optional[str] = None
    is_default: bool = False


class ShopAddressUpdate(SQLModel):
    label: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    address_line: Optional[str] = None
    postal_code: Optional[str] = None
    is_default: Optional[bool] = None


class ShopAddressRead(SQLModel):
    id: UUID
    shop_id: UUID
    label: str
    contact_name: str
    contact_phone: str
    province: str
    city: str
    district: str
    address_line: str
    postal_code: Optional[str] = None
    is_default: bool
    created_at: datetime


class ProductBase(SQLModel):
    name: str
    price: float
    description: Optional[str] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    is_active: bool = True


class Product(ProductBase, table=True):
    __tablename__ = "products"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    shop_id: UUID = Field(foreign_key="shops.id", index=True)
    stock: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProductRead(ProductBase):
    id: UUID
    shop_id: UUID
    shop_name: str
    stock: int
    created_at: datetime


class ProductListResponse(SQLModel):
    items: List[ProductRead]
    total: int
    page: int
    page_size: int


class ProductFilterMetaResponse(SQLModel):
    categories: List[str]
    price_min: float
    price_max: float


class MerchantProductCreate(ProductBase):
    stock: int = Field(default=0, ge=0)


class MerchantProductUpdate(SQLModel):
    name: Optional[str] = None
    price: Optional[float] = Field(default=None, ge=0)
    description: Optional[str] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    stock: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None


class ChatSendRequest(SQLModel):
    message: str = Field(min_length=1, max_length=2000)
    sender_id: Optional[str] = None


class ChatCard(SQLModel):
    type: str
    data: dict[str, Any] = Field(default_factory=dict)


class ChatAction(SQLModel):
    type: str
    label: str
    payload: dict[str, Any] = Field(default_factory=dict)
    style: Optional[str] = None


class ChatReplyMessage(SQLModel):
    text: str
    cards: List[ChatCard] = Field(default_factory=list)
    actions: List[ChatAction] = Field(default_factory=list)


class ChatSendResponse(SQLModel):
    messages: List[ChatReplyMessage]


class ChatPendingActionDecisionRequest(SQLModel):
    decision: str


class ChatOrderSummaryItem(SQLModel):
    id: str
    status: str
    total_amount: float
    item_count: int
    created_at: datetime
    order_link: str


class ChatOrderSummaryResponse(SQLModel):
    items: List[ChatOrderSummaryItem]


class ChatOrderLogisticsSummaryItem(SQLModel):
    id: str
    status: str
    created_at: datetime
    order_link: str
    tracking_no: Optional[str] = None
    current_location: Optional[str] = None
    estimated_delivery_at: Optional[datetime] = None
    route_plan: List[str] = Field(default_factory=list)


class ChatOrderLogisticsSummaryResponse(SQLModel):
    items: List[ChatOrderLogisticsSummaryItem]


class ChatAfterSalesSummaryItem(SQLModel):
    id: UUID
    order_id: str
    type: str
    status: str
    created_at: datetime
    reason: Optional[str] = None
    order_link: str


class ChatAfterSalesSummaryResponse(SQLModel):
    items: List[ChatAfterSalesSummaryItem]


class CartItem(SQLModel, table=True):
    __tablename__ = "cart_items"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    product_id: UUID = Field(foreign_key="products.id", index=True)
    quantity: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AddCartItemRequest(SQLModel):
    product_id: UUID
    quantity: int = Field(default=1, ge=1)


class UpdateCartItemRequest(SQLModel):
    quantity: int = Field(ge=0)


class CartItemRead(SQLModel):
    id: UUID
    product_id: UUID
    product_name: str
    product_image_url: Optional[str] = None
    unit_price: float
    quantity: int
    subtotal: float


class CartResponse(SQLModel):
    items: List[CartItemRead]
    total_items: int
    total_amount: float


class Order(SQLModel, table=True):
    __tablename__ = "orders"

    id: str = Field(primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    shop_id: UUID = Field(foreign_key="shops.id", index=True)
    status: str
    address: str
    contact_email: str
    total_amount: float
    created_at: datetime = Field(default_factory=datetime.utcnow)


class OrderItem(SQLModel, table=True):
    __tablename__ = "order_items"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    order_id: str = Field(foreign_key="orders.id", index=True)
    product_id: UUID = Field(foreign_key="products.id")
    product_name: str
    unit_price: float
    quantity: int
    subtotal: float


class Logistics(SQLModel, table=True):
    __tablename__ = "logistics"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    order_id: str = Field(foreign_key="orders.id", index=True)
    shipped_from_address_id: Optional[UUID] = Field(default=None, foreign_key="shop_addresses.id")
    tracking_no: Optional[str] = None
    status: str
    current_location: Optional[str] = None
    estimated_delivery_at: Optional[datetime] = None
    route_plan: List[str] = Field(default_factory=list, sa_column=Column(JSONB, nullable=False))
    llm_raw_text: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AfterSales(SQLModel, table=True):
    __tablename__ = "after_sales"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    order_id: str = Field(foreign_key="orders.id", index=True)
    type: str
    reason: Optional[str] = None
    status: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CreateOrderRequest(SQLModel):
    address: str
    contact_email: str


class OrderItemRead(SQLModel):
    id: UUID
    product_id: UUID
    product_name: str
    unit_price: float
    quantity: int
    subtotal: float
    product_link: str


class LogisticsRead(SQLModel):
    tracking_no: Optional[str] = None
    status: str
    current_location: Optional[str] = None
    estimated_delivery_at: Optional[datetime] = None
    route_plan: List[str] = Field(default_factory=list)
    updated_at: datetime


class AfterSalesRead(SQLModel):
    id: UUID
    order_id: str
    type: str
    reason: Optional[str] = None
    status: str
    created_at: datetime


class OrderListItem(SQLModel):
    id: str
    status: str
    address: str
    contact_email: str
    total_amount: float
    item_count: int
    created_at: datetime
    shop_id: UUID
    shop_name: str


class OrderListResponse(SQLModel):
    items: List[OrderListItem]


class OrderRead(SQLModel):
    id: str
    status: str
    address: str
    contact_email: str
    total_amount: float
    created_at: datetime
    shop_id: UUID
    shop_name: str
    items: List[OrderItemRead]
    logistics: Optional[LogisticsRead] = None
    after_sales: List[AfterSalesRead] = Field(default_factory=list)


class MerchantOrderShipRequest(SQLModel):
    ship_from_address_id: Optional[UUID] = None
    current_location: Optional[str] = None


class MerchantOrderListResponse(SQLModel):
    items: List[OrderRead]


class CreateAfterSalesRequest(SQLModel):
    type: str
    reason: str


class MerchantAfterSalesUpdateRequest(SQLModel):
    action: str
    note: Optional[str] = None


class MerchantAfterSalesItem(SQLModel):
    id: UUID
    order_id: str
    type: str
    reason: Optional[str] = None
    status: str
    created_at: datetime
    order_status: str
    contact_email: str
    order_link: str


class MerchantAfterSalesListResponse(SQLModel):
    items: List[MerchantAfterSalesItem]


class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(SQLModel):
    email: Optional[str] = None
