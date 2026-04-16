# Tests And Benchmark

`tests/` 统一负责两件事：

- 代码层面的测试。
- benchmark 的数据归档、结果归档与结果后分析。

benchmark 相关说明只保留在这里，其他 README 只做跳转，不重复描述。

## 目录说明

| 路径 | 作用 |
| --- | --- |
| `test_chat_router_logic.py` | 聊天路由、LLM 复核与事务前置拦截测试 |
| `test_chat_memory_logic.py` | 会话记忆解析、偏好提取与压缩触发规则测试 |
| `test_product_recommendation_logic.py` | 商品推荐逻辑测试 |
| `test_system_benchmark.py` | benchmark 相关测试 |
| `benchmark_data/` | 实验输入快照归档 |
| `benchmark_results/` | 实验输出结果归档 |
| `scripts/analyze_benchmark_results.ps1` | 结果后分析脚本 |
| `scripts/analyze_benchmark_results.zh-Hans.json` | 中文报告与图表文案资源 |

## 普通测试

从 `backend/` 目录执行：

```powershell
Push-Location backend
$env:UV_CACHE_DIR = "d:\Github\Rasa-EC-bot\.uv-cache"
uv sync
uv run python -m unittest discover -s ..\tests -p "test_*.py"
Pop-Location
```

## benchmark 依赖的服务

benchmark 默认会比较以下 5 套系统：

- `rasa_only`
- `llm_base_ollama`
- `llm_lora_ollama`
- `rasa_plus_llm_base`
- `rasa_plus_llm_lora`

运行前建议确认以下服务已就绪：

| 服务 | 端口 | 用途 |
| --- | --- | --- |
| PostgreSQL | `5432` | 后端业务数据 |
| Redis | `6379` | 缓存 |
| 前端 | `5173` | benchmark 中部分链接与页面地址依赖 |
| Rasa Server | `5005` | 主对话系统 |
| Rasa Action Server | `5055` | 自定义动作 |
| `rasa_only` 基线 | `5006` | 纯 Rasa 基线 |
| 后端主实例 | `8000` | `rasa_plus_llm_base` 等组合链路 |
| 后端 LoRA 实例 | `8001` | `rasa_plus_llm_lora` |
| vLLM | `8002` | LoRA OpenAI-compatible 推理服务 |
| Ollama | `11434` | 基础模型、LoRA 模型、多模态模型与 embedding |

具体启动命令分别见：

- [../backend/README.md](../backend/README.md)
- [../rasa/README.md](../rasa/README.md)
- [../LoRA/README.md](../LoRA/README.md)
- [../frontend/README.md](../frontend/README.md)

## benchmark 输入组成

benchmark 输入由后端目录下的 benchmark 资源构成：

- `backend/benchmarks/experiment.yaml`
- `backend/benchmarks/prompts/core/`
- `backend/benchmarks/prompts/extended/`
- `backend/benchmarks/assets/`
- `backend/benchmarks/kb_seed/`

场景家族包括：

- `recommendation`
- `order_query`
- `logistics_query`
- `after_sales_query`
- `knowledge_and_multimodal`
- `transactional_action`

## 生成 benchmark 数据集

从 `backend/` 目录执行：

```powershell
Push-Location backend
$env:UV_CACHE_DIR = "d:\Github\Rasa-EC-bot\.uv-cache"
uv sync
uv run python scripts\build_system_benchmark_dataset.py
Pop-Location
```

## 运行 benchmark

### quick

```powershell
Push-Location backend
$env:UV_CACHE_DIR = "d:\Github\Rasa-EC-bot\.uv-cache"
uv sync
uv run python scripts\run_system_benchmark.py `
  --profile quick `
  --systems rasa_only,llm_base_ollama,llm_lora_ollama,rasa_plus_llm_base,rasa_plus_llm_lora `
  --scenarios recommendation,order_query,logistics_query,after_sales_query,knowledge_and_multimodal,transactional_action `
  --results-root ..\tests\benchmark_results `
  --verbose
Pop-Location
```

### standard

```powershell
Push-Location backend
$env:UV_CACHE_DIR = "d:\Github\Rasa-EC-bot\.uv-cache"
uv sync
uv run python scripts\run_system_benchmark.py `
  --profile standard `
  --systems rasa_only,llm_base_ollama,llm_lora_ollama,rasa_plus_llm_base,rasa_plus_llm_lora `
  --scenarios recommendation,order_query,logistics_query,after_sales_query,knowledge_and_multimodal,transactional_action `
  --results-root ..\tests\benchmark_results
Pop-Location
```

### paper

```powershell
Push-Location backend
$env:UV_CACHE_DIR = "d:\Github\Rasa-EC-bot\.uv-cache"
uv sync
uv run python scripts\run_system_benchmark.py `
  --profile paper `
  --systems rasa_only,llm_base_ollama,llm_lora_ollama,rasa_plus_llm_base,rasa_plus_llm_lora `
  --results-root ..\tests\benchmark_results
Pop-Location
```

注意：

- `--results-root` 建议在 `backend/` 目录下写成 `..\tests\benchmark_results`。
- benchmark 结果统一存放在 `tests/benchmark_results/<run_id>/`。
- 若要保留某次实验的输入快照，可额外把对应 prompts、experiment.yaml 复制到 `tests/benchmark_data/<exp_id>/`。

## benchmark 结果目录

单次运行结果通常包含：

| 文件 | 说明 |
| --- | --- |
| `raw_events.jsonl` | 原始事件流 |
| `turn_events.jsonl` | 回合级事件 |
| `summary.csv` | 系统-场景-并发级汇总 |
| `scenario_quality.csv` | 质量标记统计 |
| `conversation_summary.csv` | 会话级摘要 |
| `capability_coverage.csv` | 能力覆盖统计 |
| `system_matrix.csv` | 论文表格常用矩阵 |
| `report.md` | 基础报告 |
| `paper_tables.md` | 论文表格草稿 |

## 结果后分析

对任意已有结果目录，可以生成更完整的中文图表与分析报告：

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
