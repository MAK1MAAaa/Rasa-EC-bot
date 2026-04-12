# Rasa-EC-bot Backend (FastAPI)

后端支持用户商城、商家中心、订单物流、售后流程与客服桥接接口，并已接入 Redis 缓存。

## 1. 主要能力
- 用户：注册登录、商品查询、购物车、下单、订单查询、取消订单、修改收货信息、申请退货/换货、提交物流投诉
- 用户：商品详情页自动记录历史浏览，商品列表页可读取最近浏览商品
- 商家：店铺读取、发货地址管理、商品管理、订单发货、售后处理
- 商家：提供物流投诉处理接口，可按提交中/处理中/已解决等状态流转
- 客服：提供订单/物流/售后/个性化商品推荐内部接口，并支持“自动下单/自动退款/取消订单/修改收货信息/物流投诉”二次确认执行
- 缓存：Redis 缓存商品筛选元数据与客服汇总数据

## 2. 运行依赖
- Python `>=3.10, <3.12`
- PostgreSQL 15（pgvector）
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

docker run --name rasa-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -v "${PGDATA_PATH}:/var/lib/postgresql/data" -d pgvector/pgvector:pg15
do {
    Start-Sleep -Seconds 1
    docker exec rasa-postgres pg_isready -U postgres | Out-Null
} until ($LASTEXITCODE -eq 0)

docker ps --filter name=rasa-postgres

docker exec -it rasa-postgres psql -U postgres -c "CREATE DATABASE rasa_ec_bot;"
```

Linux / macOS（在 `backend` 目录执行）：
```bash
mkdir -p ../database/pgdata

docker run --name rasa-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -v "$(pwd)/../database/pgdata:/var/lib/postgresql/data" -d pgvector/pgvector:pg15
until docker exec rasa-postgres pg_isready -U postgres >/dev/null 2>&1; do
  sleep 1
done

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

已有 PostgreSQL 容器升级到 pgvector（保留数据）：

1. 备份：`docker exec -t rasa-postgres pg_dump -U postgres -d rasa_ec_bot > rasa_ec_bot_backup.sql`
2. 停止并删除旧容器：`docker stop rasa-postgres && docker rm rasa-postgres`
3. 使用新镜像重建（挂载原 `pgdata`）：`pgvector/pgvector:pg15`
4. 恢复并启用扩展：
   - `docker exec -i rasa-postgres psql -U postgres -d rasa_ec_bot < rasa_ec_bot_backup.sql`
   - `docker exec -it rasa-postgres psql -U postgres -d rasa_ec_bot -c "CREATE EXTENSION IF NOT EXISTS vector;"`

### 4.2 Redis（持久化 + 初始化脚本）
在 `backend` 目录执行。

Windows PowerShell：

```powershell
# 1) 创建/启动 Redis 容器（自动读取 .env，自动挂载持久化目录）
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_redis.ps1

# 可选：强制重建容器
# powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_redis.ps1 -Recreate

# 2) 初始化 Redis（健康检查 + 初始化标记）
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\init_redis.ps1
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
Windows PowerShell：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\init_postgres.ps1
```

macOS（bash/zsh）：

```bash
chmod +x scripts/init_postgres.sh scripts/init_postgres_macos.sh
./scripts/init_postgres_macos.sh
```

Fedora（bash）：

```bash
chmod +x scripts/init_postgres.sh scripts/init_postgres_fedora.sh
./scripts/init_postgres_fedora.sh
```

说明：Windows PowerShell 不要使用 `Get-Content ... | docker exec -i psql ...` 导入中文 SQL。该管道会按本地代码页重编码，导致中文种子数据写入 PostgreSQL 后变成 `?`。项目提供的初始化脚本使用 `docker cp + psql -f`，会自动创建 `rasa_ec_bot` 并安全导入 `db/init_db.sql` 与 `db/seed_data.sql`。
- `init_postgres.sh` 是 Unix 共享实现；`init_postgres_macos.sh` 与 `init_postgres_fedora.sh` 是平台入口脚本。

