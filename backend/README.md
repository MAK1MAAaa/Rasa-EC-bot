# Rasa-EC-bot Backend (FastAPI)

后端支持用户商城、商家中心、订单物流、售后流程与客服桥接接口，并已接入 Redis 缓存。

## 1. 主要能力
- 用户：注册登录、商品查询、购物车、下单、订单查询、申请退货/换货
- 商家：店铺读取、发货地址管理、商品管理、订单发货、售后处理
- 客服：提供订单/物流/售后内部查询接口，并支持“自动下单/自动退款”二次确认执行
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

docker ps --filter name=rasa-postgres

docker exec -it rasa-postgres psql -U postgres -c "CREATE DATABASE rasa_ec_bot;"
```

Linux / macOS（在 `backend` 目录执行）：
```bash
mkdir -p ../database/pgdata

docker run --name rasa-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -v "$(pwd)/../database/pgdata:/var/lib/postgresql/data" -d pgvector/pgvector:pg15

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

用户售后阶段规则：
- 未发货（`pending_shipment`）：允许直接申请`return`。
- 物流运输中（`logistics.status=in_transit`）：暂不允许申请退货/换货。
- 已送达（`logistics.status=delivered`）：允许申请`return`或`exchange`。

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

### 8.3 客服内部接口（Rasa Action 专用）
- `GET /api/v1/chat/internal/orders-summary`
- `GET /api/v1/chat/internal/orders-logistics-summary`
- `GET /api/v1/chat/internal/after-sales-summary`

### 8.4 客服自动执行（二次确认）
- 入口：
  - `POST /api/v1/chat/send`
  - `POST /api/v1/chat/pending-action/decision`
- 支持动作：
  - 自动下单（基于当前用户购物车）
  - 自动发起退款/换货（基于订单号）
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

### 10.3 新增环境变量
```env
RASA_PARSE_PATH=/model/parse
CHAT_ROUTER_ENABLE_AGENT=true
CHAT_ROUTER_RASA_CONFIDENCE_THRESHOLD=0.72
AGENT_OLLAMA_MODEL=qwen3.5:2b-lora
AGENT_OLLAMA_TIMEOUT_SEC=45
```

### 10.4 可观测性
- 每次聊天请求生成 `trace_id`。
- 内部路由标记：`route=rule|agent`。
- Agent 模式会记录工具调用日志（工具名/读写级别/参数/成功状态）。

## 12. Multi-modal RAG（新增）

### 11.1 环境变量
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

### 11.2 新增接口
- `POST /api/v1/chat/upload-image`
  - `multipart/form-data`，字段名 `file`，仅支持 jpg/png/webp
  - 返回：`attachment_id/mime/size_bytes/width/height`
- `POST /api/v1/kb/index`
  - 入库政策/说明书（分块 + embedding + upsert）
- `POST /api/v1/chat/send`
  - 请求体新增可选：`attachments: string[]`
  - 带附件请求会强制走 Agent 路由

### 11.3 安全与执行边界
- 图片附件会校验归属，禁止跨用户读取。
- 写操作仍保持“待确认草案”机制，不会由 Agent 直接落库执行退款/退换货。

## 13. 物流地图集成（新增）

### 12.1 环境变量
请在 `backend/.env` 中新增：

```env
AMAP_WEB_KEY=
AMAP_WEB_SIG=
AMAP_TIMEOUT_MS=3000
AMAP_QPS_LIMIT=5
```

### 12.2 数据模型扩展
- `logistics` 新增字段：
  - `current_lng`
  - `current_lat`
  - `route_geo`（JSON 数组，元素结构：`name/lng/lat`）
- 新增表：`geo_cache`（地址地理编码缓存）。

### 12.3 运行时行为
- 商家发货与物流推进时会尝试补全坐标：
  - 先查询 `geo_cache`
  - 未命中时回退到 AMap 地理编码
  - 地理编码失败不会阻断发货，文本物流仍可正常工作
- 启动阶段包含轻量 schema 自检（`CREATE TABLE IF NOT EXISTS` + `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`）。

