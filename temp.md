# Rasa-EC-bot 系统架构与当前实现说明

## 1. 项目定位

本项目是一个电商场景的全栈示例系统，包含：

- 用户侧商城流程：商品浏览、筛选、购物车、下单、订单查询、售后申请
- 商家侧运营流程：商品管理、地址管理、发货、售后处理
- 智能客服流程：Rasa 对话管理 + 本地 Ollama 模型回复 + 后端业务数据查询
- 训练子系统：LoRA 微调流水线（Qwen3.5-2B）

核心目标是把“业务系统 + 对话系统 + 本地模型能力”打通成一个可运行闭环。

---

## 2. 总体架构

```text
┌───────────────────────────────┐
│           Frontend            │
│ Vue3 + Vite + Pinia + Tailwind│
└───────────────┬───────────────┘
                │ HTTP
┌───────────────▼───────────────┐
│            Backend            │
│   FastAPI + SQLModel + Redis  │
│   业务API + Chat聚合入口       │
└───────┬───────────┬───────────┘
        │           │
        │           ├──────────────► PostgreSQL (业务数据)
        │
        └──────────► Redis (缓存/确认动作状态)

┌───────────────────────────────┐
│      Rasa Server + Actions    │
│    意图识别/策略 + 业务Action   │
└───────────────┬───────────────┘
                │
                ├──────────────► Backend 内部接口
                └──────────────► Ollama (`qwen3.5:2b`)
```

默认端口：

- Frontend: `5173`
- Backend: `8000`
- Rasa Server: `5005`
- Rasa Actions: `5055`
- PostgreSQL: `5432`
- Redis: `6379`
- Ollama: `11434`

---

## 3. 分层与职责

## 3.1 前端（`frontend/`）

- 提供用户端与商家端页面
- 通过 Backend API 获取商品、订单、售后数据
- 聊天页面通过后端聊天接口接入 Rasa 能力
- 已包含实时/交互相关工具代码（例如 `src/utils/realtime.ts`）

## 3.2 后端（`backend/`）

- FastAPI 提供统一业务 API 与聊天聚合入口
- SQLModel 连接 PostgreSQL 完成业务持久化
- Redis 缓存商品筛选元数据与客服汇总数据
- 客服敏感动作实现二次确认机制（确认码 + TTL）
- 后端默认 Ollama 模型已切换为 `qwen3.5:2b`

关键能力：

- 用户侧：注册登录、商品、购物车、订单、售后
- 商家侧：商品管理、发货、售后处理
- 客服内部接口：订单汇总/物流汇总/售后汇总
- 自动执行动作：自动下单、自动退款/换货（需确认）

## 3.3 对话系统（`rasa/`）

- Rasa 做意图识别与对话策略
- Actions 向后端拉取业务数据，组合业务回复
- 兜底或自然语言补全通过 Ollama 调用本地模型
- Action 默认 Ollama 模型已切换为 `qwen3.5:2b`

## 3.4 数据层与缓存

- PostgreSQL：核心业务数据（用户、商品、订单、售后）
- Redis：
  - 缓存高频查询结果（筛选、汇总）
  - 存储“待确认动作”状态，防误操作

---

## 4. 关键业务链路

## 4.1 电商主链路

1. 用户浏览商品、加入购物车
2. 用户发起下单，后端创建订单
3. 商家后台发货，更新订单与物流状态
4. 用户可发起售后申请，商家处理申请

## 4.2 客服链路

1. 用户在前端聊天
2. 后端将消息转发给 Rasa
3. Rasa 根据意图调用 Action
4. Action 调后端内部接口查询业务数据
5. 需要自然语言补全时调用 Ollama
6. 对敏感动作先下发“待确认草案”，用户确认后执行

---

## 5. LoRA 微调子系统（`LoRA/`）

该目录是独立训练工程，产物与在线业务服务逻辑解耦。

训练流程：

1. `prepare_data.py`：多源数据清洗与统一为 SFT JSONL
2. `train_lora.py`：QLoRA 训练（smoke/full）
3. `eval_lora.py`：base vs tuned 离线规则评估
4. `export_ollama.py`：合并与导出 Ollama 可用模型

当前数据接入：

- Bitext 客服数据
- FAQ intents 数据
- E-commerce dataset 多轮数据
- ECM / ECM2 数据

训练侧已做的关键改进：

- 评估降频：`eval_steps` 从高频调整为 `1000`
- 评估抽样：`max_eval_samples`（降低单次 eval 耗时）
- 支持 `warmup_steps`，减少弃用告警
- 可通过 `eval_steps<=0` 关闭周期评估

大文件策略：

- 原始大数据不入 Git（避免 GitHub 100MB 限制）
- 跨设备手动复制到相同路径

---

## 6. 运维与启动方式（当前约定）

## 6.1 Docker 数据挂载

文档已统一为“相对路径派生”方式：

- Windows：`Resolve-Path`
- Linux/macOS：`$(pwd)/...`

并补充了容器名冲突处理：

- 复用：`docker start rasa-postgres rasa-redis`
- 重建：`docker stop/rm` 后再 `docker run`

## 6.2 模型约定

