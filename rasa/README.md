# Rasa + 后端联调客服模块

本目录负责电商客服对话能力，当前包含两种运行形态：

- 默认联调形态：Rasa 负责规则意图与 Action，后端负责 Fast Router + Agent 路由
- 纯 Rasa 对照形态：用于接口级 benchmark，显式禁用 `action_ollama_reply`

## 1. 当前职责

- Rasa：意图识别、规则策略、基础对话流转
- Action Server：调用后端内部接口读取订单、物流、售后与商品数据
- 商品推荐 Action 已改为调用后端个性化推荐接口，登录用户会自动带上历史浏览画像
- Ollama：在默认联调形态中承担 `action_ollama_reply` 的闲聊兜底与自然语言补充
- 复杂问题 Agent：由后端按 `AGENT_LLM_*` 配置处理，默认可接 OpenAI-compatible / vLLM 的 LoRA 模型

默认模型约定：

- Rasa Action fallback 模型：`OLLAMA_MODEL=qwen3.5:2b`
- 复杂问题 Agent 模型：由后端 `AGENT_LLM_*` 控制，默认推荐通过 OpenAI-compatible / vLLM 接入 `qwen3.5-2b-lora`
- 兼容说明：旧后端若仍保留 `AGENT_OLLAMA_*` 兼容字段，可继续读取，但不再作为主文档路径

## 2. 运行前准备

- 已安装 Ollama，并可运行 `qwen3.5:2b`
- 后端接口可访问：`http://127.0.0.1:8000/api/v1`
- 若后端 `AGENT_LLM_PROVIDER=openai_compat`，还需先启动对应的 OpenAI-compatible / vLLM 服务
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

- 以下变量由 `rasa/.env.sample` 提供，供 Rasa Server 与 Action Server 使用。
- 复杂问题 Agent 的 `AGENT_LLM_*` 配置位于 `backend/.env`，本目录不直接读取。
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

在新版客服链路多轮会话 benchmark 中，`rasa_only` 主要用于规则链路对照，默认只覆盖其真实支持能力：

- 支持：基础推荐、登录后订单查询、物流查询、售后进度查询、卡片输出
- 不支持：知识库检索、图片上传分析、待确认写操作、确认/取消决策链路

这些不支持能力在 benchmark 中会被标记为 `unsupported/na`，进入覆盖率统计，但不按系统失败计入主成功率。

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

### 8.1 新增推荐接口
- `GET /api/v1/chat/internal/product-recommendations`
- `action_recommend_products` 会把当前用户 `user_id`、原始 query 与识别出的类目一起传给后端。
- 后端会统一按“显式类目/关键词优先，历史浏览偏好加权次之，再按销量、评分、上架时间排序”返回商品卡片。

## 9. 联调顺序

1. 启动 Ollama（用于 `action_ollama_reply`）
2. 若后端使用 `AGENT_LLM_PROVIDER=openai_compat`，先启动对应的 OpenAI-compatible / vLLM 服务
3. 启动后端
4. 启动 Rasa Server（默认 `5005`）
5. 启动 Action Server（默认 `5055`）
6. 启动前端并打开 `/chat`

若要跑系统形态 benchmark，再额外启动：

- 纯 Rasa Server：`5006`
- LoRA 后端实例：`8001`

当前 benchmark 已从旧的 3 个单轮场景升级为 6 个客服场景族、多轮步骤执行和能力矩阵判定。Rasa 侧只需要继续保证 `benchmark/rasa_only/` 资产与真实规则能力对齐，不要为了 benchmark 人为补入图片、知识库或待确认写操作能力。

## 10. 说明

- LoRA 训练与导出流程位于 `LoRA/`，不在本目录执行。
- 若要做论文对照实验，请优先阅读根目录与 `backend/README.md` 中的 benchmark 章节。
- 当前默认推荐的复杂 Agent 推理链路见 `LoRA/README.md` 与 `backend/README.md` 中的 vLLM / OpenAI-compatible 配置章节。