### 12.4 向后兼容
API 路径保持不变，`logistics` 响应仅新增可选字段：
- `current_lng?: number`
- `current_lat?: number`
- `route_geo?: { name: string; lng: number; lat: number }[]`

### 12.5 AMap 密钥放置说明（重要）
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

### 12.6 `securityJsCode` 使用说明
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

旧版 `provider/layer` benchmark 脚本已经从仓库移除。  
当前推荐的论文主实验入口统一使用第 15 节的系统形态接口级 benchmark。
## 15. 接口级 Benchmark（系统形态）

当前推荐的论文实验入口是：

- `backend/scripts/build_system_benchmark_dataset.py`
- `backend/scripts/run_system_benchmark.py`

它直接对比 5 种系统形态，而不是旧版 `provider/layer` 基准：

- `rasa_only`
- `llm_base_ollama`
- `llm_lora_ollama`
- `rasa_plus_llm_base`
- `rasa_plus_llm_lora`

默认场景：

- `recommendation`
- `after_sales`
- `image_after_sales`

### 14.1 配置文件

主配置：`backend/benchmarks/experiment.yaml`

关键字段：

- `profiles`
- `auth.login_url`
- `auth.me_url`
- `auth.customer.email`
- `auth.customer.password`
- `image_assets_dir`
- `image_case_map`
- `systems.<name>.kind`
- `systems.<name>.base_url`
- `systems.<name>.path`
- `systems.<name>.model`
- `systems.<name>.auth_mode`
- `systems.<name>.supports_image`
- `systems.<name>.supports_cards`
- `systems.<name>.requires_upload_step`

### 14.2 纯 Rasa 实例要求

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

### 14.3 基础模型 / LoRA 模型 / 双后端

基础模型：

```bash
ollama pull qwen3.5:2b
```

LoRA 适配器导出为 Ollama 模型：

```bash
cd LoRA
uv run python scripts/export_ollama_model.py \
  --adapter-dir outputs/smoke_ec_faq_only/adapter \
  --base-model qwen3.5:2b \
  --model-name qwen3.5:2b-lora \
  --output-dir outputs/smoke_ec_faq_only/ollama_export

ollama create qwen3.5:2b-lora -f outputs/smoke_ec_faq_only/ollama_export/Modelfile
```

后端基础模型实例：

```bash
cd backend
AGENT_OLLAMA_MODEL=qwen3.5:2b uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

后端 LoRA 模型实例：

```bash
cd backend
AGENT_OLLAMA_MODEL=qwen3.5:2b-lora uv run uvicorn app.main:app --host 127.0.0.1 --port 8001
```

### 14.4 数据集与运行命令

默认 prompt 文件：

- `backend/benchmarks/prompts/recommendation.jsonl`
- `backend/benchmarks/prompts/after_sales.jsonl`
- `backend/benchmarks/prompts/image_after_sales.jsonl`

若要重新生成默认语料：

```bash
uv run python backend/scripts/build_system_benchmark_dataset.py
```

快速冒烟：

```bash
uv run python backend/scripts/run_system_benchmark.py \
  --profile quick \
  --systems rasa_only,llm_base_ollama,llm_lora_ollama,rasa_plus_llm_base,rasa_plus_llm_lora \
  --scenarios recommendation,after_sales,image_after_sales \
  --verbose
```

中等强度实验：

```bash
uv run python backend/scripts/run_system_benchmark.py \
  --profile medium \
  --systems rasa_only,llm_base_ollama,llm_lora_ollama,rasa_plus_llm_base,rasa_plus_llm_lora \
  --scenarios recommendation,after_sales,image_after_sales \
  --repeats 2
```

### 14.5 结果字段

输出目录：

`backend/benchmarks/results/<timestamp>_<profile>_system_benchmark/`

文件说明：

- `raw_events.jsonl`：逐请求原始记录。
- `summary.csv`：逐批次聚合结果。
- `scenario_quality.csv`：按系统和场景统计评分失败原因。
- `system_matrix.csv`：论文主表。
- `report.md`：中文摘要报告。

建议论文引用口径：

- 接口性能：`p95_ms`、`throughput_rps`、`success_rate`
- 任务效果：`task_success_rate`、`quality_pass_rate`
- 能力缺失：`unsupported_rate`
