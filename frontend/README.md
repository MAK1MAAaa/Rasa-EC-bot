# Rasa-EC-bot 前端商城（Vue 3）

当前前端已实现电商 MVP 全流程页面：商品浏览、商品详情、购物车、结算、订单查询。

## 1. 技术栈

- Vue 3（Composition API）
- Vite
- Pinia
- Vue Router
- Axios（请求/响应拦截器）
- Tailwind CSS + 自定义样式

## 2. 快速开始

### 2.1 安装依赖
```bash
pnpm install
```

### 2.2 启动开发服务
```bash
pnpm dev
```

访问：`http://localhost:5173`

### 2.3 生产构建
```bash
pnpm build
```

## 3. 页面与路由

### 3.1 公开页面
- `/products` 商品列表
- `/products/:id` 商品详情
- `/login` 登录
- `/register` 注册

### 3.2 受保护页面（需登录）
- `/cart` 购物车
- `/checkout` 结算
- `/orders` 我的订单

### 3.3 路由守卫
- 未登录访问受保护页面会跳转 `/login`
- 已登录访问 `/login` / `/register` 会跳转 `/products`

## 4. 本次新增功能（完整）

### 4.1 应用壳
- 顶部导航（品牌、商品、购物车、我的订单）
- 购物车角标实时显示数量
- 登录态下显示用户名与退出按钮

### 4.2 商品模块
- 商品列表分页展示
- 关键词搜索、分类筛选
- 商品详情页（图片、描述、库存、价格）

### 4.3 购物车模块
- 加入购物车
- 调整商品数量
- 删除商品
- 动态汇总总件数与总金额

### 4.4 结算与订单
- 结算页填写收货地址与联系邮箱
- 提交订单（模拟支付）
- 我的订单列表与订单详情（含明细）

## 5. 状态管理（Pinia）

### 5.1 `auth` store
- 保存 token 与用户信息
- 启动时恢复登录态
- 提供 `initialize/fetchMe/clearAuth`

### 5.2 `cart` store
- 保存购物车条目、总件数、总金额
- 提供 `refreshCart/addToCart/updateItem/removeItem`

## 6. 网络层说明

- Axios 基础路径：`/api/v1`
- 请求拦截器：自动注入 Bearer Token
- 响应拦截器：遇到 401 自动清理 token 并跳转登录页

## 7. 联调前提

1. 后端已启动：`http://localhost:8000`
2. 数据库已按 `backend/db/init_db.sql` 与 `backend/db/seed_data.sql` 初始化
3. 可用测试账号：`test1@example.com / password123`

## 8. 推荐验证路径

1. 登录账号后进入商品页
2. 搜索商品并进入详情页
3. 加入购物车并调整数量
4. 去结算页提交订单
5. 在订单页查看新订单及明细

## 9. 目录结构（关键）

- `src/views/`：页面组件（Login/Register/Products/ProductDetail/Cart/Checkout/Orders）
- `src/stores/`：Pinia 状态（`auth.ts`、`cart.ts`）
- `src/api/`：Axios 客户端与拦截器
- `src/components/`：公共组件（当前含顶部导航）
- `src/router/`：路由与路由守卫
