# Rasa-EC-bot

一个可运行的电商平台示例，集成了：
- 用户端商城（浏览、筛选、购物车、下单、订单、售后）
- 商家端控制台（商品管理、发货地址、手动发货、售后处理）
- 智能客服（Rasa + 本地 Ollama `qwen3.5:2b`）
- Redis 缓存层（商品筛选元数据 + 客服订单/物流/售后汇总）

## 1. 项目结构
- `backend/`: FastAPI 后端与数据库脚本
- `frontend/`: Vue 3 前端
- `rasa/`: Rasa 对话模型与 Action Server
- `database/`: Docker 持久化目录（PostgreSQL/Redis）
- `requirement.md`: 当前版本需求说明（已同步实现状态）

## 2. 技术栈
- Frontend: Vue 3 + Vite + Pinia + Tailwind CSS
- Backend: FastAPI + SQLModel + PostgreSQL
- Chatbot: Rasa + Rasa SDK Actions + Ollama
- Cache: Redis

## 3. 快速启动
### 3.1 启动数据库与缓存
Windows PowerShell（在项目根目录执行）：
```powershell
New-Item -ItemType Directory -Force .\database\pgdata, .\database\redisdata | Out-Null
$PGDATA_PATH = (Resolve-Path .\database\pgdata).Path
$REDISDATA_PATH = (Resolve-Path .\database\redisdata).Path

# PostgreSQL
docker run --name rasa-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -v "${PGDATA_PATH}:/var/lib/postgresql/data" -d postgres:15
docker exec -it rasa-postgres psql -U postgres -c "CREATE DATABASE rasa_ec_bot;"

# Redis
docker run --name rasa-redis -p 6379:6379 -v "${REDISDATA_PATH}:/data" -d redis:7 redis-server --appendonly yes
```

Linux / macOS（在项目根目录执行）：
```bash
mkdir -p ./database/pgdata ./database/redisdata

# PostgreSQL
docker run --name rasa-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -v "$(pwd)/database/pgdata:/var/lib/postgresql/data" -d postgres:15
docker exec -it rasa-postgres psql -U postgres -c "CREATE DATABASE rasa_ec_bot;"

# Redis
docker run --name rasa-redis -p 6379:6379 -v "$(pwd)/database/redisdata:/data" -d redis:7 redis-server --appendonly yes
```

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

