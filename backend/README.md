# Backend

`backend/` 提供 FastAPI 服务，负责认证、商品与订单接口、聊天路由、Rasa/LLM 协同、服务端记忆、知识库与附件处理。

## 目录

| 路径 | 说明 |
| --- | --- |
| `app/main.py` | FastAPI 入口 |
| `app/database.py` | PostgreSQL 连接与会话 |
| `app/cache.py` | Redis 访问 |
| `app/models.py` | SQLModel / Pydantic 模型 |
| `app/prompts.py` | 外置 prompt 加载 |
| `db/init_db.sql` | 建表脚本 |
| `db/seed_data.sql` | 基础种子数据 |
| `scripts/init_postgres.ps1` | Windows 下的 PostgreSQL 初始化脚本 |
| `scripts/init_postgres.sh` | macOS / Linux 通用 PostgreSQL 初始化脚本 |
| `scripts/start_redis.ps1` | Windows 下的 Redis Docker 启动脚本 |
| `scripts/start_redis.sh` | macOS / Linux 通用 Redis Docker 启动脚本 |
| `scripts/init_redis.ps1` | Windows 下的 Redis 初始化脚本 |
| `scripts/init_redis.sh` | macOS / Linux 通用 Redis 初始化脚本 |
| `prompts/` | agent prompt 文件 |

## 前置依赖

- Python 3.10
- `uv`
- Docker
- 可选：本地 PostgreSQL / Redis。如果不使用 Docker，只要 `.env` 指向正确实例即可。

## 环境变量

首次使用建议先复制模板：

```powershell
cd backend
Copy-Item .env.sample .env
```

```bash
cd backend
cp .env.sample .env
```

至少确认这些变量：

- `DATABASE_URL`
- `REDIS_URL`
- `RASA_SERVER_URL`
- `OLLAMA_BASE_URL`
- `AGENT_LLM_PROVIDER`
- `AGENT_LLM_BASE_URL`
- `AGENT_LLM_MODEL`

## 安装依赖

```powershell
cd backend
uv sync
```

```bash
cd backend
uv sync
```

## PostgreSQL

### 启动

仓库里没有单独的 PostgreSQL 启动脚本，推荐直接用 Docker：

```powershell
docker run --name rasa-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_USER=postgres -e POSTGRES_DB=postgres -p 5432:5432 -d postgres:16
```

```powershell
docker start rasa-postgres
```

```bash
docker run --name rasa-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_USER=postgres -e POSTGRES_DB=postgres -p 5432:5432 -d postgres:16
```

```bash
docker start rasa-postgres
```

### 初始化

Windows：

```powershell
cd backend
.\scripts\init_postgres.ps1
```

Linux / macOS：

```bash
cd backend
bash scripts/init_postgres.sh
```

脚本会根据 `DATABASE_URL` 创建数据库、执行 [`init_db.sql`](/D:/Github/Rasa-EC-bot/backend/db/init_db.sql) 和 [`seed_data.sql`](/D:/Github/Rasa-EC-bot/backend/db/seed_data.sql)。

## Redis

### 启动

Windows：

```powershell
cd backend
.\scripts\start_redis.ps1
```

Linux / macOS：

```bash
cd backend
bash scripts/start_redis.sh
```

### 初始化

Windows：

```powershell
cd backend
.\scripts\init_redis.ps1
```

Linux / macOS：

```bash
cd backend
bash scripts/init_redis.sh
```

## 启动服务

### 基础版

```powershell
cd backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```bash
cd backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### LoRA 版

```powershell
cd backend
$env:AGENT_LLM_PROVIDER = "openai_compat"
$env:AGENT_LLM_BASE_URL = "http://127.0.0.1:8002/v1"
$env:AGENT_LLM_API_KEY = "EMPTY"
$env:AGENT_LLM_MODEL = "qwen3.5-2b-lora"
uv run uvicorn app.main:app --host 127.0.0.1 --port 8001
```

```bash
cd backend
export AGENT_LLM_PROVIDER=openai_compat
export AGENT_LLM_BASE_URL=http://127.0.0.1:8002/v1
export AGENT_LLM_API_KEY=EMPTY
export AGENT_LLM_MODEL=qwen3.5-2b-lora
uv run uvicorn app.main:app --host 127.0.0.1 --port 8001
```

## 建议顺序

1. 配置 [`backend/.env`](/D:/Github/Rasa-EC-bot/backend/.env)。
2. 启动 PostgreSQL。
3. 执行 `init_postgres.ps1` 或 `init_postgres.sh`。
4. 启动 Redis。
5. 执行 `init_redis.ps1` 或 `init_redis.sh`。
6. 启动后端基础版或 LoRA 版。

## 说明

- `backend/prompts/*.md` 是当前后端使用的正式 prompt 来源。
- 商品推荐链路会解析用户消息里的显式预算、颜色和部分规格词，并优先过滤不满足这些硬约束的候选商品。
- 聊天记忆快照刷新链路会显式转换 `session_id` 的 SQL 参数类型，避免 asyncpg 在原生 SQL 中因 `text` / `varchar` 推断冲突而报错。
- `backend/data/chat_uploads/` 属于运行时上传产物目录，不再纳入版本控制。
- Linux 和 macOS 现在统一复用同一份 `*.sh` 脚本，不再保留额外的 `*_fedora.sh` / `*_macos.sh` 包装层。
- Benchmark 的完整启动顺序、基线重置和运行方法只在 [`benchmark/README.md`](/D:/Github/Rasa-EC-bot/benchmark/README.md) 中维护。
