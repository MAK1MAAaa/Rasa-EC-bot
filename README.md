# Rasa-EC-bot

本项目是一个可运行的电商客服实验系统，包含以下四部分：

- 电商前端：商品浏览、购物车、下单、订单、售后、商家中心
- 业务后端：FastAPI + PostgreSQL + Redis
- 客服系统：Rasa 规则链路 + 后端 Fast Router + Agent
- 论文实验：LoRA 微调、Ollama 部署、系统形态 benchmark

当前项目重点不再是“只跑通”，而是同时支持：

- 规则型客服与 LLM 客服对照
- 基础模型与 LoRA 模型对照
- 单纯 Rasa、单纯 LLM、Rasa + LLM 等系统形态对照
- 推荐、售后、图片售后三类业务场景 benchmark

## 1. 项目结构

- `frontend/`：Vue 3 前端
- `backend/`：FastAPI 后端、数据库脚本、benchmark 脚本
- `rasa/`：Rasa 机器人、Action Server、纯 Rasa benchmark 配置
- `LoRA/`：LoRA 数据准备、训练、评估、导出到 Ollama
- `database/`：PostgreSQL / Redis 本地数据目录
- `tests/`：benchmark 规则与脚本测试
- `design.md`：当前项目架构设计说明
- `requirement.md`：需求说明

## 2. 技术栈

- 前端：Vue 3、Vite、Pinia、Vue Router、Tailwind CSS
- 后端：FastAPI、SQLModel、SQLAlchemy Async
- 数据库：PostgreSQL 15、pgvector
- 缓存：Redis 7
- 客服：Rasa Open Source、Rasa SDK
- 模型服务：Ollama
- 微调：LoRA
- 实验工具：系统形态接口级 benchmark

## 3. 文档索引

- 根架构说明：[design.md](design.md)
- 需求说明：[requirement.md](requirement.md)
- 后端说明：[backend/README.md](backend/README.md)
- 前端说明：[frontend/README.md](frontend/README.md)
- 客服说明：[rasa/README.md](rasa/README.md)
- LoRA 说明：[LoRA/README.md](LoRA/README.md)

## 4. 运行前准备

需要提前安装：

- Docker
- Ollama
- Python 3.10
- `uv`
- Node.js
- `pnpm`

建议先拉取基础模型：

```bash
ollama pull qwen3.5:2b
```

如果要跑图片售后与 RAG：

```bash
ollama pull qwen3-vl:2b
ollama pull mxbai-embed-large
```

如果已经有 LoRA 导出的 Ollama 模型，也一并确认：

```bash
ollama list
```

## 5. 快速启动

### 5.1 启动 PostgreSQL 与 Redis

Windows PowerShell：

```powershell
New-Item -ItemType Directory -Force .\database\pgdata, .\database\redisdata | Out-Null
$PGDATA_PATH = (Resolve-Path .\database\pgdata).Path
$REDISDATA_PATH = (Resolve-Path .\database\redisdata).Path

docker run --name rasa-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -v "${PGDATA_PATH}:/var/lib/postgresql/data" -d pgvector/pgvector:pg15
docker exec -it rasa-postgres psql -U postgres -c "CREATE DATABASE rasa_ec_bot;"

docker run --name rasa-redis -p 6379:6379 -v "${REDISDATA_PATH}:/data" -d redis:7 redis-server --appendonly yes
```

Linux / macOS：

```bash
mkdir -p ./database/pgdata ./database/redisdata

docker run --name rasa-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -v "$(pwd)/database/pgdata:/var/lib/postgresql/data" -d pgvector/pgvector:pg15
docker exec -it rasa-postgres psql -U postgres -c "CREATE DATABASE rasa_ec_bot;"

docker run --name rasa-redis -p 6379:6379 -v "$(pwd)/database/redisdata:/data" -d redis:7 redis-server --appendonly yes
```

### 5.2 初始化数据库

```powershell
cd backend
Get-Content -Raw -Encoding UTF8 db/init_db.sql | docker exec -i -e PGCLIENTENCODING=UTF8 rasa-postgres psql -U postgres -d rasa_ec_bot
Get-Content -Raw -Encoding UTF8 db/seed_data.sql | docker exec -i -e PGCLIENTENCODING=UTF8 rasa-postgres psql -U postgres -d rasa_ec_bot
```

