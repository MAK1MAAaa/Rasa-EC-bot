# Rasa-EC-bot 前端（Vue 3）

前端已覆盖用户商城、商家中心、客服对话三个场景，并与后端/客服系统联通。

## 1. 技术栈
- Vue 3（Composition API）
- Vite（构建工具）
- Pinia（状态管理）
- Vue Router（路由）
- Axios（HTTP 客户端）
- Tailwind CSS（样式系统）
- `shadcn-vue` 风格组件层（本地落地于 `src/components/ui`）
- Headless UI（弹层 / 抽屉 / 折叠容器）
- `class-variance-authority` + `clsx` + `tailwind-merge`（组件变体与 class 合并）
- `tailwindcss-animate`（统一动效）
- Lucide Vue（图标）

## 2. 页面与路由
- `/products`：商品列表（分类/价格/库存筛选，支持展开筛选面板）
- `/products/:id`：商品详情
- `/cart`：购物车
- `/checkout`：结算
- `/orders`：订单列表、物流信息、取消订单、收货信息修改、物流投诉、售后申请（退货/换货）
- `/history`：历史浏览（位于顶部导航“订单”右侧，无记录时显示空态占位）
- `/chat`：智能客服
- `/login` / `/register`：登录注册
- `/merchant`：商家中心（商家角色可访问）

## 3. 已实现前端功能
### 3.0 视觉系统升级
- 重构全局设计令牌：统一背景、表面层、描边、阴影、品牌色、状态色、圆角和排版层级
- 新增公共 UI 组件层：按钮、徽标、弹层、分页、页面 Hero、空态等，减少页面各自维护一套 scoped CSS
- 顶部导航升级为统一 App Shell：品牌区、主导航区、账户区、移动端抽屉导航一体化
- 登录注册、商品列表/详情、购物车、结算、订单列表、历史浏览、客服页、商家中心统一到同一套暖金电商视觉语言

### 3.1 用户端
- 商品搜索、分类筛选、价格区间筛选、仅看有货
- 商品详情自动记录历史浏览，历史浏览页独立展示最近看过的商品
- 下单后查看订单、物流路线与预计送达
- 订单详情页支持取消待发货订单、修改待发货订单收货信息
- 订单详情页支持提交物流投诉并查看投诉状态/处理备注
- 在订单页发起售后并查看售后状态
- 购物车与订单列表都改为固定内容面板空态，空列表时也保留完整背景壳层
- 购物车支持页码分页，订单列表支持后端分页与上一页/下一页切换
- 购物车中的商品图片和商品标题支持直接跳转到商品详情页，便于回看规格后再决定是否结算

### 3.2 商家端
- 商家中心拆分为 `工作台 / 商品管理 / 添加商品 / 店铺资料 / 地址管理` 五个 tab
- 工作台合并订单与售后处理；切换订单状态筛选或售后状态筛选时会自动刷新列表，并带局部加载动画
- 工作台订单卡片中的商品改为点击弹出的居中浮层商品清单，浮层打开时背景带轻微模糊，商家侧不再从商品名跳转到商品详情
- 商品管理支持搜索、单个商品编辑、单个上下架、多选批量下架
- 添加商品独立成单独 tab，避免与商品列表、店铺资料混排
- 店铺资料独立成单独 tab，集中维护联系方式、发货城市、简介、Logo、主营类目、服务标签
- 地址管理支持新增、编辑、设为默认、删除地址
- 发货成功/失败浮窗提示
- 商家中心的订单、商品、地址、售后列表统一为固定列表壳层，空态和有内容状态视觉一致
- 商家中心的订单、商品、地址、售后列表都支持页码分页；订单发货下拉地址不受地址列表分页影响

### 3.3 客服页
- 对话区布局优化（消息气泡自适应高度）
- 消息区滚动条与历史消息浏览
- 支持结构化卡片消息（商品、订单、物流、售后、物流投诉、待确认操作）
- 支持图片上传链路，可把单张售后图片提交到后端并触发图片售后分析
- 自动兼容旧文本消息中的订单/商品链接渲染
- 二次确认改为弹窗确认卡片（确认/取消按钮），无需手动输入确认码
- 快捷提问入口覆盖查订单、查物流、取消订单、修改地址、物流投诉等最低可交付场景

## 4. 启动
Windows PowerShell 速查（对应位置：根目录 `README` 的“快速启动 / 启动前端”章节）：

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

当前 `build` 会执行：

```bash
vue-tsc && vite build
```

已补充 `tsconfig.json` 和 `src/env.d.ts`，用于 Vue SFC、路径别名和类型检查。

## 5.1 组件与主题目录
- `src/components/ui`
  - 基础 UI 组件层，采用 `shadcn-vue` 风格组织方式
- `src/components/shared`
  - 页面级复用组件，例如 `PageHero`、`EmptyState`
- `src/lib/utils.ts`
  - `cn()` class 合并工具
- `src/style.css`
  - 全局设计令牌、基础表单样式、按钮/徽标样式、弹层样式、公共页面壳层
- `components.json`
  - `shadcn-vue` 风格组件配置元数据

## 5.2 新增依赖
```bash
pnpm add @headlessui/vue class-variance-authority clsx radix-vue tailwind-merge tailwindcss-animate
pnpm add -D vue-tsc
```