## 6. 启动后端
```bash
uv sync
uv run uvicorn app.main:app --reload
```
- API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`
- 后端启动时会自动读取 `backend/.env`；若 `AMAP_WEB_KEY` 为空，启动日志会直接给出警告，物流地图会退回文本路线。

## 7. Redis 缓存说明
### 7.1 缓存接口
- `GET /api/v1/products/filters`
- `GET /api/v1/chat/internal/orders-summary`
- `GET /api/v1/chat/internal/orders-logistics-summary`
- `GET /api/v1/chat/internal/after-sales-summary`
- `GET /api/v1/chat/internal/product-recommendations`

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
- `GET /api/v1/products/history`
- `GET /api/v1/products/{product_id}`
- `POST /api/v1/products/{product_id}/history`
- `GET /api/v1/cart`
- `POST /api/v1/cart/items`
- `PATCH /api/v1/cart/items/{item_id}`
- `DELETE /api/v1/cart/items/{item_id}`
- `POST /api/v1/orders`
- `POST /api/v1/orders/{order_id}/cancel`
- `PATCH /api/v1/orders/{order_id}/shipping`
- `GET /api/v1/orders`
- `GET /api/v1/orders/{order_id}`
- `GET /api/v1/orders/{order_id}/after-sales`
- `POST /api/v1/orders/{order_id}/after-sales`
- `GET /api/v1/orders/{order_id}/logistics-complaints`
- `POST /api/v1/orders/{order_id}/logistics-complaints`

分页说明：
- `GET /api/v1/orders` 现支持 `page`、`page_size`，返回 `items / total / page / page_size`。

用户售后阶段规则：
- 未发货（`pending_shipment`）：允许直接申请`return`。
- 物流运输中（`logistics.status=in_transit`）：暂不允许申请退货/换货。
- 已送达（`logistics.status=delivered`）：允许申请`return`或`exchange`。

用户订单变更规则：
- 取消订单仅允许 `pending_shipment` 状态，取消后会自动回补商品库存。
- 修改收货信息仅允许 `pending_shipment` 状态，当前最低交付版支持修改收货地址与联系邮箱。
- 物流投诉仅允许 `shipped` 状态且订单已有物流记录时发起，同一订单只允许存在一条进行中的物流投诉。

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
- `POST /api/v1/merchant/orders/{order_id}/logistics/advance`
- `GET /api/v1/merchant/after-sales?status_filter=open|all|...`
- `PATCH /api/v1/merchant/after-sales/{after_sales_id}`
- `GET /api/v1/merchant/logistics-complaints?status_filter=open|all|...`
- `PATCH /api/v1/merchant/logistics-complaints/{complaint_id}`

分页说明：
- `GET /api/v1/merchant/addresses` 支持 `page`、`page_size`，返回 `ShopAddressListResponse`。
- `GET /api/v1/merchant/products` 已支持 `page`、`page_size`。
- `GET /api/v1/merchant/orders` 支持 `status_filter + page + page_size`，返回 `MerchantOrderListResponse`。
- `GET /api/v1/merchant/after-sales` 支持 `status_filter + page + page_size`，返回 `MerchantAfterSalesListResponse`。

### 8.3 客服内部接口（Rasa Action 专用）
- `GET /api/v1/chat/internal/orders-summary`
- `GET /api/v1/chat/internal/orders-logistics-summary`
- `GET /api/v1/chat/internal/after-sales-summary`
- `GET /api/v1/chat/internal/product-recommendations`

商品历史浏览与个性化推荐说明：
- `POST /api/v1/products/{product_id}/history` 仅客户账号可调用，语义为记录一次商品浏览。
- `GET /api/v1/products/history` 仅客户账号可调用，返回最近浏览商品列表，默认取最近 8 条。
- 后端最多保留每个用户最近 20 个唯一商品浏览记录；重复浏览会更新 `view_count` 与 `last_viewed_at`。
- 客服推荐统一复用后端推荐 helper：显式类目/关键词优先，历史浏览偏好加权次之，再按销量、评分、上架时间排序。

### 8.4 客服自动执行（二次确认）
- 入口：
  - `POST /api/v1/chat/send`
  - `POST /api/v1/chat/pending-action/decision`
- 支持动作：
- 自动下单（基于当前用户购物车）
- 自动发起退款/换货（基于订单号）
- 自动取消待发货订单（基于订单号）
- 自动修改待发货订单收货信息（基于订单号 + 地址）
- 自动提交物流投诉（基于订单号 + 原因）
- 权限约束：
  - 商家账号调用 `POST /api/v1/chat/send` 将返回 `403`
- 安全机制：
  - 首次只生成“待确认草案”
  - 用户通过前端弹窗按钮确认/取消（无需确认码）
  - 待确认动作默认 5 分钟有效（`CHAT_ACTION_TTL_SEC`）

### 8.5 客服消息结构化协议
- `POST /api/v1/chat/send` 返回 `messages[]`，每条消息支持：
  - `text: string`
  - `cards: ChatCard[]`（可选）
  - `actions: ChatAction[]`（可选）
- 后端会透传 Rasa `custom.cards/actions`，前端可直接渲染卡片；旧客户端可仅使用 `text` 字段。

## 9. 种子账号
统一密码：`password123`
- 用户：`test1@example.com`
- 用户：`test2@example.com`
- 商家：`merchant1@example.com`（星河数码旗舰店）
- 商家：`merchant2@example.com`（青禾智家生活馆）
- 商家：`merchant3@example.com`（极昼办公装备店）
- 商家：`merchant4@example.com`（光谱影音专营店）
- 商家：`merchant5@example.com`（山系户外精选店）
- 商家：`merchant6@example.com`（沐川厨房电器馆）
- 商家：`merchant7@example.com`（脉搏健康穿戴馆）

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
  'merchant2@example.com',
  'merchant3@example.com',
  'merchant4@example.com',
  'merchant5@example.com',
  'merchant6@example.com',
  'merchant7@example.com'
);
```

