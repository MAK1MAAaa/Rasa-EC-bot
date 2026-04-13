# Rasa-EC-bot Backend

本目录承载 FastAPI 后端、数据库初始化脚本、客服路由、知识检索、待确认动作与商家侧业务接口。

相关文档：

- 根说明：[README.md](../README.md)
- 测试与 benchmark：[tests/README.md](../tests/README.md)
- Rasa 说明：[rasa/README.md](../rasa/README.md)
- LoRA 说明：[LoRA/README.md](../LoRA/README.md)

说明：

- benchmark 细节已迁移到 `tests/README.md`
- 本文只保留后端能力、接口、环境变量与运行方式

## 1. 主要能力

### 1.1 业务能力

- 用户注册、登录、商品浏览、购物车、下单、订单查询
- 订单取消、收货信息修改、物流投诉、售后申请
- 商家店铺读取、地址管理、商品管理、订单发货、售后处理
- 商品历史浏览记录与个性化推荐
- 物流地图与轨迹点位返回

### 1.2 客服能力

- Rasa 高频规则链路接入
- Agent 复杂问题路由
- 订单、物流、售后、推荐等内部客服接口
- 图片上传、图片理解与知识检索
- 待确认动作草案生成、确认与取消执行

## 2. 运行依赖

- Python `>=3.10, <3.12`
- PostgreSQL 15
- Redis 7
- Rasa Server
- Rasa Action Server
- Ollama

可选：

- vLLM / OpenAI-compatible LLM，用于 LoRA Agent

## 3. 环境变量

先复制模板：

```powershell
Copy-Item .env.sample .env
```

### 3.1 基础设施

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/rasa_ec_bot

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

### 3.2 Rasa 与客服路由

```env
RASA_SERVER_URL=http://127.0.0.1:5005
RASA_REST_WEBHOOK_PATH=/webhooks/rest/webhook
RASA_PARSE_PATH=/model/parse
RASA_REQUEST_TIMEOUT_SEC=30
RASA_INTERNAL_TOKEN=change-me-in-production

FRONTEND_BASE_URL=http://localhost:5173
CHAT_ROUTER_ENABLE_AGENT=true
CHAT_ROUTER_RASA_CONFIDENCE_THRESHOLD=0.72
```

### 3.3 LLM 与 Agent

基础 Ollama 模式：

```env
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3.5:2b
OLLAMA_TIMEOUT_SEC=45
```

LoRA Agent 模式：

```env
AGENT_LLM_PROVIDER=openai_compat
AGENT_LLM_BASE_URL=http://127.0.0.1:8002/v1
AGENT_LLM_MODEL=qwen3.5-2b-lora
AGENT_LLM_API_KEY=EMPTY
AGENT_LLM_TIMEOUT_SEC=45
```

兼容字段：

- `AGENT_OLLAMA_MODEL`
- `AGENT_OLLAMA_TIMEOUT_SEC`

新部署建议统一使用 `AGENT_LLM_*`。

### 3.4 Multi-modal RAG

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

### 3.5 物流地图

```env
AMAP_WEB_KEY=
AMAP_WEB_SIG=
AMAP_TIMEOUT_MS=3000
AMAP_QPS_LIMIT=5
```

说明：

- `AMAP_WEB_KEY` 仅供后端使用
- `AMAP_WEB_SIG` 为可选签名

## 4. 启动数据库与缓存

### 4.1 PostgreSQL

Windows PowerShell：

```powershell
New-Item -ItemType Directory -Force ..\database\pgdata | Out-Null
$PGDATA_PATH = (Resolve-Path ..\database\pgdata).Path

docker run --name rasa-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -v "${PGDATA_PATH}:/var/lib/postgresql/data" -d pgvector/pgvector:pg15
do {
    Start-Sleep -Seconds 1
    docker exec rasa-postgres pg_isready -U postgres | Out-Null
} until ($LASTEXITCODE -eq 0)

docker exec rasa-postgres psql -U postgres -c "CREATE DATABASE rasa_ec_bot;"
```

Linux / macOS：

```bash
mkdir -p ../database/pgdata

docker run --name rasa-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -v "$(pwd)/../database/pgdata:/var/lib/postgresql/data" -d pgvector/pgvector:pg15
until docker exec rasa-postgres pg_isready -U postgres >/dev/null 2>&1; do
  sleep 1
done

docker exec rasa-postgres psql -U postgres -c "CREATE DATABASE rasa_ec_bot;"
```

### 4.2 Redis

