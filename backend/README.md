# Backend

`backend/` 提供 FastAPI 业务后端，负责认证、商品、购物车、订单、物流、售后、知识库索引，以及聊天编排。

benchmark 相关说明不再放在这里，统一见 [../tests/README.md](../tests/README.md)。

## 目录说明

| 路径 | 作用 |
| --- | --- |
| `app/main.py` | FastAPI 入口，包含主要 API 路由 |
| `app/nexau_orchestrator.py` | 聊天编排与复杂查询分流 |
| `app/auth.py` | 登录、鉴权与 token 处理 |
| `app/database.py` | 数据库连接与 session |
| `app/cache.py` | Redis 缓存封装 |
| `app/models.py` | SQLModel / Pydantic 模型 |
| `scripts/` | 数据库初始化、Redis 初始化、benchmark 数据构建与执行脚本 |
| `benchmarks/` | benchmark 配置、提示词、知识库种子和素材 |

## 依赖服务

后端本身依赖以下服务：

| 服务 | 默认地址 | 用途 |
| --- | --- | --- |
| PostgreSQL | `127.0.0.1:5432` | 业务数据存储 |
| Redis | `127.0.0.1:6379` | 缓存 |
| Rasa Server | `127.0.0.1:5005` | 对话理解与规则链路 |
| Ollama | `127.0.0.1:11434` | 默认 LLM / VLM / embedding 提供方 |
| OpenAI-compatible LLM | `127.0.0.1:8002/v1` | LoRA 推理接口，可由 vLLM 提供 |

## 环境文件

- 使用 `backend/.env` 作为本地环境文件。
- 可从 `backend/.env.sample` 复制一份再修改。
- 常见变量包括数据库连接、Redis 地址、Rasa 地址、Ollama 地址、Agent 模型配置、地图服务配置等。
- 聊天路由新增了 `CHAT_ROUTER_LLM_REVIEW_ENABLED` 与 `CHAT_ROUTER_LLM_REVIEW_THRESHOLD`，用于控制规则型业务意图在 Rasa 命中后的 LLM 二次复核。

## 本地启动

### 1. 安装依赖

```powershell
cd backend
uv sync
```

### 2. 初始化数据库与缓存

Windows:

```powershell
cd backend
.\scripts\init_postgres.ps1
.\scripts\init_redis.ps1
```

Linux / macOS:

```bash
cd backend
./scripts/init_postgres.sh
./scripts/init_redis.sh
```

### 3. 启动默认后端实例

默认实例通常连接 Ollama，监听 `8000`：

```powershell
cd backend
$env:AGENT_LLM_PROVIDER = "ollama"
$env:AGENT_LLM_BASE_URL = "http://127.0.0.1:11434"
$env:AGENT_LLM_MODEL = "qwen3.5:2b"
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 4. 启动 LoRA 后端实例

如果要让后端走 LoRA 推理链路，后端本身仍然是同一套代码，只是模型提供方改成 OpenAI-compatible 接口，通常监听 `8001`：

```powershell
cd backend
$env:AGENT_LLM_PROVIDER = "openai_compat"
$env:AGENT_LLM_BASE_URL = "http://127.0.0.1:8002/v1"
$env:AGENT_LLM_API_KEY = "EMPTY"
$env:AGENT_LLM_MODEL = "qwen3.5-2b-lora"
uv run uvicorn app.main:app --host 127.0.0.1 --port 8001
```

vLLM 的启动方式只在 [../LoRA/README.md](../LoRA/README.md) 维护，这里不重复展开。

## 主要能力

- 用户注册、登录、角色区分。
- 商品列表、详情、购物车、下单、浏览历史。
- 订单查询、物流推进、售后申请、物流投诉。
- 聊天消息路由：事务型命令前置拦截、Rasa 规则链路、以及 LLM Agent / LoRA Agent 的组合编排。
- 规则型业务意图支持 Rasa 命中后的 LLM 复核；复核置信度低于阈值时转交 Agent 处理。
- 知识库文本切分、向量化、索引与检索。
- 图片上传与多模态辅助问答。

## 与其他模块的边界

- 前端如何调用这些接口：见 [../frontend/README.md](../frontend/README.md)。
- Rasa 侧如何运行与训练：见 [../rasa/README.md](../rasa/README.md)。
- LoRA 模型如何训练、导出和提供推理服务：见 [../LoRA/README.md](../LoRA/README.md)。
- benchmark 如何使用后端实例、如何收集结果：见 [../tests/README.md](../tests/README.md)。
