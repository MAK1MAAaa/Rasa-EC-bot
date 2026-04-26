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

使用 `rasa/.env` 作为本地环境文件，可从 `rasa/.env.sample` 复制：

```powershell
cd rasa
Copy-Item .env.sample .env
```

```bash
cd rasa
cp .env.sample .env
```

当前推荐采用“所有服务都跑在当前 Windows 主机”的方式，因此建议：

- `BACKEND_API_URL=http://127.0.0.1:8000/api/v1`
- `OLLAMA_BASE_URL=http://127.0.0.1:11434`
- `FRONTEND_BASE_URL=http://<本机 Tailnet IP>:5173`
- `RASA_INTERNAL_TOKEN` 与 `backend/.env` 保持一致

说明：

- `BACKEND_API_URL` 和 `OLLAMA_BASE_URL` 都继续指向本机回环地址，不需要改成 Tailnet IP。
- `FRONTEND_BASE_URL` 用于返回给用户的跳转链接，应该指向远端可访问的地址。

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
- Benchmark 基线模型训练、`5006` 端口服务启动和完整 benchmark 流程统一维护在 [../benchmark/README.md](../benchmark/README.md)。
