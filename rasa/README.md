# Rasa + Ollama 客服模块

本目录负责电商客服对话能力，当前包含两种运行形态：

- 默认联调形态：Rasa 负责规则意图与 Action，后端负责 Fast Router + Agent 路由
- 纯 Rasa 对照形态：用于接口级 benchmark，显式禁用 `action_ollama_reply`

## 1. 当前职责

- Rasa：意图识别、规则策略、基础对话流转
- Action Server：调用后端内部接口读取订单、物流、售后与商品数据
- Ollama：在默认联调形态中承担闲聊兜底与自然语言补充

默认模型约定：

- 规则链路兜底模型：`qwen3.5:2b`
- 复杂问题的 Agent 模型由后端 `AGENT_OLLAMA_MODEL` 控制，可切到 `qwen3.5:2b-lora`

## 2. 运行前准备

- 已安装 Ollama，并可运行 `qwen3.5:2b`
- 后端接口可访问：`http://127.0.0.1:8000/api/v1`
- 若要跑系统形态 benchmark，还需按根 README 额外启动纯 Rasa 实例和第二个后端实例

拉取默认模型：

```bash
ollama pull qwen3.5:2b
```

## 3. 环境变量

复制样例文件：

```bash
cd rasa
# Windows PowerShell
Copy-Item .env.sample .env
# Linux/macOS
# cp .env.sample .env
```

关键变量：

- `OLLAMA_BASE_URL`
- `OLLAMA_CHAT_PATH`
- `OLLAMA_MODEL`
- `BACKEND_API_URL`
- `FRONTEND_BASE_URL`
- `RASA_INTERNAL_TOKEN`
- `ACTION_HTTP_TIMEOUT_SEC`

## 4. 安装依赖

```bash
cd rasa
uv sync
```

## 5. 默认联调形态

### 5.1 训练默认模型

```bash
uv run rasa train --config config.yml --domain domain.yml --data data
```

### 5.2 启动 Rasa Server

```bash
uv run rasa run --enable-api --cors "*" --credentials credentials.yml --endpoints endpoints.yml --port 5005
```

### 5.3 启动 Action Server

```bash
uv run rasa run actions --actions actions --port 5055
```

## 6. 纯 Rasa Benchmark 形态

`rasa_only` 对照实验不允许使用 `action_ollama_reply`，请使用独立 benchmark 配置：

- `benchmark/rasa_only/config.yml`
- `benchmark/rasa_only/domain.yml`
- `benchmark/rasa_only/rules.yml`

训练：

```bash
uv run rasa train \
  --config benchmark/rasa_only/config.yml \
  --domain benchmark/rasa_only/domain.yml \
  --data data/nlu.yml benchmark/rasa_only/rules.yml \
  --out models/benchmark_rasa_only
```

启动：

```bash
uv run rasa run \
  --model models/benchmark_rasa_only \
  --enable-api \
  --cors "*" \
  --credentials credentials.yml \
  --endpoints endpoints.yml \
  --port 5006
```

Action Server 仍复用：

```bash
uv run rasa run actions --actions actions --port 5055
```

## 7. 当前对话能力

### 7.1 已支持意图

- 问候、致谢、告别
- 查询我的订单
- 查询物流进度
- 查询售后进度
- 商品推荐
- 闲聊兜底

### 7.2 已实现 Action

- `action_recommend_products`
- `action_query_my_orders`
- `action_query_order_logistics`
- `action_query_after_sales`
- `action_ollama_reply`

查询类 Action 当前支持结构化输出，会返回商品、订单、物流、售后卡片。

## 8. 与后端联动接口

- `POST /api/v1/chat/send`
- `POST /api/v1/chat/upload-image`
- `POST /api/v1/chat/pending-action/decision`
- `GET /api/v1/chat/internal/orders-summary`
- `GET /api/v1/chat/internal/orders-logistics-summary`
- `GET /api/v1/chat/internal/after-sales-summary`

路由关系：

- 高频确定性问题：后端优先走 Rasa 规则链路
- 低置信、复杂、多目标问题：后端切到 Agent
- 带图片附件的问题：后端强制走 Agent，不走纯 Rasa 回复

## 9. 联调顺序

1. 启动 Ollama
2. 启动后端
3. 启动 Rasa Server（默认 `5005`）
4. 启动 Action Server（默认 `5055`）
5. 启动前端并打开 `/chat`

若要跑系统形态 benchmark，再额外启动：

- 纯 Rasa Server：`5006`
- LoRA 后端实例：`8001`

## 10. 说明

- LoRA 训练与导出流程位于 `LoRA/`，不在本目录执行。
- 若要做论文对照实验，请优先阅读根目录与 `backend/README.md` 中的 benchmark 章节。
