# Rasa-EC-bot Backend (FastAPI)

后端支持用户商城、商家中心、订单物流、售后流程与客服桥接接口，并已接入 Redis 缓存。

## 1. 主要能力
- 用户：注册登录、商品查询、购物车、下单、订单查询、申请退货/换货
- 商家：店铺读取、发货地址管理、商品管理、订单发货、售后处理
- 客服：提供订单/物流/售后内部查询接口，并支持“自动下单/自动退款”二次确认执行
- 缓存：Redis 缓存商品筛选元数据与客服汇总数据

## 2. 运行依赖
- Python `>=3.10, <3.12`
- PostgreSQL 15
- Redis 7（Docker）

## 3. 环境变量
先复制环境变量模板：

```powershell
Copy-Item .env.sample .env
```

Redis 相关配置（在 `.env` 中）：

```env
REDIS_URL=redis://127.0.0.1:6379/0
REDIS_CACHE_TTL_SEC=180
CHAT_ACTION_TTL_SEC=300
REDIS_DOCKER_CONTAINER_NAME=rasa-redis
REDIS_DOCKER_IMAGE=redis:7
REDIS_DOCKER_HOST_PORT=6379
REDIS_DOCKER_CONTAINER_PORT=6379
REDIS_DOCKER_DATA_DIR=../database/redisdata
REDIS_APPENDONLY=yes
REDIS_INIT_MARKER_KEY=rasa_ec_bot:system:initialized_at
REDIS_INIT_SCHEMA_KEY=rasa_ec_bot:system:schema_version
REDIS_INIT_SCHEMA_VERSION=1
```

说明：
- `REDIS_DOCKER_DATA_DIR` 决定 Redis 持久化目录（默认 `../database/redisdata`）。
- `REDIS_URL` 是后端服务实际连接地址。
- `CHAT_ACTION_TTL_SEC` 是客服自动执行“待确认动作”有效期（秒）。

## 4. 启动 PostgreSQL 与 Redis
### 4.1 PostgreSQL
Windows PowerShell（在 `backend` 目录执行）：
```powershell
New-Item -ItemType Directory -Force ..\database\pgdata | Out-Null
$PGDATA_PATH = (Resolve-Path ..\database\pgdata).Path

docker run --name rasa-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -v "${PGDATA_PATH}:/var/lib/postgresql/data" -d postgres:15

docker ps --filter name=rasa-postgres

docker exec -it rasa-postgres psql -U postgres -c "CREATE DATABASE rasa_ec_bot;"
```

Linux / macOS（在 `backend` 目录执行）：
```bash
mkdir -p ../database/pgdata

docker run --name rasa-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -v "$(pwd)/../database/pgdata:/var/lib/postgresql/data" -d postgres:15

docker ps --filter name=rasa-postgres

docker exec -it rasa-postgres psql -U postgres -c "CREATE DATABASE rasa_ec_bot;"
```

如果提示容器名已存在（`Conflict. The container name ... is already in use`）：

- 直接复用已有容器：
  - `docker start rasa-postgres`
- 如需按当前挂载路径重建：
  - `docker stop rasa-postgres`
  - `docker rm rasa-postgres`
  - 再执行上面的 `docker run` 命令

### 4.2 Redis（持久化 + 初始化脚本）
在 `backend` 目录执行。

Windows PowerShell：

```powershell
# 1) 创建/启动 Redis 容器（自动读取 .env，自动挂载持久化目录）
powershell -ExecutionPolicy Bypass -File .\scripts\start_redis.ps1

# 可选：强制重建容器
# powershell -ExecutionPolicy Bypass -File .\scripts\start_redis.ps1 -Recreate

# 2) 初始化 Redis（健康检查 + 初始化标记）
powershell -ExecutionPolicy Bypass -File .\scripts\init_redis.ps1
```

macOS（bash/zsh）：

```bash
# 首次执行建议加权限
chmod +x scripts/start_redis.sh scripts/init_redis.sh scripts/start_redis_macos.sh scripts/init_redis_macos.sh

# 1) 创建/启动 Redis 容器（自动读取 .env）
./scripts/start_redis_macos.sh

# 可选：强制重建容器
# ./scripts/start_redis_macos.sh --recreate

# 2) 初始化 Redis（健康检查 + 初始化标记）
./scripts/init_redis_macos.sh
```

Linux Fedora（bash）：

