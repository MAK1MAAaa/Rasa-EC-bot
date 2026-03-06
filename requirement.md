# 基于 Rasa CALM 与 LLM 的电商智能客服系统设计及实现

**项目类型**：本科/硕士毕业设计

**开发周期**：4周（极速敏捷开发版）

## 1. 项目概述

### 1.1 项目背景

随着电商业务的快速发展，传统基于意图识别和规则树（Intent & Story）的客服机器人在处理复杂多轮对话、上下文打断以及自然语言泛化方面暴露出维护成本高、灵活性差的问题。本项目旨在设计并实现一款支持多任务场景的智能客服系统，融合大语言模型（LLM）与 Rasa 最新的 CALM（Conversational AI with Language Models）架构，实现对话流程的声明式管理与生成式回复的完美结合。

### 1.2 核心目标

1. **任务型对话闭环**：覆盖订单查询、物流跟踪与投诉、订单收货信息修改、订单取消、退换货售后申请 5 大核心场景。
2. **对话修复与闲聊**：支持用户在任务途中的跑题（Digression）、纠正（Correction）与取消（Cancellation），并支持兜底的闲聊功能。
3. **系统高效协同**：前端现代化展示，Python (FastAPI) 后端承载业务高并发，PostgreSQL+Redis 保障数据与缓存一致性，Rasa CALM 负责对话路由。
4. **LLM 微调优化**：通过 LoRA 技术对基座模型进行微调，优化业务指令生成（Command Generation）效率和槽位抽取准确率。

## 2. 技术栈选型

* **前端 (Frontend)**: Vue 3 + Vite + Tailwind CSS + Axios
* **业务后端 (Backend)**: Python (FastAPI) + SQLAlchemy (异步 ORM) / SQLModel
* **数据库与缓存 (DB & Cache)**: PostgreSQL (持久化) + Redis (Session/Token 缓存与高频数据字典)
* **对话引擎 (Dialogue Engine)**: Rasa Pro (CALM 架构) + Python Action Server
* **大语言模型 (LLM)**: Qwen2-7B 或 GLM-4-9B (基于 Ollama 本地部署)
* **微调框架 (Fine-tuning)**: Unsloth / HuggingFace PEFT (LoRA)

## 3. 系统架构设计

系统整体采用 **前后端分离 + 纯 Python AI 微服务** 的架构，技术栈高度统一，大幅降低沟通 and 维护成本：

1. **表现层 (UI)**：Vue3 负责渲染 WebChat 界面，与 FastAPI 后端通过 HTTP/WebSocket 通信。
2. **业务网关层 (FastAPI)**：处理鉴权、限流、数据库 CRUD 操作。包含两个核心方向：响应前端请求，以及为 Rasa Action Server 提供 RESTful 接口。利用其原生异步 (Asyncio) 特性处理高并发对话请求。
3. **对话管理层 (Rasa CALM)**：解析用户输入，利用内置的 LLM Command Generator 将自然语言转化为业务指令，并通过 `flows.yaml`驱动对话状态机。当需要查询数据时，调用 Python Action Server。
4. **动作执行层 (Action Server)**：Python 服务，作为 Rasa 和 FastAPI 核心业务线之间的粘合剂，发起 HTTP 请求给 FastAPI 接口。*(注：由于语言统一，后期甚至可以直接把 Action 逻辑揉进核心 FastAPI 服务中，简化架构。)*
5. **LLM 支撑层**：部署于本地的微调大模型，提供意图/槽位解析、闲聊生成服务。

## 4. 数据库设计 (PostgreSQL)

基于 MVP（最小可行性产品）原则，设计 5 张核心业务表：

### 4.1 用户表 (`users`)


| **字段名**   | **类型**  | **说明**      |
| :----------- | :-------- | :------------ |
| `id`         | UUID      | 主键          |
| `username`   | VARCHAR   | 用户名        |
| `email`      | VARCHAR   | 邮箱 (唯一)   |
| `created_at` | TIMESTAMP | 注册时间      |

### 4.2 订单主表 (`orders`)


| **字段名**      | **类型** | **说明**                           |
| :-------------- | :------- | :--------------------------------- |
| `id`            | VARCHAR  | 订单号 (主键)                      |
| `user_id`       | UUID     | 外键 -> users.id                   |
| `status`        | VARCHAR  | 状态 (待发货/已发货/已完成/已取消) |
| `address`       | VARCHAR  | 收货地址                           |
| `contact_email` | VARCHAR  | 收件人邮箱                         |
| `total_amount`  | DECIMAL  | 订单总金额                         |

### 4.3 商品表 (`products`)


| **字段名** | **类型** | **说明** |
| :--------- | :------- | :------- |
| `id`       | UUID     | 主键     |
| `name`     | VARCHAR  | 商品名称 |
| `price`    | DECIMAL  | 单价     |
| `stock`    | INT      | 库存量   |

### 4.4 物流表 (`logistics`)


| **字段名**         | **类型** | **说明**                  |
| :----------------- | :------- | :------------------------ |
| `id`               | UUID     | 主键                      |
| `order_id`         | VARCHAR  | 外键 -> orders.id         |
| `tracking_no`      | VARCHAR  | 物流单号                  |
| `status`           | VARCHAR  | 揽件/运输中/派送中/已签收 |
| `current_location` | VARCHAR  | 当前位置                  |

