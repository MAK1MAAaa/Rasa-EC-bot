# Rasa-EC-bot

电商场景智能客服实验项目，包含前端商城、FastAPI 后端、Rasa 助手、LoRA 训练链路，以及独立的 benchmark 与结果分析工具。

## 项目结构

| 模块 | 目录 | 作用 |
| --- | --- | --- |
| 前端 | `frontend/` | Vue 3 + Vite 电商界面，包含商品、购物车、订单、商家中心与客服页 |
| 后端 | `backend/` | FastAPI 服务，负责用户认证、商品与订单接口、聊天编排、知识库与内部 benchmark 脚本 |
| Rasa | `rasa/` | Rasa 助手运行时与 Action Server，承担规则对话和 `rasa_only` 基线 |
| LoRA | `LoRA/` | Qwen3.5-2B 的 QLoRA 训练、评测、导出与 vLLM / Ollama 适配 |
| 测试与实验 | `tests/` | 单元测试、benchmark 数据归档、结果目录与结果后分析脚本 |

## 文档导航

- [backend/README.md](backend/README.md)：后端接口、依赖服务和运行方式。
- [frontend/README.md](frontend/README.md)：前端页面、环境变量和开发命令。
- [rasa/README.md](rasa/README.md)：Rasa 助手训练、运行与 benchmark 基线模型。
- [LoRA/README.md](LoRA/README.md)：LoRA 训练、导出与 vLLM 服务。
- [tests/README.md](tests/README.md)：测试、benchmark、实验数据归档与结果分析。

## 服务拓扑

| 服务 | 默认端口 | 说明 |
| --- | --- | --- |
| PostgreSQL | `5432` | 后端业务数据 |
| Redis | `6379` | 缓存与会话辅助 |
| 前端 | `5173` | 开发环境 UI |
| 后端主实例 | `8000` | 默认业务后端 |
| 后端 LoRA 实例 | `8001` | 指向 OpenAI-compatible / vLLM 的后端实例 |
| vLLM | `8002` | LoRA 模型推理服务，建议在 WSL 中启动 |
| Rasa Server | `5005` | 主 Rasa API |
| Rasa Action Server | `5055` | 自定义动作服务 |
| Rasa benchmark 基线 | `5006` | `rasa_only` 独立基线实例 |

## 约定

- benchmark 说明只保留在 `tests/README.md`，其他 README 只做链接，不重复描述。
- 模块 README 只覆盖本模块职责、依赖和命令，不重复其他模块的实现细节。
- benchmark 结果目录与实验数据目录都放在 `tests/` 下统一管理。
- 主线 Rasa 训练数据与 benchmark 基线数据已拆分维护：主线走 `rasa/data/main/`，benchmark 继续复用 `rasa/data/nlu.yml` 快照。
- 登录用户的聊天服务端记忆已统一落在 PostgreSQL，并在 `backend/data/chat_memory/` 下派生会话级与用户级 Markdown 快照；匿名用户仍只保留前端本地会话。
