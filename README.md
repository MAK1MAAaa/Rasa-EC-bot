# Rasa-EC-bot

一个可运行的电商平台示例，集成了：
- 用户端商城（浏览、筛选、购物车、下单、订单、售后）
- 商家端控制台（商品管理、发货地址、手动发货、物流下一站推进、售后处理）
- 智能客服（Rasa + 本地 Ollama `qwen3.5:2b`）
- Redis 缓存层（商品筛选元数据 + 客服订单/物流/售后汇总）

> 客服前端已升级：商家账号不可访问客服；买家/游客客服消息支持商品、订单、物流、售后卡片；自动执行二次确认改为弹窗按钮确认/取消。
> 订单售后规则已升级：未发货可直接申请退货；运输中不可申请退货/换货；送达后可申请更多售后帮助。

## 1. 项目结构
- `backend/`: FastAPI 后端与数据库脚本
- `frontend/`: Vue 3 前端
- `rasa/`: Rasa 对话模型与 Action Server
- `database/`: Docker 持久化目录（PostgreSQL/Redis）
- `requirement.md`: 当前版本需求说明（已同步实现状态）

## 2. 技术栈
- Frontend: Vue 3 + Vite + Pinia + Tailwind CSS
- Backend: FastAPI + SQLModel + PostgreSQL(pgvector)
- Chatbot: Rasa + Rasa SDK Actions + Ollama
- Cache: Redis

## 3. 快速启动
### 3.1 启动数据库与缓存
Windows PowerShell（在项目根目录执行）：
```powershell
New-Item -ItemType Directory -Force .\database\pgdata, .\database\redisdata | Out-Null
$PGDATA_PATH = (Resolve-Path .\database\pgdata).Path
$REDISDATA_PATH = (Resolve-Path .\database\redisdata).Path

# PostgreSQL (pgvector)
docker run --name rasa-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -v "${PGDATA_PATH}:/var/lib/postgresql/data" -d pgvector/pgvector:pg15
docker exec -it rasa-postgres psql -U postgres -c "CREATE DATABASE rasa_ec_bot;"

# Redis
docker run --name rasa-redis -p 6379:6379 -v "${REDISDATA_PATH}:/data" -d redis:7 redis-server --appendonly yes
```

Linux / macOS（在项目根目录执行）：
```bash
mkdir -p ./database/pgdata ./database/redisdata

# PostgreSQL (pgvector)
docker run --name rasa-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -v "$(pwd)/database/pgdata:/var/lib/postgresql/data" -d pgvector/pgvector:pg15
docker exec -it rasa-postgres psql -U postgres -c "CREATE DATABASE rasa_ec_bot;"

# Redis
docker run --name rasa-redis -p 6379:6379 -v "$(pwd)/database/redisdata:/data" -d redis:7 redis-server --appendonly yes
```

如果提示容器名已存在（`Conflict. The container name ... is already in use`）：

- 直接复用已有容器：
  - `docker start rasa-postgres rasa-redis`
- 如需按当前挂载路径重建：
  - `docker stop rasa-postgres rasa-redis`
  - `docker rm rasa-postgres rasa-redis`
  - 再执行上面的 `docker run` 命令

已有 PostgreSQL 容器升级到 pgvector（保留数据）：

1. 备份：
   - `docker exec -t rasa-postgres pg_dump -U postgres -d rasa_ec_bot > rasa_ec_bot_backup.sql`
2. 停止并删除旧容器（不删宿主机 `database/pgdata`）：
   - `docker stop rasa-postgres`
   - `docker rm rasa-postgres`
3. 用 pgvector 镜像重建：
   - `docker run --name rasa-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -v ".../database/pgdata:/var/lib/postgresql/data" -d pgvector/pgvector:pg15`
4. 恢复数据并启用扩展：
   - `docker exec -i rasa-postgres psql -U postgres -d rasa_ec_bot < rasa_ec_bot_backup.sql`
   - `docker exec -it rasa-postgres psql -U postgres -d rasa_ec_bot -c "CREATE EXTENSION IF NOT EXISTS vector;"`

### 3.2 初始化数据库
```powershell
cd backend
$OutputEncoding = [System.Text.Encoding]::UTF8
Get-Content -Raw -Encoding UTF8 db/init_db.sql | docker exec -i -e PGCLIENTENCODING=UTF8 rasa-postgres psql -U postgres -d rasa_ec_bot
Get-Content -Raw -Encoding UTF8 db/seed_data.sql | docker exec -i -e PGCLIENTENCODING=UTF8 rasa-postgres psql -U postgres -d rasa_ec_bot
```

### 3.3 启动后端
```bash
cd backend
# 首次复制环境变量
# Windows: Copy-Item .env.sample .env
# Linux/macOS: cp .env.sample .env

# 建议使用 2B 模型
# OLLAMA_MODEL=qwen3.5:2b

uv sync
uv run uvicorn app.main:app --reload
```
后端地址：`http://127.0.0.1:8000`

### 3.4 启动 Rasa 与 Action Server
```bash
ollama pull qwen3.5:2b

cd rasa
# 首次复制环境变量
# Windows: Copy-Item .env.sample .env
# Linux/macOS: cp .env.sample .env

uv sync
uv run rasa train --config config.yml --domain domain.yml --data data
uv run rasa run --enable-api --cors "*" --credentials credentials.yml --endpoints endpoints.yml --port 5005
uv run rasa run actions --actions actions --port 5055
```

### 3.5 启动前端
Windows PowerShell 速查（对应位置：根目录 `README` 的本节、`frontend/README` 第 4 节）：