## 10. 混合客服路由（新增）

### 10.1 路由策略
- `POST /api/v1/chat/send` 先尝试 Rasa intent parse。
- 命中 `nlu_fallback`、低置信度（默认 `<0.72`）或复杂查询（多域/条件/并列目标）时，切换到 Agent 路由。
- 高频意图（问候、订单、物流、售后、推荐）且高置信时继续走 Rasa。

### 10.2 Agent 工具分级
- 读取工具：
  - `query_orders_summary`
  - `query_logistics_summary`
  - `query_after_sales_summary`
  - `query_price_protection`
- 写入工具：
  - `draft_after_sales_request`（只生成待确认草案，不直接执行写操作）

## 11. 商品/店铺比较字段与接口升级

### 11.1 目录模型
- `products` 新增字段：`brand`、`model`、`sku_code`、`original_price`、`rating`、`review_count`、`monthly_sales`、`ship_in_hours`、`warranty_days`、`tags`、`spec_highlights`
- `shops` 新增字段：`logo_url`、`rating`、`service_score`、`logistics_score`、`after_sales_score`、`shipping_city`、`featured_categories`、`service_tags`
- 启动时会执行 `ensure_catalog_schema()`，通过 `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` 自动兼容旧库，无需手动删库
- 商品筛选缓存键已升级为 `products:filters:v2`
- 新增索引：`idx_products_brand`、`idx_products_monthly_sales`、`idx_products_rating`

### 11.2 筛选与排序接口
- `GET /api/v1/products`
  - 新增参数：`brand`
  - 排序扩展：`sort_by=rating_desc|sales_desc`
  - 关键词搜索覆盖：`name`、`brand`、`model`、`sku_code`、`description`、`tags`
- `GET /api/v1/products/filters`
  - 新增 `brands: string[]`
  - 新增 `shops[]: { id, name, rating, shipping_city, active_product_count }`

