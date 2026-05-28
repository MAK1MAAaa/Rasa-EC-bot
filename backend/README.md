# Backend

`backend/` 提供 FastAPI 服务，负责认证、商品与订单接口、聊天路由、Rasa/LLM 协同、服务端记忆、知识库和附件处理。

## 目录

| 路径 | 说明 |
| --- | --- |
| `app/main.py` | FastAPI 入口 |
| `app/llm_client.py` | 主备 LLM 调用与失败切换 |
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
- 可选：本地 PostgreSQL / Redis。如果不用 Docker，只要 `.env` 指向正确实例即可。

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
- `FRONTEND_BASE_URL`
- `BACKEND_CORS_ALLOW_ORIGINS`
- `OLLAMA_BASE_URL`
- `AGENT_LLM_PROVIDER`
- `AGENT_LLM_BASE_URL`
- `AGENT_LLM_MODEL`

### LLM 主备切换

后端现在支持“主用 LLM 失败时自动切换到后备 API”。默认行为：

- 主用链路继续读取 `AGENT_LLM_PROVIDER`、`AGENT_LLM_BASE_URL`、`AGENT_LLM_MODEL`、`AGENT_LLM_API_KEY`、`AGENT_LLM_TIMEOUT_SEC`。
- 后备链路读取 `AGENT_LLM_FALLBACK_PROVIDER`、`AGENT_LLM_FALLBACK_BASE_URL`、`AGENT_LLM_FALLBACK_MODEL`、`AGENT_LLM_FALLBACK_API_KEY`、`AGENT_LLM_FALLBACK_TIMEOUT_SEC`。
- 主服务出现 `500/502/503/504`、`408`、`429`、超时、连接失败、空响应或无效响应时，会自动切到后备链路。
- 主服务如果返回明确的 `4xx` 配置错误，默认不会盲目切后备，避免掩盖错误配置。
- `AGENT_LLM_PROVIDER` 和 `AGENT_LLM_FALLBACK_PROVIDER` 支持 `ollama`、`openai_compat`；`openai` 和 `deepseek` 会作为别名按 OpenAI-compatible 协议处理。

示例：主用 Ollama，本机失败时切到 OpenAI-compatible API。

```env
OLLAMA_BASE_URL=http://127.0.0.1:11434

AGENT_LLM_PROVIDER=ollama
AGENT_LLM_BASE_URL=http://127.0.0.1:11434
AGENT_LLM_MODEL=qwen3.5:2b-lora
AGENT_LLM_TIMEOUT_SEC=45

AGENT_LLM_FALLBACK_PROVIDER=openai_compat
AGENT_LLM_FALLBACK_BASE_URL=http://127.0.0.1:8002/v1
AGENT_LLM_FALLBACK_MODEL=qwen3.5-2b-lora
AGENT_LLM_FALLBACK_API_KEY=EMPTY
AGENT_LLM_FALLBACK_TIMEOUT_SEC=45
```

## 当前推荐拓扑

当前仓库按“所有服务都跑在当前 Windows 主机”来演示更稳妥：

- 前端、后端、Rasa、Redis、PostgreSQL、Ollama、vLLM 都启动在同一台 Windows 上。
- 另一台电脑只通过 Tailscale 访问这台 Windows 主机的前端地址：`http://<本机 Tailnet IP>:5173`。
- 后端、Rasa、Ollama、vLLM、Redis、PostgreSQL 之间都继续走 `127.0.0.1`，不要为了演示把它们改成 Tailnet IP。

这套拓扑下：

- `OLLAMA_BASE_URL` 应保持 `http://127.0.0.1:11434`。
- `RASA_SERVER_URL` 应保持 `http://127.0.0.1:5005`。
- `REDIS_URL` 应保持 `redis://127.0.0.1:6379/0`。
- `DATABASE_URL` 应保持指向本机数据库。
- `FRONTEND_BASE_URL` 建议改成对外演示地址，例如 `http://100.110.132.72:5173`，这样聊天卡片里的商品/订单链接会跳到远端用户可访问的地址，而不是 `localhost`。
- `BACKEND_CORS_ALLOW_ORIGINS` 建议至少包含：

```env
BACKEND_CORS_ALLOW_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://100.110.132.72:5173
```

## Windows + Tailscale 检查结论

当前机器上，如果你的 Tailscale 网卡已经是 `Private`，而且 Windows 防火墙的 `Private/Public` 配置档本身就是关闭状态，那么“Ollama 被拦截”通常不是防火墙主因，更常见的是：

- Ollama 根本没启动。
- Ollama 启动了，但你把业务链路错误地改成了 Tailnet IP。
- 前端能访问，但后端链接仍然生成了 `localhost`。

如果当前方案是“只让另一台电脑访问前端”，那就不要暴露 Ollama 端口；让它继续只监听本机即可。

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

脚本会根据 `DATABASE_URL` 创建数据库、执行 [`init_db.sql`](db/init_db.sql) 和 [`seed_data.sql`](db/seed_data.sql)。

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

脚本会读取这些可选变量：

- `REDIS_BIND_ADDRESS`
- `REDIS_PROTECTED_MODE`
- `REDIS_PASSWORD`

默认值保持本机安全模式；只有你显式关闭 `REDIS_PROTECTED_MODE` 或设置密码时，才会改变跨机器访问行为。

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

1. 配置 `backend/.env`。
2. 启动 PostgreSQL。
3. 执行 `init_postgres.ps1` 或 `init_postgres.sh`。
4. 启动 Redis。
5. 执行 `init_redis.ps1` 或 `init_redis.sh`。
6. 启动 Rasa。
7. 启动后端基础版或 LoRA 版。
8. 启动前端 Vite 开发服务。
9. 在另一台电脑访问 `http://<本机 Tailnet IP>:5173`。

## 说明

- `backend/prompts/*.md` 是当前后端使用的正式 prompt 来源。
- 商品推荐链路会解析用户消息里的显式预算、颜色和部分规格词，并优先过滤不满足硬约束的候选商品；聊天推荐默认只返回 1 个最匹配商品，内部推荐接口仍支持显式 `limit` 获取多条结果。
- 登录用户的服务端记忆以 PostgreSQL 为主存储，Markdown 文件落在 `backend/data/chat_memory/`，仅作为派生产物。
- 聊天待确认动作持久化在 `chat_pending_actions`，过期时间统一按 UTC 归一化后比较，兼容 PostgreSQL `TIMESTAMP WITH TIME ZONE` 返回的带时区时间。
- 聊天下单和修改地址草案支持 `地址:`、`地址为`、`地址是`、`收货地址为` 等表达，避免漏提取地址后误用最近订单地址。
- 知识库索引接口的请求字段仍使用 `metadata`，后端模型内部使用 `metadata_` 承载，避免和 SQLModel 基类属性重名产生启动 warning。
