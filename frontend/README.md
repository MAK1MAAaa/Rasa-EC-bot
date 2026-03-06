# Rasa-EC-bot 前端界面

基于 Vue 3 + Vite + Tailwind CSS 构建的电商智能客服系统前端。

## 技术栈
- **框架**: Vue 3 (Composition API)
- **构建工具**: Vite
- **样式**: Tailwind CSS
- **状态管理**: Pinia
- **路由**: Vue Router
- **网络请求**: Axios
- **图标**: Lucide Vue Next

## 快速开始

### 1. 安装依赖
确保已安装 [pnpm](https://pnpm.io/)：
```bash
pnpm install
```

### 2. 启动开发服务器
```bash
pnpm dev
```
启动后访问: `http://localhost:5173`

### 3. 构建生产版本
```bash
pnpm build
```

## 项目结构
- `src/views/`: 页面组件（登录、注册、聊天界面等）
- `src/components/`: 复用组件
- `src/api/`: API 请求封装
- `src/store/`: Pinia 状态管理
- `src/router/`: 路由配置

## 已实现功能
- [x] 用户注册页面
- [x] 用户登录页面 (对接 FastAPI OAuth2)
- [ ] 聊天对话界面 (待开发)
- [ ] 订单/商品查询展示 (待开发)
