# Benchmark

`benchmark/` 是当前仓库 benchmark 的唯一正式入口，独立负责配置、数据集、执行器、结果归档、结果分析与 benchmark 相关测试。

## 目录结构

- `config/experiment.yaml`：benchmark 主配置，定义 profile、系统矩阵、知识库种子与默认结果目录。
- `config/labels.zh-Hans.json`：图表标题、系统名、场景名、失败标签与报告文案。
- `datasets/core/`、`datasets/extended/`：benchmark 数据集。
- `scripts/build_dataset.py`：重建数据集目录并生成 `manifest.json`。
- `scripts/run_benchmark.py`：执行 benchmark。
- `scripts/analyze_results.py`：分析一次 benchmark 结果，生成 CSV、PNG、Markdown 和 JSON 结论。
- `src/benchmark/`：benchmark 核心实现。
- `tests/`：benchmark 工程自己的测试。
- `results/<run_id>/`：每次运行的原始结果与分析产物。

## 环境初始化

```powershell
cd benchmark
uv sync
```

## Benchmark 对比对象

当前默认比较三套系统：

- `rasa_only`
- `rasa_plus_llm`
- `rasa_plus_lora_llm`

## 需要启动的服务

如果三套系统一起跑，至少需要以下服务全部可用：

| 服务 | 端口 | 用途 |
| --- | --- | --- |
| PostgreSQL | `5432` | 后端业务数据、聊天与记忆数据 |
| Redis | `6379` | 缓存、锁与辅助状态 |
| Ollama | `11434` | `rasa_plus_llm` 使用的基础 LLM |
| vLLM / OpenAI-compatible | `8002` | `rasa_plus_lora_llm` 使用的 LoRA 推理服务 |
| Rasa Action Server | `5055` | 主线 Rasa action |
| 主线 Rasa Server | `5005` | 后端 `rasa_plus_llm` / `rasa_plus_lora_llm` 共用 |
| Benchmark Rasa Server | `5006` | `rasa_only` 基线 |
| 后端基础版 | `8000` | `rasa_plus_llm` |
| 后端 LoRA 版 | `8001` | `rasa_plus_lora_llm` |

如果只跑部分系统，可以按需缩减：

- 只跑 `rasa_only`：需要 `5006`。
- 只跑 `rasa_plus_llm`：需要 `5432`、`6379`、`11434`、`5005`、`5055`、`8000`。
- 只跑 `rasa_plus_lora_llm`：需要 `5432`、`6379`、`8002`、`5005`、`5055`、`8001`。

运行 `rasa_plus_llm` 或 `rasa_plus_lora_llm` 时，benchmark 会使用商家账号自动调用后端 `/api/v1/kb/index` 写入 `config/experiment.yaml` 中配置的知识库种子文档。

## 推荐启动顺序

1. 启动 PostgreSQL 和 Redis。
2. 启动 Ollama 与 LoRA 推理服务。
3. 训练并启动主线 Rasa、benchmark Rasa、Action Server。
4. 启动后端基础版和后端 LoRA 版。
5. 回到 `benchmark/` 目录执行 benchmark。

## 启动命令

### 1. 初始化 PostgreSQL / Redis

Windows：

```powershell
cd backend
.\scripts\init_postgres.ps1
.\scripts\init_redis.ps1
```

Linux / macOS：

```bash
cd backend
./scripts/init_postgres.sh
./scripts/init_redis.sh
```

如果数据库已经初始化完成，确保 PostgreSQL 和 Redis 服务处于运行状态即可。

### 2. 启动 Ollama

先启动 Ollama 服务：

```powershell
ollama serve
```

首次运行需要拉取基础模型：

```powershell
ollama pull qwen3.5:2b
```

### 3. 启动 LoRA 推理服务

在 Linux / WSL 中启动 vLLM OpenAI-compatible 服务：

