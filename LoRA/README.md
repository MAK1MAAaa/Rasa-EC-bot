# LoRA

`LoRA/` 用于基于 `Qwen/Qwen3.5-2B` 做 QLoRA 微调，并将结果接入 `vLLM` 或 `Ollama`。

## 目录说明

| 路径 | 说明 |
| --- | --- |
| `configs/` | 训练配置 |
| `data/` | 原始数据与中间数据 |
| `scripts/prepare_data.py` | 生成 SFT 数据集 |
| `scripts/filter_sft_sources.py` | 从总数据集中筛出指定来源的数据 |
| `scripts/train_lora.py` | 执行 LoRA 训练 |
| `scripts/eval_lora.py` | 评估基础模型与 LoRA 适配器 |
| `scripts/export_ollama_model.py` | 生成 Ollama `Modelfile` |
| `models/` | 基础模型目录，属于本地大文件产物 |
| `outputs/` | 训练输出目录，包含 `adapter/`、checkpoint、导出结果 |
| `reports/` | 评估报告输出 |

## 环境要求

- Python `3.10`，且 `<3.12`
- CUDA 可用
- 如果要运行 `vLLM`，建议使用 Linux 或 WSL 环境

## 平台说明

- Windows 命令默认以 PowerShell 为准。
- macOS / Linux 命令默认以 Bash 为准。
- `vLLM` 实际更建议在 Linux 或 Windows 的 WSL 中运行；macOS 通常不作为 `vLLM` 运行环境。

## 安装依赖

```powershell
cd LoRA
uv sync
```

```bash
cd LoRA
uv sync
```

## 数据准备

### 1. 生成基础 SFT 数据

下面命令会把 FAQ 数据和电商对话数据整理成统一的 `jsonl`：

```powershell
cd LoRA
uv run python scripts/prepare_data.py `
  --faq-json data/Ecommerce_FAQ_intents.json `
  --ec-train-jsonl data/dianshang_dataset/output.jsonl `
  --out-dir data/processed
```

```bash
cd LoRA
uv run python scripts/prepare_data.py \
  --faq-json data/Ecommerce_FAQ_intents.json \
  --ec-train-jsonl data/dianshang_dataset/output.jsonl \
  --out-dir data/processed
```

### 2. 过滤出当前训练配置使用的数据集

当前默认训练配置 [configs/smoke_ec_faq_only.yaml](/D:/Github/Rasa-EC-bot/LoRA/configs/smoke_ec_faq_only.yaml) 使用的是 `data/processed/ec_faq_only/`：

```powershell
cd LoRA
uv run python scripts/filter_sft_sources.py `
  --input-train data/processed/train.jsonl `
  --input-val data/processed/val.jsonl `
  --input-test data/processed/test.jsonl `
  --out-dir data/processed/ec_faq_only `
  --allowed-sources ecommerce_dialogue_train,ecommerce_faq
```

```bash
cd LoRA
uv run python scripts/filter_sft_sources.py \
  --input-train data/processed/train.jsonl \
  --input-val data/processed/val.jsonl \
  --input-test data/processed/test.jsonl \
  --out-dir data/processed/ec_faq_only \
  --allowed-sources ecommerce_dialogue_train,ecommerce_faq
```

## 训练

训练前先复制 `.env.sample` 为 `.env`，并把 `BASE_MODEL_PATH` 改成当前机器上的基础模型目录，例如 `LoRA/models/Qwen3.5-2B`。

```powershell
cd LoRA
Copy-Item .env.sample .env
uv run python scripts/train_lora.py --config configs/smoke_ec_faq_only.yaml
```

```bash
cd LoRA
cp .env.sample .env
uv run python scripts/train_lora.py --config configs/smoke_ec_faq_only.yaml
```

当前配置会读取：

- `data/processed/ec_faq_only/train.jsonl`
- `data/processed/ec_faq_only/val.jsonl`
- 输出到 `outputs/smoke_ec_faq_only/`

## 评估

```powershell
cd LoRA
uv run python scripts/eval_lora.py `
  --model-dir outputs/smoke_ec_faq_only/adapter `
  --test-file data/processed/eval_prompts_20.jsonl `
  --report-file reports/smoke_ec_faq_only_eval.json
