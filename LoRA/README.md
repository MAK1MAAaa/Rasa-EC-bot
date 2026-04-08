# Qwen3.5-2B LoRA 微调说明（电商客服）

本目录提供一套完整的 QLoRA 微调流程，用于在以下数据上训练 `Qwen/Qwen3.5-2B`：

- `Bitext_Sample_Customer_Support_Training_Dataset_27K_responses-v11.csv`
- `Ecommerce_FAQ_intents.json`

最终可同时产出：

- Hugging Face LoRA Adapter 与合并后的模型
- Ollama 可运行模型包

## 1. 目录结构

```text
LoRA/
  .env.sample
  configs/
    smoke.yaml
    full.yaml
    eval_prompts_20.jsonl
  data/
    Bitext_Sample_Customer_Support_Training_Dataset_27K_responses-v11.csv
    Ecommerce_FAQ_intents.json
    processed/
      train.jsonl
      val.jsonl
      test.jsonl
      summary.json
      eval_prompts_20.jsonl
  outputs/
  reports/
  scripts/
    env_utils.py
    prepare_data.py
    train_lora.py
    eval_lora.py
    export_ollama.py
  pyproject.toml
  README.md
```

## 2. 环境准备（uv）

PowerShell：

```powershell
cd LoRA
$env:UV_CACHE_DIR='d:\Github\Rasa-EC-bot\.uv-cache'
$env:UV_PYTHON_INSTALL_DIR='d:\Github\Rasa-EC-bot\.uv-python'
uv python install 3.10
uv sync
```

如果你要用 CUDA 训练，请根据显卡驱动/CUDA 版本安装匹配的 PyTorch CUDA 轮子。

## 3. 用 .env 管理 base_model 路径

先复制模板：

```powershell
cd LoRA
Copy-Item .env.sample .env
```

编辑 `LoRA/.env`，设置：

```env
BASE_MODEL_PATH=d:/Github/Rasa-EC-bot/LoRA/models/Qwen3.5-2B
```

说明：

- `train_lora.py` 会优先读取 `.env` 的 `BASE_MODEL_PATH`
- `eval_lora.py` 若未传 `--base-model`，会使用 `.env` 的路径
- `export_ollama.py` 若未传 `--base-model`，也会使用 `.env` 的路径

## 4. 通过 ModelScope 下载模型到本地

在 `LoRA` 目录执行：

```powershell
uv run python -c "from modelscope.hub.snapshot_download import snapshot_download; snapshot_download('Qwen/Qwen3.5-2B', local_dir='models/Qwen3.5-2B')"
```

如果你的环境里有 `modelscope` 命令，也可使用：

```powershell
uv run modelscope download --model Qwen/Qwen3.5-2B --local_dir models/Qwen3.5-2B
```

## 5. 数据预处理

```powershell
cd LoRA
uv run python scripts/prepare_data.py `
  --bitext-csv data/Bitext_Sample_Customer_Support_Training_Dataset_27K_responses-v11.csv `
  --faq-json data/Ecommerce_FAQ_intents.json `
  --ec-train-txt "data/E-commerce dataset/train.txt" `
  --ecm-train-txt data/ecm/Emotional_train.txt `
  --ecm-dev-txt data/ecm/Emotional_dev.txt `
  --ecm2-train-txt data/ecm2/train.txt `
  --ecm2-dev-txt data/ecm2/dev.txt `
  --out-dir data/processed `
  --faq-upsample 6 `
  --ec-upsample 1 `
  --ecm-upsample 1 `
  --ecm2-upsample 1 `
  --ec-max-samples 120000 `
  --ecm-max-samples 80000 `
  --ecm2-max-samples 10000 `
  --ecm2-label-whitelist "others,happy,sad,angry" `
  --seed 42