Windows PowerShell：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_redis.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\init_redis.ps1
```

macOS：

```bash
chmod +x scripts/start_redis.sh scripts/init_redis.sh scripts/start_redis_macos.sh scripts/init_redis_macos.sh
./scripts/start_redis_macos.sh
./scripts/init_redis_macos.sh
```

Fedora：

```bash
chmod +x scripts/start_redis.sh scripts/init_redis.sh scripts/start_redis_fedora.sh scripts/init_redis_fedora.sh
./scripts/start_redis_fedora.sh
./scripts/init_redis_fedora.sh
```

### 4.3 校验 Redis

```powershell
docker ps --filter name=rasa-redis
docker exec -it rasa-redis redis-cli ping
```

## 5. 初始化数据库

Windows PowerShell：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\init_postgres.ps1
```

macOS：

```bash
chmod +x scripts/init_postgres.sh scripts/init_postgres_macos.sh
./scripts/init_postgres_macos.sh
```

Fedora：

```bash
chmod +x scripts/init_postgres.sh scripts/init_postgres_fedora.sh
./scripts/init_postgres_fedora.sh
```

说明：

- 初始化脚本使用 `docker cp + psql -f`
- 避免 PowerShell 管道导入中文 SQL 时出现编码损坏

## 6. 启动后端

### 6.1 默认实例

```bash
uv sync
uv run uvicorn app.main:app --reload
```

- API：`http://127.0.0.1:8000`
- Swagger：`http://127.0.0.1:8000/docs`

### 6.2 基础模型对照实例

```powershell
$env:AGENT_LLM_PROVIDER = "ollama"
$env:AGENT_LLM_BASE_URL = "http://127.0.0.1:11434"
$env:AGENT_LLM_MODEL = "qwen3.5:2b"
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 6.3 LoRA 对照实例

先启动 `vLLM`，再启动：

```powershell
$env:AGENT_LLM_PROVIDER = "openai_compat"
$env:AGENT_LLM_BASE_URL = "http://127.0.0.1:8002/v1"
$env:AGENT_LLM_API_KEY = "EMPTY"
$env:AGENT_LLM_MODEL = "qwen3.5-2b-lora"
uv run uvicorn app.main:app --host 127.0.0.1 --port 8001
```

### 6.4 vLLM 示例

强调：

- `vLLM` 默认按 WSL/Linux + CUDA 环境运行
- Windows 原生 PowerShell 不作为默认推荐路径
- 后端 LoRA 实例 `8001` 只负责业务接口转发，模型推理由 `8002` 的 `vLLM` 提供

```bash
cd /mnt/d/Github/Rasa-EC-bot/LoRA
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

## 7. 业务模块

### 7.1 商品、店铺与目录

当前目录模型已支持：

- 商品基础字段
- 品牌、型号、`sku_code`
- 原价、评分、评论数、月销
- 标签、核心参数
- 店铺评分、服务分、物流分、售后分
- 发货城市、特色类目、服务标签

相关能力：

- `GET /api/v1/products`
- `GET /api/v1/products/filters`
- `GET /api/v1/products/{product_id}`
- `GET /api/v1/merchant/shop`
- `PATCH /api/v1/merchant/shop`
- `GET /api/v1/merchant/products`
- `POST /api/v1/merchant/products`
- `PATCH /api/v1/merchant/products/{product_id}`

筛选与排序：

- `brand`
- `sort_by=rating_desc|sales_desc`

### 7.2 用户侧订单、物流与售后

主要接口：

- `POST /api/v1/orders`
- `GET /api/v1/orders`
- `GET /api/v1/orders/{order_id}`
- `POST /api/v1/orders/{order_id}/cancel`
- `PATCH /api/v1/orders/{order_id}/shipping`
- `GET /api/v1/orders/{order_id}/after-sales`
- `POST /api/v1/orders/{order_id}/after-sales`
- `GET /api/v1/orders/{order_id}/logistics-complaints`
- `POST /api/v1/orders/{order_id}/logistics-complaints`

规则约束：

- 取消订单仅允许 `pending_shipment`
- 修改收货信息仅允许 `pending_shipment`
- 物流投诉仅允许已发货且已有物流记录的订单

### 7.3 商家侧运营

主要接口：

- `GET /api/v1/merchant/addresses`
- `POST /api/v1/merchant/addresses`
- `PATCH /api/v1/merchant/addresses/{address_id}`
- `GET /api/v1/merchant/orders`
- `POST /api/v1/merchant/orders/{order_id}/ship`
- `POST /api/v1/merchant/orders/{order_id}/logistics/advance`
- `GET /api/v1/merchant/after-sales`
- `PATCH /api/v1/merchant/after-sales/{after_sales_id}`
- `GET /api/v1/merchant/logistics-complaints`
- `PATCH /api/v1/merchant/logistics-complaints/{complaint_id}`

