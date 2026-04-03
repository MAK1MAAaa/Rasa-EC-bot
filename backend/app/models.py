from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class UserBase(SQLModel):
    username: str = Field(index=True)
    email: str = Field(unique=True, index=True)


class User(UserBase, table=True):
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: UUID
    created_at: datetime


class LoginRequest(SQLModel):
    email: str
    password: str


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
    stock: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProductRead(ProductBase):
    id: UUID
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


class OrderListItem(SQLModel):
    id: str
    status: str
    address: str
    contact_email: str
    total_amount: float
    item_count: int
    created_at: datetime


class OrderListResponse(SQLModel):
    items: List[OrderListItem]


class OrderRead(SQLModel):
    id: str
    status: str
    address: str
    contact_email: str
    total_amount: float
    created_at: datetime
    items: List[OrderItemRead]


class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(SQLModel):
    email: Optional[str] = None
