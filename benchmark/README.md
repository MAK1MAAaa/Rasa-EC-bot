# Benchmark

`benchmark/` 是系统 benchmark 的唯一正式入口。环境准备、数据集、执行、结果分析和测试都以本 README 为准。

## 当前规则

- 正式结论只输出 `shared_core` 和 `agent_extension` 双榜。
- 正式排序使用去重后的样本级指标，不再直接按原始会话行数排名。
- `quick` 默认使用 `sampled` 抽样模式，只用于 smoke。
- `standard` 和 `paper` 默认使用 `all_unique`，目标是覆盖全部唯一样本。
- `paper_only` 样本只会在 `--profile paper` 中执行。
- `repeatable: false` 样本只在 `repeat = 1` 时执行一次。
- `analysis/failure_breakdown.csv` 使用互斥的 `primary_failure_reason`。
- `analysis/failure_flags.csv` 保留多标签诊断统计。

## 目录

| 路径 | 说明 |
| --- | --- |
| `config/experiment.yaml` | benchmark 主配置 |
| `config/labels.zh-Hans.json` | 报告标签与图表文案 |
| `datasets/core/` | `quick` 默认数据集 |
| `datasets/extended/` | `standard` / `paper` 默认数据集 |
| `datasets/manifest.json` | 数据集输出与统计 |
| `kb_seed/` | 写入后端知识库的种子文档 |
| `sql/reset_benchmark_state.sql` | 基线状态重置 SQL |
| `scripts/build_dataset.py` | 重建数据集与 manifest |
| `scripts/run_benchmark.py` | 执行 benchmark |
| `scripts/analyze_results.py` | 分析一次运行结果 |
| `src/benchmark/` | benchmark 核心实现 |
| `tests/` | benchmark 单测 |

## 从零开始跑一轮 Benchmark

### 1. 准备环境变量

先确认以下文件已经按本机环境配置完成：

- [`backend/.env`](/D:/Github/Rasa-EC-bot/backend/.env)
- [`rasa/.env`](/D:/Github/Rasa-EC-bot/rasa/.env)

至少检查：

- `backend/.env` 中的 `DATABASE_URL`
- `backend/.env` 中的 `REDIS_URL`
- `backend/.env` 中的 `RASA_SERVER_URL`
- `backend/.env` 中的 `OLLAMA_BASE_URL` / `AGENT_LLM_BASE_URL`
- `rasa/.env` 中的 `OLLAMA_BASE_URL`

### 2. 安装依赖

```powershell
cd benchmark
uv sync
```

同时安装主服务依赖：

```powershell
cd backend
uv sync

cd ..\rasa
uv sync
```

### 3. 启动 PostgreSQL 和 Redis

PostgreSQL：

```powershell
docker run --name rasa-postgres `
  -e POSTGRES_PASSWORD=postgres `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_DB=postgres `
  -p 5432:5432 `
  -d postgres:16
```

已存在容器时：

```powershell
docker start rasa-postgres
```

初始化 PostgreSQL：

```powershell
cd backend
.\scripts\init_postgres.ps1
```

启动 Redis：

```powershell
cd backend
.\scripts\start_redis.ps1
```

初始化 Redis：

```powershell
cd backend
.\scripts\init_redis.ps1
```

### 4. 启动模型服务

如果要跑 `rasa_plus_llm`，先启动 Ollama：

```powershell
ollama serve
```

首次使用拉取模型：

```powershell
ollama pull qwen3.5:2b
```

如果要跑 `rasa_plus_lora_llm`，还需要启动兼容 OpenAI 的 LoRA 推理服务，例如：

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

### 5. 启动主线 Rasa 服务

训练主线模型：

```powershell
cd rasa
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

### 6. 启动 benchmark 基线 `rasa_only`

训练基线模型：

```powershell
cd rasa
uv run rasa train `
  --config benchmark/rasa_only/config.yml `
  --domain benchmark/rasa_only/domain.yml `
  --data data/nlu.yml benchmark/rasa_only/rules.yml `
  --out models/benchmark_rasa_only
