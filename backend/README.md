# Rasa-EC-bot 后端服务

## 数据库运行与初始化

本项目使用 PostgreSQL 15 作为主数据库。

### 1. 数据库连接信息
- **容器名称**: `rasa-postgres`
- **端口**: `5432`
- **用户名**: `postgres`
- **密码**: `postgres`
- **数据库名**: `postgres` (默认) 或 `rasa_ec_bot` (建议创建)

### 2. 初始化数据库表结构与数据

#### 在 PowerShell (Windows) 中运行：
> **注意**: 必须指定 `-Encoding UTF8` 以防止中文乱码导致 SQL 语法错误。
```powershell
# 创建表结构
Get-Content -Encoding UTF8 db/init_db.sql | docker exec -i rasa-postgres psql -U postgres -d postgres

# 插入测试数据
Get-Content -Encoding UTF8 db/seed_data.sql | docker exec -i rasa-postgres psql -U postgres -d postgres
```

#### 在 Bash (Linux/macOS/Git Bash) 中运行：
> **注意**: 使用 `PGCLIENTENCODING=UTF8` 确保客户端编码正确处理中文。
```bash
# 创建表结构
docker exec -i -e PGCLIENTENCODING=UTF8 rasa-postgres psql -U postgres -d postgres < db/init_db.sql

# 插入测试数据
docker exec -i -e PGCLIENTENCODING=UTF8 rasa-postgres psql -U postgres -d postgres < db/seed_data.sql
```

### 3. 环境变量配置
在 `backend` 目录下创建 `.env` 文件，并配置数据库连接字符串：
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/postgres
```

## 运行后端服务

### 1. 环境准备
确保已安装 `uv` 包管理工具：
```bash
pip install uv
```

### 2. 安装依赖
在 `backend` 目录下执行：
```bash
uv sync
```

### 3. 启动服务
在 `backend` 目录下执行：
```bash
uv run uvicorn app.main:app --reload
```

服务启动后，可以通过以下地址访问：
- API 根路径: http://127.0.0.1:8000
- 交互式 API 文档 (Swagger UI): http://127.0.0.1:8000/docs
- 替代 API 文档 (ReDoc): http://127.0.0.1:8000/redoc
