# Rasa-EC-bot

本项目是一个可运行的电商客服实验系统，覆盖用户商城、商家后台、Rasa 规则链路、后端 Agent 路由、LoRA 模型推理与论文实验支撑。

当前重点不是单一模块演示，而是完整的客服闭环：

- 规则客服与 LLM 客服对照
- 基础模型与 LoRA 模型对照
- 订单、物流、售后、推荐、多轮会话、图片售后等统一链路
- 前后端联调、知识检索、待确认动作与实验数据归档

## 1. 项目结构

- `frontend/`：Vue 3 前端
- `backend/`：FastAPI 后端、数据库脚本、客服路由、业务接口
- `rasa/`：Rasa Server、Action Server、纯规则链路配置
- `LoRA/`：LoRA 数据准备、训练、推理相关说明
- `tests/`：单元测试与 benchmark 实验规范
- `database/`：PostgreSQL / Redis 本地数据目录
- `design.md`：项目架构设计说明

## 2. 文档索引

- 架构设计：[design.md](design.md)
- 后端说明：[backend/README.md](backend/README.md)
- 前端说明：[frontend/README.md](frontend/README.md)
- Rasa 说明：[rasa/README.md](rasa/README.md)
- LoRA 说明：[LoRA/README.md](LoRA/README.md)
- 测试与 benchmark 实验规范：[tests/README.md](tests/README.md)

说明：

- benchmark 的数据集、运行方式、结果目录、纯 Rasa 对照实例、论文表格产物，现已统一迁移到 `tests/README.md`。
- 根 README 仅保留项目总览与基础启动入口。

## 3. 技术栈

- 前端：Vue 3、Vite、Pinia、Vue Router、Tailwind CSS
- 后端：FastAPI、SQLModel、SQLAlchemy Async
- 数据库：PostgreSQL 15、pgvector
- 缓存：Redis 7
- 客服：Rasa Open Source、Rasa SDK
- 模型服务：Ollama、vLLM
- 微调：LoRA

## 4. 运行前准备

需要预先安装：

- Docker
- Ollama
- Python 3.10
- `uv`
- Node.js
- `pnpm`

建议先准备基础模型：

```bash
ollama pull qwen3.5:2b
```

如果要跑图片售后与知识检索链路，再准备：

```bash
ollama pull qwen3-vl:2b
ollama pull mxbai-embed-large
```

## 5. 快速启动

### 5.1 启动 PostgreSQL 与 Redis

Windows PowerShell：

```powershell
New-Item -ItemType Directory -Force .\database\pgdata, .\database\redisdata | Out-Null
$PGDATA_PATH = (Resolve-Path .\database\pgdata).Path
$REDISDATA_PATH = (Resolve-Path .\database\redisdata).Path

docker run --name rasa-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -v "${PGDATA_PATH}:/var/lib/postgresql/data" -d pgvector/pgvector:pg15
do {
    Start-Sleep -Seconds 1
    docker exec rasa-postgres pg_isready -U postgres | Out-Null
} until ($LASTEXITCODE -eq 0)
docker exec rasa-postgres psql -U postgres -c "CREATE DATABASE rasa_ec_bot;"

docker run --name rasa-redis -p 6379:6379 -v "${REDISDATA_PATH}:/data" -d redis:7 redis-server --appendonly yes
```

Linux / macOS：

```bash
mkdir -p ./database/pgdata ./database/redisdata

docker run --name rasa-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -v "$(pwd)/database/pgdata:/var/lib/postgresql/data" -d pgvector/pgvector:pg15
until docker exec rasa-postgres pg_isready -U postgres >/dev/null 2>&1; do
  sleep 1
done
docker exec rasa-postgres psql -U postgres -c "CREATE DATABASE rasa_ec_bot;"

docker run --name rasa-redis -p 6379:6379 -v "$(pwd)/database/redisdata:/data" -d redis:7 redis-server --appendonly yes
```

### 5.2 初始化数据库

Windows PowerShell：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\init_postgres.ps1
```

macOS：

```bash
cd backend
chmod +x scripts/init_postgres.sh scripts/init_postgres_macos.sh
./scripts/init_postgres_macos.sh
```

Fedora：

```bash
cd backend
chmod +x scripts/init_postgres.sh scripts/init_postgres_fedora.sh
./scripts/init_postgres_fedora.sh
```

### 5.3 启动后端

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

默认地址：`http://127.0.0.1:8000`

### 5.4 启动 Rasa 与 Action Server

```bash
cd rasa
uv sync
uv run rasa train --config config.yml --domain domain.yml --data data
uv run rasa run --enable-api --cors "*" --credentials credentials.yml --endpoints endpoints.yml --port 5005
uv run rasa run actions --actions actions --port 5055
```

### 5.5 启动前端

```bash
cd frontend
pnpm install
pnpm dev
```

默认地址：`http://localhost:5173`

## 6. 默认账号

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

## 7. 当前架构口径

项目当前采用三层客服链路：

1. Rasa 负责高频、确定性问题
2. 后端 Fast Router 判断是否切入 Agent
3. Agent 负责复杂、多轮、跨领域与图片售后问题

统一对外入口仍然是：

- `POST /api/v1/chat/send`

相关链路说明：

- 图片售后走 `POST /api/v1/chat/upload-image` + `POST /api/v1/chat/send`
- 待确认动作走 `POST /api/v1/chat/pending-action/decision`
- 复杂 LoRA Agent 默认通过 `vLLM(OpenAI-compatible API)` 提供推理能力

## 8. LoRA 与 vLLM

当前默认链路不会把 LoRA adapter 导出为 Ollama 模型。复杂客服 Agent 直接使用训练产物 `adapter/`，由 `vLLM + PEFT runtime` 加载。

强调：

- `vLLM` 默认按 WSL/Linux + CUDA 环境运行
- Windows 原生 PowerShell 不作为默认推荐启动方式
- 后端 LoRA 对照实例 `8001` 依赖 `8002` 的 `vLLM` 服务

参考启动方式：

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

后端如需指向该实例，在 `backend/.env` 中配置：

```env
AGENT_LLM_PROVIDER=openai_compat
AGENT_LLM_BASE_URL=http://127.0.0.1:8002/v1
AGENT_LLM_MODEL=qwen3.5-2b-lora
AGENT_LLM_API_KEY=EMPTY
AGENT_LLM_TIMEOUT_SEC=45
```

更完整的训练与推理说明见 [LoRA/README.md](LoRA/README.md) 与 [backend/README.md](backend/README.md)。

## 9. 常用端口

- 后端：`8000`
- Rasa Server：`5005`
- Rasa Action Server：`5055`
- 前端：`5173`
- PostgreSQL：`5432`
- Redis：`6379`
- Ollama：`11434`
- vLLM：`8002`

说明：

- `8001` 与 `5006` 属于对照实验常用端口，已统一放到 [tests/README.md](tests/README.md) 说明。

## 10. 说明

- benchmark 相关内容已统一迁移到 [tests/README.md](tests/README.md)。
- `backend/README.md` 关注后端能力、接口、环境变量与运行方式。
- `LoRA/README.md` 关注训练产物、推理服务与模型侧说明。
