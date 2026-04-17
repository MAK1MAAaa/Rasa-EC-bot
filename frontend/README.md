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

## 环境变量

- 使用 `frontend/.env` 作为本地环境文件。
- 可从 `frontend/.env.sample` 复制一份再修改。
- 前端通常至少需要配置后端 API 基地址，以及地图服务或实时通信相关地址。

Windows：

```powershell
cd frontend
Copy-Item .env.sample .env
```

macOS / Linux：

```bash
cd frontend
cp .env.sample .env
```

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
- `/chat` 聊天页当前采用固定面板高度与内部滚动设计，聊天区和会话历史区在桌面端保持同高，超长内容会显示滚动条而不是继续把页面撑高。
- `/chat` 的会话历史项采用统一卡片高度，长标题会截断到两行，避免列表项大小不一致。
- `/chat` 的会话历史列表和消息列表都固定从容器顶部连续堆叠，不会在可用高度内被均匀拉散。
- `/chat` 左侧会话标题默认取当前会话的首条用户问题，新建空会话才显示“新会话”。
- benchmark 不直接在前端里执行；相关说明统一放在 [../tests/README.md](../tests/README.md)。
