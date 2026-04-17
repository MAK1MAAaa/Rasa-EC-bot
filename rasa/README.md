# Rasa

`rasa/` 负责主线规则型客服能力和 Action Server。

## 目录

| 路径 | 说明 |
| --- | --- |
| `data/main/` | 主线 Rasa 训练数据 |
| `data/nlu.yml` | NLU 快照数据 |
| `actions/actions.py` | Action Server 逻辑 |
| `config.yml` | 主线配置 |
| `domain.yml` | 主线 domain |
| `endpoints.yml` | Rasa 外部依赖配置 |
| `credentials.yml` | 渠道配置 |

## 安装依赖

Windows：

```powershell
cd rasa
uv sync
```

macOS / Linux：

```bash
cd rasa
uv sync
```

## 训练主线模型

Windows：

```powershell
cd rasa
uv run rasa train --config config.yml --domain domain.yml --data data/main
```

macOS / Linux：

```bash
cd rasa
uv run rasa train --config config.yml --domain domain.yml --data data/main
```

## 启动主线 Rasa Server

Windows：

```powershell
cd rasa
uv run rasa run --enable-api --cors "*" --credentials credentials.yml --endpoints endpoints.yml --port 5005
```

macOS / Linux：

```bash
cd rasa
uv run rasa run --enable-api --cors "*" --credentials credentials.yml --endpoints endpoints.yml --port 5005
```

## 启动 Action Server

Windows：

```powershell
cd rasa
uv run rasa run actions --actions actions --port 5055
```

macOS / Linux：

```bash
cd rasa
uv run rasa run actions --actions actions --port 5055
```

## 说明

- 本 README 只覆盖主线 Rasa 的训练与运行。
- Benchmark 基线模型训练、5006 端口服务启动和完整 benchmark 流程统一维护在 [`benchmark/README.md`](/D:/Github/Rasa-EC-bot/benchmark/README.md)。