### 4.5 售后表 (`after_sales`)


| **字段名** | **类型** | **说明**                 |
| :--------- | :------- | :----------------------- |
| `id`       | UUID     | 主键                     |
| `order_id` | VARCHAR  | 外键 -> orders.id        |
| `type`     | VARCHAR  | 退货 / 换货              |
| `reason`   | TEXT     | 售后原因                 |
| `status`   | VARCHAR  | 处理中 / 已同意 / 已驳回 |

## 5. API 接口设计 (FastAPI 后端)

利用 FastAPI 自动生成基于 OpenAPI 标准的交互式文档 (Swagger UI)，极大便利后期联调。提供给前端和 Rasa Action Server 调用的核心 RESTful API 示例：

* **Chat 接口 (提供给 Vue 前端)**

  * `POST /api/v1/chat/send`: 发送消息（接收前端 message，转发给 Rasa REST channel，返回机器人的回复）。
* **订单相关 (提供给 Rasa Action Server)**

  * `GET /api/v1/orders/{order_id}`: 异步查询订单基本信息及状态。
  * `PUT /api/v1/orders/{order_id}/address`: 修改订单收货信息。
  * `POST /api/v1/orders/{order_id}/cancel`: 取消订单（内部校验：仅当状态为“待发货”时允许）。
* **物流相关**

  * `GET /api/v1/logistics/{order_id}`: 查询指定订单的最新物流轨迹。
* **售后相关**

  * `POST /api/v1/aftersales/apply`: 提交退换货申请。

## 6. 核心对话流设计 (Rasa CALM `flows.yaml`)

不再编写繁杂的 Intent 和 Story，使用声明式的业务流。以下为伪代码示例设计：

```yaml
flows:
  check_order_status:
    description: "用户想要查询订单状态"
    steps:
      - collect: order_id
      - action: action_fetch_order_status
        next:
          - if: slots.order_status == "not_found"
            step: not_found_msg
          - else:
            step: show_status

  modify_shipping_info:
    description: "用户想要修改收货地址或邮箱"
    steps:
      - collect: order_id
      - action: action_check_order_can_modify # 校验是否已发货
      - collect: new_address
      - collect: new_email
      - action: action_update_shipping_info
```

## 7. LLM 微调与闲聊策略

### 7.1 数据集构建 (Data Construction)

针对电商客服域构建指令微调数据集（约200-300条）。

**Format (JSONL):**

{"instruction": "抽取客服对话中的关键信息。", "input": "我刚买的那个订单号是 88291 的衣服，帮我把地址改成北京市朝阳区望京SOHO", "output": "{\"order_id\": \"88291\", \"new_address\": \"北京市朝阳区望京SOHO\"}"}
### 7.2 微调方案 (Fine-Tuning)

* **基座模型**：Qwen2-7B-Instruct
* **方法**：使用 Unsloth 框架应用 LoRA (Low-Rank Adaptation) 技术。
* **目标**：提升模型在 JSON 格式化输出、槽位填充 (Slot Filling) 和业务意图路由上的准确性和稳定性，减少大模型的“幻觉”。

### 7.3 闲聊与对话修复 (Chitchat & Repair)

* **Chitchat**: 当用户输入与 5 大核心 Flow 无关时（如：“你们这儿的客服态度真好”），触发 Fallback，直接请求本地 LLM 生成闲聊文本并返回。
* **Repair**: 利用 CALM 特性。若用户在执行 `modify_shipping_info` 途中询问 `check_order_status`（物流流转），Rasa 自动挂起修改流程，执行物流查询流，结束后提示“我们回到刚才修改地址的步骤，您的新邮箱是？”。

## 8. 项目实施计划（4周极限版）

* **第 1 周：基础设施拉齐与底层服务打通**

  * 配置 PostgreSQL + Redis，创建数据表并注入测试数据。
  * 使用 **FastAPI** 搭建后端脚手架，集成 SQLAlchemy (异步配置)，实现基础的订单查询 API，并查看自动生成的 Swagger 接口文档。
  * 本地 Ollama 部署 Qwen2-7B，测试基础 API 调用。
* **第 2 周：Rasa CALM 业务流与 FastAPI 接口联调**

  * 初始化 Rasa Pro，编写 5 大核心场景的 `flows.yaml`。
  * 使用 Python 编写 Action Server，通过 `httpx` 异步请求对接 FastAPI 后端的所有 RESTful 接口。
  * 跑通所有业务的正常对话分支。
* **第 3 周：LLM 指令微调与对话能力进阶**

  * 构造 200 条电商垂类数据集。
  * 运行 LoRA 微调，替换本地基座模型权重。
  * 测试并优化“闲聊兜底”和“多轮对话打断与修复”功能。
* **第 4 周：前端开发、全链路压测与论文撰写**

  * Vue3 + Tailwind CSS 开发响应式 WebChat 界面。
  * 前后端联调，修复跨域（CORS）、WebSocket 断连等工程问题。
  * 撰写毕业论文，整理系统截图与性能评测指标（如槽位提取准确率、平均响应延迟等），录制答辩 Demo 视频。