```

```bash
cd LoRA
uv run python scripts/eval_lora.py \
  --model-dir outputs/smoke_ec_faq_only/adapter \
  --test-file data/processed/eval_prompts_20.jsonl \
  --report-file reports/smoke_ec_faq_only_eval.json
```

## 导出 Ollama 模型定义

```powershell
cd LoRA
uv run python scripts/export_ollama_model.py `
  --adapter-dir outputs/smoke_ec_faq_only/adapter `
  --base-model qwen3.5:2b `
  --model-name qwen3.5:2b-lora `
  --output-dir outputs/smoke_ec_faq_only/ollama_export
```

```bash
cd LoRA
uv run python scripts/export_ollama_model.py \
  --adapter-dir outputs/smoke_ec_faq_only/adapter \
  --base-model qwen3.5:2b \
  --model-name qwen3.5:2b-lora \
  --output-dir outputs/smoke_ec_faq_only/ollama_export
```

如果还要直接在本机创建 Ollama 模型，可追加 `--run-create`。

## 启动 vLLM

下面示例会把基础模型和 LoRA adapter 组合成 OpenAI-compatible 服务：

Windows（推荐在 WSL 中执行）：

```bash
cd /mnt/<drive>/path/to/Rasa-EC-bot/LoRA
uv run --with vllm python -m vllm.entrypoints.openai.api_server \
  --host 0.0.0.0 \
  --port 8002 \
  --model /mnt/<drive>/path/to/Rasa-EC-bot/LoRA/models/Qwen3.5-2B \
  --served-model-name qwen3.5-2b-lora \
  --enable-lora \
  --lora-modules qwen3.5-2b-lora=/mnt/<drive>/path/to/Rasa-EC-bot/LoRA/outputs/smoke_ec_faq_only/adapter \
  --max-model-len 4096 \
  --max-num-seqs 2 \
  --gpu-memory-utilization 0.55 \
  --enforce-eager
```

macOS / Linux：

```bash
cd /path/to/Rasa-EC-bot/LoRA
uv run --with vllm python -m vllm.entrypoints.openai.api_server \
  --host 0.0.0.0 \
  --port 8002 \
  --model /path/to/Rasa-EC-bot/LoRA/models/Qwen3.5-2B \
  --served-model-name qwen3.5-2b-lora \
  --enable-lora \
  --lora-modules qwen3.5-2b-lora=/path/to/Rasa-EC-bot/LoRA/outputs/smoke_ec_faq_only/adapter \
  --max-model-len 4096 \
  --max-num-seqs 2 \
  --gpu-memory-utilization 0.55 \
  --enforce-eager
```

如为 macOS，本段通常只作为命令格式参考；实际跑 `vLLM` 仍建议使用 Linux 环境。

后端如何接到该服务，见 [backend/README.md](/D:/Github/Rasa-EC-bot/backend/README.md)。

## 迁移到其他设备时需要带哪些文件

### 只迁移源码和配置，目标机器上重新装环境、重新准备数据、重新训练

至少带走这些被 Git 跟踪的文件：

- `LoRA/pyproject.toml`
- `LoRA/uv.lock`
- `LoRA/.env.sample`
- `LoRA/README.md`
- `LoRA/configs/`
- `LoRA/scripts/`
- `LoRA/data/Ecommerce_FAQ_intents.json`
- `LoRA/data/dianshang_dataset/`

这种迁移方式通常不需要带：

- `LoRA/.venv/`
- `LoRA/data/processed/`
- `LoRA/reports/`

### 想在目标机器上直接继续使用当前训练结果，不重新训练

除了上面的源码和配置，还要带：

- `LoRA/models/Qwen3.5-2B/`
- `LoRA/outputs/smoke_ec_faq_only/adapter/`

如果目标机器还要继续复用当前导出结果，再额外带上对应目录：

- `LoRA/outputs/smoke_ec_faq_only/merged_hf/`
- `LoRA/outputs/smoke_ec_faq_only/ollama_export/`
- `LoRA/outputs/smoke_ec_faq_only/ollama_gguf/`

## 相关文档

- [README.md](/D:/Github/Rasa-EC-bot/README.md)
- [backend/README.md](/D:/Github/Rasa-EC-bot/backend/README.md)
- [tests/README.md](/D:/Github/Rasa-EC-bot/tests/README.md)