1. 先确认：`npm.cmd -v` 正常、`where.exe pnpm` 找不到（表示 npm 有，pnpm 没装好）。
2. 如果 `corepack` 或 `pnpm` 联网失败，先清代理（本机曾出现 `127.0.0.1:9`）：
   `Remove-Item Env:HTTP_PROXY,Env:HTTPS_PROXY,Env:ALL_PROXY -ErrorAction SilentlyContinue`
3. 无管理员权限安装 pnpm（推荐）：
   `npm.cmd config set prefix "$env:APPDATA\npm"`
   `npm.cmd install -g pnpm`
   `$env:Path += ";$env:APPDATA\npm"`
4. 如果 `pnpm -v` 被 `PSSecurityException` 拦截，改用：
   `pnpm.cmd -v`
5. 持久化 PATH（只需一次）并重开 PowerShell：
   `$userPath=[Environment]::GetEnvironmentVariable("Path","User"); if($userPath -notlike "*$env:APPDATA\npm*"){[Environment]::SetEnvironmentVariable("Path","$userPath;$env:APPDATA\npm","User")}`

```bash
cd frontend
pnpm install
pnpm dev
```
前端地址：`http://localhost:5173`

## 4. 默认账号
统一密码：`password123`
- 用户：`test1@example.com`
- 用户：`test2@example.com`
- 商家：`merchant1@example.com`（星河数码旗舰店）
- 商家：`merchant2@example.com`（青禾智家生活馆）

## 5. 文档索引
- 后端说明：[backend/README.md](backend/README.md)
- 前端说明：[frontend/README.md](frontend/README.md)
- 客服说明：[rasa/README.md](rasa/README.md)

## 6. 跨电脑迁移检查清单
在另一台电脑拉取仓库后，按下面顺序检查，避免环境差异导致启动失败：

1. 安装并启动 Docker、Ollama、Node.js、Python 3.10+、uv。
2. 执行 `ollama pull qwen3.5:2b`，并确认 `ollama list` 里能看到该模型。
3. 复制并检查环境文件：
   - `backend/.env.sample -> backend/.env`
   - `rasa/.env.sample -> rasa/.env`
   - 两处都确认 `OLLAMA_MODEL=qwen3.5:2b`
4. 启动 PostgreSQL / Redis 并导入 `backend/db/init_db.sql` 与 `backend/db/seed_data.sql`。
5. 分别启动：
   - backend: `uv run uvicorn app.main:app --reload`
   - rasa server: `uv run rasa run ...`
   - rasa actions: `uv run rasa run actions ...`
   - frontend: `pnpm dev`
6. 冒烟验证：
   - 打开 `http://127.0.0.1:8000/docs`
   - 前端进入聊天页，发送一条普通咨询，确认能收到回复


## 7. 混合客服路由（Rasa Fast Router + NexAU Agent）

当前后端已支持混合客服路由：
- 高频确定性问题（高置信 intent）继续走 Rasa 规则链路。
- 复杂多轮/多目标问题（如补差价+退换货组合）切到内置 NexAU Agent Orchestrator（ReAct + Tool Calling）。

说明：
- `POST /api/v1/chat/send` 返回结构保持不变：`messages[].text/cards/actions`。
- 后端内部新增可观测字段：`trace_id` 与 `route`（仅日志/metadata 使用，不改变前端协议）。
- 写操作（下单/售后）仍通过二次确认草案机制，Agent 不会直接落库执行。

## 8. Multi-modal RAG（pgvector + 图片）

- 数据层升级为 `pgvector/pgvector:pg15`，向量与业务数据同库。
- 新增能力：
  - `POST /api/v1/chat/upload-image`：聊天单图上传（返回 `attachment_id`）。
  - `POST /api/v1/kb/index`：政策/说明书入库分块 + embedding。
  - `POST /api/v1/chat/send`：新增可选 `attachments: string[]`，旧请求保持兼容。
- Agent 新增工具：
  - `retrieve_policy_knowledge`
  - `retrieve_manual_knowledge`
  - `analyze_uploaded_image_vlm`（固定模型 `qwen3-vl:2b`）
- 返回协议保持不变：`messages[].text/cards/actions`。

## 9. Logistics Visualization & Shipping Experience Upgrade

### 9.1 What Changed
- Customer order detail now supports map-based logistics visualization (AMap JSAPI), with text fallback.
- Backend now enriches logistics with coordinates and route geo points.
- Merchant shipping panel now has slow-operation hints + animated loading states.

### 9.2 New Config
- Backend (`backend/.env`): `AMAP_WEB_KEY`, `AMAP_WEB_SIG`, `AMAP_TIMEOUT_MS`, `AMAP_QPS_LIMIT`
- Frontend (`frontend/.env`): `VITE_ENABLE_LOGISTICS_MAP`, `VITE_AMAP_JS_KEY`, `VITE_AMAP_SECURITY_JS_CODE`

### 9.3 Compatibility
- Existing API paths are unchanged.
- Existing response contract remains compatible; logistics object only adds optional fields.
- Existing after-sales stage rules are unchanged.

### 9.4 AMap env quick-reference
Backend (`backend/.env`):

```env
AMAP_WEB_KEY=your_amap_web_service_key
AMAP_WEB_SIG=optional_signature
AMAP_TIMEOUT_MS=3000
AMAP_QPS_LIMIT=5
```

Frontend (`frontend/.env`):

```env
VITE_ENABLE_LOGISTICS_MAP=true
VITE_AMAP_JS_KEY=your_amap_js_key
VITE_AMAP_SECURITY_JS_CODE=your_security_js_code
```

Usage split:
- `AMAP_WEB_KEY`: backend geocoding only.
- `VITE_AMAP_JS_KEY` + `VITE_AMAP_SECURITY_JS_CODE`: frontend JSAPI rendering.
