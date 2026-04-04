# Rasa + Ollama 客服子系统

该目录提供一个最小可运行的客服链路：
- Rasa NLU/Policy 负责意图识别与对话路由
- Action Server 负责调用本地 Ollama (`qwen3.5:9b`) 和后端商品接口
- FastAPI 通过 `/api/v1/chat/send` 转发前端消息到 Rasa REST channel

## 1. 准备 Ollama 模型

```bash
ollama pull qwen3.5:9b
ollama run qwen3.5:9b
```

## 2. 配置 `.env`

在 `rasa` 目录下复制环境变量模板：

```bash
cd rasa
cp .env.sample .env
```

Windows PowerShell：

```powershell
cd rasa
Copy-Item .env.sample .env
```

关键变量说明：
- `OLLAMA_BASE_URL`：Ollama 服务地址
- `OLLAMA_CHAT_PATH`：Ollama chat 接口路径（默认 `/api/chat`）
- `OLLAMA_MODEL`：模型名（默认 `qwen3.5:9b`）
- `BACKEND_API_URL`：Action 访问后端商品接口的地址
- `FRONTEND_BASE_URL`：前端地址，用于生成商品/订单跳转链接
- `RASA_INTERNAL_TOKEN`：Rasa 调用后端内部订单接口的鉴权 token（需与 `backend/.env` 保持一致）
- `ACTION_HTTP_TIMEOUT_SEC`：Action 请求超时秒数

## 3. 使用 uv 安装依赖

```bash
cd rasa
uv sync
```

## 4. 训练并启动 Rasa（uv）

在 `rasa` 目录执行：

```bash
uv run rasa train --config config.yml --domain domain.yml --data data
uv run rasa run --enable-api --cors "*" --credentials credentials.yml --endpoints endpoints.yml --port 5005
```

另开一个终端启动 Action Server：

```bash
cd rasa
uv run rasa run actions --actions actions --port 5055
```

## 5. 联调顺序

1. 启动 Ollama
2. 启动 Rasa Server (`5005`) 与 Action Server (`5055`)
3. 启动 FastAPI (`8000`)
4. 启动前端 (`5173`)
5. 在前端 `智能客服` 页面发消息验证

## 6. 兼容模式（非 uv）

如果你不用 uv，也可执行：

```bash
pip install -r requirements.txt
```
