# Rasa-EC-bot

本项目是一个可运行的电商客服实验系统，包含以下四部分：

- 电商前端：商品浏览、购物车、下单、订单、订单取消、收货信息修改、物流投诉、售后、商家中心
- 业务后端：FastAPI + PostgreSQL + Redis
- 客服系统：Rasa 规则链路 + 后端 Fast Router + Agent
- 论文实验：LoRA 微调、Ollama 部署、系统形态 benchmark

当前项目重点不再是“只跑通”，而是同时支持：

- 规则型客服与 LLM 客服对照
- 基础模型与 LoRA 模型对照
- 单纯 Rasa、单纯 LLM、Rasa + LLM 等系统形态对照
- 六类客服场景族、多轮会话、知识检索、图片售后、待确认动作 benchmark
- 最低可交付客服闭环已补齐：订单查询、物流查询、订单取消、收货信息修改、物流投诉、退换货售后

## 1. 项目结构

- `frontend/`：Vue 3 前端
- `backend/`：FastAPI 后端、数据库脚本、benchmark 脚本
- `rasa/`：Rasa 机器人、Action Server、纯 Rasa benchmark 配置
- `LoRA/`：LoRA 数据准备、训练、评估、兼容导出脚本
- `database/`：PostgreSQL / Redis 本地数据目录
- `tests/`：benchmark 规则与脚本测试
- `design.md`：当前项目架构设计说明

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

macOS（bash/zsh）：

```bash
cd backend
chmod +x scripts/init_postgres.sh scripts/init_postgres_macos.sh
./scripts/init_postgres_macos.sh
```

Fedora（bash）：

```bash
cd backend
chmod +x scripts/init_postgres.sh scripts/init_postgres_fedora.sh
./scripts/init_postgres_fedora.sh
```

说明：Windows PowerShell 不要再用 `Get-Content ... | docker exec -i psql ...` 导入中文 SQL，管道编码会把 UTF-8 中文种子数据写坏。初始化脚本改为 `docker cp + psql -f`，会自动创建 `rasa_ec_bot` 并安全导入 `db/init_db.sql` 与 `db/seed_data.sql`。
如需脚本化管理 Redis，请在 `backend` 目录使用 `scripts/start_redis*` 与 `scripts/init_redis*` 入口，具体见 `backend/README.md`。

### 5.3 启动后端

```bash
cd backend
# Windows: Copy-Item .env.sample .env
# Linux/macOS: cp .env.sample .env

uv sync
uv run uvicorn app.main:app --reload
```

默认地址：`http://127.0.0.1:8000`
后端启动时会自动读取 `backend/.env`，无需再手动把 `AMAP_WEB_KEY`、`REDIS_URL` 等变量提前注入 PowerShell 会话。

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

### 7.1 商家表单与物流地图增强

- 商家中心的店铺资料与商品录入已调整为“核心字段直出 + 高级字段折叠”的混合表单。
- 商品录入现在支持维护 `sku_code`，并继续兼容品牌、型号、评分、月销、标签、核心参数等比较字段。
- 商家发货时，后端已改为基于“发货地址 + 收货地址 + 高德 geocode”生成确定性物流站点与 `route_geo`，不再依赖本地 Ollama 规划路线。
- 历史订单若缺少坐标，订单详情读取时也会尝试按已保存地址现场补算地图点位。
- 若订单详情仍只显示文本轨迹，先检查后端启动日志中的 `AMAP_WEB_KEY` 生效情况，以及发货时输出的 AMap geocode 成功/失败日志。

### 7.2 历史浏览与个性化推荐

- 登录中的用户账号在访问商品详情页时，会自动写入服务端历史浏览记录。
- 历史浏览已改为独立页面入口，位于前端顶部导航“订单”右侧；即使没有记录，也会先显示空态占位页。
- 当前默认展示最近 8 条；服务端最多保留最近 20 个唯一商品。
- 客服推荐已统一接入历史浏览画像：
  - 简单推荐问法走 Rasa Action 时，会调用后端内部推荐接口。
  - 复杂推荐问法走 Agent 时，会调用同一套推荐 helper。
- 推荐排序规则为“显式类目/关键词优先，历史浏览偏好加权次之，再按销量、评分、上架时间排序”。
- 历史浏览只对登录客户账号生效，访客与商家账号不记录。

### 7.3 列表空态与分页升级

- 用户侧 `购物车` 与 `订单列表` 已统一为固定内容面板：无数据时保留同一块背景壳层，有数据后直接在原位置填充卡片，不再出现空态和内容态视觉断裂。
- 购物车改为前端分页，默认按页展示购物车条目，并保留右侧结算概览面板。
- 用户订单改为后端分页，接口与前端页码同步；实时刷新时会尽量保持当前页。
- 商家中心的 `订单 / 商品 / 地址 / 售后` 四个列表都已支持分页，并统一使用同一类列表壳层与空态占位。
- 商家订单页里的发货地址选择与地址列表分页解耦，避免默认地址因为地址分页而在发货操作中丢失。

## 8. 系统形态 Benchmark

