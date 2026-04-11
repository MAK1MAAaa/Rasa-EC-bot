# LoRA 复现实验（仅两份数据集，无 ReAct 合成）

当前流程固定为四步：

1. 两数据集预处理
2. 数据过滤（可选）
3. LoRA 训练
4. 离线评估

## 1. 数据来源

- ModelScope: `xuri2004/dianshang_dataset`  
  https://www.modelscope.cn/datasets/xuri2004/dianshang_dataset
- Kaggle: `ecommerce-dataset-for-nlpchatbot`（FAQ）  
  https://www.kaggle.com/datasets/walterebhota/ecommerce-dataset-for-nlpchatbot

说明：当前不使用旧 `data/E-commerce dataset/*.txt`。

## 2. 目录基线（当前流程所需）

```text
LoRA/
  .env
  .env.sample
  pyproject.toml
  uv.lock
  models/
    Qwen3.5-2B/
  configs/
    smoke_ec_faq_only.yaml
  data/
    dianshang_dataset/
      output.jsonl
    Ecommerce_FAQ_intents.json
    processed/                           # 运行后生成
      train.jsonl
      val.jsonl
      test.jsonl
      eval_prompts_20.jsonl
      ec_faq_only/
        train.jsonl
        val.jsonl
        test.jsonl
        summary.json
  scripts/
    env_utils.py
    prepare_data.py
    filter_sft_sources.py
    train_lora.py
    eval_lora.py
  outputs/                               # 训练后生成
  reports/                               # 评估后生成
```

## 3. 环境准备

```powershell
cd LoRA
$env:UV_CACHE_DIR='d:\Github\Rasa-EC-bot\.uv-cache'
$env:UV_PYTHON_INSTALL_DIR='d:\Github\Rasa-EC-bot\.uv-python'
uv python install 3.10
uv sync
```

`LoRA/.env` 里确认：

```env
BASE_MODEL_PATH=d:/Github/Rasa-EC-bot/LoRA/models/Qwen3.5-2B
```

## 4. 数据准备

### 4.1 下载 dianshang_dataset

```powershell
cd D:\Github\Rasa-EC-bot
uv run modelscope download --dataset xuri2004/dianshang_dataset --local_dir LoRA/data/dianshang_dataset
```

确认文件存在：`LoRA/data/dianshang_dataset/output.jsonl`

### 4.2 准备 FAQ 文件

将 FAQ JSON 放到：`LoRA/data/Ecommerce_FAQ_intents.json`

## 5. 两数据集预处理

```powershell
cd LoRA
uv run python scripts/prepare_data.py `
  --faq-json data/Ecommerce_FAQ_intents.json `
  --ec-train-jsonl data/dianshang_dataset/output.jsonl `
  --out-dir data/processed `
  --faq-upsample 6 `
  --ec-upsample 1 `
  --ec-max-samples 120000 `
  --seed 42
```

输出：

- `data/processed/train.jsonl`
- `data/processed/val.jsonl`
- `data/processed/test.jsonl`
- `data/processed/eval_prompts_20.jsonl`

## 6. 数据过滤（可选，但推荐保留）

你当前输入只含两类来源：`ecommerce_dialogue_train`（对应 dianshang_dataset）和 `ecommerce_faq`。  
该步骤通常是幂等操作（`kept_rows == total_rows`），主要用于可审计复现。

```powershell
cd LoRA
uv run python scripts/filter_sft_sources.py `
  --input-train data/processed/train.jsonl `
  --input-val data/processed/val.jsonl `
  --input-test data/processed/test.jsonl `
  --allowed-sources ecommerce_dialogue_train,ecommerce_faq `
  --out-dir data/processed/ec_faq_only
```

快速核对：

```powershell
Get-Content data/processed/ec_faq_only/summary.json
```

## 7. LoRA 训练

配置文件：`configs/smoke_ec_faq_only.yaml`

```powershell
cd LoRA
uv run python scripts/train_lora.py --config configs/smoke_ec_faq_only.yaml
```

输出：

- `outputs/smoke_ec_faq_only/adapter`
- `outputs/smoke_ec_faq_only/run_summary.json`

## 8. 离线评估

```powershell
cd LoRA
uv run python scripts/eval_lora.py `
  --model-dir outputs/smoke_ec_faq_only/adapter `
  --test-file data/processed/eval_prompts_20.jsonl `
  --report-file reports/smoke_ec_faq_only_eval.json
```

### 8.1 本次实验记录（2026-04-11）

训练（`configs/smoke_ec_faq_only.yaml`）：

- `trainable params`: `10,911,744 / 1,892,736,832`（`0.5765%`）
- `train_samples`: `3139`
- `eval_samples`: `174`
- `train_loss`: `0.8576`
- `eval_loss`: `0.4111`
- `train_runtime`: `3733s`（约 `1:02:13`）
- `train_steps`: `393`

评估（`reports/smoke_ec_faq_only_eval.json`）：

- `base_pass_rate`: `0.85`
- `tuned_pass_rate`: `0.80`
- `pass_rate_delta`: `-0.05`
- `base_hallucinated_order_id / tuned_hallucinated_order_id`: `0 / 0`
- `base_missing_confirmation / tuned_missing_confirmation`: `3 / 4`
- `base_missing_required_keywords / tuned_missing_required_keywords`: `0 / 0`
- `base_contains_forbidden_keywords / tuned_contains_forbidden_keywords`: `0 / 0`

说明：本次微调后在 20 条离线约束集上未超过基座（少通过 1 条）。