```

启动 5006 基线服务：

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

### 7. 启动后端服务

基础版：

```powershell
cd backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

LoRA 版：

```powershell
cd backend
$env:AGENT_LLM_PROVIDER = "openai_compat"
$env:AGENT_LLM_BASE_URL = "http://127.0.0.1:8002/v1"
$env:AGENT_LLM_API_KEY = "EMPTY"
$env:AGENT_LLM_MODEL = "qwen3.5-2b-lora"
uv run uvicorn app.main:app --host 127.0.0.1 --port 8001
```

### 8. 重置 benchmark 基线状态

正式跑 benchmark 前，先恢复业务数据和聊天状态：

如果本机已有 `psql`：

```powershell
psql -h 127.0.0.1 -U postgres -d rasa_ec_bot -f benchmark/sql/reset_benchmark_state.sql
```

如果没有本机 `psql`，推荐直接用 Docker 容器内的 `psql`，并避免 PowerShell 管道转码：

```powershell
docker cp benchmark/sql/reset_benchmark_state.sql rasa-postgres:/tmp/reset_benchmark_state.sql
docker exec rasa-postgres psql -U postgres -d rasa_ec_bot -f /tmp/reset_benchmark_state.sql
```

### 9. 重建数据集

```powershell
cd benchmark
uv run python scripts/build_dataset.py
```

### 10. 先跑单测

```powershell
cd benchmark
uv run python -m unittest discover -s tests -p "test_*.py"
```

### 11. 执行 Benchmark

Smoke：

```powershell
cd benchmark
uv run python scripts/run_benchmark.py --profile quick --verbose
```

标准档：

```powershell
cd benchmark
uv run python scripts/run_benchmark.py --profile standard
```

论文档：

```powershell
cd benchmark
uv run python scripts/run_benchmark.py --profile paper
```

### 12. 分析结果

```powershell
cd benchmark
uv run python scripts/analyze_results.py --result-dir results/<run_id>
```

## 常用参数

- `--systems rasa_only,rasa_plus_llm`
- `--scenarios recommendation,order_query,transactional_action`
- `--results-root results`
- `--dataset-tier core`
- `--concurrency 1`

## 结果结构

原始运行目录 `results/<run_id>/` 常见文件：

- `summary.csv`
- `scenario_quality.csv`
- `conversation_summary.csv`
- `capability_coverage.csv`
- `system_matrix.csv`
- `paper_tables.md`
- `prompt_versions.json`
- `run_metadata.json`
- `report.md`

分析目录 `results/<run_id>/analysis/` 常见文件：

- `suite_metrics.csv`
- `family_metrics.csv`
- `sample_coverage.csv`
- `suite_scenario_leaders.csv`
- `failure_breakdown.csv`
- `failure_flags.csv`
- `charts/shared_core_ranking.svg`
- `charts/agent_extension_ranking.svg`
- `charts/exclusive_failure_pie.svg`
- `charts/failure_flags_bar.svg`
- `report.md`

## 正式排名口径

`analysis/report.md` 使用以下顺序排名：

1. `suite_family_macro_pass_rate`
2. `suite_unique_micro_pass_rate`
3. `suite_family_macro_success_rate`
4. `eligibility_rate`

补充说明：

- `suite_pass_rate` 只保留为 raw attempt 调试字段。
- `sample_coverage.csv` 会展示 expected / executed unique sample id 和缺失样本。
- `suite_unique_micro_pass_rate` 会输出 Wilson 95% CI。
- `leader_status = no_pass` 表示该 family 没有系统取得正的 `family_pass_rate`。

## 说明

- `backend/prompts/*.md` 的路径和 SHA-256 会写入每次运行的 `prompt_versions.json`。
- `selection_mode` 会写入 `run_metadata.json`。
- benchmark 会话使用 `benchmark_<...>` session id，后端会跳过记忆加载与刷新，避免污染基线。
