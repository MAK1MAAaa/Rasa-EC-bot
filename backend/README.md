# Rasa-EC-bot 后端服务（FastAPI）

本文档覆盖后端当前完整能力：认证、商品、购物车、模拟下单与订单查询。

## 1. 技术栈与版本

- FastAPI
- SQLModel + SQLAlchemy Async
- PostgreSQL 15
- JWT（Bearer Token）

## 2. 数据库运行与初始化

### 2.1 连接信息
- 容器名：`rasa-postgres`
- 端口：`5432`
- 用户名：`postgres`
- 密码：`postgres`
- 数据库名：`rasa_ec_bot`

### 2.2 启动并确认 PostgreSQL 容器
```powershell
# 1) 先启动 PostgreSQL 容器（项目 README 里的命令）
docker run --name rasa-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -v D:/Github/Rasa-EC-bot/database/pgdata:/var/lib/postgresql/data -d postgres:15

# 2) 确认容器在跑
docker ps --filter name=rasa-postgres
```

### 2.3 创建数据库
```bash
docker exec -it rasa-postgres psql -U postgres -c "CREATE DATABASE rasa_ec_bot;"
```

### 2.4 导入表结构与种子数据

#### PowerShell
```powershell
$OutputEncoding = [System.Text.Encoding]::UTF8
Get-Content -Raw -Encoding UTF8 db/init_db.sql | docker exec -i -e PGCLIENTENCODING=UTF8 rasa-postgres psql -U postgres -d rasa_ec_bot
Get-Content -Raw -Encoding UTF8 db/seed_data.sql | docker exec -i -e PGCLIENTENCODING=UTF8 rasa-postgres psql -U postgres -d rasa_ec_bot
```

#### Bash / Git Bash
```bash
docker exec -i -e PGCLIENTENCODING=UTF8 rasa-postgres psql -U postgres -d rasa_ec_bot < db/init_db.sql
docker exec -i -e PGCLIENTENCODING=UTF8 rasa-postgres psql -U postgres -d rasa_ec_bot < db/seed_data.sql
```

## 3. 环境变量

在 `backend` 目录创建 `.env`：

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/rasa_ec_bot
```

## 4. 启动后端

```bash
uv sync
uv run uvicorn app.main:app --reload
```

访问：
- API 根路径：`http://127.0.0.1:8000`
- Swagger：`http://127.0.0.1:8000/docs`

## 5. 数据结构（本次新增/调整）

### 5.1 users（用户）
- 使用邮箱体系登录，邮箱大小写无关唯一索引。

### 5.2 products（商品）
新增字段：
- `description`
- `image_url`
- `category`
- `is_active`
- `created_at`

### 5.3 cart_items（购物车）
- 字段：`id/user_id/product_id/quantity/created_at/updated_at`
- 约束：`UNIQUE(user_id, product_id)`

### 5.4 order_items（订单明细快照）
- 字段：`order_id/product_id/product_name/unit_price/quantity/subtotal`

### 5.5 orders（订单主表）
- 继续使用：`address/contact_email/total_amount/status`
- 订单号格式：`ORD{yyyyMMddHHmmss}{4位随机数}`

## 6. API 清单（MVP）

### 6.1 认证
- `POST /api/v1/auth/register` 注册
- `POST /api/v1/auth/login` 登录
- `GET /api/v1/auth/me` 获取当前用户

### 6.2 商品（公开）
- `GET /api/v1/products?page=1&page_size=12&keyword=&category=`
- `GET /api/v1/products/{product_id}`

### 6.3 购物车（需 Bearer Token）
- `GET /api/v1/cart`
- `POST /api/v1/cart/items`，Body: `{ "product_id": "...", "quantity": 1 }`
- `PATCH /api/v1/cart/items/{item_id}`，Body: `{ "quantity": 2 }`（0 表示删除）
- `DELETE /api/v1/cart/items/{item_id}`

### 6.4 订单（需 Bearer Token）
- `POST /api/v1/orders`，Body: `{ "address": "...", "contact_email": "..." }`
- `GET /api/v1/orders`
- `GET /api/v1/orders/{order_id}`

## 7. 关键业务规则

1. 下单必须在单次提交流程中完成：
   - 校验购物车非空
   - 校验库存
   - 扣减库存
   - 创建订单与明细
   - 清空购物车
2. 错误码：
   - 空购物车：`400`
   - 库存不足：`409`
   - 越权访问：`403`

## 8. 手动验收

1. 使用 `test1@example.com / password123` 登录。
2. 调 `GET /api/v1/products` 验证分页与搜索。
3. 调 `POST /api/v1/cart/items` 后再调 `GET /api/v1/cart` 验证金额和数量。
4. 调 `PATCH /api/v1/cart/items/{item_id}` 验证数量更新。
5. 调 `POST /api/v1/orders` 创建订单，检查状态为 `待发货`。
6. 再查购物车应为空，查订单列表/详情应有新记录。

## 9. 与前端联调说明

- 前端默认通过 Vite 代理 `/api -> http://localhost:8000`
- 认证头为：`Authorization: Bearer <token>`
- 若返回 401，前端会自动清理 token 并跳转登录
