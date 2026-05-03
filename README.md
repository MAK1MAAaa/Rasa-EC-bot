# Rasa-EC-bot

电商客服实验项目，包含前端商城、FastAPI 后端、Rasa 助手、LoRA 训练链路，以及独立 benchmark 工程。

## 仓库结构

| 模块 | 路径 | 说明 |
| --- | --- | --- |
| 前端 | `frontend/` | Vue 3 + Vite 商城与客服页面 |
| 后端 | `backend/` | FastAPI 服务，负责商品、订单、聊天路由、记忆与知识库 |
| Rasa | `rasa/` | 主线规则助手与 `rasa_only` benchmark 基线 |
| LoRA | `LoRA/` | LoRA 训练与推理相关资源 |
| Benchmark | `benchmark/` | benchmark 唯一正式入口，独立 uv 工程 |
| 测试 | `tests/` | 普通代码测试，不承载 benchmark 流程 |

## 文档入口

- [backend/README.md](backend/README.md)
- [frontend/README.md](frontend/README.md)
- [rasa/README.md](rasa/README.md)
- [LoRA/README.md](LoRA/README.md)
- [benchmark/README.md](benchmark/README.md)
- [tests/README.md](tests/README.md)

## 客服聊天交互

- `/chat` 的待确认写操作由后端返回 `pending_action` 卡片和 `pending_action_decision` actions；前端只在消息外层 actions 区展示确认/取消入口，卡片本身只展示操作摘要和明细。
- 用户发送文本、图片或快捷提问后，客服页会在接口响应前显示非持久化的“正在思考”气泡；该气泡不写入本地会话历史。
- 客服聊天发送接口单独使用 90 秒前端超时，图片上传使用 30 秒超时，避免后端 LLM/VLM 仍在处理时被 15 秒全局请求超时提前中断。

## 常用端口

| 服务 | 端口 | 说明 |
| --- | --- | --- |
| 前端 | `5173` | 商城与客服页面 |
| 后端 | `8000` | Rasa + LLM 主链路 |
| 后端 LoRA | `8001` | Rasa + LoRA LLM 主链路 |
| vLLM / OpenAI-compatible | `8002` | LoRA 推理服务 |
| Rasa Server | `5005` | 主线 Rasa |
| Rasa Action Server | `5055` | Rasa Action Server |
| Rasa benchmark 基线 | `5006` | `rasa_only` benchmark 基线 |
| PostgreSQL | `5432` | 主数据库 |
| Redis | `6379` | 缓存、锁与会话辅助 |
| Ollama | `11434` | 本机模型服务 |

## 当前推荐演示拓扑

当前更推荐使用“所有服务都跑在当前 Windows，本机只通过 Tailscale 暴露前端”的方式：

- 前端、后端、Rasa、Redis、PostgreSQL、Ollama、vLLM 都启动在同一台 Windows 主机。
- 另一台电脑只访问这台主机的 Tailscale 地址：`http://<本机 Tailnet IP>:5173`。
- 前端通过 Vite 代理把 `/api` 和 `/ws` 转到当前主机本机的 `127.0.0.1:8000`。
- 后端到 Rasa、Ollama、Redis、PostgreSQL 的访问都继续走 `127.0.0.1`，不要为了演示改成 Tailnet IP。

这套模式下：

- 更不容易出现 “开启 Tailscale 后 Ollama 被拦截” 的问题，因为 Ollama 不需要外放。
- 另一台电脑只需要能访问 `5173`，其余端口都不必对 Tailnet 暴露。
- 聊天卡片和订单链接要能在远端可用，需要把 `backend/.env` 和 `rasa/.env` 中的 `FRONTEND_BASE_URL` 改成 `http://<本机 Tailnet IP>:5173`。

## 快速启动

### Windows

```powershell
cd frontend
pnpm install
Copy-Item .env.sample .env -Force
pnpm dev
```

```powershell
cd backend
Copy-Item .env.sample .env -Force
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```powershell
cd rasa
Copy-Item .env.sample .env -Force
uv sync
uv run rasa run --enable-api --cors "*" --credentials credentials.yml --endpoints endpoints.yml --port 5005
```

```powershell
cd rasa
uv run rasa run actions --actions actions --port 5055
```

### macOS / Linux

```bash
cd frontend
cp .env.sample .env
pnpm install
pnpm dev
```

```bash
cd backend
cp .env.sample .env
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```bash
cd rasa
cp .env.sample .env
uv sync
uv run rasa run --enable-api --cors "*" --credentials credentials.yml --endpoints endpoints.yml --port 5005
```

```bash
cd rasa
uv run rasa run actions --actions actions --port 5055
```

## 关键配置提醒

- 前端代理：`frontend/.env` 中的 `VITE_BACKEND_PROXY_TARGET` 默认是 `http://127.0.0.1:8000`。
- 后端主 LLM：`backend/.env` 中的 `AGENT_LLM_*`。
- 后端后备 LLM：`backend/.env` 中的 `AGENT_LLM_FALLBACK_*`。
- LLM provider：支持 `ollama`、`openai_compat`；`openai` 和 `deepseek` 会按 OpenAI-compatible 别名处理。
- Ollama：当前推荐保持 `OLLAMA_BASE_URL=http://127.0.0.1:11434`。
- 聊天跳转链接：`backend/.env` 和 `rasa/.env` 中的 `FRONTEND_BASE_URL` 应改成对外演示地址，而不是 `localhost`。
- 后端 CORS：如果你不只通过 Vite 代理访问后端，而是前端直接跨域请求后端，需要把 `BACKEND_CORS_ALLOW_ORIGINS` 追加 `http://<本机 Tailnet IP>:5173`。

## 说明

- benchmark 相关命令、数据集、结果与分析统一维护在 [benchmark/README.md](benchmark/README.md)。
- 登录用户的服务端记忆以 PostgreSQL 为主存储，Markdown 文件落在 `backend/data/chat_memory/`，仅作为派生产物。
- 后端现在支持主备 LLM 故障切换：主链路出现 `500/超时/连接失败/空响应` 时，会自动切到 `AGENT_LLM_FALLBACK_*` 配置的后备服务。
- 聊天待确认动作的过期时间统一按 UTC 处理，兼容数据库返回的带时区时间，避免阻塞后续 LLM 路由。
- 聊天事务动作会从 `地址:`、`地址为`、`地址是`、`收货地址为` 等表达中提取地址，用于下单和修改收货信息草案。
- 知识库索引请求仍对外使用 `metadata` 字段，后端内部避开 SQLModel 同名属性，启动时不再产生字段遮蔽 warning。
