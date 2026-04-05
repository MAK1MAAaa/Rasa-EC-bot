# Rasa-EC-bot 需求文档（当前实现版）

## 0. 文档状态
- 更新时间：2026-04-05
- 适用分支：`main`
- 当前版本定位：电商平台 MVP + 智能客服联动
- 说明：本版本**不包含 LoRA 微调**，仅使用本地 Ollama 推理模型。

## 1. 项目目标
构建一个可运行的电商系统，包含用户端购物、商家端经营、订单物流、售后流程，以及基于 Rasa + LLM 的客服对话能力。

## 2. 当前范围（不含 LoRA）
### 2.1 用户侧
- 注册、登录、身份识别（customer）
- 商品浏览、详情查看、筛选（分类/价格/库存）
- 购物车、下单、订单查询
- 订单内发起售后（退货/换货）
- 客服聊天（订单、物流、售后、推荐）

### 2.2 商家侧
- 与用户共用登录入口，按 `role=merchant` 进入商家中心
- 店铺信息读取
- 发货地址管理（新增、设为默认）
- 商品管理（上架、编辑、上下架、库存）
- 订单列表与手动发货
- 售后请求处理（同意/拒绝/处理中/完成）

### 2.3 智能客服侧
- Rasa 负责意图识别与对话编排
- Action Server 调用后端内部接口获取当前登录用户数据
- 本地 Ollama（`qwen3.5:9b`）用于兜底闲聊与物流文案辅助

## 3. 已实现能力清单
### 3.1 前端（Vue 3）
- 页面：商品列表、商品详情、购物车、结算、我的订单、客服聊天、商家中心
- 客服消息区支持滚动、链接识别、快捷问题
- 订单与客服推荐中可跳转商品/订单链接
- 商家发货与操作反馈使用顶部浮窗提示

### 3.2 后端（FastAPI）
- JWT 鉴权、用户角色隔离（customer/merchant）
- 完整电商数据 API（商品、购物车、订单、物流、售后）
- 客服内部接口：
  - `/api/v1/chat/internal/orders-summary`
  - `/api/v1/chat/internal/orders-logistics-summary`
  - `/api/v1/chat/internal/after-sales-summary`
- 商家发货支持默认地址与物流预测结果落库

### 3.3 对话系统（Rasa + Actions）
- 已覆盖意图：问候、订单帮助、物流帮助、售后帮助、商品推荐、闲聊
- Action 通过 metadata 识别当前是否登录并绑定用户查询
- 对话回复可包含订单/商品链接

## 4. 技术架构
- 前端：Vue 3 + Vite + Pinia + Vue Router + Tailwind CSS
- 后端：FastAPI + SQLModel + SQLAlchemy Async + PostgreSQL
- 缓存：Redis
- 对话：Rasa Open Source + Rasa SDK Action Server
- 本地模型：Ollama + `qwen3.5:9b`

## 5. Redis 设计与实现（本次补全）
### 5.1 目标
降低高频查询接口的数据库压力，提升客服查询响应速度，同时保证写操作后缓存可及时失效。

### 5.2 已接入缓存的接口
- `GET /api/v1/products/filters`
- `GET /api/v1/chat/internal/orders-summary`
- `GET /api/v1/chat/internal/orders-logistics-summary`
- `GET /api/v1/chat/internal/after-sales-summary`

### 5.3 键设计
- `rasa_ec_bot:products:filters:v1`
- `rasa_ec_bot:chat:orders-summary:{user_id}:{limit}`
- `rasa_ec_bot:chat:orders-logistics-summary:{user_id}:{limit}:{order_id|all}`
- `rasa_ec_bot:chat:after-sales-summary:{user_id}:{limit}`

### 5.4 失效策略
- 商品新增/编辑后失效 `products:filters`
- 用户下单后失效该用户订单/物流汇总缓存
- 商家发货后失效对应用户订单/物流汇总缓存
- 用户创建售后或商家更新售后后失效对应用户售后汇总缓存

### 5.5 可用性策略
- Redis 连接失败时自动降级为直连数据库，不阻断主流程
- 缓存 TTL 通过环境变量配置

## 6. 核心数据模型
- `users`：账号、角色、密码哈希
- `shops`：店铺主体（绑定商家用户）
- `shop_addresses`：店铺发货地址
- `products`：商品（归属店铺）
- `cart_items`：购物车
- `orders` / `order_items`：订单主从
- `logistics`：物流轨迹、预计送达、LLM 结果
- `after_sales`：退货/换货申请与状态流转

## 7. 核心 API 分组
### 7.1 认证与用户
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`

### 7.2 商品与购物
- `GET /api/v1/products`
- `GET /api/v1/products/filters`
- `GET /api/v1/products/{product_id}`
- `GET/POST/PATCH/DELETE /api/v1/cart...`

### 7.3 订单与售后（用户）
- `POST /api/v1/orders`
- `GET /api/v1/orders`
- `GET /api/v1/orders/{order_id}`
- `GET /api/v1/orders/{order_id}/after-sales`
- `POST /api/v1/orders/{order_id}/after-sales`

### 7.4 商家中心
- `GET /api/v1/merchant/shop`
- `GET/POST/PATCH /api/v1/merchant/addresses...`
- `GET/POST/PATCH /api/v1/merchant/products...`
- `GET /api/v1/merchant/orders`
- `POST /api/v1/merchant/orders/{order_id}/ship`
- `GET/PATCH /api/v1/merchant/after-sales...`

### 7.5 客服桥接
- `POST /api/v1/chat/send`
- `GET /api/v1/chat/internal/orders-summary`
- `GET /api/v1/chat/internal/orders-logistics-summary`
- `GET /api/v1/chat/internal/after-sales-summary`

## 8. 环境变量基线
### 8.1 backend
- `DATABASE_URL`
- `REDIS_URL`
- `REDIS_CACHE_TTL_SEC`
- `RASA_SERVER_URL`
- `RASA_REST_WEBHOOK_PATH`
- `RASA_INTERNAL_TOKEN`
- `FRONTEND_BASE_URL`
- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`

### 8.2 rasa
- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
- `BACKEND_API_URL`
- `FRONTEND_BASE_URL`
- `RASA_INTERNAL_TOKEN`

## 9. 验收标准
- 用户可完成“浏览 -> 加购 -> 下单 -> 查单 -> 申请售后”闭环
- 商家可完成“商品管理 -> 查看订单 -> 发货 -> 处理售后”闭环
- 客服可基于当前登录用户查询订单/物流/售后并返回可点击链接
- Redis 开启时可命中缓存，写操作后缓存能正确失效
- Redis 关闭或不可用时系统仍可正常工作

## 10. 后续迭代（不在当前版本）
- LoRA 微调与专用客服模型训练
- 更精细的缓存分层与监控
- 接入地图物流 API（如高德）提升物流节点地址真实性
- 完整运营能力（优惠券、营销活动、评价体系）
