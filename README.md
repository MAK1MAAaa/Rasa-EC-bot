# Rasa-EC-bot: 基于 Rasa CALM 与 LLM 的电商智能客服系统

本项目是一款融合了大语言模型（LLM）与 Rasa CALM 架构的现代化电商智能客服系统。

## 🏗️ 系统架构

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

## 🚀 快速开始

### 后端环境配置
1. 进入 `backend` 目录
2. 安装依赖: `pip install -r requirements.txt`
3. 配置 `.env` 环境变量
4. 启动服务: `uvicorn app.main:app --reload`

### 前端环境配置
1. 进入 `frontend` 目录
2. 安装依赖: `npm install`
3. 启动开发服务器: `npm run dev`
