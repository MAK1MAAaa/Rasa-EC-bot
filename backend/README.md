# Rasa-EC-bot 后端服务

## 数据库运行与初始化

本项目使用 PostgreSQL 15 作为主数据库。

### 1. 数据库连接信息
- **容器名称**: `rasa-postgres`
- **端口**: `5432`
- **用户名**: `postgres`
- **密码**: `postgres`
- **数据库名**: `rasa_ec_bot`

### 2. 初始化数据库表结构与数据

#### 第一步：创建数据库
在终端运行以下命令创建 `rasa_ec_bot` 数据库：
```bash
docker exec -it rasa-postgres psql -U postgres -c "CREATE DATABASE rasa_ec_bot;"
```

#### 第二步：导入表结构与数据 (PowerShell)
> **注意**: 为了彻底解决中文乱码，请务必先执行第一行设置编码的命令。
```powershell
# 设置 PowerShell 管道输出编码为 UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# 创建表结构
Get-Content -Raw -Encoding UTF8 db/init_db.sql | docker exec -i -e PGCLIENTENCODING=UTF8 rasa-postgres psql -U postgres -d rasa_ec_bot

# 插入测试数据
Get-Content -Raw -Encoding UTF8 db/seed_data.sql | docker exec -i -e PGCLIENTENCODING=UTF8 rasa-postgres psql -U postgres -d rasa_ec_bot
```

#### 第二步：导入表结构与数据 (Bash/Git Bash)
```bash
# 创建表结构
docker exec -i -e PGCLIENTENCODING=UTF8 rasa-postgres psql -U postgres -d rasa_ec_bot < db/init_db.sql

# 插入测试数据
docker exec -i -e PGCLIENTENCODING=UTF8 rasa-postgres psql -U postgres -d rasa_ec_bot < db/seed_data.sql
```

### 3. 环境变量配置
在 `backend` 目录下创建 `.env` 文件，并配置数据库连接字符串：
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/rasa_ec_bot
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
