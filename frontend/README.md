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
- 自动识别并渲染消息中的订单/商品链接
- 快捷提问入口（查订单、查物流、查售后、商品推荐）

## 4. 启动
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
