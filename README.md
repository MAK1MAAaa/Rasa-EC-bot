# Rasa-EC-bot

## Docker 一键启动

该方式会用 Docker Compose 启动前端、FastAPI 后端、Rasa Server、Rasa Action Server、PostgreSQL 和 Redis。Ollama 不在 Compose 内启动，需要你先在宿主机手动启动，并确保容器可通过 `http://host.docker.internal:11434` 访问。

### 启动

```powershell
docker compose up --build
```

默认访问地址：

| 服务 | 地址 |
| --- | --- |
| 前端商城 | `http://localhost:5173` |
| 后端 API | `http://localhost:8000` |
| Rasa Server | `http://localhost:5005` |

首次创建 PostgreSQL volume 时，Compose 会自动执行 `backend/db/init_db.sql` 和 `backend/db/seed_data.sql`。后续再次 `docker compose up` 会复用已有数据，不会自动重置演示数据。

### 可选配置

默认命令不依赖额外环境文件。如需修改端口、模型名、CORS、`FRONTEND_BASE_URL` 或 token，可复制 Docker 样例配置后启动：

```powershell
Copy-Item .env.docker.sample .env.docker
docker compose --env-file .env.docker up --build
```

默认 LLM 配置走宿主机 Ollama：

```text
OLLAMA_BASE_URL=http://host.docker.internal:11434
AGENT_LLM_PROVIDER=ollama
AGENT_LLM_BASE_URL=http://host.docker.internal:11434
AGENT_LLM_MODEL=qwen3.5:2b
```

如果模型名不同，修改 `.env.docker` 中的 `OLLAMA_MODEL`、`AGENT_LLM_MODEL`、`OLLAMA_EMBED_MODEL` 和 `OLLAMA_VLM_MODEL`。

### 重置演示数据

只有显式删除 volume 才会重置 PostgreSQL 和 Redis 数据：

```powershell
docker compose down -v
docker compose up --build
```

### 常见问题

- 如果聊天链路连接 Ollama 失败，先确认宿主机 Ollama 已启动，并可在宿主机访问 `http://127.0.0.1:11434`。
- 如果 Rasa 构建时间较长，这是因为镜像构建阶段会安装 Rasa 依赖并训练模型，避免依赖本地已生成但被 gitignore 的 `rasa/models/`。
- 如果要让另一台设备访问前端，把 `.env.docker` 中的 `FRONTEND_BASE_URL` 改成对方可访问的地址，并按需扩展 `BACKEND_CORS_ALLOW_ORIGINS`。

### Tailscale 远端访问慢

同一 Tailscale 网络里的另一台电脑访问前端时，建议优先使用 Docker Nginx 版本：

```powershell
docker compose up -d
```

前端已做三项远端访问优化：移除 Google Fonts 外链，避免远端浏览器等待外网字体；路由页面按需加载，减少首屏 JavaScript 体积；Docker Nginx 对 `/assets/` 和 `/demo-assets/` 启用 gzip 与缓存头。

## 毕设答辩 HTML PPT

项目新增独立普通 HTML 答辩演示页：`defense-presentation/index.html`。该页面不替换原有 `report_presentation.html`，不依赖 HyperFrames、Vite 或外部 CDN，可直接像 PPT 一样手动翻页讲解毕业设计，内容聚焦电商业务闭环、Rasa + LLM/Agent 混合客服、安全待确认动作、商家端处理闭环和 benchmark 结论。

另有一个动画试验副本：`defense-presentation/index-animated.html`。它用于尝试标题、卡片、流程线和进度条的短入场动画；答辩正式使用时优先选择稳定的 `index.html`，需要更强展示感时再使用动画版。

实现聚焦版：`defense-presentation/index-implementation.html`。该版本从普通版复制而来，重点讲已完成能力、系统设计、关键接口、安全写入机制、商家端闭环和技术实现亮点。

### 打开方式

最简单方式是直接用浏览器打开：

```text
defense-presentation/index.html
```

动画版：

```text
defense-presentation/index-animated.html
```

实现聚焦版：

```text
defense-presentation/index-implementation.html
```

如果希望通过本地 HTTP 地址预览，可在项目根目录运行：

```powershell
python -m http.server 3025
```

然后访问：

```text
http://localhost:3025/defense-presentation/
```

动画版 HTTP 地址：

```text
http://localhost:3025/defense-presentation/index-animated.html
```

实现聚焦版 HTTP 地址：

```text
http://localhost:3025/defense-presentation/index-implementation.html
```

### 翻页

