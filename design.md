# 项目架构设计

## 1. 设计目标

Rasa-EC-bot 当前的目标不是单一聊天机器人，而是一个可运行的电商系统样例，覆盖以下能力：

- 用户侧电商闭环：商品浏览、购物车、下单、订单查询、售后申请。
- 商家侧运营闭环：商品管理、店铺管理、发货、售后处理。
- 智能客服闭环：规则型问答、交易查询、复杂多轮问答、图片售后分析。
- 论文实验闭环：支持系统形态对照 benchmark，并直接输出可用于论文的结果表。

系统设计采用“业务系统 + 对话系统 + 本地模型服务 + 实验工具链”并行演进的方式，避免把所有能力都堆在单一服务中。

## 2. 总体分层

### 2.1 前端层

- 目录：`frontend/`
- 技术：Vue 3、Vite、Pinia、Vue Router、Tailwind CSS
- 职责：
  - 用户端商城页面
  - 商家中心页面
  - 聊天客服界面
  - 图片上传与物流可视化展示

### 2.2 后端应用层

- 目录：`backend/`
- 技术：FastAPI、SQLModel、SQLAlchemy Async
- 职责：
  - 提供统一 REST API
  - 处理鉴权、订单、购物车、售后、商家管理
  - 提供客服统一入口 `/api/v1/chat/send`
  - 管理上传图片、知识库索引、Agent 工具调用
  - 提供给 Rasa Action Server 使用的内部摘要接口

### 2.3 对话编排层

- 目录：`rasa/`
- 技术：Rasa Open Source、Rasa SDK
- 职责：
  - 处理高频、确定性、流程清晰的客服意图
  - 维护规则型对话和 action 调用
  - 通过 Action Server 回调后端内部接口获取订单、物流、售后摘要

### 2.4 模型服务层

- 当前运行方式：Ollama + OpenAI-compatible / vLLM
- 当前口径：
  - 基础聊天模型：`qwen3.5:2b`
  - Rasa Action fallback：通过 Ollama 调用 `qwen3.5:2b`
  - Agent 默认模型：通过 OpenAI-compatible / vLLM 调用 `qwen3.5-2b-lora`
  - 多模态模型：`qwen3-vl:2b`
  - 向量模型：`mxbai-embed-large`
- 职责：
  - 通用生成
  - LoRA 微调模型推理
  - 图片理解
  - 文本 embedding

### 2.5 数据与缓存层

- PostgreSQL：业务主库
- pgvector：知识库向量检索
- Redis：高频摘要和筛选元数据缓存
- 本地文件目录：聊天图片上传落盘

### 2.6 实验与评测层

- 目录：`backend/benchmarks/`、`backend/scripts/`
- 职责：
  - 构造场景化数据集
  - 通过 HTTP 接口压测不同系统形态
  - 输出性能和规则质量指标
  - 生成论文可复用结果表

## 3. 核心目录职责

```text
Rasa-EC-bot/
├─ backend/                    FastAPI 后端与 benchmark 主体
│  ├─ app/                     业务 API、模型、缓存、Agent 编排
│  ├─ db/                      建表与种子数据
│  ├─ benchmarks/              benchmark 配置、语料、结果目录
│  └─ scripts/                 数据集构建与基准执行脚本
├─ frontend/                   Vue 前端
├─ rasa/                       Rasa 机器人与 Action Server
│  ├─ actions/                 自定义 action
│  ├─ benchmark/rasa_only/     纯 Rasa 对照配置
│  └─ data/                    NLU 与规则数据
├─ LoRA/                       LoRA 数据处理、训练、评估、导出脚本
├─ tests/                      benchmark 评分规则测试
└─ design.md                   当前架构设计说明
```

## 4. 运行拓扑

```mermaid
graph TD
    A[Frontend Vue] --> B[FastAPI Backend]
    A --> C[Rasa Server]
    B --> D[(PostgreSQL)]
    B --> E[(Redis)]
    B --> F[Ollama]
    B --> L[vLLM / OpenAI Compatible]
    B --> G[Action Server]
    G --> B
    C --> G
    B --> H[(pgvector)]
    B --> I[上传图片目录]
    J[LoRA 训练产物 Adapter] --> L
```

说明：

- 前端的电商业务请求主要进入 FastAPI。
- Rasa Server 负责规则型客服链路。
- Action Server 不直接访问数据库，而是优先通过后端内部接口取业务摘要。
- Ollama 负责基础聊天、多模态与 embedding 模型。
- 复杂 Agent 默认通过 OpenAI-compatible / vLLM 加载 LoRA adapter。

