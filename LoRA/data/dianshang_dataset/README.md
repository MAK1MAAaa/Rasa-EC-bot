# `dianshang_dataset` 目录说明

本目录用于存放从 ModelScope 下载的原始电商对话数据。  
它是 LoRA 数据准备阶段的上游输入之一，不是在线服务资源，也不是 benchmark 直接消费的文件。

## 1. 作用

- 作为 `LoRA/scripts/prepare_data.py` 的输入数据源
- 与 FAQ intents 等数据一起整理为统一的 SFT JSONL
- 为 LoRA 微调提供更贴近电商客服场景的多轮对话样本

## 2. 获取方式

建议在仓库根目录执行：

Windows：

```powershell
uv run modelscope download --dataset xuri2004/dianshang_dataset --local_dir LoRA/data/dianshang_dataset
```

macOS / Linux：

```bash
uv run modelscope download --dataset xuri2004/dianshang_dataset --local_dir LoRA/data/dianshang_dataset
```

下载完成后，典型输入文件为：

- `LoRA/data/dianshang_dataset/output.jsonl`

## 3. 使用方式

在 `LoRA/` 目录执行：

Windows：

```powershell
uv run python scripts/prepare_data.py `
  --faq-json data/Ecommerce_FAQ_intents.json `
  --ec-train-jsonl data/dianshang_dataset/output.jsonl `
  --out-dir data/processed `
  --faq-upsample 6 `
  --ec-upsample 1 `
  --ec-max-samples 120000 `
  --seed 42
```

macOS / Linux：

```bash
uv run python scripts/prepare_data.py \
  --faq-json data/Ecommerce_FAQ_intents.json \
  --ec-train-jsonl data/dianshang_dataset/output.jsonl \
  --out-dir data/processed \
  --faq-upsample 6 \
  --ec-upsample 1 \
  --ec-max-samples 120000 \
  --seed 42
```

## 4. 注意事项

- 原始大文件不要提交到 Git。
- 若跨设备迁移，请手动复制该目录下的大文件。
- 该目录只是原始数据落盘位置，字段定义以上游数据集为准。
