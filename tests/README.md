# Tests And Benchmark Notes

本目录统一承载两类内容：

- Python 单元测试
- 系统级 benchmark 的实验规范、输入快照与结果归档

## 1. 当前测试文件说明

| 文件 | 类型 | 是否需要外部服务 | 说明 |
| --- | --- | --- | --- |
| `tests/test_product_recommendation_logic.py` | 单元测试 | 否 | 验证推荐词提取、显式类目识别、历史画像打分与推荐问句识别。 |
| `tests/test_system_benchmark.py` | 单元测试 | 否 | 验证 benchmark 数据集解析、会话评分、能力覆盖率、系统矩阵等纯逻辑函数。 |

结论：

- `tests/` 下现有两个测试都不要求先启动数据库、后端、Rasa、Ollama 或前端。
- 真正依赖多服务联调的是 `backend/scripts/run_system_benchmark.py`，它是实验执行器，不属于单元测试本身。

## 2. Benchmark 总览

当前仓库统一使用“客服链路多轮会话 benchmark”，用于论文级系统形态对照与接口黑盒评测。

原则：

- 只通过真实 HTTP 接口评测
- 不直接调用内部业务函数
- 不新增 benchmark 专用业务 API
- 将能力缺失与系统失败区分统计

实验入口脚本：

- 数据集构建：`backend/scripts/build_system_benchmark_dataset.py`
- 实验执行：`backend/scripts/run_system_benchmark.py`

## 3. Benchmark 数据与配置

### 3.1 关键目录

- 主配置：`backend/benchmarks/experiment.yaml`
- 核心数据集：`backend/benchmarks/prompts/core/`
- 扩展数据集：`backend/benchmarks/prompts/extended/`
- 数据清单：`backend/benchmarks/prompts/dataset_manifest.json`
- 图片资产：`backend/benchmarks/assets/`
- 知识库种子：`backend/benchmarks/kb_seed/`
- 默认结果目录：`backend/benchmarks/results/<timestamp>_<profile>_system_benchmark/`

### 3.2 对照系统

- `rasa_only`
- `llm_base_ollama`
- `llm_lora_ollama`
- `rasa_plus_llm_base`
- `rasa_plus_llm_lora`

### 3.3 场景族

- `recommendation`
- `order_query`
- `logistics_query`
- `after_sales_query`
- `knowledge_and_multimodal`
- `transactional_action`

说明：

- benchmark 只覆盖客服入口、图片上传、知识检索与待确认动作链路。
- 不扩展到全量电商 REST API。

### 3.4 样本结构

每条会话样本固定包含：

- `scenario_family`
- `scenario`
- `turns`
- `account`
- `required_capabilities`
- `preconditions`
- `expected_outcomes`
- `tags`

当前支持的 `turns` 步骤：

- `login`
- `upload_image`
- `chat_send`
- `pending_decision`
- `sleep_until_expired`

### 3.5 能力矩阵

系统能力位固定为：

- `supports_auth_queries`
- `supports_kb_policy`
- `supports_kb_manual`
- `supports_pending_action`
- `supports_pending_decision`
- `supports_attachments`
- `supports_image_analysis`
- `supports_cards`

判定规则：

- 样本通过 `required_capabilities` 声明最低要求
- 系统缺少能力时，该样本标记为 `unsupported/na`
- `unsupported/na` 不计入成功率和质量通过率
- `unsupported/na` 仍计入能力覆盖率与 `unsupported_rate`

### 3.6 Profile

- `quick`：`core` 数据集，单次并发，用于冒烟与联调
- `standard`：`extended` 数据集，多并发层级，用于常规回归与压力观察
- `paper`：`core` 数据集，固定并发与重复次数，用于论文主实验

## 4. 服务依赖与账号

### 4.1 直接依赖的服务

按 `backend/benchmarks/experiment.yaml` 当前配置，真实 benchmark 会直接访问：

| 系统名 | 端口 | 作用 |
| --- | --- | --- |
| `rasa_only` | `5006` | 纯 Rasa 对照系统，入口为 `/webhooks/rest/webhook` |
| `llm_base_ollama` | `11434` | 直接调用 Ollama `/api/chat`，模型为 `qwen3.5:2b` |
| `llm_lora_ollama` | `11434` | 直接调用 Ollama `/api/chat`，模型为 `qwen3.5:2b-lora` |
| `rasa_plus_llm_base` | `8000` | 后端混合客服实例 |
| `rasa_plus_llm_lora` | `8001` | 后端 LoRA 对照实例 |

### 4.2 间接依赖的服务

要完整跑通 `rasa_plus_llm_base` 与 `rasa_plus_llm_lora`，还需要：

| 服务 | 端口 | 原因 |
| --- | --- | --- |
| PostgreSQL | `5432` | 业务数据读取 |
| Redis | `6379` | 缓存与待确认动作状态 |
| Rasa Server | `5005` | 后端意图解析与规则链路 |
| Rasa Action Server | `5055` | Action 执行 |
| 前端开发服务器 | `5173` | benchmark metadata 固定携带 `frontend_base_url` |
| vLLM / OpenAI-compatible LLM | `8002` | LoRA Agent 默认指向该服务 |