### 4.1 Benchmark 拓扑

```mermaid
graph TD
    K[System Benchmark Runner] --> B0[Backend Base 8000]
    K --> B1[Backend LoRA 8001]
    K --> R0[Rasa Only 5006]
    K --> O0[Ollama Base Chat]
    K --> O1[Ollama LoRA Chat]
    B0 --> KB0[KB Index API]
    B1 --> KB1[KB Index API]
```

说明：

- benchmark 只通过 HTTP 接口访问系统，不直接调用内部函数。
- benchmark 与业务运行拓扑解耦，便于单独说明对照系统和外部依赖。
- backend 系统若声明支持知识检索，benchmark 会在运行前通过现有 KB 接口写入种子文档。

## 5. 关键业务链路

### 5.1 电商主链路

普通交易链路由前端直连后端：

1. 用户登录后获取 JWT。
2. 用户浏览商品、加入购物车、创建订单。
3. 商家在商家中心处理商品、发货和售后。
4. 后端统一维护订单、物流、售后状态。

这一部分与客服系统解耦，确保即使关闭聊天能力，电商功能仍然可运行。

### 5.2 客服主链路

统一入口为：

- `POST /api/v1/chat/send`

后端内部采用双路由：

1. 前端发送消息到后端。
2. 后端先做快速路由判断。
3. 如果是高频且确定性的意图，走 Rasa 规则链路。
4. 如果是复杂、多轮、跨领域、带附件或需要综合推理的问题，走 Agent 链路。
5. 最终统一返回 `messages[].text/cards/actions`，前端无需区分底层来源。

这种设计的核心价值是：

- 简单问题保持稳定和低成本。
- 复杂问题保留 LLM 的灵活性。
- 前端协议不需要因为路由策略变化而频繁改动。

### 5.3 Rasa 规则链路

规则链路适合：

- 问候
- 商品推荐类固定问法
- 订单查询
- 物流查询
- 售后状态查询

链路流程：

1. 后端将消息转给 Rasa。
2. Rasa 命中 intent 与 rule。
3. 需要业务数据时调用 Action Server。
4. Action Server 调后端内部摘要接口。
5. 结果回到 Rasa，再统一返回给前端。

关键收益：

- 规则可控
- 结果稳定
- 易于做“纯 Rasa”对照实验

### 5.4 Agent 链路

复杂问题由 `backend/app/nexau_orchestrator.py` 负责编排。

它的职责不是直接执行业务写操作，而是：

- 判断消息涉及的领域
- 生成工具调用计划
- 调用订单、物流、售后、知识库、图片分析等工具
- 汇总 observation
- 让本地模型生成最终答复

当前 Agent 设计遵守两个边界：

- 读操作可自动完成
- 写操作必须通过二次确认草案机制，不允许模型直接落库

这保证了系统在引入 Agent 后仍然保留业务安全边界。

### 5.5 图片售后链路

图片售后采用两步接口：

1. `POST /api/v1/chat/upload-image`
2. `POST /api/v1/chat/send`，并携带 `attachments`

后端会：

- 校验图片格式与大小
- 保存文件并生成 `attachment_id`
- 在 Agent 链路中调用图片分析工具
- 结合知识库与售后规则生成答复

这条链路主要服务于：

- 包裹破损
- 商品破损
- 收错货

## 6. 数据与状态管理

### 6.1 PostgreSQL

承担核心业务数据：

- 用户与商家
- 商品与店铺
- 购物车
- 订单与订单明细
- 物流
- 售后
- 聊天相关持久化对象
- 知识库文档与向量索引元数据

### 6.2 pgvector

用于多模态 RAG 的向量检索：

- 政策知识检索
- 说明书/手册检索
- Agent 检索增强

### 6.3 Redis

承担高频读缓存，降低数据库压力。

当前缓存重点包括：

- 商品筛选元数据
- 订单摘要
- 物流摘要
- 售后摘要

设计原则是“摘要缓存”，而不是把完整业务对象全部复制到缓存中。

### 6.4 本地上传目录

聊天图片采用本地目录保存：

- 减少对象存储依赖
- 便于本地开发与论文演示
- 与附件 ID 映射，供后续多模态分析使用

## 7. 模型与知识增强设计

### 7.1 基础模型

基础模型负责：

- 通用聊天
- 客服答复润色
- Agent 最终总结

### 7.2 LoRA 模型

LoRA 目录负责：

- 数据准备
- 训练
- 评估
- 产出可被 PEFT runtime 加载的 adapter

当前主链路入口：

- `LoRA/scripts/train_lora.py`