- 线上/联调默认模型：`qwen3.5:2b`
- 相关位置已同步：
  - `backend/app/main.py`
  - `backend/.env.sample`
  - `rasa/actions/actions.py`
  - `rasa/.env.sample`
  - 根 README / rasa README

---

## 7. 当前完成内容清单（可交接视角）

- 完成全栈闭环：前端、后端、Rasa、Ollama 联调路径
- 完成缓存体系：Redis 缓存与降级策略
- 完成客服二次确认执行机制
- 完成 LoRA 训练工程搭建（数据、训练、评估、导出）
- 完成多数据源预处理增强（ECM/ECM2 + 电商数据）
- 完成训练配置调优（评估耗时优化）
- 完成跨平台 Docker 路径文档修正（Win/Linux/macOS）
- 完成 `.gitignore` 整理与大文件/本地环境文件剥离策略

---

## 8. 当前注意事项

- 如果 `git status` 出现大量 `.rasa/cache` 删除记录，需确保 `/.rasa/` 已忽略并从索引移除。
- 如果 `git push` 失败提示大文件，说明历史提交仍包含大文件，需要把该提交改写为不含大文件版本。
- LoRA 训练耗时主要取决于：
  - 训练样本规模
  - eval 频率与 eval 样本量
  - GPU 实际可用加速路径（是否走 fast path）


## 9. 本次同步更新（2026-04-08）：QA -> ReAct Agent 数据合成

### 9.1 新增内容
- 新增脚本：LoRA/scripts/synthesize_react_data.py
- 新增 schema：LoRA/configs/react_action_schemas.json
- 保持训练输入结构不变：messages=[system,user,assistant]
- 将 ssistant 转换为五段体：Thought / Action / Action_Input / Observation / Response

### 9.2 合成策略（已落地）
- 两阶段生成：
  - 阶段1：LLM 仅生成 	hought/action/action_input/response
  - 阶段2：脚本按 schema 注入 Observation，避免模型脑补接口字段
- 默认样本量：1500
- 动作级目标配比：
  - query_order_status 28%
  - query_logistics 17%
  - query_product_info 20%
  - create_return_request 18%
  - query_refund_status 12%
  - query_orders_summary 5%

### 9.3 Action 与真实接口对齐
- query_order_status -> GET /api/v1/orders/{order_id} -> OrderRead
- query_logistics -> GET /api/v1/chat/internal/orders-logistics-summary -> ChatOrderLogisticsSummaryResponse
- query_product_info -> GET /api/v1/products -> ProductListResponse
- create_return_request -> POST /api/v1/orders/{order_id}/after-sales -> AfterSalesRead
- query_refund_status -> GET /api/v1/chat/internal/after-sales-summary -> ChatAfterSalesSummaryResponse
- query_orders_summary -> GET /api/v1/chat/internal/orders-summary -> ChatOrderSummaryResponse

### 9.4 输出产物
- ReAct 子集：LoRA/data/processed/react_agent/{train,val,test}.jsonl
- 合并子集：LoRA/data/processed/combined_react_agent/{train,val,test}.jsonl
- 统计报告：LoRA/data/processed/react_agent/summary.json

### 9.5 稳定性增强（已完成）
- 处理 Ollama 超时与 500：请求失败不再中断整批任务，转为重试与 fallback。
- 新增失败原因统计：ollama_request_timeout、ollama_response_not_json 等。
- 输入文件增加多编码回退读取：utf-8/utf-8-sig/gb18030/latin-1。

### 9.6 建议执行参数
`powershell
cd LoRA
uv run python scripts/synthesize_react_data.py 
  --schema-config configs/react_action_schemas.json 
  --sample-size 1500 
  --ollama-model qwen3.5:9b 
  --ollama-base-url http://127.0.0.1:11434 
  --timeout-sec 300 
  --max-retries 6 
  --react-out-dir data/processed/react_agent 
  --combined-out-dir data/processed/combined_react_agent
`

## 10. 后续可扩展方向（预研）

### 10.1 架构范式升级：引入 ReAct 混合 Agent 架构
- 将 Rasa 定位为 Fast Router，处理高频确定性任务。
- 将复杂多轮问题切换到 ReAct Agent，利用 Tool Calling 自主规划步骤。
- 预期收益：降低规则树复杂度，提高复杂场景决策质量与可解释性。

### 10.2 检索增强与多模态扩展（Multi-modal RAG）
- 在结构化查询之外引入向量检索，覆盖退换货政策、长文档说明书等非结构化知识。
- 预留图像输入链路，接入 VLM（如 Qwen-VL）处理破损图、报错截图等视觉售后场景。
- 预期收益：提升复杂问答命中率与客服“可感知智能度”。

### 10.3 模型部署与推理系统优化（SysML 视角）
- 对比 Ollama 与 vLLM 的吞吐、时延、并发能力。
- 结合硬件约束研究 Prefix Caching 在多轮客服对话中的收益。
- 评估显存占用与调度行为，形成工程化部署建议。

### 10.4 严谨评测与对齐（Evaluation & Alignment）
- 从规则评估升级为多维基准：业务准确率、同理心、安全性。
- 引入 LLM-as-a-Judge 机制构建自动化评分闭环。
- 参考 OpenCompass 思路设计长上下文“信息检索”场景测试，验证长历史对话下的关键信息提取能力。