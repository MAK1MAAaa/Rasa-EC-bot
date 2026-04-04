# Rasa-EC-bot

基于 **Rasa CALM + LLM** 的电商智能客服项目，当前已完成一套可运行的电商 MVP 闭环：

- 用户注册/登录（邮箱体系）
- 商品浏览与搜索
- 商品详情
- 购物车（增删改查）
- 结算与模拟下单
- 我的订单与订单详情

## 近期已完成功能（本次迭代）

### 1. 电商业务闭环
- 商品列表分页、关键词搜索、分类筛选
- 商品详情页与库存展示
- 购物车条目增删改（数量 0 自动删除）
- 订单创建（模拟支付），并生成订单明细快照
- 订单列表与详情查询

### 2. 后端能力增强
- 新增商品、购物车、订单明细模型与接口
- 下单事务流程：
  1) 校验购物车非空
  2) 校验库存
  3) 扣减库存
  4) 创建订单与明细
  5) 清空购物车
- 库存不足返回 `409`、空购物车返回 `400`、越权返回 `403`

### 3. 前端体验增强
- 新增应用壳（顶部导航、购物车角标、登录态入口）
- 新增页面：商品列表、商品详情、购物车、结算、我的订单、智能客服
- 路由守卫：公开页面与受保护页面分离
- Axios 拦截器：自动附带 Token，401 自动回登录页

### 4. 智能客服链路接入
- 新增 `POST /api/v1/chat/send`：前端统一调用后端网关，再转发给 Rasa REST Channel
- 新增 `rasa/` 子工程：包含意图样本、规则与 Action Server
- Action Server 接入本地 Ollama，模型默认 `qwen3.5:9b`
- 支持商品推荐场景：Rasa Action 会读取后端商品接口给出推荐结果

## 技术架构

- **Frontend**: Vue 3 + Vite + Pinia + Vue Router + Axios + Tailwind CSS
- **Backend**: FastAPI + SQLModel + SQLAlchemy Async + JWT
- **Database**: PostgreSQL（主库）+ Redis（预留）
- **AI Layer**: Rasa + 本地 LLM（Ollama / `qwen3.5:9b`）

## 快速开始

### 1. 启动基础设施（Docker）

```powershell
# PostgreSQL
docker run --name rasa-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -v D:/Github/Rasa-EC-bot/database/pgdata:/var/lib/postgresql/data -d postgres:15

# Redis
docker run --name rasa-redis -p 6379:6379 -v D:/Github/Rasa-EC-bot/database/redisdata:/data -d redis:7 redis-server --appendonly yes
```

### 2. 初始化数据库

进入 `backend` 目录后，参考 [backend/README.md](backend/README.md) 执行建库、建表与种子数据导入。

### 3. 启动后端

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

后端地址：`http://127.0.0.1:8000`

### 4. 启动 Ollama 与 Rasa

```bash
# 1) 本地模型
ollama pull qwen3.5:9b

# 2) 进入 Rasa 子目录
cd rasa

# 3) 复制环境变量模板
cp .env.sample .env

# 4) 安装 Rasa 依赖（uv）
uv sync

# 5) 训练模型
uv run rasa train --config config.yml --domain domain.yml --data data

# 6) 启动 Rasa Server
uv run rasa run --enable-api --cors "*" --credentials credentials.yml --endpoints endpoints.yml --port 5005

# 7) 新终端启动 Action Server
uv run rasa run actions --actions actions --port 5055
```

### 5. 启动前端

```bash
cd frontend
pnpm install
pnpm dev
```

前端地址：`http://localhost:5173`

## 测试账号（种子数据）

- 邮箱：`test1@example.com`
- 密码：`password123`

## 推荐验收路径

1. 登录后进入商品列表
2. 进入商品详情并加入购物车
3. 在购物车调整数量并去结算
4. 提交订单（模拟支付）
5. 在“我的订单”查看新订单与订单明细

## 项目目录

- `backend/`: FastAPI 后端服务
- `frontend/`: Vue 3 前端商城界面
- `rasa/`: Rasa 对话引擎与 Action Server
- `backend/db/`: 数据库初始化与种子 SQL
- `database/`: 本地数据库持久化目录（git 忽略）
- `requirement.md`: 需求文档

## 文档索引

- 后端文档：[`backend/README.md`](backend/README.md)
- 前端文档：[`frontend/README.md`](frontend/README.md)
- Rasa 文档：[`rasa/README.md`](rasa/README.md)