说明：
- `radix-vue` 已纳入前端组件基础设施依赖，后续若继续扩展 `shadcn-vue` 风格组件，可直接复用
- 当前首批组件已优先落地在本地 `ui` 组件层，避免业务页继续散落实现

## 6. 联调要求
- 后端启动：`http://127.0.0.1:8000`
- Rasa Server：`http://127.0.0.1:5005`
- Action Server：`http://127.0.0.1:5055`

若要联调系统形态 benchmark 中的双后端对照，还需要额外启动：

- LoRA 后端实例：`http://127.0.0.1:8001`
- 纯 Rasa benchmark 实例：`http://127.0.0.1:5006`

## 7. 权限说明
- 未登录可访问：`/products`、`/products/:id`、`/chat`、`/login`、`/register`
- 用户登录后可访问：`/cart`、`/checkout`、`/orders`、`/history`
- 商家登录后可访问：`/merchant`
- 商家账号不允许访问 `/chat`（导航入口隐藏，手动访问会重定向到 `/merchant`）
- 图片售后入口只在聊天页对买家/游客显示，最终提交权限仍以后端校验为准

## 8. 物流地图与发货体验增强

### 8.1 前端环境变量
先从 `.env.sample` 复制 `.env`，并配置：

```env
VITE_ENABLE_LOGISTICS_MAP=false
VITE_AMAP_JS_KEY=
VITE_AMAP_SECURITY_JS_CODE=
```

### 8.2 订单详情页
- 在物流面板新增地图卡片。
- 地图容器常驻 DOM，首次进入订单详情页即可尝试渲染，不依赖二次刷新。
- 仅当 `VITE_ENABLE_LOGISTICS_MAP=true` 且后端返回坐标时才渲染地图。
- 地图会绘制起点、终点、当前位置；文本物流路线始终保留。
- 若地图 SDK / Key / 网络失败，页面会自动降级为文本物流路线。
- 后端发货路线已改为“发货地址 + 收货地址 + AMap geocode”确定性生成；历史订单若原始物流缺少坐标，读取详情时也会尝试回补 `route_geo`。
- 若页面持续只有文本轨迹，优先检查后端启动日志里的 `AMAP_WEB_KEY` 是否生效，以及发货时的 AMap geocode 日志。

### 8.3 商家页面
- 发货/推进物流按钮加入加载动效。
- 请求超过约 1200ms 时显示慢请求提示。
- 待发货卡片显示处理时长徽标（`待处理 Xh / Xd Xh`），并高亮超时订单。
- 商家中心已拆为工作台、商品管理、添加商品、店铺资料、地址管理五个独立 tab。
- 工作台内订单与售后并排呈现，状态筛选变化后会自动重新请求列表，并显示局部 skeleton 加载动画。
- 工作台里的搜索框、筛选框、复选框已统一为更强的暖金表单控件风格。
- 订单卡片中的商品清单改为点击后居中弹层展示，打开时背景带轻微模糊，商家查看订单时不再从商品名跳转到商品详情。
- 商品管理新增搜索、详情编辑和批量下架能力；添加商品不再和商品列表混在同一屏。
- 地址管理支持对已有地址执行编辑、删除、设为默认，并保留新增地址表单。
- 订单、商品、地址、售后列表统一使用固定背景列表面板；无数据时仍显示完整占位壳层。
- 商品、地址、订单、售后列表统一支持 `上一页 / 下一页` 分页切换。

### 8.4 AMap JS API 与 SecurityJsCode 配置
前端环境文件：`frontend/.env`（从 `frontend/.env.sample` 复制）

```env
VITE_ENABLE_LOGISTICS_MAP=true
VITE_AMAP_JS_KEY=your_amap_js_key
VITE_AMAP_SECURITY_JS_CODE=your_security_js_code
```

行为说明：
- 仅当 `VITE_ENABLE_LOGISTICS_MAP=true` 时启用地图渲染。
- `VITE_AMAP_SECURITY_JS_CODE` 会在加载 JSAPI 前注入到 `window._AMapSecurityConfig`。
- 当 key / 网络 / SDK 失败时，界面自动降级为文本物流路线。

安全建议：
- 在高德控制台为 JS Key 配置域名白名单。
- 不要把 `AMAP_WEB_KEY` 放到前端环境变量中。

## 9. 商品/店铺比较展示升级

- 商品列表页：
  - 新增品牌筛选、店铺筛选
  - 新增评分优先、销量优先排序
  - 商品卡片展示品牌、评分、月销、发货时效、标签、原价
- 商品详情页：
  - 新增“核心参数”“服务保障”“店铺画像”三个信息区
  - 展示规格亮点、保修、销量口碑、店铺评分、发货城市、服务标签
- 商家中心：
  - 店铺资料编辑区按核心信息/高级信息分组，可维护联系方式、发货城市、简介、Logo、主营类目、服务标签
  - 商品录入表单补齐 `sku_code`，并按核心字段/高级字段分组维护品牌、型号、原价、评分、评价数、月销、发货时效、保修、标签、核心参数
  - `tags`、`spec_highlights`、`featured_categories`、`service_tags` 均支持用中英文逗号或换行输入多值
- 聊天页：
  - 商品推荐卡片同步展示品牌、评分、月销、发货时效、标签
  - 客服在“推荐几款手机 / 比较两家店的显示器”场景下可直接输出更易比较的商品卡片