```bash
# 首次执行建议加权限
chmod +x scripts/start_redis.sh scripts/init_redis.sh scripts/start_redis_fedora.sh scripts/init_redis_fedora.sh

# 1) 创建/启动 Redis 容器（自动读取 .env）
./scripts/start_redis_fedora.sh

# 可选：强制重建容器
# ./scripts/start_redis_fedora.sh --recreate

# 2) 初始化 Redis（健康检查 + 初始化标记）
./scripts/init_redis_fedora.sh
```

若 Redis 容器名冲突，可先执行：

- `docker start rasa-redis`（复用已有容器）
- 或 `docker stop rasa-redis && docker rm rasa-redis` 后再运行启动脚本

说明：
- `start_redis_macos.sh` / `start_redis_fedora.sh` 是平台入口脚本，内部复用 `start_redis.sh`。
- `init_redis_macos.sh` / `init_redis_fedora.sh` 是平台入口脚本，内部复用 `init_redis.sh`。
- macOS / Fedora 均要求本机可用 `docker` 命令。

初始化脚本会写入：
- `REDIS_INIT_MARKER_KEY`（记录初始化时间）
- `REDIS_INIT_SCHEMA_KEY`（仅首次写入 schema 版本）

### 4.3 校验 Redis
```powershell
docker ps --filter name=rasa-redis
docker exec -it rasa-redis redis-cli ping
```

## 5. 导入表结构与种子数据
```powershell
$OutputEncoding = [System.Text.Encoding]::UTF8
Get-Content -Raw -Encoding UTF8 db/init_db.sql | docker exec -i -e PGCLIENTENCODING=UTF8 rasa-postgres psql -U postgres -d rasa_ec_bot
Get-Content -Raw -Encoding UTF8 db/seed_data.sql | docker exec -i -e PGCLIENTENCODING=UTF8 rasa-postgres psql -U postgres -d rasa_ec_bot
```

## 6. 启动后端
```bash
uv sync
uv run uvicorn app.main:app --reload
```
- API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`

## 7. Redis 缓存说明
### 7.1 缓存接口
- `GET /api/v1/products/filters`
- `GET /api/v1/chat/internal/orders-summary`
- `GET /api/v1/chat/internal/orders-logistics-summary`
- `GET /api/v1/chat/internal/after-sales-summary`

### 7.2 失效触发
- 商品新增/编辑后：失效商品筛选缓存
- 用户下单后：失效该用户订单/物流汇总缓存
- 商家发货后：失效该用户订单/物流汇总缓存
- 创建/处理售后后：失效该用户售后汇总缓存

### 7.3 降级策略
- Redis 未配置或连接失败时，接口自动回退数据库查询，不影响功能。

## 8. 核心 API
### 8.1 用户侧
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
- `GET /api/v1/orders/{order_id}/after-sales`
- `POST /api/v1/orders/{order_id}/after-sales`

### 8.2 商家侧
- `GET /api/v1/merchant/shop`
- `GET /api/v1/merchant/addresses`
- `POST /api/v1/merchant/addresses`
- `PATCH /api/v1/merchant/addresses/{address_id}`
- `GET /api/v1/merchant/products`
- `POST /api/v1/merchant/products`
- `PATCH /api/v1/merchant/products/{product_id}`
- `GET /api/v1/merchant/orders?status_filter=pending_shipment|shipped|all`
- `POST /api/v1/merchant/orders/{order_id}/ship`
- `GET /api/v1/merchant/after-sales?status_filter=open|all|...`
- `PATCH /api/v1/merchant/after-sales/{after_sales_id}`

### 8.3 客服内部接口（Rasa Action 专用）
- `GET /api/v1/chat/internal/orders-summary`
- `GET /api/v1/chat/internal/orders-logistics-summary`
- `GET /api/v1/chat/internal/after-sales-summary`

### 8.4 客服自动执行（二次确认）
- 入口：`POST /api/v1/chat/send`
- 支持动作：
  - 自动下单（基于当前用户购物车）
  - 自动发起退款/换货（基于订单号）
- 安全机制：
  - 首次只生成“待确认草案”
  - 用户必须回复 `确认 <确认码>` 才会执行
  - 回复 `取消 <确认码>` 可放弃执行

## 9. 种子账号
统一密码：`password123`
- 用户：`test1@example.com`
- 用户：`test2@example.com`
- 商家：`merchant1@example.com`（星河数码旗舰店）
- 商家：`merchant2@example.com`（青禾智家生活馆）

### 9.1 老库密码不匹配排查
如果历史种子数据密码哈希不一致，可执行：

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