### 11.3 商家接口
- `GET /api/v1/merchant/shop` 已返回完整店铺画像字段
- 新增 `PATCH /api/v1/merchant/shop`
  - 允许更新：`logo_url`、`description`、`contact_email`、`contact_phone`、`shipping_city`、`featured_categories`、`service_tags`
  - 评分相关字段保持只读
- `POST /api/v1/merchant/products` 与 `PATCH /api/v1/merchant/products/{product_id}` 已支持结构化商品字段与数组字段

### 11.4 种子数据
- 固定 7 家店铺、7 个商家账号、112 款商品
- 每店 16 款商品，所有商品完整填充比较字段
- 店铺定位：
  - 星河数码旗舰店：手机、电脑、外设
  - 青禾智家生活馆：家电、智能家居
  - 极昼办公装备店：办公、显示器、电脑
  - 光谱影音专营店：音频、显示器、摄影
  - 山系户外精选店：户外、穿戴
  - 沐川厨房电器馆：家电、家居
  - 脉搏健康穿戴馆：穿戴、智能家居

### 11.5 新增环境变量
```env
RASA_PARSE_PATH=/model/parse
CHAT_ROUTER_ENABLE_AGENT=true
CHAT_ROUTER_RASA_CONFIDENCE_THRESHOLD=0.72
AGENT_LLM_MODEL=qwen3.5-2b-lora
AGENT_LLM_TIMEOUT_SEC=45
```

### 11.6 可观测性
- 每次聊天请求生成 `trace_id`。
- 内部路由标记：`route=rule|agent`。
- Agent 模式会记录工具调用日志（工具名/读写级别/参数/成功状态）。

## 12. Multi-modal RAG（新增）

### 12.1 环境变量
在 `.env` 中新增：

```env
OLLAMA_EMBED_MODEL=mxbai-embed-large
OLLAMA_VLM_MODEL=qwen3-vl:2b
KB_EMBEDDING_DIM=1024
KB_RETRIEVAL_TOP_K=4
KB_CHUNK_SIZE=500
KB_CHUNK_OVERLAP=80
CHAT_UPLOAD_DIR=data/chat_uploads
CHAT_UPLOAD_MAX_MB=8
```

### 12.2 新增接口
- `POST /api/v1/chat/upload-image`
  - `multipart/form-data`，字段名 `file`，仅支持 jpg/png/webp
  - 返回：`attachment_id/mime/size_bytes/width/height`
- `POST /api/v1/kb/index`
  - 入库政策/说明书（分块 + embedding + upsert）
- `POST /api/v1/chat/send`
  - 请求体新增可选：`attachments: string[]`
  - 带附件请求会强制走 Agent 路由

### 12.3 安全与执行边界
- 图片附件会校验归属，禁止跨用户读取。
- 写操作仍保持“待确认草案”机制，不会由 Agent 直接落库执行退款/退换货。

## 13. 物流地图集成（新增）

### 13.1 环境变量
请在 `backend/.env` 中新增：

```env
AMAP_WEB_KEY=
AMAP_WEB_SIG=
AMAP_TIMEOUT_MS=3000
AMAP_QPS_LIMIT=5
```

后端启动时会自动加载 `backend/.env`，并在日志中输出 AMap key 是否已生效的掩码信息，便于确认当前进程读到的是不是正确配置。

### 13.2 数据模型扩展
- `logistics` 新增字段：
  - `current_lng`
  - `current_lat`
  - `route_geo`（对外响应仍为 `name/lng/lat`，库内原始 JSON 可额外保留 `amap_query/stage`）
- 新增表：`geo_cache`（地址地理编码缓存）。

### 13.3 运行时行为
- 商家发货时不再依赖本地 Ollama 生成路线，改为基于“发货地址 + 收货地址 + AMap geocode”生成内部 `route_steps[]`：
  - `name`：站点显示名
  - `amap_query`：用于调用高德地理编码的查询词
  - `stage`：阶段标记（`pickup/origin_hub/destination_hub/delivery_station/sorting`）
