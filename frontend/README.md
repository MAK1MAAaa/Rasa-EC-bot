# Rasa-EC-bot Frontend (Vue 3)

前端已覆盖用户商城、商家中心、客服对话三个场景，并与后端/客服系统联通。

## 1. 技术栈
- Vue 3 + Composition API
- Vite
- Pinia
- Vue Router
- Axios
- Tailwind CSS

## 2. 页面与路由
- `/products`：商品列表（分类/价格/库存筛选，支持展开筛选面板）
- `/products/:id`：商品详情
- `/cart`：购物车
- `/checkout`：结算
- `/orders`：订单列表、物流信息、售后申请（退货/换货）
- `/chat`：智能客服
- `/login` / `/register`：登录注册
- `/merchant`：商家中心（商家角色可访问）

## 3. 已实现前端功能
### 3.1 用户端
- 商品搜索、分类筛选、价格区间筛选、仅看有货
- 下单后查看订单、物流路线与预计送达
- 在订单页发起售后并查看售后状态

### 3.2 商家端
- 订单分页与发货操作
- 发货地址管理（新增、默认地址）
- 商品上架与编辑
- 售后请求处理（状态流转）
- 发货成功/失败浮窗提示

### 3.3 客服页
- 对话区布局优化（消息气泡自适应高度）
- 消息区滚动条与历史消息浏览
- 支持结构化卡片消息（商品、订单、物流、售后、待确认操作）
- 自动兼容旧文本消息中的订单/商品链接渲染
- 二次确认改为弹窗确认卡片（确认/取消按钮），无需手动输入确认码
- 快捷提问入口（查订单、查物流、查售后、商品推荐）

## 4. 启动
Windows PowerShell 速查（对应位置：根目录 `README` 第 3.5 节）：

1. 检查现状：`npm.cmd -v` 正常且 `where.exe pnpm` 无结果。
2. 若联网失败（例如代理指向 `127.0.0.1:9`），先清代理：
   `Remove-Item Env:HTTP_PROXY,Env:HTTPS_PROXY,Env:ALL_PROXY -ErrorAction SilentlyContinue`
3. 无管理员权限安装 pnpm：
   `npm.cmd config set prefix "$env:APPDATA\npm"`
   `npm.cmd install -g pnpm`
   `$env:Path += ";$env:APPDATA\npm"`
4. 若 `pnpm` 被执行策略拦截（`PSSecurityException`），先用：
   `pnpm.cmd -v`
5. 持久化 PATH（一次）后重开 PowerShell：
   `$userPath=[Environment]::GetEnvironmentVariable("Path","User"); if($userPath -notlike "*$env:APPDATA\npm*"){[Environment]::SetEnvironmentVariable("Path","$userPath;$env:APPDATA\npm","User")}`

```bash
pnpm install
pnpm dev
```
默认地址：`http://localhost:5173`

## 5. 构建
```bash
pnpm build
```

## 6. 联调要求
- 后端启动：`http://127.0.0.1:8000`
- Rasa Server：`http://127.0.0.1:5005`
- Action Server：`http://127.0.0.1:5055`

## 7. 权限说明
- 未登录可访问：`/products`、`/products/:id`、`/chat`、`/login`、`/register`
- 用户登录后可访问：`/cart`、`/checkout`、`/orders`
- 商家登录后可访问：`/merchant`
- 商家账号不允许访问 `/chat`（导航入口隐藏，手动访问会重定向到 `/merchant`）

## 8. Logistics Map + Shipping UX Enhancements

### 8.1 Frontend Env
Create `.env` from `.env.sample` and configure:

```env
VITE_ENABLE_LOGISTICS_MAP=false
VITE_AMAP_JS_KEY=
VITE_AMAP_SECURITY_JS_CODE=
```

### 8.2 Order Detail Page
- Added map card in logistics panel.
- Map renders only when `VITE_ENABLE_LOGISTICS_MAP=true` and coordinates are available.
- If map SDK/key/network fails, page auto-falls back to text route timeline.

### 8.3 Merchant Page
- Shipping/advance buttons now include animated loading indicator.
- Slow-request hint appears when request lasts over ~1200ms.
- Pending shipment card shows a processing-age badge (`Pending Xh / Xd Xh`) and highlights stale orders.

### 8.4 AMap JS API & SecurityJsCode setup
Frontend env file: `frontend/.env` (copy from `frontend/.env.sample`)

```env
VITE_ENABLE_LOGISTICS_MAP=true
VITE_AMAP_JS_KEY=your_amap_js_key
VITE_AMAP_SECURITY_JS_CODE=your_security_js_code
```

Behavior:
- Map renders only when `VITE_ENABLE_LOGISTICS_MAP=true`.
- `VITE_AMAP_SECURITY_JS_CODE` is injected to `window._AMapSecurityConfig` before JSAPI script load.
- When key/network/sdk fails, UI falls back to text logistics route.

Security recommendations:
- Configure JS key domain whitelist in AMap console.
- Do not place `AMAP_WEB_KEY` in frontend env.