训练产物默认直接输出为 adapter 目录，供 vLLM / OpenAI-compatible 推理端按 PEFT runtime 加载。

仓库中仍保留：

- `LoRA/scripts/export_ollama_model.py`

但该脚本只用于历史兼容或单独实验，不属于当前默认部署链路，也不是当前 benchmark 的必需步骤。

### 7.3 多模态与知识库

系统使用两类增强方式：

- 图片理解：`qwen3-vl:2b`
- 文档检索：embedding + pgvector

这样可以把客服从“纯文本问答”扩展为“图片售后 + 政策检索 + 说明书辅助”。

## 8. Benchmark 体系设计

当前 benchmark 已经从旧版 provider/layer 口径升级为“客服链路多轮会话 + 系统形态对照”口径。

### 8.1 对照系统

- `rasa_only`
- `llm_base_ollama`
- `llm_lora_ollama`
- `rasa_plus_llm_base`
- `rasa_plus_llm_lora`

### 8.2 场景范围

benchmark 范围严格锁定客服入口及其图片上传、待确认动作链路，不扩展到全量电商 REST API。当前固定 6 个场景族：

- `recommendation`
- `order_query`
- `logistics_query`
- `after_sales_query`
- `knowledge_and_multimodal`
- `transactional_action`

其中：

- `core` 数据集用于论文主实验，固定 15 个人工编排会话样本
- `extended` 数据集用于常规回归、补充实验和压力实验

### 8.3 数据集与核心脚本

- 数据集目录：`backend/benchmarks/prompts/core/`
- 扩展集目录：`backend/benchmarks/prompts/extended/`
- 数据清单：`backend/benchmarks/prompts/dataset_manifest.json`
- 知识库种子：`backend/benchmarks/kb_seed/`
- 构建脚本：`backend/scripts/build_system_benchmark_dataset.py`
- 执行脚本：`backend/scripts/run_system_benchmark.py`

每条样本固定包含：

- `scenario_family`
- `scenario`
- `turns`
- `account`
- `required_capabilities`
- `preconditions`
- `expected_outcomes`
- `tags`

多轮步骤当前支持：

- `login`
- `upload_image`
- `chat_send`
- `pending_decision`
- `sleep_until_expired`

### 8.4 能力矩阵与评测维度

系统能力位包括：

- `supports_auth_queries`
- `supports_kb_policy`
- `supports_kb_manual`
- `supports_pending_action`
- `supports_pending_decision`
- `supports_attachments`
- `supports_image_analysis`
- `supports_cards`

评测维度分为三层：

- 能力型评分：推荐、查询、检索、图片分析、草案生成是否完成
- 结构型评分：卡片、按钮、待确认卡、附件流程结果是否符合预期
- 流程型评分：登录拦截、订单号要求、越权阻止、确认/取消、过期拦截是否正确

同时保留性能指标：

- 时延
- 吞吐
- 错误率

并新增会话与覆盖率指标：

- 会话成功率
- 能力覆盖率
- 流程完成率
- 确认动作成功率
- 过期动作拦截率

### 8.5 设计原则

- 只走 HTTP 接口，不直接调用内部函数
- 不修改业务主协议语义，不新增专用 benchmark API
- 纯 Rasa 必须是单独实例，不能混用带 LLM fallback 的服务
- 不支持能力统一记为 `unsupported/na`，不混淆为系统失败
- 输出结果直接服务论文写作与系统对照分析

## 9. 启动与部署顺序

推荐启动顺序：

1. PostgreSQL 与 Redis
2. 后端 FastAPI
3. Ollama 与所需模型
4. Rasa Server
5. Rasa Action Server
6. 前端
7. Benchmark 脚本

如果只做 benchmark，可按实验对象最小化启动，不必拉起整个前端。

## 10. 当前架构边界

当前架构刻意保留以下边界：

- benchmark 不修改业务协议
- Rasa 与 Agent 共存，而不是相互替代
- 写操作必须经过确认机制
- LoRA 训练与业务运行解耦
- 模型部署默认以本地 Ollama 为主

这意味着系统既适合课程/论文演示，也适合继续扩展为更强的本地部署研究平台。

## 11. 后续可扩展方向

- 将 `extended` 数据集从“目录级复制”进一步收敛为“缺省回退到 core”的去重加载策略
- 把 benchmark 结果继续自动转换为更完整的论文图表和附录素材
- 在不破坏黑盒原则的前提下，补充更细粒度的错误归因与流程可视化
- 将图片分析、知识检索、待确认动作继续统一到更稳定的 Agent 工具协议