- 公开 API 不新增请求参数，仍返回 `route_plan` 与 `route_geo`。
- 商家发货与物流推进时会尝试补全坐标：
  - 先查询 `geo_cache`
  - 未命中时优先用 `amap_query` 调用 AMap 地理编码
  - `amap_query` 失败时回退到站点名称、去后缀名称、城市级查询词
  - 地理编码失败不会阻断发货，文本物流仍可正常工作
- 订单详情读取时，若历史 `route_geo` 中缺少有效坐标，会基于已保存的 `shipped_from_address_id + order.address` 现场重算路线与坐标并返回，方便旧订单恢复地图展示。
- 启动阶段包含轻量 schema 自检（`CREATE TABLE IF NOT EXISTS` + `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`）。
- 为避免本机代理环境干扰高德请求，后端 geocode 调用会忽略系统代理变量，并把 query、状态码、`info/infocode`、是否命中坐标写入日志，方便排查“只有文本路线没有地图”的问题。

### 13.4 向后兼容
API 路径保持不变，`logistics` 响应仅新增可选字段：
- `current_lng?: number`
- `current_lat?: number`
- `route_geo?: { name: string; lng: number; lat: number }[]`

### 13.5 AMap 密钥放置说明（重要）
本项目同时使用两类 AMap 密钥：

1. Web Service Key（后端地理编码）
2. JS API Key（前端地图渲染）

后端 `.env` 示例（参考 `backend/.env.sample`）：

```env
AMAP_WEB_KEY=your_amap_web_service_key
AMAP_WEB_SIG=optional_signature
AMAP_TIMEOUT_MS=3000
AMAP_QPS_LIMIT=5
```

说明：
- `AMAP_WEB_KEY` 仅后端使用，不要暴露到前端。
- `AMAP_WEB_SIG` 为可选项，若你在高德控制台开启签名校验则需要配置。

### 13.6 `securityJsCode` 使用说明
`securityJsCode` 用于 JS API 安全增强，应配置在前端环境变量中：

```env
VITE_ENABLE_LOGISTICS_MAP=true
VITE_AMAP_JS_KEY=your_amap_js_key
VITE_AMAP_SECURITY_JS_CODE=your_security_js_code
```

前端加载器会在加载 JSAPI 脚本前注入：
- `window._AMapSecurityConfig = { securityJsCode: ... }`

可选生产加固：
- 在 `window._AMapSecurityConfig` 中使用 `serviceHost` 反向代理模式
- 在高德控制台为 JS Key 配置域名白名单
- 将 Web Service Key 严格限制在后端服务器使用

## 14. Benchmark 口径说明

旧版 `provider/layer` benchmark 已从仓库移除。当前统一使用客服链路多轮会话 benchmark，目标是做论文级系统形态对照，而不是最小化 CI 成本。

## 15. 接口级 Benchmark（系统形态）

当前推荐的论文实验入口：

- `backend/scripts/build_system_benchmark_dataset.py`
- `backend/scripts/run_system_benchmark.py`

它直接对比 5 种系统形态：

- `rasa_only`
- `llm_base_ollama`
- `llm_lora_ollama`
- `rasa_plus_llm_base`
- `rasa_plus_llm_lora`

### 15.1 场景范围

benchmark 只覆盖客服入口及其图片上传、待确认动作链路，不扩展到全量电商 REST API。当前固定 6 个场景族：

- `recommendation`
- `order_query`
- `logistics_query`
- `after_sales_query`
- `knowledge_and_multimodal`
- `transactional_action`

其中核心集固定 15 个人工编排子场景，扩展集用于放大量级和压力实验。

### 15.2 数据集结构

数据集由脚本生成到以下目录：

- `backend/benchmarks/prompts/core/`
- `backend/benchmarks/prompts/extended/`
- `backend/benchmarks/prompts/dataset_manifest.json`

每条会话样本固定包含：

