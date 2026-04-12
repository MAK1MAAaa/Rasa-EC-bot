# Tests And Benchmark Notes

本目录同时承载两类内容：

- `pytest` 单元测试
- 系统级 benchmark 的实验规范、输入快照与结果归档约定

## 1. 当前测试文件说明

| 文件 | 类型 | 是否需要外部服务 | 说明 |
| --- | --- | --- | --- |
| `tests/test_product_recommendation_logic.py` | 单元测试 | 否 | 直接导入 `backend/app/main.py` 与 `backend/app/nexau_orchestrator.py`，验证推荐词提取、显式类目识别、历史画像打分与推荐问句识别。 |
| `tests/test_system_benchmark.py` | 单元测试 | 否 | 直接导入 `backend/scripts/run_system_benchmark.py`，验证 benchmark 数据集解析、会话评分、能力覆盖率、系统矩阵等纯逻辑函数。 |

结论：

- `tests/` 下现有两个测试都不要求先启动数据库、后端、Rasa、Ollama 或前端。
- 真正依赖多服务联调的是 `backend/scripts/run_system_benchmark.py`，它属于实验脚本，不属于 `pytest` 单测本身。

## 2. 真正运行系统 benchmark 时会用到的内容

`backend/scripts/run_system_benchmark.py` 会读取：

- 配置文件：`backend/benchmarks/experiment.yaml`
- 数据集目录：`backend/benchmarks/prompts/core/` 或 `backend/benchmarks/prompts/extended/`
- 知识库种子：`backend/benchmarks/kb_seed/`
- 图片资产：`backend/benchmarks/assets/`

它会写出：

- 默认结果目录：`backend/benchmarks/results/<timestamp>_<profile>_system_benchmark/`
- 建议本地实验目录：`tests/benchmark_results/<timestamp>_<profile>_system_benchmark/`

### 2.1 直接依赖的服务

按 `backend/benchmarks/experiment.yaml` 当前配置，真实 benchmark 会访问以下服务：

| 系统名 | 端口 | 作用 |
| --- | --- | --- |
| `rasa_only` | `5006` | 纯 Rasa 对照系统，入口为 `/webhooks/rest/webhook` |
| `llm_base_ollama` | `11434` | 直接调用 Ollama `/api/chat`，模型为 `qwen3.5:2b` |
| `llm_lora_ollama` | `11434` | 直接调用 Ollama `/api/chat`，模型为 `qwen3.5:2b-lora` |
| `rasa_plus_llm_base` | `8000` | 后端混合客服入口，调用 `/api/v1/chat/send`、`/api/v1/chat/upload-image`、`/api/v1/chat/pending-action/decision` |
| `rasa_plus_llm_lora` | `8001` | 第二个后端实例，接口同上，用于 LoRA 对照 |

### 2.2 间接依赖的服务

如果要完整跑通 `rasa_plus_llm_base` / `rasa_plus_llm_lora`，还需要这些依赖：

| 服务 | 端口 | 原因 |
| --- | --- | --- |
| PostgreSQL | `5432` | 后端读取商品、订单、售后、用户等业务数据 |
| Redis | `6379` | 后端缓存与待确认动作状态 |
| Rasa Server | `5005` | 后端会调用 `RASA_SERVER_URL` 与 `RASA_PARSE_PATH` |
| Rasa Action Server | `5055` | Rasa 规则链路的动作执行依赖它 |
| 前端开发服务器 | `5173` | benchmark 发给 Rasa 的 metadata 中固定包含 `frontend_base_url=http://localhost:5173` |
| vLLM / OpenAI-compatible LLM | `8002` | `backend/.env.sample` 默认将 LoRA Agent 指向 `AGENT_LLM_BASE_URL=http://127.0.0.1:8002/v1` |

### 2.3 Ollama 侧模型准备

真实 benchmark 覆盖了 `knowledge_and_multimodal` 与图片售后链路，因此除了聊天模型，还要准备：

- `qwen3.5:2b`
- `qwen3.5:2b-lora` 或等价可调用模型
- `qwen3-vl:2b`
- `mxbai-embed-large`

其中：

- `qwen3.5:2b` 用于基础聊天对照与基础后端实例
- `qwen3.5:2b-lora` 用于 LoRA 对照系统
- `qwen3-vl:2b` 用于图片理解
- `mxbai-embed-large` 用于知识库索引与检索 embedding

### 2.4 账号依赖

`experiment.yaml` 当前固定使用：

- 客户账号：`test1@example.com`
- 商家账号：`merchant1@example.com`
- 统一密码：`password123`

脚本会在需要时自动调用：

- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`

## 3. tests 目录下的实验资产约定

本目录新增两类位置：

- `tests/benchmark_data/`
- `tests/benchmark_results/`

用途约定：

- `tests/benchmark_data/`：保存实验输入快照，例如当次实验使用的 `experiment.yaml`、数据集副本、运行参数说明、人工标注补充说明。
- `tests/benchmark_results/`：保存本地运行产物，例如 `raw_events.jsonl`、`summary.csv`、`report.md` 等输出目录。

版本控制约定：

- `tests/benchmark_results/` 默认只保留 `.gitkeep`，动态结果文件不提交。
- `tests/benchmark_data/` 可以提交必要的小型输入快照与说明，避免正式实验时无法复现实验输入。

## 4. 标准实验流程

以下流程按 Windows PowerShell 书写。为避免本机 `uv` 全局缓存冲突，命令统一显式设置 `UV_CACHE_DIR`。

额外前提：

- 仓库根目录没有 `pyproject.toml`，Python 侧运行环境以 `backend/pyproject.toml` 为准。
- 因此 `tests/` 里的 Python 测试与 benchmark 脚本，都建议在 `backend/` 目录下通过 `uv` 执行。

### 4.1 先跑 tests 侧单元测试

```powershell
Push-Location backend
$env:UV_CACHE_DIR = "d:\Github\Rasa-EC-bot\.uv-cache"
uv sync
uv run python -m unittest discover -s ..\tests -p "test_*.py"
Pop-Location
```

这一步只检查逻辑，不检查真实服务连通性。

### 4.2 如需刷新 benchmark 数据集

```powershell
Push-Location backend
$env:UV_CACHE_DIR = "d:\Github\Rasa-EC-bot\.uv-cache"
uv sync
uv run python scripts\build_system_benchmark_dataset.py
Pop-Location
```

### 4.3 在 tests 下保存实验输入快照

建议每次正式实验建立一个独立目录，例如 `tests/benchmark_data/20260412_paper/`，至少保存：

- `experiment.yaml` 副本
- 使用的数据集目录副本
- 一份运行命令记录

可参考：

```powershell
$expId = "20260412_paper"
New-Item -ItemType Directory -Force "tests\benchmark_data\$expId" | Out-Null
Copy-Item backend\benchmarks\experiment.yaml "tests\benchmark_data\$expId\experiment.yaml"
Copy-Item backend\benchmarks\prompts "tests\benchmark_data\$expId\prompts" -Recurse -Force
```

### 4.4 启动真实 benchmark 所需服务

最小完整实验建议至少启动：

1. PostgreSQL `5432`
2. Redis `6379`
3. 后端基础实例 `8000`
4. 后端 LoRA 实例 `8001`
5. Rasa Server `5005`
6. Rasa benchmark 专用实例 `5006`
7. Rasa Action Server `5055`
8. Ollama `11434`
9. LoRA 对应的 OpenAI-compatible / vLLM 服务 `8002`
10. 前端 `5173`

如果只做单系统冒烟，可按 `--systems` 缩小范围，但要确保该系统的直接依赖和间接依赖都已经启动。

### 4.5 将实验结果统一落到 tests/benchmark_results

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

正式实验建议把输出目录名称和 `tests/benchmark_data/<exp_id>/` 对齐，便于一一对应。

## 5. 结果文件如何看

主要文件含义如下：

| 文件 | 含义 |
| --- | --- |
| `raw_events.jsonl` | 会话级原始事件 |
| `turn_events.jsonl` | 逐步执行事件，适合排查登录、上传图片、待确认动作等链路 |
| `summary.csv` | 按系统、场景族、并发和重复次数聚合 |
| `scenario_quality.csv` | 按场景族统计失败原因 |
| `conversation_summary.csv` | 每条会话的成功与质量结果 |
| `capability_coverage.csv` | 能力覆盖率与 `unsupported/na` 统计 |
| `system_matrix.csv` | 论文主表候选结果 |
| `report.md` | 中文实验报告 |
| `paper_tables.md` | 可直接引用到论文的表格 |

## 6. 冗余文件检查结论

当前检查结论如下：

- `tests/__pycache__/` 是解释器缓存，属于冗余产物，但 `.gitignore` 已覆盖，不需要纳入实验资产。
- `tests/test_product_recommendation_logic.py` 与 `tests/test_system_benchmark.py` 都有明确用途，不冗余。
- `backend/benchmarks/prompts/`、`backend/benchmarks/kb_seed/`、`backend/benchmarks/assets/` 都被 `backend/scripts/run_system_benchmark.py` 或 `experiment.yaml` 直接引用，不冗余。
- 根目录 `design.md`、`frontend/README.md` 被根 README 直接引用，不冗余。
- 根目录 `1.txt` 没有被仓库内代码或文档引用，属于高概率冗余文件候选；如果它不是临时记录，建议先确认来源，再决定是否删除或迁移。

## 7. 推荐执行边界

建议以后遵守以下边界：

- Python 逻辑测试放在 `tests/*.py`
- 实验输入快照放在 `tests/benchmark_data/<exp_id>/`
- 实验运行输出放在 `tests/benchmark_results/<run_id>/`
- 不要把新的 benchmark 输出继续写进仓库根目录或零散文本文件