```bash
cd /mnt/d/Github/Rasa-EC-bot/LoRA
uv sync
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

### 4. 训练并启动主线 Rasa

训练主线模型：

```powershell
cd rasa
uv sync
uv run rasa train --config config.yml --domain domain.yml --data data/main
```

启动主线 Rasa Server：

```powershell
cd rasa
uv run rasa run --enable-api --cors "*" --credentials credentials.yml --endpoints endpoints.yml --port 5005
```

启动 Action Server：

```powershell
cd rasa
uv run rasa run actions --actions actions --port 5055
```

### 5. 训练并启动 benchmark `rasa_only`

训练 benchmark 基线：

```powershell
cd rasa
uv run rasa train `
  --config benchmark/rasa_only/config.yml `
  --domain benchmark/rasa_only/domain.yml `
  --data data/nlu.yml benchmark/rasa_only/rules.yml `
  --out models/benchmark_rasa_only
```

启动 benchmark 基线服务：

```powershell
cd rasa
uv run rasa run `
  --model models/benchmark_rasa_only `
  --enable-api `
  --cors "*" `
  --credentials credentials.yml `
  --endpoints endpoints.yml `
  --port 5006
```

### 6. 启动后端基础版 `rasa_plus_llm`

```powershell
cd backend
$env:AGENT_LLM_PROVIDER = "ollama"
$env:OLLAMA_BASE_URL = "http://127.0.0.1:11434"
$env:OLLAMA_MODEL = "qwen3.5:2b"
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 7. 启动后端 LoRA 版 `rasa_plus_lora_llm`

```powershell
cd backend
$env:AGENT_LLM_PROVIDER = "openai_compat"
$env:AGENT_LLM_BASE_URL = "http://127.0.0.1:8002/v1"
$env:AGENT_LLM_API_KEY = "EMPTY"
$env:AGENT_LLM_MODEL = "qwen3.5-2b-lora"
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8001
```

## 数据集构建

默认会读取 `benchmark/datasets/` 中的分层 JSONL，重新输出到目标目录并生成 `manifest.json`。

```powershell
cd benchmark
uv run python scripts/build_dataset.py
```

可选指定输出目录：

```powershell
cd benchmark
uv run python scripts/build_dataset.py --output-dir data/generated_datasets
```

## 运行 Benchmark

快速跑一轮：

```powershell
cd benchmark
uv run python scripts/run_benchmark.py --profile quick --verbose
```

标准 profile：

```powershell
cd benchmark
uv run python scripts/run_benchmark.py --profile standard
```

论文风格 profile：

```powershell
cd benchmark
uv run python scripts/run_benchmark.py --profile paper
```

常用覆盖参数：

- `--systems rasa_only,rasa_plus_llm`
- `--scenarios recommendation,order_query,transactional_action`
- `--results-root results`
- `--dataset-tier core`
- `--concurrency 1,2,4`

结果会默认写入 `benchmark/results/<run_id>/`。

## 分析结果

分析脚本读取一次 run 的结果目录，输出到对应 run 的 `analysis/` 子目录。

```powershell
cd benchmark
uv run python scripts/analyze_results.py --result-dir results/<run_id>
```

固定输出包括：

- `analysis/overall_metrics.csv`
- `analysis/scenario_leaders.csv`
- `analysis/failure_breakdown.csv`
- `analysis/latency_by_concurrency.csv`
- `analysis/business_vs_boundary.csv`
- `analysis/hallucination_breakdown.csv`
- `analysis/plots/*.png`
- `analysis/report.md`
- `analysis/conclusions.json`

## 运行测试

```powershell
cd benchmark
uv run python -m unittest discover -s tests -p "test_*.py"
```

## 相关说明

- benchmark 不再依赖 `backend/pyproject.toml`，必须从 `benchmark/` 目录单独初始化 uv 环境。
- benchmark 结果默认不再写入根目录 `tests/benchmark_results/`。
- 历史 `tests/benchmark_results/` 仅作为旧实验归档，不属于当前流程。