```

该脚本会：

- 标准化占位符（如 `{{Order Number}}`）与空白字符
- 去除空样本与重复 `user+assistant` 对
- 支持 Bitext + FAQ + E-commerce dataset + ECM + ECM2 五类数据合并
- FAQ/EC/ECM/ECM2 可独立上采样（`--faq-upsample/--ec-upsample/--ecm-upsample/--ecm2-upsample`）
- `ecm2/test_without_label.txt` 不用于 SFT 监督训练
- 转为 SFT 聊天格式：`messages=[system,user,assistant]`
- 按 `90/5/5` 划分 train/val/test
- 输出 `data/processed/summary.json`，检查 `raw_source_counts` 中是否包含 `ecm_emotional_dialogue`、`ecm2_emotion`

## 6. 训练 LoRA

快速验证（smoke）：

```powershell
cd LoRA
uv run python scripts/train_lora.py --config configs/smoke.yaml
```

全量训练（full）：

```powershell
cd LoRA
uv run python scripts/train_lora.py --config configs/full.yaml
```

配置中的固定参数：

- QLoRA：4-bit NF4，BF16 计算
- LoRA：`r=16`，`alpha=32`，`dropout=0.05`
- 目标模块：`q/k/v/o + gate/up/down`
- smoke：`max_seq_len=1024`，`epochs=1`，`batch=1`，`grad_accum=8`
- full：`max_seq_len=2048`，`epochs=2`，`batch=1`，`grad_accum=16`，`lr=2e-4`
- 评估加速默认值（已写入配置）：
  - smoke：`eval_steps=1000`，`save_steps=1000`，`max_eval_samples=1000`，`per_device_eval_batch_size=4`
  - full：`eval_steps=1000`，`save_steps=1000`，`max_eval_samples=2000`，`per_device_eval_batch_size=2`
  - 预热：`warmup_steps=800`（优先于 `warmup_ratio`，避免新版 transformers 的弃用告警）

训练脚本新增可调项（`train_lora.py`）：

- `max_eval_samples`：限制每次评估使用的验证集样本数（>0 生效）
- `warmup_steps`：若设置则优先使用，不再使用 `warmup_ratio`
- `eval_steps<=0`：自动关闭周期评估（`evaluation_strategy=no`）

## 7. 离线评估（固定 20 条提示词）

```powershell
cd LoRA
uv run python scripts/eval_lora.py `
  --model-dir outputs/smoke/adapter `
  --test-file configs/eval_prompts_20.jsonl `
  --report-file reports/smoke_eval.json
```

评估会检查：

- 固定提示词约束通过率
- 在用户未提供订单号时是否乱编订单号
- 对敏感执行动作是否先要求确认

## 8. 导出到 Ollama

前置条件：

- 本机可用 `ollama`
- 已编译 `llama.cpp`，并包含 `convert_hf_to_gguf.py` 与 `llama-quantize(.exe)`

示例命令：

```powershell
cd LoRA
uv run python scripts/export_ollama.py `
  --adapter-dir outputs/full/adapter `
  --merged-dir outputs/full/merged_fp16 `
  --gguf-dir outputs/full/gguf `
  --ollama-model-name qwen3.5-2b-lora-ec `
  --llama-cpp-dir .\tools\llama.cpp
