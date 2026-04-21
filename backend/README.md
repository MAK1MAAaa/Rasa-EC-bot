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

### Tailscale 跨机演示模板

如果采用“MBA 跑前端/后端/Rasa，台式机跑 Postgres/Redis/Ollama/vLLM”的演示拓扑：

- 仓库根目录下的 `backend/.env` 已按这个拓扑预填好一份模板。
- 当前默认启用的是 MagicDNS 写法，远程主机占位符是 `__TAILSCALE_DESKTOP_MAGICDNS__`。
- 同一份文件里保留了 Tailnet IP 备选行，占位符是 `__TAILSCALE_DESKTOP_IP__`。
- 本机链路保持不变：`RASA_SERVER_URL=http://127.0.0.1:5005`、`FRONTEND_BASE_URL=http://localhost:5173`。
- 远程链路改到台式机：`DATABASE_URL`、`REDIS_URL`、`OLLAMA_BASE_URL`、`AGENT_LLM_BASE_URL`。
- `RASA_INTERNAL_TOKEN` 需要和 `rasa/.env` 保持一致。
- 当前仓库里的本地 `backend/.env` 已切到你提供的台式机 Tailnet IP `100.110.132.72`；如果之后改用 MagicDNS，只需要把对应行切回去。

### 台式机端调试清单

如果台式机负责跑 Postgres、Redis、Ollama、vLLM，建议按下面检查：

1. PostgreSQL

- 继续使用 `-p 5432:5432` 的 Docker 暴露方式即可。
- 如果启用了 Windows 防火墙，只放行给 MBA 的 Tailnet IP `100.65.236.105` 或 Tailscale 网卡。

2. Redis

- `backend/.env.sample` 新增了 `REDIS_BIND_ADDRESS`、`REDIS_PROTECTED_MODE`、`REDIS_PASSWORD`。
- 默认值仍是本地安全模式：`REDIS_PROTECTED_MODE=yes`，不影响原来的 Windows 单机运行。
- 如果要让 MBA 通过 Tailscale 访问台式机 Redis，建议在台式机 `backend/.env` 里显式设置：

```powershell
REDIS_BIND_ADDRESS=0.0.0.0
REDIS_PROTECTED_MODE=no
REDIS_PASSWORD=改成你自己的强密码
```

- 然后重新运行：

```powershell
cd backend
.\scripts\start_redis.ps1 -Recreate
.\scripts\init_redis.ps1
```

- 如果设置了 `REDIS_PASSWORD`，MBA 侧 `backend/.env` 的 `REDIS_URL` 也要改成：

```text
redis://:你的密码@100.110.132.72:6379/0
```

3. Ollama

- 台式机上需要让 Ollama 监听非 `127.0.0.1` 地址，否则 MBA 无法访问：

```powershell
$env:OLLAMA_HOST="0.0.0.0:11434"
ollama serve
```

4. vLLM

- 台式机上的 vLLM 继续保持 `--host 0.0.0.0 --port 8002` 即可。

5. 防火墙

- 只放行 `11434`、`8002`、`5432`、`6379` 给 `100.65.236.105` 或 Tailscale 网卡。
- 如果不需要 MBA 访问 Redis，可以保留 `REDIS_PROTECTED_MODE=yes`，后端会在 Redis 不可用时降级为无缓存模式。

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

脚本现在会读取这些可选变量：

- `REDIS_BIND_ADDRESS`
- `REDIS_PROTECTED_MODE`
- `REDIS_PASSWORD`

默认值保持原来的本地安全模式；只有你显式关闭 `REDIS_PROTECTED_MODE` 或设置密码时，才会改变跨机器访问行为。

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
6. 启动后端基础版或 LoRA 版。

## 说明

- `backend/prompts/*.md` 是当前后端使用的正式 prompt 来源。
- 商品推荐链路会解析用户消息里的显式预算、颜色和部分规格词，并优先过滤不满足这些硬约束的候选商品。
- 聊天记忆快照刷新链路会显式转换 `session_id` 的 SQL 参数类型，避免 asyncpg 在原生 SQL 中因 `text` / `varchar` 推断冲突而报错。
- `backend/data/chat_uploads/` 属于运行时上传产物目录，不再纳入版本控制。
- Linux 和 macOS 现在统一复用同一份 `*.sh` 脚本，不再保留额外的 `*_fedora.sh` / `*_macos.sh` 包装层。
- Benchmark 的完整启动顺序、基线重置和运行方法只在 [`benchmark/README.md`](../benchmark/README.md) 中维护。