- `scenario_family`
- `scenario`
- `turns`
- `account`
- `required_capabilities`
- `preconditions`
- `expected_outcomes`
- `tags`

`turns` 显式描述多轮步骤，当前支持：

- `login`
- `upload_image`
- `chat_send`
- `pending_decision`
- `sleep_until_expired`

### 15.3 配置文件

主配置：`backend/benchmarks/experiment.yaml`

重点字段：

- `profiles.quick`
- `profiles.standard`
- `profiles.paper`
- `knowledge_seed`
- `auth.customer`
- `auth.merchant`
- `systems.<name>.kind`
- `systems.<name>.base_url`
- `systems.<name>.path`
- `systems.<name>.upload_path`
- `systems.<name>.pending_action_path`
- `systems.<name>.auth_mode`
- `systems.<name>.capabilities`

### 15.4 能力矩阵与 `unsupported/na`

系统能力位固定为：

- `supports_auth_queries`
- `supports_kb_policy`
- `supports_kb_manual`
- `supports_pending_action`
- `supports_pending_decision`
- `supports_attachments`
- `supports_image_analysis`
- `supports_cards`

每个样本会声明 `required_capabilities`。若系统缺少所需能力，执行器会将该样本标记为 `unsupported/na`：

- 不计入成功率和质量通过率
- 计入覆盖率和 `unsupported_rate`
- 会出现在 `capability_coverage.csv` 与 `paper_tables.md`

### 15.5 知识库种子

为了保持黑盒评测原则，benchmark 不依赖预置内部数据。对支持知识检索的 backend system，执行器会在运行前通过现有接口自动写入 benchmark 专用 KB 种子：

- `backend/benchmarks/kb_seed/after_sales_policy.md`
- `backend/benchmarks/kb_seed/product_manual.md`

接口入口仍是：

- `POST /api/v1/kb/index`

### 15.6 Profile

- `quick`：`core` 数据集，单次并发，用于联调和冒烟。
- `standard`：`extended` 数据集，多并发层级，用于常规回归和压力观察。
- `paper`：`core` 数据集，固定并发与重复次数，用于论文主实验。

### 15.7 纯 Rasa 实例要求

为了保证 `rasa_only` 真正不含 LLM fallback，请使用独立 benchmark 资产：

- `rasa/benchmark/rasa_only/config.yml`
- `rasa/benchmark/rasa_only/domain.yml`
- `rasa/benchmark/rasa_only/rules.yml`

启动命令：

```bash
cd rasa
uv run rasa train \
  --config benchmark/rasa_only/config.yml \
  --domain benchmark/rasa_only/domain.yml \
  --data data/nlu.yml benchmark/rasa_only/rules.yml \
  --out models/benchmark_rasa_only

uv run rasa run \
  --model models/benchmark_rasa_only \
  --enable-api \
  --cors "*" \
  --credentials credentials.yml \
  --endpoints endpoints.yml \
  --port 5006
```

Action Server 仍可复用现有 `actions.py`：

```bash
cd rasa
uv run rasa run actions --actions actions --port 5055
```

### 15.8 基础模型 / LoRA 模型 / 双后端

基础模型：

```bash
ollama pull qwen3.5:2b
```

LoRA 对照实例不需要把 adapter 导出到 Ollama。当前默认做法是直接加载训练产物 `outputs/.../adapter`，通过第 16 节的 `vLLM + PEFT runtime` 提供 OpenAI-compatible 接口。

后端基础模型实例：

```bash
cd backend
AGENT_LLM_PROVIDER=ollama AGENT_LLM_BASE_URL=http://127.0.0.1:11434 AGENT_LLM_MODEL=qwen3.5:2b uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

后端 LoRA 模型实例：

```bash
cd backend
AGENT_LLM_PROVIDER=openai_compat AGENT_LLM_BASE_URL=http://127.0.0.1:8002/v1 AGENT_LLM_API_KEY=EMPTY AGENT_LLM_MODEL=qwen3.5-2b-lora uv run uvicorn app.main:app --host 127.0.0.1 --port 8001
```

### 15.9 数据集与运行命令

重建 benchmark 数据集：

```bash
uv run python backend/scripts/build_system_benchmark_dataset.py
```

快速冒烟：

```bash
uv run python backend/scripts/run_system_benchmark.py \
  --profile quick \
  --systems rasa_only,llm_base_ollama,llm_lora_ollama,rasa_plus_llm_base,rasa_plus_llm_lora \
  --scenarios recommendation,order_query,logistics_query,after_sales_query,knowledge_and_multimodal,transactional_action \
  --verbose
