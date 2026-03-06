# Rasa-EC-bot: 基于 Rasa CALM 与 LLM 的电商智能客服系统

本项目是一款融合了大语言模型（LLM）与 Rasa CALM 架构的现代化电商智能客服系统。

## 系统架构

系统采用 **前后端分离 + AI 微服务** 的架构设计：

1.  **表现层 (Frontend)**: 基于 **Vue 3 + Vite + Tailwind CSS** 构建的响应式 Web 聊天界面。
2.  **业务网关层 (Backend)**: 使用 **FastAPI** 异步框架，负责：
    *   用户鉴权与管理 (JWT)
    *   业务数据 CRUD (PostgreSQL)
    *   与 Rasa 对话引擎及 Action Server 的协同
3.  **对话管理层 (Rasa CALM)**: 核心对话逻辑引擎，利用 **Rasa Pro** 的 CALM 架构进行声明式对话流管理。
4.  **大语言模型层 (LLM)**: 本地部署的 **Qwen2-7B** (通过 Ollama)，用于意图识别优化、槽位提取及闲聊生成。
5.  **数据持久化层**:
    *   **PostgreSQL**: 存储用户、订单、商品及物流等核心业务数据。
    *   **Redis**: 用于 Session 管理、Token 缓存及高频数据字典。

---

## 快速开始

### 1. 基础设施准备 (Docker)

在启动后端服务之前，请确保已运行 PostgreSQL 和 Redis。建议将数据挂载到项目根目录下的 `database` 文件夹中。

#### 运行 PostgreSQL (本地路径持久化)
```powershell
# 请确保已创建 database/pgdata 目录
docker run --name rasa-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -v D:/Github/Rasa-EC-bot/database/pgdata:/var/lib/postgresql/data -d postgres:15
```

#### 运行 Redis (本地路径持久化)
```powershell
# 请确保已创建 database/redisdata 目录
docker run --name rasa-redis -p 6379:6379 -v D:/Github/Rasa-EC-bot/database/redisdata:/data -d redis:7 redis-server --appendonly yes
```

### 2. 后端环境配置
1. 进入 `backend` 目录。
2. 安装依赖: `uv sync` (推荐) 或 `pip install -r requirements.txt`。
3. 配置 `.env` 环境变量。
4. 初始化数据库: 参考 `backend/README.md` 中的数据库初始化章节。
5. 启动服务: `uv run uvicorn app.main:app --reload`。

### 3. 前端环境配置
1. 进入 `frontend` 目录。
2. 安装依赖: `pnpm install`。
3. 启动开发服务器: `pnpm dev`。
4. 详细说明请参考 `frontend/README.md`。

---

## 项目结构
- `backend/`: FastAPI 后端服务
- `frontend/`: Vue 3 前端界面
- `database/`: 数据库持久化文件 (已忽略)
- `db/`: 数据库初始化 SQL 脚本
