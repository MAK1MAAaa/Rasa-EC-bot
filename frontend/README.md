# Frontend

`frontend/` 是基于 Vue 3 + Vite 的电商前端，覆盖用户商城、购物车、订单、客服聊天和商家中心。

## 目录说明

| 路径 | 作用 |
| --- | --- |
| `src/views/` | 页面级视图 |
| `src/router/index.ts` | 路由配置与登录态守卫 |
| `src/api/client.ts` | 后端 API 客户端 |
| `src/stores/` | Pinia 状态管理 |
| `src/components/` | 业务组件与基础 UI 组件 |
| `src/lib/` | 前端共享样式工具与通用辅助函数 |
| `src/utils/` | AMap、实时通信等前端工具 |

## 主要页面

| 路由 | 说明 |
| --- | --- |
| `/products` | 商品列表 |
| `/products/:id` | 商品详情 |
| `/cart` | 购物车 |
| `/checkout` | 结算页 |
| `/orders` | 订单列表 |
| `/order/:id` | 订单详情 |
| `/history` | 浏览历史 |
| `/chat` | 客服聊天页 |
| `/merchant` | 商家中心 |
| `/login` / `/register` | 登录与注册 |

## 客服聊天页交互

- 待确认写操作使用后端返回的 `pending_action` 卡片展示摘要和明细，确认/取消按钮只渲染在消息外层 actions 区，避免同一条回复出现两组确认入口。
- 发送文本、上传图片和快捷提问期间，聊天流末尾会显示非持久化的“正在思考”客服气泡；接口成功或失败后自动消失，不会进入 `localStorage` 会话记录。
- 客服聊天发送请求使用 90 秒超时，图片上传请求使用 30 秒超时，长耗时 LLM/VLM 响应期间会继续保持等待态，超时后显示系统错误消息。

## 环境变量

使用 `frontend/.env` 作为本地环境文件，可从 `frontend/.env.sample` 复制：

```powershell
cd frontend
Copy-Item .env.sample .env
```

```bash
cd frontend
cp .env.sample .env
```

当前支持的关键变量：

- `VITE_DEV_HOST`
- `VITE_DEV_PORT`
- `VITE_BACKEND_PROXY_TARGET`
- `VITE_WS_BASE_URL`
- `VITE_ENABLE_LOGISTICS_MAP`
- `VITE_AMAP_JS_KEY`
- `VITE_AMAP_SECURITY_JS_CODE`

其中：

- `VITE_DEV_HOST` 默认 `0.0.0.0`。
- `VITE_DEV_PORT` 默认 `5173`。
- `VITE_BACKEND_PROXY_TARGET` 默认 `http://127.0.0.1:8000`。
- `VITE_WS_BASE_URL` 为空时，会自动使用当前浏览器访问的主机名和端口。

## 本地开发

安装依赖：

```powershell
cd frontend
pnpm install
```

```bash
cd frontend
pnpm install
```

启动开发服务器：

```powershell
cd frontend
pnpm dev
```

```bash
cd frontend
pnpm dev
```

## Tailscale 演示方式

如果所有服务都跑在当前 Windows 主机，推荐这样配置：

```env
VITE_DEV_HOST=0.0.0.0
VITE_DEV_PORT=5173
VITE_BACKEND_PROXY_TARGET=http://127.0.0.1:8000
```

说明：

- Vite 会监听 `0.0.0.0:5173`，因此另一台电脑可以直接访问 `http://<本机 Tailnet IP>:5173`。
- 浏览器请求 `/api` 和 `/ws` 时，会由 Vite 代理到当前 Windows 主机本机的 `127.0.0.1:8000`。
- 这意味着后端、Rasa、Ollama、Redis、PostgreSQL 都不需要为了演示暴露到 Tailnet。
- 如果你切到 LoRA 后端端口 `8001`，只需要把 `VITE_BACKEND_PROXY_TARGET` 改成 `http://127.0.0.1:8001`。

## 构建与预览

构建生产包：

```powershell
cd frontend
pnpm build
```

```bash
cd frontend
pnpm build
```

本地预览：

```powershell
cd frontend
pnpm preview
```

```bash
cd frontend
pnpm preview
```

## 依赖关系

- 前端默认对接 [../backend/README.md](../backend/README.md) 中的 FastAPI 后端。
- 聊天页、订单页和商家中心都依赖后端接口返回的数据结构。
- 如果要让聊天卡片里的商品/订单链接在另一台电脑上可点击，记得把 `backend/.env` 和 `rasa/.env` 里的 `FRONTEND_BASE_URL` 改成 `http://<本机 Tailnet IP>:5173`，不要保留成 `http://localhost:5173`。
