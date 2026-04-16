# Backend

`backend/` 提供 FastAPI 服务，负责认证、商品与订单接口、聊天路由、Rasa/LLM 协同、服务端记忆、知识库与附件处理。

## 目录

| 路径 | 说明 |
| --- | --- |
| `app/main.py` | FastAPI 主入口 |
| `app/auth.py` | 认证逻辑 |
| `app/database.py` | 数据库连接与会话 |
| `app/cache.py` | Redis 访问 |
| `app/models.py` | SQLModel / Pydantic 模型 |
| `db/` | 初始化 SQL 与数据库脚本 |
| `scripts/` | Postgres、Redis 等初始化脚本 |
| `data/chat_memory/` | 运行时 Markdown 记忆派生文件 |

## 启动

```powershell
cd backend
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

LoRA 版本通常运行在 `8001`：

```powershell
cd backend
$env:AGENT_LLM_PROVIDER = "openai_compat"
$env:AGENT_LLM_BASE_URL = "http://127.0.0.1:8002/v1"
$env:AGENT_LLM_API_KEY = "EMPTY"
$env:AGENT_LLM_MODEL = "qwen3.5-2b-lora"
uv run uvicorn app.main:app --host 127.0.0.1 --port 8001
```

## 关键环境变量

- `CHAT_ROUTER_LLM_REVIEW_ENABLED`
- `CHAT_ROUTER_LLM_REVIEW_THRESHOLD`
- `CHAT_MEMORY_COMPACT_MESSAGE_THRESHOLD`
- `CHAT_MEMORY_COMPACT_CHAR_THRESHOLD`
- `CHAT_MEMORY_RECENT_WINDOW_MESSAGES`
- `CHAT_MEMORY_AGENT_RECENT_MESSAGES`
- `CHAT_MEMORY_LOCK_TTL_SEC`

## 说明

- benchmark 已经迁到根目录 `benchmark/`，相关命令与结果分析统一见 [../benchmark/README.md](../benchmark/README.md)。
- 后端仍然是 benchmark 中 `rasa_plus_llm` 与 `rasa_plus_lora_llm` 两套系统的承载服务。