### 5.3 启动后端

```bash
cd backend
# Windows: Copy-Item .env.sample .env
# Linux/macOS: cp .env.sample .env

uv sync
uv run uvicorn app.main:app --reload
```

默认地址：`http://127.0.0.1:8000`

### 5.4 启动 Rasa 与 Action Server

```bash
cd rasa
# Windows: Copy-Item .env.sample .env
# Linux/macOS: cp .env.sample .env

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

项目当前采用三层客服架构：

1. Rasa 负责高频、确定性问题
2. 后端 Fast Router 判断是否转入 Agent
3. Agent 负责复杂、多轮、跨领域、图片售后等问题

统一对外入口仍是：

- `POST /api/v1/chat/send`

图片售后采用两步：

- `POST /api/v1/chat/upload-image`
- `POST /api/v1/chat/send`

知识增强采用两类能力：

- pgvector 文档检索
- `qwen3-vl:2b` 图片分析

更完整的架构说明见：[design.md](design.md)

## 8. 系统形态 Benchmark

当前论文实验口径已经统一到系统形态 benchmark，不再使用旧版 provider/layer benchmark。

### 8.1 对照系统

- `rasa_only`
- `llm_base_ollama`
- `llm_lora_ollama`
- `rasa_plus_llm_base`
- `rasa_plus_llm_lora`

### 8.2 业务场景

- `recommendation`
- `after_sales`
- `image_after_sales`

### 8.3 关键脚本

- `backend/scripts/build_system_benchmark_dataset.py`
- `backend/scripts/run_system_benchmark.py`
- `backend/benchmarks/experiment.yaml`

### 8.4 生成数据集

```bash
uv run python backend/scripts/build_system_benchmark_dataset.py
```

### 8.5 运行快速实验

```bash
uv run python backend/scripts/run_system_benchmark.py \
  --profile quick \
  --systems rasa_only,llm_base_ollama,llm_lora_ollama,rasa_plus_llm_base,rasa_plus_llm_lora \
  --scenarios recommendation,after_sales,image_after_sales \
  --verbose
```

### 8.6 结果目录

输出目录位于：

- `backend/benchmarks/results/<timestamp>_<profile>_system_benchmark/`

主要文件包括：

- `raw_events.jsonl`
- `summary.csv`
- `scenario_quality.csv`
- `system_matrix.csv`
- `report.md`

## 9. 纯 Rasa 对照实例

`rasa_only` 不允许使用 `action_ollama_reply`，必须使用独立 benchmark 配置。

配置位置：

- `rasa/benchmark/rasa_only/config.yml`
- `rasa/benchmark/rasa_only/domain.yml`
- `rasa/benchmark/rasa_only/rules.yml`

训练并启动：

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

## 10. LoRA 导出到 Ollama

如果已经完成 LoRA 训练，可通过下面的脚本生成 Ollama `Modelfile` 并注册模型：

```bash
cd LoRA
uv run python scripts/export_ollama_model.py \
  --adapter-dir outputs/smoke_ec_faq_only/adapter \
  --base-model qwen3.5:2b \
  --model-name qwen3.5:2b-lora \
  --output-dir outputs/smoke_ec_faq_only/ollama_export
```

然后执行：

```bash
ollama create qwen3.5:2b-lora -f LoRA/outputs/smoke_ec_faq_only/ollama_export/Modelfile
```

## 11. 常用端口

- 后端：`8000`
- LoRA 后端对照实例：`8001`
- Rasa Server：`5005`
- 纯 Rasa benchmark 实例：`5006`
- Rasa Action Server：`5055`
- 前端：`5173`
- PostgreSQL：`5432`
- Redis：`6379`
- Ollama：`11434`

## 12. 当前 README 检查结论

当前仓库自有 README 的状态如下：

- 根目录 `README.md`：已修复
- `backend/README.md`：文件编码正常
- `frontend/README.md`：文件编码正常
- `rasa/README.md`：文件编码正常
- `LoRA/README.md`：文件编码正常
- `LoRA/data/dianshang_dataset/README.md`：文件编码正常

`node_modules`、`.venv`、模型输出目录下的第三方或自动生成 README 不纳入项目文档修复范围。