### 4.3 Ollama 与模型准备

建议准备：

- `qwen3.5:2b`
- `qwen3.5:2b-lora`
- `qwen3-vl:2b`
- `mxbai-embed-large`

用途：

- `qwen3.5:2b`：基础聊天对照与基础后端实例
- `qwen3.5:2b-lora`：LoRA 对照系统
- `qwen3-vl:2b`：图片理解
- `mxbai-embed-large`：知识库 embedding

### 4.4 账号依赖

`experiment.yaml` 当前固定使用：

- 客户账号：`test1@example.com`
- 商家账号：`merchant1@example.com`
- 统一密码：`password123`

脚本会按需调用：

- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`

## 5. 标准启动顺序

建议按以下顺序准备实验环境。

### 5.1 数据库与缓存

先启动：

1. PostgreSQL `5432`
2. Redis `6379`

### 5.2 vLLM 实例

`vLLM` 负责为 LoRA Agent 提供 OpenAI-compatible 接口。

强调：

- `vLLM` 默认按 WSL/Linux + CUDA 环境运行
- Windows 原生 PowerShell 不作为默认推荐启动方式
- 后端 LoRA 对照实例 `8001` 依赖 `8002` 的 `vLLM` 服务先启动

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

### 5.3 后端基础实例

```powershell
cd backend
$env:AGENT_LLM_PROVIDER = "ollama"
$env:AGENT_LLM_BASE_URL = "http://127.0.0.1:11434"
$env:AGENT_LLM_MODEL = "qwen3.5:2b"
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 5.4 后端 LoRA 对照实例

先确认 WSL 中的 `vLLM` `8002` 已经启动，再启动该实例。

```powershell
cd backend
$env:AGENT_LLM_PROVIDER = "openai_compat"
$env:AGENT_LLM_BASE_URL = "http://127.0.0.1:8002/v1"
$env:AGENT_LLM_API_KEY = "EMPTY"
$env:AGENT_LLM_MODEL = "qwen3.5-2b-lora"
uv run uvicorn app.main:app --host 127.0.0.1 --port 8001
```

### 5.5 默认 Rasa 链路

```powershell
cd rasa
uv sync
uv run rasa train --config config.yml --domain domain.yml --data data
uv run rasa run --enable-api --cors "*" --credentials credentials.yml --endpoints endpoints.yml --port 5005
uv run rasa run actions --actions actions --port 5055
```

### 5.6 纯 Rasa benchmark 对照实例

`rasa_only` 不允许使用 `action_ollama_reply`，必须使用独立 benchmark 资产：

- `rasa/benchmark/rasa_only/config.yml`
- `rasa/benchmark/rasa_only/domain.yml`
- `rasa/benchmark/rasa_only/rules.yml`

训练与启动命令：

```powershell
cd rasa
uv run rasa train `
  --config benchmark/rasa_only/config.yml `
  --domain benchmark/rasa_only/domain.yml `
  --data data/nlu.yml benchmark/rasa_only/rules.yml `
  --out models/benchmark_rasa_only

uv run rasa run `
  --model models/benchmark_rasa_only `
  --enable-api `
  --cors "*" `
  --credentials credentials.yml `
  --endpoints endpoints.yml `
  --port 5006
```

Action Server 仍然复用现有 `actions.py`：

```powershell
cd rasa
uv run rasa run actions --actions actions --port 5055
```

### 5.7 前端

```powershell
cd frontend
pnpm install
pnpm dev
```

## 6. 数据集构建与实验运行

额外前提：

- 仓库根目录没有 `pyproject.toml`
- Python 侧运行环境以 `backend/pyproject.toml` 为准
- 因此测试和 benchmark 相关 Python 命令建议在 `backend/` 下通过 `uv` 执行

### 6.1 先跑 tests 侧单元测试

```powershell
Push-Location backend
$env:UV_CACHE_DIR = "d:\Github\Rasa-EC-bot\.uv-cache"
uv sync
uv run python -m unittest discover -s ..\tests -p "test_*.py"
Pop-Location
```

### 6.2 重建 benchmark 数据集

```powershell
Push-Location backend
$env:UV_CACHE_DIR = "d:\Github\Rasa-EC-bot\.uv-cache"
uv sync
uv run python scripts\build_system_benchmark_dataset.py
Pop-Location
```

### 6.3 快速实验

```powershell
Push-Location backend
$env:UV_CACHE_DIR = "d:\Github\Rasa-EC-bot\.uv-cache"
uv sync
uv run python scripts\run_system_benchmark.py `
  --profile quick `
  --systems rasa_only,llm_base_ollama,llm_lora_ollama,rasa_plus_llm_base,rasa_plus_llm_lora `
  --scenarios recommendation,order_query,logistics_query,after_sales_query,knowledge_and_multimodal,transactional_action `
  --results-root tests\benchmark_results `
  --verbose