当前论文实验统一使用“客服链路多轮会话 benchmark”，继续保持系统形态对照和 HTTP 黑盒评测原则，不直接调用内部业务函数，也不新增专用 benchmark API。

### 8.1 对照系统

- `rasa_only`
- `llm_base_ollama`
- `llm_lora_ollama`
- `rasa_plus_llm_base`
- `rasa_plus_llm_lora`

### 8.2 场景族

- `recommendation`
- `order_query`
- `logistics_query`
- `after_sales_query`
- `knowledge_and_multimodal`
- `transactional_action`

核心集固定覆盖 15 个人工编排客服子场景，扩展集在核心集基础上放大量级，用于压力实验，不作为论文主表唯一来源。

### 8.3 数据集与配置

- 脚本：`backend/scripts/build_system_benchmark_dataset.py`
- 执行器：`backend/scripts/run_system_benchmark.py`
- 主配置：`backend/benchmarks/experiment.yaml`
- 核心集目录：`backend/benchmarks/prompts/core/`
- 扩展集目录：`backend/benchmarks/prompts/extended/`
- 数据清单：`backend/benchmarks/prompts/dataset_manifest.json`
- 知识库种子：`backend/benchmarks/kb_seed/`

每条样本固定包含：

- `scenario_family`
- `scenario`
- `turns`
- `account`
- `required_capabilities`
- `preconditions`
- `expected_outcomes`
- `tags`

### 8.4 能力矩阵

`experiment.yaml` 为每个系统声明能力位：

- `supports_auth_queries`
- `supports_kb_policy`
- `supports_kb_manual`
- `supports_pending_action`
- `supports_pending_decision`
- `supports_attachments`
- `supports_image_analysis`
- `supports_cards`

样本会声明 `required_capabilities`。系统缺少所需能力时，结果记为 `unsupported/na`，不计入成功率，但会进入覆盖率统计和论文补充表。

### 8.5 Profile

- `quick`：使用 `core` 数据集，每个场景族至少覆盖一条会话，用于冒烟和联调。
- `standard`：使用 `extended` 数据集，带多并发层级，用于常规回归和压力观察。
- `paper`：使用 `core` 数据集、固定并发和重复次数，用于论文主实验。

### 8.6 生成数据集

```bash
uv run python backend/scripts/build_system_benchmark_dataset.py
```

### 8.7 运行快速实验

```bash
uv run python backend/scripts/run_system_benchmark.py \
  --profile quick \
  --systems rasa_only,llm_base_ollama,llm_lora_ollama,rasa_plus_llm_base,rasa_plus_llm_lora \
  --scenarios recommendation,order_query,logistics_query,after_sales_query,knowledge_and_multimodal,transactional_action \
  --verbose
```

说明：

- `rasa_plus_llm_base` 与 `rasa_plus_llm_lora` 会在运行前按能力矩阵自动尝试写入 benchmark 专用 KB 种子文档。
- 多轮样本支持 `login`、`upload_image`、`chat_send`、`pending_decision`、`sleep_until_expired` 五类步骤。
- `transactional_action` 场景会验证待确认草案、确认执行、取消执行和过期拦截。

### 8.8 结果目录

输出目录位于：

- `backend/benchmarks/results/<timestamp>_<profile>_system_benchmark/`

主要文件包括：

- `raw_events.jsonl`
- `turn_events.jsonl`
- `summary.csv`
- `scenario_quality.csv`
- `conversation_summary.csv`
- `capability_coverage.csv`
- `system_matrix.csv`
- `report.md`
- `paper_tables.md`

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

## 10. LoRA 训练产物与兼容导出

当前默认链路不会把 LoRA 导出到 Ollama。复杂客服 Agent 直接使用训练产物 `adapter/` 目录，由 `vLLM(OpenAI Compatible API) + PEFT runtime` 加载。

仓库中仍保留 `LoRA/scripts/export_ollama_model.py`，但它只用于历史兼容或单独实验，不属于当前默认部署和 benchmark 必需步骤。

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

## 13. LoRA 推理栈切换（vLLM + PEFT Runtime）

从本次版本开始，复杂客服 Agent 的 LoRA 推理默认不再依赖 Ollama 的 `ADAPTER` 注册路径，改为 `vLLM(OpenAI Compatible API) + PEFT adapter runtime`。

说明：
- `qwen3.5` 的 LoRA：走 vLLM。
- `qwen3-vl:2b` 与 `mxbai-embed-large`：继续走 Ollama。

### 13.1 启动 vLLM（加载 base + adapter）

```bash
# 以 LoRA 目录为例
cd LoRA

# 需要先安装 vllm（建议在 Linux/WSL + CUDA 环境）
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

### 13.2 后端 Agent 对接 vLLM

在 `backend/.env` 中配置：

```env
AGENT_LLM_PROVIDER=openai_compat
AGENT_LLM_BASE_URL=http://127.0.0.1:8002/v1
AGENT_LLM_MODEL=qwen3.5-2b-lora
AGENT_LLM_API_KEY=EMPTY
AGENT_LLM_TIMEOUT_SEC=45
```

完成后，后端复杂路由会通过 OpenAI 兼容接口调用 vLLM 的 LoRA 运行时。