## 8. 客服链路

### 8.1 混合路由策略

`POST /api/v1/chat/send` 的执行顺序：

1. 先尝试 Rasa intent parse
2. 高频确定性问题优先走规则链路
3. `nlu_fallback`、低置信度或复杂问题切到 Agent
4. 带图片附件的问题强制走 Agent

### 8.2 内部客服接口

供 Rasa Action 或内部客服逻辑使用：

- `GET /api/v1/chat/internal/orders-summary`
- `GET /api/v1/chat/internal/orders-logistics-summary`
- `GET /api/v1/chat/internal/after-sales-summary`
- `GET /api/v1/chat/internal/product-recommendations`

### 8.3 待确认动作

入口：

- `POST /api/v1/chat/send`
- `POST /api/v1/chat/pending-action/decision`

支持动作：

- 自动下单
- 自动取消订单
- 自动修改收货信息
- 自动发起退款 / 换货
- 自动提交物流投诉

安全机制：

- 首次仅生成“待确认草案”
- 用户通过确认或取消按钮决定是否执行
- 默认有效期受 `CHAT_ACTION_TTL_SEC` 控制

### 8.4 结构化消息协议

`POST /api/v1/chat/send` 返回 `messages[]`，每条消息可包含：

- `text`
- `cards`
- `actions`

后端会透传 Rasa `custom.cards/actions`，前端可直接渲染卡片与动作按钮。

### 8.5 历史浏览与个性化推荐

相关接口：

- `POST /api/v1/products/{product_id}/history`
- `GET /api/v1/products/history`
- `GET /api/v1/chat/internal/product-recommendations`

推荐排序规则：

1. 显式类目与关键词优先
2. 历史浏览偏好加权
3. 再按月销、评分、上架时间排序

## 9. Multi-modal RAG

### 9.1 上传与索引

主要接口：

- `POST /api/v1/chat/upload-image`
- `POST /api/v1/kb/index`
- `POST /api/v1/chat/send`

说明：

- 上传仅支持 `jpg/png/webp`
- 图片请求可携带 `attachments: string[]`
- 知识库索引会进行分块、embedding 与 upsert

### 9.2 安全与执行边界

- 图片附件会校验归属
- 禁止跨用户读取
- 写操作依旧通过“待确认草案”机制执行
- Agent 不会直接越权落库执行退款或换货

## 10. 物流地图

### 10.1 数据模型

物流相关返回已支持：

- `current_lng`
- `current_lat`
- `route_geo`

并新增：

- `geo_cache`

### 10.2 运行时行为

- 发货时基于“发货地址 + 收货地址 + AMap geocode”生成物流点位
- 读取订单详情时可对历史订单尝试补算轨迹
- geocode 失败不会阻断发货
- 启动阶段包含轻量 schema 自检

### 10.3 前后端密钥边界

- 后端使用 `AMAP_WEB_KEY`
- 前端地图脚本使用 `VITE_AMAP_JS_KEY`
- `securityJsCode` 只出现在前端环境变量

## 11. Redis 缓存

### 11.1 缓存接口

- `GET /api/v1/products/filters`
- `GET /api/v1/chat/internal/orders-summary`
- `GET /api/v1/chat/internal/orders-logistics-summary`
- `GET /api/v1/chat/internal/after-sales-summary`
- `GET /api/v1/chat/internal/product-recommendations`

### 11.2 失效触发

- 商品新增或编辑
- 用户下单
- 商家发货
- 创建或处理售后

### 11.3 降级策略

Redis 不可用时，接口会自动回退数据库查询，不影响功能正确性。

## 12. 种子账号

统一密码：`password123`

- 用户：`test1@example.com`
- 用户：`test2@example.com`
- 商家：`merchant1@example.com`
- 商家：`merchant2@example.com`
- 商家：`merchant3@example.com`
- 商家：`merchant4@example.com`
- 商家：`merchant5@example.com`
- 商家：`merchant6@example.com`
- 商家：`merchant7@example.com`

老库密码不匹配时，可执行：

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

## 13. 可观测性与说明

- 每次聊天请求生成 `trace_id`
- 路由会记录 `route=rule|agent`
- Agent 模式会记录工具调用日志

Benchmark 说明：

- benchmark 细节已迁移到 [tests/README.md](../tests/README.md)
- 如需运行系统形态对照实验，请直接使用 `tests/README.md` 中的启动顺序、命令与结果目录约定