```

导出后测试：

```powershell
ollama run qwen3.5-2b-lora-ec
```

## 9. 推荐执行顺序

1. `Copy-Item .env.sample .env` 并设置 `BASE_MODEL_PATH`
2. 使用 ModelScope 下载模型到 `models/Qwen3.5-2B`
3. `prepare_data.py`
4. smoke 训练（`configs/smoke.yaml`）
5. smoke 评估（`reports/smoke_eval.json`）
6. full 训练（`configs/full.yaml`）
7. full 评估
8. 导出 Ollama 并做回归问答

## 10. 结果记录模板

每次实验可记录如下：

| Run | Config | Train samples | Val samples | Test samples | Final loss | Pass rate | Hallucinated order ID | Missing confirmation | Notes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| smoke-001 | smoke.yaml |  |  |  |  |  |  |  |  |
| full-001 | full.yaml |  |  |  |  |  |  |  |  |

## 11. 常见问题

- 出现 `No Python at ...` 或 `uv run` 权限错误：
  - 设置 `UV_PYTHON_INSTALL_DIR` 到仓库可写目录
  - 执行 `uv python install 3.10`
  - 执行 `uv sync`
- Windows 上 `bitsandbytes` 异常：建议优先在 WSL2/Linux 跑 QLoRA。
- CUDA OOM：
  - 降低 `max_seq_len`
  - 增大 `gradient_accumulation_steps`
  - 保持 `batch size=1`
- 评估太慢：
  - 降低 `--max-new-tokens`
  - 使用 GPU 评估而不是 CPU
- 训练一开始就很慢，且日志里出现 `bitsandbytes/backends/cpu`：
  - 先检查是否装成了 CPU 版 torch：
    ```powershell
    uv run python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
    ```
  - 若输出类似 `2.x.x+cpu False`，请重装 CUDA 版 torch（示例，CUDA 12.1）：
    ```powershell
    uv pip uninstall -y torch torchvision torchaudio
    uv pip install --index-url https://download.pytorch.org/whl/cu121 torch torchvision torchaudio
    ```
  - 安装后再次确认 `torch.cuda.is_available()` 为 `True` 再训练。

## 12. 合规提示

用于生产前，请确认数据许可和商用合规，尤其是 Bitext 数据集的 `CDLA-Sharing-1.0` 条款。

## 13. 生成中文 hard 训练/评测集（Ollama 本地 9B）

用于补充以下场景：

- 中文口语 + 错别字 + 混合意图
- 订单号缺失但要求直接退款/取消
- 需要澄清关键信息的多轮问题

生成命令（默认模型 `qwen3.5:9b`）：

```powershell
cd LoRA
uv run python scripts/generate_zh_hardset.py `
  --ollama-model qwen3.5:9b `
  --train-size 300 `
  --eval-size 80 `
  --train-out-dir data/processed/zh_hard `
  --eval-out configs/eval_prompts_zh_hard_80.jsonl `
  --combined-out-dir data/processed/combined_zh_hard
```

输出：

- `data/processed/zh_hard/train.jsonl`
- `data/processed/zh_hard/val.jsonl`
- `data/processed/zh_hard/test.jsonl`
- `configs/eval_prompts_zh_hard_80.jsonl`
- 可选：`data/processed/combined_zh_hard/{train,val,test}.jsonl`（与原始数据合并）

### base vs tuned 对比（hard 评测集）

```powershell
cd LoRA
uv run python scripts/eval_lora.py `
  --model-dir outputs/smoke/adapter `
  --test-file configs/eval_prompts_zh_hard_80.jsonl `
  --report-file reports/smoke_eval_zh_hard.json
```

新版评测支持附加规则字段：

- `required_any_keywords`（回复必须包含任一关键词）
- `forbidden_keywords`（回复不得包含）

## 14. 最近修正（2026-04-08）

为避免 hard 集评测偏差，脚本已做以下修正：

1. `scripts/generate_zh_hardset.py`
- 修复布尔字段解析：`"false"`、`"0"`、`"no"` 不再被误判为 `True`。
- 覆盖字段：`requires_confirmation`、`must_not_hallucinate_order_id`。

2. `scripts/eval_lora.py`
- 确认规则加入中文关键词：`确认`、`请确认`、`二次确认`、`确认码`、`回复确认` 等。
- 生成回复时仅统计模型新生成内容（不混入输入 prompt）。

### 修正后推荐命令

```powershell
cd LoRA

uv run python scripts/generate_zh_hardset.py `
  --ollama-model qwen3.5:9b `
  --train-size 300 `
  --eval-size 80 `
  --train-out-dir data/processed/zh_hard_v2 `
  --eval-out configs/eval_prompts_zh_hard_80_v2.jsonl `
  --combined-out-dir data/processed/combined_zh_hard_v2

uv run python scripts/eval_lora.py `
  --model-dir outputs/smoke/adapter `
  --test-file configs/eval_prompts_zh_hard_80_v2.jsonl `
  --report-file reports/smoke_eval_zh_hard_v3.json
