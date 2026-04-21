# Rasa-EC-bot

电商客服实验项目，包含前端商城、FastAPI 后端、Rasa 助手、LoRA 训练链路，以及独立的 benchmark 工程。

## 仓库结构

| 模块 | 路径 | 说明 |
| --- | --- | --- |
| 前端 | `frontend/` | Vue 3 + Vite 商城与客服页面 |
| 后端 | `backend/` | FastAPI 服务，负责商品、订单、聊天路由、记忆与知识库 |
| Rasa | `rasa/` | 主线规则助手与 `rasa_only` benchmark 基线 |
| LoRA | `LoRA/` | LoRA 训练与推理相关资源 |
| Benchmark | `benchmark/` | benchmark 唯一正式入口，独立 uv 工程 |
| 测试 | `tests/` | 普通代码测试，不再承载 benchmark 流程 |

## 文档入口

- [backend/README.md](backend/README.md)
- [frontend/README.md](frontend/README.md)
- [rasa/README.md](rasa/README.md)
- [LoRA/README.md](LoRA/README.md)
- [benchmark/README.md](benchmark/README.md)
- [tests/README.md](tests/README.md)

## 常用入口命令

完整启动顺序和依赖说明分别维护在各子模块 README 中，这里只保留最常用的进入命令。

### Windows

```powershell
cd frontend
pnpm install
pnpm dev
```

```powershell
cd backend
Copy-Item .env.sample .env
uv sync
```

```powershell
cd rasa
uv sync
```

```powershell
cd benchmark
uv sync
```

### macOS / Linux

```bash
cd frontend
pnpm install
pnpm dev
```

```bash
cd backend
cp .env.sample .env
uv sync
```

```bash
cd rasa
uv sync
```

```bash
cd benchmark
uv sync
```

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

## Tailscale 跨机启动分工

当前仓库默认采用这一套跨机演示拓扑：

- MBA 负责前端、后端和主线 Rasa。
- 台式机负责数据库、缓存和模型服务。

### MBA 上启动

| 服务 | 端口 | 说明 |
| --- | --- | --- |
| 前端 | `5173` | `frontend/` 的 Vite 开发服务 |
| 后端基础版或 LoRA 版 | `8000` 或 `8001` | 二选一；都跑在 MBA，本机继续连 `127.0.0.1:5005` 的 Rasa |
| Rasa Server | `5005` | 主线 Rasa 服务 |
| Rasa Action Server | `5055` | 主线 Action Server |

补充说明：

- `backend/.env` 里的 `RASA_SERVER_URL`、`FRONTEND_BASE_URL` 保持指向 MBA 本机。
- `rasa/.env` 里的 `BACKEND_API_URL`、`FRONTEND_BASE_URL` 也保持指向 MBA 本机。
- 如果要跑 benchmark，`benchmark/` 命令和 `5006` 的 benchmark 基线通常也放在 MBA 上启动，不放到台式机。

### 台式机上启动

| 服务 | 端口 | 说明 |
| --- | --- | --- |
| PostgreSQL | `5432` | `backend/.env` 的 `DATABASE_URL` 指向这里 |
| Redis | `6379` | `backend/.env` 的 `REDIS_URL` 指向这里；用于缓存、锁和会话辅助 |
| Ollama | `11434` | `backend/.env` 和 `rasa/.env` 的 `OLLAMA_BASE_URL` 指向这里 |
| vLLM / OpenAI-compatible | `8002` | `backend/.env` 的 `AGENT_LLM_BASE_URL` 指向这里 |

补充说明：

- Ollama 需要监听 `0.0.0.0:11434`，否则 MBA 无法通过 Tailscale 访问。
- vLLM 继续保持 `--host 0.0.0.0 --port 8002` 即可。
- Redis 默认仍是本地安全模式；只有当 MBA 需要访问台式机 Redis 时，才需要显式配置 `REDIS_BIND_ADDRESS`、`REDIS_PROTECTED_MODE`、`REDIS_PASSWORD`。
- Windows 防火墙建议只对 MBA 的 Tailnet IP 或 Tailscale 网卡放行 `11434`、`8002`、`5432`、`6379`。

## 说明

- benchmark 相关命令、数据集、结果与分析已经统一迁到 [benchmark/README.md](benchmark/README.md)。
- 当前 benchmark 正式结论改为 `shared_core` / `agent_extension` 双榜，不再输出单一综合冠军。
- benchmark 默认并发固定为 `1`，时延与并发数据只保留在原始结果中，不参与正式排序。
- benchmark 运行前需要先恢复事务基线数据，恢复脚本位于 `benchmark/sql/reset_benchmark_state.sql`。
- 后端 agent prompt 已外置到 `backend/prompts/*.md`，benchmark 运行结果会记录 prompt 文件路径与 hash。
- 主线 Rasa 训练数据位于 `rasa/data/main/`，benchmark 基线继续使用 `rasa/data/nlu.yml` 快照，二者隔离维护。
- 登录用户的服务端记忆以 PostgreSQL 为主存储，Markdown 文件落在 `backend/data/chat_memory/`，仅作为派生产物。
- 后端商品推荐已补上显式预算、颜色和常见规格词（如 `Type-C`、`27 寸`）的约束解析与候选过滤，避免把不满足条件的商品混进推荐结果。
- 仓库已补充一套 Tailscale 跨机演示用的 `backend/.env` 和 `rasa/.env` 本地模板：默认走 MagicDNS，占位符可切换为 Tailnet IP，适合 MBA 本机跑前后端/Rasa、台式机远程跑模型与数据库。
- Redis Docker 启动脚本已支持 `REDIS_BIND_ADDRESS`、`REDIS_PROTECTED_MODE`、`REDIS_PASSWORD` 三个可选变量；默认行为不变，只有显式开启时才用于 Tailscale 跨机调试。
- 前端 Vite 开发服务器现在默认监听 `0.0.0.0:5173`；如果整套服务都跑在台式机上，MBA 只需要访问 `http://<台式机 Tailnet IP>:5173`，前端代理会继续转发到台式机本机 `localhost:8000`。