Pop-Location
```

### 6.4 标准实验

```powershell
Push-Location backend
$env:UV_CACHE_DIR = "d:\Github\Rasa-EC-bot\.uv-cache"
uv sync
uv run python scripts\run_system_benchmark.py `
  --profile standard `
  --systems rasa_only,llm_base_ollama,llm_lora_ollama,rasa_plus_llm_base,rasa_plus_llm_lora `
  --scenarios recommendation,order_query,logistics_query,after_sales_query,knowledge_and_multimodal,transactional_action `
  --results-root tests\benchmark_results
Pop-Location
```

### 6.5 论文主实验

```powershell
Push-Location backend
$env:UV_CACHE_DIR = "d:\Github\Rasa-EC-bot\.uv-cache"
uv sync
uv run python scripts\run_system_benchmark.py `
  --profile paper `
  --systems rasa_only,llm_base_ollama,llm_lora_ollama,rasa_plus_llm_base,rasa_plus_llm_lora `
  --results-root tests\benchmark_results
Pop-Location
```

重要说明：

- `run_system_benchmark.py` 会把 `--results-root` 的相对路径按仓库根目录解析，不是按当前 PowerShell 工作目录解析。
- 因此在 `backend/` 目录中运行时，正确写法是 `tests\benchmark_results`。
- 如果写成 `..\tests\benchmark_results`，最终会落到仓库外层目录，例如 `D:\Github\tests\benchmark_results\...`。

## 7. tests 目录下的实验资产约定

本目录约定新增两类位置：

- `tests/benchmark_data/`
- `tests/benchmark_results/`

用途约定：

- `tests/benchmark_data/`：保存实验输入快照，例如 `experiment.yaml` 副本、数据集副本、运行参数说明、人工补充标注。
- `tests/benchmark_results/`：保存本地实验输出，例如 `raw_events.jsonl`、`summary.csv`、`report.md` 等。

版本控制约定：

- `tests/benchmark_results/` 默认只保留 `.gitkeep`
- 动态结果文件不提交
- `tests/benchmark_data/` 可提交必要的小型输入快照

建议每次正式实验建立独立目录，例如 `tests/benchmark_data/20260412_paper/`：

```powershell
$expId = "20260412_paper"
New-Item -ItemType Directory -Force "tests\benchmark_data\$expId" | Out-Null
Copy-Item backend\benchmarks\experiment.yaml "tests\benchmark_data\$expId\experiment.yaml"
Copy-Item backend\benchmarks\prompts "tests\benchmark_data\$expId\prompts" -Recurse -Force
```

## 8. 结果文件说明

| 文件 | 含义 |
| --- | --- |
| `raw_events.jsonl` | 会话级原始事件 |
| `turn_events.jsonl` | 逐步执行事件，适合排查登录、图片上传、待确认动作等链路 |
| `summary.csv` | 按系统、场景族、并发和重复次数聚合 |
| `scenario_quality.csv` | 按场景族统计失败原因 |
| `conversation_summary.csv` | 每条会话的成功与质量结果 |
| `capability_coverage.csv` | 能力覆盖率与 `unsupported/na` 统计 |
| `system_matrix.csv` | 论文主表候选结果 |
| `report.md` | 中文实验报告 |
| `paper_tables.md` | 论文可直接引用的表格 |

论文正文常用指标：

- `quality_pass_rate`
- `conversation_success_rate`
- `unsupported_rate`
- `p95_ms`

## 9. 冗余文件检查结论

当前检查结论如下：

- `tests/__pycache__/` 是解释器缓存，属于冗余产物，但 `.gitignore` 已覆盖。
- `tests/test_product_recommendation_logic.py` 与 `tests/test_system_benchmark.py` 都有明确用途，不冗余。
- `backend/benchmarks/prompts/`、`backend/benchmarks/kb_seed/`、`backend/benchmarks/assets/` 都被实际引用，不冗余。
- 根目录 `1.txt` 在仓库内没有代码或文档引用，属于高概率冗余候选，建议确认来源后再决定是否删除或迁移。

## 10. 执行边界

建议后续遵守以下边界：

- Python 逻辑测试放在 `tests/*.py`
- 实验输入快照放在 `tests/benchmark_data/<exp_id>/`
- 实验输出放在 `tests/benchmark_results/<run_id>/`
- 不要把新的 benchmark 输出继续写进仓库根目录或零散文本文件
## Benchmark 结果后分析

当 benchmark 运行结束后，可以针对任意已有结果目录生成更完整的图表和中文分析报告：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\scripts\analyze_benchmark_results.ps1 `
  -ResultDir .\tests\benchmark_results\20260413_065529_paper_system_benchmark
```

脚本会输出：

- `analysis/overall_metrics.csv`
- `analysis/scenario_leaders.csv`
- `analysis/failure_breakdown.csv`
- `analysis/concurrency_latency.csv`
- `analysis/*.svg`
- `detailed_analysis.md`

中文文案统一由 `tests/scripts/analyze_benchmark_results.zh-Hans.json` 管理。
这样可以稳定生成中文 CSV 表头、中文 Markdown 报告和中文 SVG 图标题，避免再次出现英文模板或编码污染。
