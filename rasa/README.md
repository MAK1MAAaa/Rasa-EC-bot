# Rasa

`rasa/` 提供规则型助手运行时与 Action Server，用于承担基础对话能力，并支持 `rasa_only` benchmark 基线。

## 目录说明

| 路径 | 作用 |
| --- | --- |
| `data/main/` | 主线 Rasa 训练数据与规则，面向当前系统需求 |
| `data/nlu.yml` | benchmark 基线快照 NLU 数据，供 `rasa_only` 继续复用 |
| `domain.yml` | 域配置 |
| `actions/actions.py` | 自定义动作 |
| `benchmark/rasa_only/` | benchmark 专用 `rasa_only` 配置 |

## 环境文件

- 使用 `rasa/.env` 作为本地环境文件。
- 可从 `rasa/.env.sample` 复制一份再修改。
- 常见变量包括后端 API 地址、Ollama 地址、前端地址和内部 token。

## 安装依赖

```powershell
cd rasa
uv sync
```

## 训练与运行

### 1. 训练默认模型

```powershell
cd rasa
uv run rasa train --config config.yml --domain domain.yml --data data/main
```

主线模型只读取 `data/main/`，不会再复用 benchmark 的快照数据。

### 2. 启动 Rasa Server

```powershell
cd rasa
uv run rasa run --enable-api --cors "*" --credentials credentials.yml --endpoints endpoints.yml --port 5005
```

### 3. 启动 Action Server

```powershell
cd rasa
uv run rasa run actions --actions actions --port 5055
```

## benchmark 基线模型

`rasa_only` 需要使用 `benchmark/rasa_only/` 下的独立配置，不影响默认助手模型。
benchmark 基线继续复用 `data/nlu.yml`，与主线 `data/main/` 硬隔离。

训练：

```powershell
cd rasa
uv run rasa train `
  --config benchmark/rasa_only/config.yml `
  --domain benchmark/rasa_only/domain.yml `
  --data data/nlu.yml benchmark/rasa_only/rules.yml `
  --out models/benchmark_rasa_only
```

运行：

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

Action Server 仍复用 `5055`：

```powershell
cd rasa
uv run rasa run actions --actions actions --port 5055
```

## 与其他模块的边界

- Rasa 的 benchmark 使用方式统一见 [../tests/README.md](../tests/README.md)。
- Action Server 如何访问 FastAPI 后端接口，见 [../backend/README.md](../backend/README.md)。
- 根目录 [../README.md](../README.md) 只保留模块导航，不重复训练命令。
