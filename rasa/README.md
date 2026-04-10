# Rasa + Ollama 客服模块

本目录负责电商客服对话能力：
- Rasa 负责 NLU + 对话策略
- Action Server 调用后端接口读取订单/物流/售后数据
- 本地 Ollama（`qwen3.5:2b`）提供闲聊与自然语言补充回复

## 1. 运行前准备
- 已安装 Ollama，并可运行 `qwen3.5:2b`
- 后端接口可访问：`http://127.0.0.1:8000/api/v1`

先拉取模型：
```bash
ollama pull qwen3.5:2b
```

## 2. 环境变量
复制样例文件：

```bash
cd rasa
# Windows PowerShell
Copy-Item .env.sample .env
# Linux/macOS
# cp .env.sample .env
```

关键变量：
- `OLLAMA_BASE_URL`：Ollama 服务地址
- `OLLAMA_CHAT_PATH`：聊天接口路径（默认 `/api/chat`）
- `OLLAMA_MODEL`：模型名（默认 `qwen3.5:2b`）
- `BACKEND_API_URL`：后端 API 根路径
- `FRONTEND_BASE_URL`：前端地址（用于构造可点击链接）
- `RASA_INTERNAL_TOKEN`：与后端内部接口鉴权一致
- `ACTION_HTTP_TIMEOUT_SEC`：Action HTTP 超时

## 3. 安装依赖（uv）
```bash
cd rasa
uv sync
```

## 4. 训练与启动
### 4.1 训练模型
```bash
uv run rasa train --config config.yml --domain domain.yml --data data
```

### 4.2 启动 Rasa Server
```bash
uv run rasa run --enable-api --cors "*" --credentials credentials.yml --endpoints endpoints.yml --port 5005
```

### 4.3 启动 Action Server
```bash
uv run rasa run actions --actions actions --port 5055
```

## 5. 当前对话能力
### 5.1 已支持意图
- 问候、致谢、告别
- 查询我的订单
- 查询物流进度
- 查询售后进度
- 商品推荐
- 闲聊兜底

### 5.2 已实现 Action
- `action_recommend_products`
- `action_query_my_orders`
- `action_query_order_logistics`
- `action_query_after_sales`
- `action_ollama_reply`

以上查询 Action 已升级为结构化输出：在保留简短 `text` 的同时，返回 `json_message.cards`（商品/订单/物流/售后卡片）。

### 5.3 与后端联动接口
- `POST /api/v1/chat/send`（前端 -> 后端 -> Rasa）
- `POST /api/v1/chat/pending-action/decision`（前端二次确认 -> 后端执行）
- `GET /api/v1/chat/internal/orders-summary`
- `GET /api/v1/chat/internal/orders-logistics-summary`
- `GET /api/v1/chat/internal/after-sales-summary`

## 6. 联调顺序
1. 启动 Ollama
2. 启动后端（`8000`）
3. 启动 Rasa Server（`5005`）
4. 启动 Action Server（`5055`）
5. 启动前端并打开 `/chat`

## 7. 说明
- 当前版本不包含 LoRA 微调流程。
- 推荐先完成业务闭环与数据联调，再进入模型微调阶段。

