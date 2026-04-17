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

## 说明

- benchmark 相关命令、数据集、结果与分析已经统一迁到 [benchmark/README.md](benchmark/README.md)。
- 当前 benchmark 正式结论改为 `shared_core` / `agent_extension` 双榜，不再输出单一综合冠军。
- benchmark 默认并发固定为 `1`，时延与并发数据只保留在原始结果中，不参与正式排序。
- benchmark 运行前需要先恢复事务基线数据，恢复脚本位于 `benchmark/sql/reset_benchmark_state.sql`。
- 后端 agent prompt 已外置到 `backend/prompts/*.md`，benchmark 运行结果会记录 prompt 文件路径与 hash。
- 主线 Rasa 训练数据位于 `rasa/data/main/`，benchmark 基线继续使用 `rasa/data/nlu.yml` 快照，二者隔离维护。
- 登录用户的服务端记忆以 PostgreSQL 为主存储，Markdown 文件落在 `backend/data/chat_memory/`，仅作为派生产物。
- 后端商品推荐已补上显式预算、颜色和常见规格词（如 `Type-C`、`27 寸`）的约束解析与候选过滤，避免把不满足条件的商品混进推荐结果。
