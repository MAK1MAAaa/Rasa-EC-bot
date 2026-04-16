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

## 本地开发

安装依赖：

```powershell
cd frontend
pnpm install
```

启动开发服务器：

```powershell
cd frontend
pnpm dev
```

构建生产包：

```powershell
cd frontend
pnpm build
```

本地预览：

```powershell
cd frontend
pnpm preview
```

## 依赖关系

- 前端默认对接 [../backend/README.md](../backend/README.md) 中的 FastAPI 后端。
- 聊天页、订单页和商家中心都依赖后端接口返回的数据结构。
- benchmark 不直接在前端里执行；相关说明统一放在 [../tests/README.md](../tests/README.md)。
