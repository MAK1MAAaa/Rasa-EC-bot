# Rasa

`rasa/` 负责规则型客服能力与 Action Server，同时保留 `rasa_only` benchmark 基线。

## 目录

| 路径 | 说明 |
| --- | --- |
| `data/main/` | 主线 Rasa 训练数据 |
| `data/nlu.yml` | benchmark 基线 NLU 快照 |
| `benchmark/rasa_only/` | `rasa_only` 基线专用配置 |
| `actions/actions.py` | Action Server 逻辑 |
| `domain.yml` | 主线 domain |

## 主线训练与运行

训练：

```powershell
cd rasa
uv sync
uv run rasa train --config config.yml --domain domain.yml --data data/main
```

启动 Rasa Server：

```powershell
cd rasa
uv run rasa run --enable-api --cors "*" --credentials credentials.yml --endpoints endpoints.yml --port 5005
```

启动 Action Server：

```powershell
cd rasa
uv run rasa run actions --actions actions --port 5055
```

## Benchmark 基线

`rasa_only` 使用 `benchmark/rasa_only/` 下的独立配置，不影响主线模型。

训练 benchmark 基线：

```powershell
cd rasa
uv run rasa train `
  --config benchmark/rasa_only/config.yml `
  --domain benchmark/rasa_only/domain.yml `
  --data data/nlu.yml benchmark/rasa_only/rules.yml `
  --out models/benchmark_rasa_only
```

启动 benchmark 基线：

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

## 说明

- benchmark 的正式入口、运行命令和结果分析已迁到 [../benchmark/README.md](../benchmark/README.md)。
- 主线数据与 benchmark 快照数据硬隔离：主线走 `data/main/`，benchmark 基线走 `data/nlu.yml`。
