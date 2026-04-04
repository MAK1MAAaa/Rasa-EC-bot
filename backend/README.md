# Rasa-EC-bot Backend (FastAPI)

后端已支持用户侧商城 + 商家侧控制台：
- 用户登录、商品浏览、购物车、下单、订单查询
- 商家登录（复用同一登录页）、商品上架/下架、发货地址管理、手动发货
- 发货时接入本地 Ollama（`qwen3.5:9b`）自动生成物流预计送达时间与途径节点

## 1. 技术栈
- FastAPI
- SQLModel + SQLAlchemy Async
- PostgreSQL 15
- JWT Bearer Token
- HTTPX（转发 Rasa、调用 Ollama）

## 2. PostgreSQL 启动与初始化

### 2.1 启动容器
```powershell
# 1) 先启动 PostgreSQL 容器（项目 README 里的命令）
docker run --name rasa-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -v D:/Github/Rasa-EC-bot/database/pgdata:/var/lib/postgresql/data -d postgres:15

# 2) 确认容器在跑
docker ps --filter name=rasa-postgres

# 3) 创建数据库
docker exec -it rasa-postgres psql -U postgres -c "CREATE DATABASE rasa_ec_bot;"
```

### 2.2 导入表结构和种子数据
```powershell
$OutputEncoding = [System.Text.Encoding]::UTF8
Get-Content -Raw -Encoding UTF8 db/init_db.sql | docker exec -i -e PGCLIENTENCODING=UTF8 rasa-postgres psql -U postgres -d rasa_ec_bot
Get-Content -Raw -Encoding UTF8 db/seed_data.sql | docker exec -i -e PGCLIENTENCODING=UTF8 rasa-postgres psql -U postgres -d rasa_ec_bot
```

## 3. 环境变量
在 `backend` 目录创建 `.env`（可直接复制 `.env.sample`）：

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/rasa_ec_bot

RASA_SERVER_URL=http://127.0.0.1:5005
RASA_REST_WEBHOOK_PATH=/webhooks/rest/webhook
RASA_REQUEST_TIMEOUT_SEC=30
RASA_INTERNAL_TOKEN=change-me-in-production

FRONTEND_BASE_URL=http://localhost:5173

OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3.5:9b
OLLAMA_TIMEOUT_SEC=45
```

## 4. 启动后端
```bash
uv sync
uv run uvicorn app.main:app --reload
```

- API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`

## 5. 主要数据结构变更
- `users.role`: `customer | merchant`
- `shops`: 商家店铺
- `shop_addresses`: 商家发货地址（支持默认地址）
- `products.shop_id`: 商品归属店铺
- `orders.shop_id`: 订单归属店铺
- `logistics`: 新增 `shipped_from_address_id / estimated_delivery_at / route_plan / llm_raw_text`

## 6. 主要 API

### 6.1 用户侧
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `GET /api/v1/products`
- `GET /api/v1/products/filters`
- `GET /api/v1/products/{product_id}`
- `GET /api/v1/cart`
- `POST /api/v1/cart/items`
- `PATCH /api/v1/cart/items/{item_id}`
- `DELETE /api/v1/cart/items/{item_id}`
- `POST /api/v1/orders`
- `GET /api/v1/orders`
- `GET /api/v1/orders/{order_id}`

### 6.2 商家侧
- `GET /api/v1/merchant/shop`
- `GET /api/v1/merchant/addresses`
- `POST /api/v1/merchant/addresses`
- `PATCH /api/v1/merchant/addresses/{address_id}`
- `GET /api/v1/merchant/products`
- `POST /api/v1/merchant/products`
- `PATCH /api/v1/merchant/products/{product_id}`
- `GET /api/v1/merchant/orders?status_filter=pending_shipment|shipped|all`
- `POST /api/v1/merchant/orders/{order_id}/ship`

## 7. 种子账号
密码统一：`password123`

- 用户：`test1@example.com`
- 用户：`test2@example.com`
- 商家：`merchant1@example.com`（星河数码旗舰店）
- 商家：`merchant2@example.com`（青禾智家生活馆）

### 7.1 登录失败排查（旧数据）
如果你之前已经导入过旧版 `seed_data.sql`，用户密码哈希可能不匹配。可执行以下 SQL 直接重置种子账号密码：

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;

UPDATE users
SET hashed_password = crypt('password123', gen_salt('bf', 12))
WHERE email IN (
  'test1@example.com',
  'test2@example.com',
  'merchant1@example.com',
  'merchant2@example.com'
);
```