```

## 15. 大文件数据说明（不入库）

以下原始数据文件体积较大，不提交到 Git（避免超过 GitHub 100MB 限制）：

- `data/ecm/Emotional_train.txt`
- `data/ecm/Emotional_dev.txt`
- `data/ecm2/*.txt`
- `data/E-commerce dataset/*.txt`
- `data/Bitext_Sample_Customer_Support_Training_Dataset_27K_responses-v11.csv`

跨设备使用时，请手动复制上述文件到相同路径，再执行预处理与训练命令。

## 16. QA -> ReAct Agent ���ݺϳɣ��ӿ�ǿ���� + �ֲ������

### 16.1 Ŀ��
- �������� SFT `messages=[system,user,assistant]` �ṹ���䡣
- �� `assistant` תΪ����壺`Thought/Action/Action_Input/Observation/Response`��
- `Observation` ����ģ���������ɣ������ɱ��� schema ģ��ע�룬ȷ��������ʵ�ӿ��ֶ�һ�¡�

### 16.2 �����ļ�
- `configs/react_action_schemas.json`
- `scripts/synthesize_react_data.py`

### 16.3 Action ���˽ӿ�ӳ��
- `query_order_status` -> `GET /api/v1/orders/{order_id}` -> `OrderRead`
- `query_logistics` -> `GET /api/v1/chat/internal/orders-logistics-summary` -> `ChatOrderLogisticsSummaryResponse`
- `query_product_info` -> `GET /api/v1/products` -> `ProductListResponse`
- `create_return_request` -> `POST /api/v1/orders/{order_id}/after-sales` -> `AfterSalesRead`
- `query_refund_status` -> `GET /api/v1/chat/internal/after-sales-summary` -> `ChatAfterSalesSummaryResponse`
- `query_orders_summary` -> `GET /api/v1/chat/internal/orders-summary` -> `ChatOrderSummaryResponse`

### 16.4 Ĭ�Ϸֲ�����
- ����������`1500`
- ������Ŀ��ռ�ȣ���˳�򣩣�
  - `query_order_status`: `28%`
  - `query_logistics`: `17%`
  - `query_product_info`: `20%`
  - `create_return_request`: `18%`
  - `query_refund_status`: `12%`
  - `query_orders_summary`: `5%`
- �鼶�ο�ռ�ȣ�����ͳ�ƶ��գ���`����/���� 45%`��`�ۺ� 35%`��`��Ʒ 20%`

### 16.5 ��������
```powershell
cd LoRA
uv run python scripts/synthesize_react_data.py `
  --schema-config configs/react_action_schemas.json `
  --sample-size 1500 `
  --ollama-model qwen3.5:9b `
  --ollama-base-url http://127.0.0.1:11434 `
  --react-out-dir data/processed/react_agent `
  --combined-out-dir data/processed/combined_react_agent
```

### 16.6 ��Ҫ����
- `--input-train/--input-val/--input-test`: ���� QA �������루Ĭ�� `data/processed/{train,val,test}.jsonl`��
- `--sample-size`: �ϳ�����������Ĭ�� `1500`��
- `--schema-config`: Observation schema �����ļ�·��
- `--max-retries`: �������� Ollama ������Դ�����Ĭ�� `4`��
- `--temperature`: Ollama �����¶ȣ�Ĭ�� `0.4`��
- `--dry-run`: ������ Ollama�����ñ��� fallback �߼����ɣ�������ˮ������

### 16.7 �������
- ReAct �Ӽ���
  - `data/processed/react_agent/train.jsonl`
  - `data/processed/react_agent/val.jsonl`
  - `data/processed/react_agent/test.jsonl`
- �ϲ�����base + react����
  - `data/processed/combined_react_agent/train.jsonl`
  - `data/processed/combined_react_agent/val.jsonl`
  - `data/processed/combined_react_agent/test.jsonl`
- ���ܱ��棺
  - `data/processed/react_agent/summary.json`

### 16.8 ���ս���
1. �ṹУ�飺ȷ��ÿ��������Ϊ����壬�� `Action_Input/Observation` �� JSON ������
2. schema У�飺`summary.json` �� `schema_validation_errors.num_errors` Ӧ�ӽ� `0`��
3. �ֲ�У�飺��� `actual_action_counts` ��Ŀ��ռ��ƫ���������� ��5%����
4. ѵ�����ݣ��� `train_lora.py` �� `train_file/eval_file` ָ�� `react_agent` �� `combined_react_agent` ���������ʼѵ����
