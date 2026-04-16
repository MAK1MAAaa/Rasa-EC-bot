# LoRA

`LoRA/` 负责 Qwen3.5-2B 的 QLoRA 训练、评测、导出，以及通过 vLLM / Ollama 提供推理能力。

## 目录说明

| 路径 | 作用 |
| --- | --- |
| `configs/` | 训练配置 |
| `data/` | 原始或处理后的训练数据 |
| `scripts/prepare_data.py` | 数据准备 |
| `scripts/train_lora.py` | LoRA 训练 |
| `scripts/eval_lora.py` | LoRA 评测 |
| `scripts/export_ollama_model.py` | 导出 Ollama 模型 |
| `models/` | 本地基座模型目录 |
| `outputs/` | 训练输出、adapter、导出结果 |

## 环境要求

- Python `3.10` 到 `<3.12`
- CUDA 环境
- 建议在 Linux / WSL 中运行训练和 vLLM

## 安装依赖

```powershell
cd LoRA
uv sync
```

## 训练流程

### 1. 准备数据

```powershell
cd LoRA
uv run python scripts\prepare_data.py
```

### 2. 启动训练

```powershell
cd LoRA
uv run python scripts\train_lora.py --config configs\smoke_ec_faq_only.yaml
```

当前默认示例配置见 [configs/smoke_ec_faq_only.yaml](../LoRA/configs/smoke_ec_faq_only.yaml)。

### 3. 评测

```powershell
cd LoRA
uv run python scripts\eval_lora.py --config configs\smoke_ec_faq_only.yaml
```

### 4. 导出 Ollama 模型

```powershell
cd LoRA
uv run python scripts\export_ollama_model.py --config configs\smoke_ec_faq_only.yaml
```

## vLLM 服务

如果后端 LoRA 实例要通过 OpenAI-compatible 接口调用 LoRA 模型，建议在 WSL 中启动 vLLM。

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

后端如何接入这个 vLLM 实例，统一见 [../backend/README.md](../backend/README.md)。

## 与其他模块的边界

- LoRA 训练细节只在当前 README 维护。
- benchmark 如何使用 LoRA 后端实例、如何记录结果，统一见 [../tests/README.md](../tests/README.md)。
- 根目录 [../README.md](../README.md) 只保留模块入口，不重复训练步骤。
