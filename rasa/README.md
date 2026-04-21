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

## 环境变量

- 仓库根目录下的 `rasa/.env` 已提供 MBA 本机跑 Rasa、台式机远程跑 Ollama 的模板。
- 当前默认启用的是 MagicDNS 写法，远程主机占位符是 `__TAILSCALE_DESKTOP_MAGICDNS__`。
- 同一份文件里保留了 Tailnet IP 备选行，占位符是 `__TAILSCALE_DESKTOP_IP__`。
- 本机链路保持不变：`BACKEND_API_URL=http://127.0.0.1:8000/api/v1`、`FRONTEND_BASE_URL=http://localhost:5173`。
- 远程链路只改 `OLLAMA_BASE_URL`。
- `RASA_INTERNAL_TOKEN` 需要和 `backend/.env` 保持一致。

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
- Benchmark 基线模型训练、5006 端口服务启动和完整 benchmark 流程统一维护在 [`benchmark/README.md`](../benchmark/README.md)。