```

标准实验：

```bash
uv run python backend/scripts/run_system_benchmark.py \
  --profile standard \
  --systems rasa_only,llm_base_ollama,llm_lora_ollama,rasa_plus_llm_base,rasa_plus_llm_lora \
  --scenarios recommendation,order_query,logistics_query,after_sales_query,knowledge_and_multimodal,transactional_action
```

论文实验：

```bash
uv run python backend/scripts/run_system_benchmark.py \
  --profile paper \
  --systems rasa_only,llm_base_ollama,llm_lora_ollama,rasa_plus_llm_base,rasa_plus_llm_lora
```

### 15.10 结果文件与论文引用

输出目录：

`backend/benchmarks/results/<timestamp>_<profile>_system_benchmark/`

文件说明：

- `raw_events.jsonl`：会话级原始事件。
- `turn_events.jsonl`：逐步骤事件，适合排查多轮流程和附件上传。
- `summary.csv`：按系统、场景族、并发和重复次数聚合。
- `scenario_quality.csv`：按系统和场景族统计质量失败原因。
- `conversation_summary.csv`：会话级成功率、流程完成率、确认动作结果。
- `capability_coverage.csv`：能力覆盖率与 `unsupported/na` 统计。
- `system_matrix.csv`：论文主表，按场景族输出 `quality_pass_rate`、`conversation_success_rate`、`unsupported_rate`、`p95_ms`。
- `report.md`：中文摘要报告。
- `paper_tables.md`：可直接引用到论文的主表、补充表和威胁说明。

建议论文主文引用：

- 质量：`quality_pass_rate`
- 会话成功：`conversation_success_rate`
- 能力缺失：`unsupported_rate`
- 性能：`p95_ms`

## 16. Agent LoRA 推理改为 vLLM + PEFT

当前推荐方案：
- 复杂客服 Agent：`vLLM + PEFT adapter runtime`
- 视觉与向量：继续使用 Ollama（`qwen3-vl:2b`、`mxbai-embed-large`）

### 16.1 后端环境变量

`backend/.env` 新增/更新：

```env
AGENT_LLM_PROVIDER=openai_compat
AGENT_LLM_BASE_URL=http://127.0.0.1:8002/v1
AGENT_LLM_MODEL=qwen3.5-2b-lora
AGENT_LLM_API_KEY=EMPTY
AGENT_LLM_TIMEOUT_SEC=45
```

兼容说明：
- 旧字段 `AGENT_OLLAMA_MODEL`、`AGENT_OLLAMA_TIMEOUT_SEC` 仍可被读取，但仅用于平滑迁移。
- 新部署请统一使用 `AGENT_LLM_*`。

### 16.2 启动 vLLM（PEFT Runtime）

```bash
cd LoRA
uv run --with vllm python -m vllm.entrypoints.openai.api_server \
  --host 0.0.0.0 \
  --port 8002 \
  --model /mnt/d/Github/Rasa-EC-bot/LoRA/models/Qwen3.5-2B \
  --served-model-name qwen3.5-2b-lora \
  --enable-lora \
  --lora-modules qwen3.5-2b-lora=/mnt/d/Github/Rasa-EC-bot/LoRA/outputs/smoke_ec_faq_only/adapter \
  --max-model-len 4096 \
  --max-num-seqs 2 \
  --gpu-memory-utilization 0.55 \
  --enforce-eager
```

### 16.3 启动后端

```bash
cd backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```