- `ArrowRight`、`PageDown`、空格：下一页。
- `ArrowLeft`、`PageUp`：上一页。
- `Home`：回到第一页。
- `End`：跳到最后一页。
- URL hash 支持直接跳页，例如 `#slide-9`。

### 原版 15 页答辩主线

1. 毕设题目与系统完成情况。
2. 用户端、智能客服和商家端功能范围。
3. 系统分层设计。
4. 实现重点：稳定、真实、可控。
5. 本地演示数据与图片资产。
6. 商品推荐链路。
7. 待确认事务机制。
8. 购物车下单草稿。
9. 订单、物流、售后查询。
10. 售后申请草稿。
11. 用户侧到商家侧的业务流转。
12. 商家工作台闭环。
13. 技术实现亮点。
14. benchmark 与方案选择。
15. 收尾总结。

## 毕设演示数据

`backend/db/seed_data.sql` 内置一套面向答辩演示的中文初始化数据，包含 4 个中文店铺、36 个演示商品，覆盖客服推荐、购物车下单、订单查询、物流查询、售后申请和商家售后处理。商品图、店铺 Logo 和前端缺省商品图均使用 `frontend/public/demo-assets/` 下的本地资源，初始化后商品图不依赖外部图片站点。

### 演示账号

| 角色 | 邮箱 | 密码 | 用途 |
| --- | --- | --- | --- |
| 客户 | `test1@example.com` | `password123` | 推荐、购物车下单、订单查询、物流查询、兼容 benchmark |
| 客户 | `test2@example.com` | `password123` | 已签收订单、售后全状态、物流投诉历史 |
| 商家 | `merchant1@example.com` | `password123` | 数码店订单与待处理售后 |
| 商家 | `merchant3@example.com` | `password123` | 办公店售后同意、处理中状态演示 |
| 商家 | `merchant4@example.com` | `password123` | 户外店售后处理中、已完成状态演示 |

### 初始化命令

Windows:

```powershell
cd backend
.\scripts\init_postgres.ps1
```

macOS / Linux:

```bash
cd backend
bash scripts/init_postgres.sh
```

### 推荐演示话术

聊天推荐默认只返回 1 个最匹配商品，正文推荐和商品卡片保持一致；内部推荐接口仍可通过显式 `limit` 参数支持多商品场景。

```text
推荐一台适合写论文和轻量开发的银色笔记本，预算 6000 以内。
```

```text
我最近看了显示器和笔记本，帮我推荐适合毕业设计答辩准备的商品。
```

### 下单演示话术

`test1@example.com` 购物车预置了同店铺商品，可直接触发下单草稿：

```text
帮我把购物车里的商品下单，地址：北京市海淀区中关村软件园二期 8 号楼，邮箱：test1@example.com
```

### 订单、物流和售后演示话术

```text
帮我查询订单 ORD202603300001 的状态。
```

```text
查询订单 ORD202603300002 的物流进度。
```

```text
申请退货 ORD202603300001，原因：尺寸不合适。
```

```text
查询订单 ORD202603300002 的售后进度。
```

```text
申请换货 ORD202604010001，原因：屏幕边框有磕碰。
```

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
- Redis：后端缓存使用 `redis.asyncio`，兼容 Python 3.10/3.11；配置 `REDIS_URL` 后启动日志应显示 Redis cache connected。
- 聊天跳转链接：`backend/.env` 和 `rasa/.env` 中的 `FRONTEND_BASE_URL` 应改成对外演示地址，而不是 `localhost`。
- 后端 CORS：如果你不只通过 Vite 代理访问后端，而是前端直接跨域请求后端，需要把 `BACKEND_CORS_ALLOW_ORIGINS` 追加 `http://<本机 Tailnet IP>:5173`。

## 说明

- benchmark 相关命令、数据集、结果与分析统一维护在 [benchmark/README.md](benchmark/README.md)。
- 登录用户的服务端记忆以 PostgreSQL 为主存储，Markdown 文件落在 `backend/data/chat_memory/`，仅作为派生产物。
- 后端现在支持主备 LLM 故障切换：主链路出现 `500/超时/连接失败/空响应` 时，会自动切到 `AGENT_LLM_FALLBACK_*` 配置的后备服务。
- 聊天待确认动作的过期时间统一按 UTC 处理，兼容数据库返回的带时区时间，避免阻塞后续 LLM 路由。
- 聊天事务动作会从 `地址:`、`地址为`、`地址是`、`收货地址为` 等表达中提取地址，用于下单和修改收货信息草案。
- 知识库索引请求仍对外使用 `metadata` 字段，后端内部避开 SQLModel 同名属性，启动时不再产生字段遮蔽 warning。
