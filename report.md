# Benchmark 实验结果分析报告

本报告基于 [benchmark/results/20260417_222317_paper_system_benchmark](benchmark/results/20260417_222317_paper_system_benchmark) 的正式实验结果撰写，目标不是重复输出原始表格，而是回答三个更重要的问题：

1. 当前哪套系统组合最值得继续投入。
2. 分数差距到底来自能力差异、质量差异，还是技术故障。
3. 从工程角度看，系统距离“可上线”还差哪几步。

## 1. 实验范围与评测口径

本轮实验配置如下：

- 评测档位：`paper`
- 数据集层级：`extended`
- 样本选择方式：`all_unique`
- 参评系统：`rasa_only`、`rasa_plus_llm`、`rasa_plus_lora_llm`
- 榜单划分：
  - `shared_core`：共享核心能力
  - `agent_extension`：智能体扩展能力

正式排序按以下优先级决胜：

1. `suite_family_macro_pass_rate`
2. `suite_unique_micro_pass_rate`
3. `suite_family_macro_success_rate`
4. `eligibility_rate`

其中：

- `pass_rate` 衡量“最终是否满足质量门槛”。
- `success_rate` 只看“流程有没有走通”，不代表内容已经合格。
- `eligibility_rate` 衡量系统是否具备该任务的基础能力。

这一点很关键，因为本轮结果里最容易出现的误读就是把“流程跑通”误认为“回答合格”，或者把“能力不支持”误认为“回答质量差”。

## 2. 一页结论

先给最终判断：

- 当前综合最优方案是 `Rasa + LoRA LLM`，但优势只出现在 `agent_extension`，而且统计上还不够稳定，不能表述成“显著优于”。
- 在 `shared_core` 上，`Rasa + LLM` 与 `Rasa + LoRA LLM` 的正式指标完全相同，LoRA 没有带来可见收益。
- `纯 Rasa` 不适合作为扩展能力主方案，但在窄域、强结构化任务上仍然有价值，尤其是物流查询。
- 当前最大的工程瓶颈不是样本覆盖率，而是两类问题：
  - 共享核心链路里的订单号幻觉。
  - 扩展链路里事务性动作的技术失败和极端长尾时延。

更直接地说，这轮实验并没有证明“模型加上去之后所有能力都变好了”，反而说明系统已经出现了很典型的分化：

- 推荐类场景，混合系统明显强于纯 Rasa。
- 物流、订单、售后这类需要强约束和强事实对齐的场景，混合系统还没有把“会说”变成“说得对”。
- 涉及草案生成、待确认动作、确认按钮的事务性链路，目前还处在不稳定甚至不可用状态。

## 3. 覆盖率先排除，结果可信度足够

从 [benchmark/results/20260417_222317_paper_system_benchmark/analysis/sample_coverage.csv](benchmark/results/20260417_222317_paper_system_benchmark/analysis/sample_coverage.csv) 看：

- 所有系统在两个榜单、所有场景族上的 `coverage_rate` 都是 `1.0`。
- 所有 `missing_sample_ids` 为空。

这意味着本轮结果不是“某些难样本漏跑了”导致的偏差，结论主要反映真实能力差异。

需要补充一个细节：`agent_extension` 总会话数是 29 而不是 30，是因为 `transaction_pending_action_expired_extended` 本身被标记为 `repeatable = False`，这属于设计使然，不影响去重样本覆盖率。

## 4. 总体排名与含义

### 4.1 共享核心能力：LoRA 没有带来增益

![共享核心能力正式排名图](benchmark/results/20260417_222317_paper_system_benchmark/analysis/charts/shared_core_ranking.svg)

`shared_core` 的正式结果如下：

| 系统 | 场景族等权通过率 | 去重样本微平均通过率 | 场景族等权成功率 | 可评分样本占比 | 结论 |
| --- | ---: | ---: | ---: | ---: | --- |
| Rasa + LLM | 0.3333 | 0.3846 | 0.9167 | 1.0 | 与 LoRA 实质并列第一 |
| Rasa + LoRA LLM | 0.3333 | 0.3846 | 0.9167 | 1.0 | 与 Base LLM 指标完全相同 |
| 纯 Rasa | 0.2500 | 0.2308 | 1.0000 | 1.0 | 流程稳定，但质量门槛不足 |

这里最值得注意的是两点：

- `Rasa + LLM` 和 `Rasa + LoRA LLM` 的核心指标完全一致，LoRA 在共享核心链路上没有形成增益。
- `纯 Rasa` 的 `suite_family_macro_success_rate = 1.0`，但 `suite_unique_micro_pass_rate = 0.2308`。这说明它经常能把流程走完，但输出结构、字段或内容经常不满足质量要求。

换句话说，`shared_core` 上的主要矛盾不是“能不能回答”，而是“回答是否满足业务格式和事实约束”。

### 4.2 智能体扩展能力：LoRA 暂时领先，但不能夸大

![智能体扩展能力正式排名图](benchmark/results/20260417_222317_paper_system_benchmark/analysis/charts/agent_extension_ranking.svg)

`agent_extension` 的正式结果如下：

| 系统 | 场景族等权通过率 | 去重样本微平均通过率 | 场景族等权成功率 | 可评分样本占比 | 重复稳定性 | 结论 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Rasa + LoRA LLM | 0.3750 | 0.3333 | 0.6875 | 1.0 | 0.8571 | 当前第一 |
| Rasa + LLM | 0.2916 | 0.2667 | 0.6875 | 1.0 | 0.8571 | 当前第二 |
| 纯 Rasa | 0.0000 | 0.0000 | 0.1667 | 0.1333 | 1.0 | 仅能作基线参考 |

这里的结论要讲清楚边界：

- `Rasa + LoRA LLM` 确实排名第一。
- 但它和 `Rasa + LLM` 的 Wilson 95% 置信区间重叠，说明领先差距还不稳定。
- 因此更准确的表述是：LoRA 在扩展能力上出现了正向信号，但还不足以宣称已经稳定领先。

对 `纯 Rasa` 也必须客观解读。它在这一榜单低分的主要原因不是“答得差”，而是“多数任务根本不支持”：

- `eligibility_rate = 0.1333`
- `unsupported = 25/29`

所以 `agent_extension` 榜单里 `纯 Rasa` 的低分，更多是在反映能力边界，而不是生成质量。

## 5. 场景族拆开看，差距到底出在哪里

### 5.1 推荐场景已经证明混合系统必要

推荐是本轮最明确的结论点。

`shared_core / recommendation`：

- `Rasa + LLM = 1.0`
- `Rasa + LoRA LLM = 1.0`
- `纯 Rasa = 0.0`

`agent_extension / recommendation`：

- `Rasa + LoRA LLM = 0.6667`
- `Rasa + LLM = 0.3333`
- `纯 Rasa = 0.0`

这说明两件事：

- 纯规则系统已经无法胜任当前定义下的推荐质量门槛。
- LoRA 的主要收益集中在推荐扩展场景，而不是所有扩展场景全面提升。

所以如果后续资源有限，LoRA 相关优化应该优先押在推荐链路，而不是平均撒在所有模块上。

### 5.2 物流查询是纯 Rasa 仍然有竞争力的证据

`shared_core / logistics_query` 的结果非常有代表性：

- `纯 Rasa = 0.6667`
- `Rasa + LLM = 0.0`
- `Rasa + LoRA LLM = 0.0`

这不是偶然噪声，而是结构化任务的典型现象：规则系统虽然不灵活，但在窄域、字段固定、答案边界明确的查询任务上，稳定性依然有优势。

因此本项目的正确方向不是“完全抛弃 Rasa”，而是：

- 把 Rasa 保留为结构化事实查询和流程控制层。
- 让 LLM 负责推荐、知识融合、多轮理解这类规则难以覆盖的场景。

如果反过来让 LLM 直接主导订单、物流、售后状态回答，而缺少足够强的约束与检索绑定，就会出现本轮已经暴露出来的问题：流程成功，但事实不可信。

### 5.3 订单与售后说明混合系统还没有解决“强约束事实对齐”

`shared_core / order_query` 三个系统都是 `0.3333`，看上去差异不大，但失败原因完全不同。

- 纯 Rasa 的问题更偏结构化缺失。
- 两个混合系统的问题更偏事实幻觉和登录拦截。

`shared_core / after_sales_query` 更进一步暴露了问题：

- 三个系统的 `family_pass_rate` 都是 `0.0`
- 但 `纯 Rasa family_success_rate = 1.0`
- 两个混合系统 `family_success_rate = 0.6667`

这说明售后查询目前没有任何方案真正达到合格线，只是失败形态不同：

- 纯 Rasa 倾向于“信息不全、格式不达标”。
- 混合系统倾向于“看起来更聪明，但更容易产生错误事实或技术失败”。

### 5.4 扩展能力里的事务性动作是当前最严重短板

`agent_extension / transactional_action` 的结果没有歧义：

- 三个系统 `family_pass_rate` 全部为 `0.0`
- 两个混合系统 `conversation_success_rate` 也都是 `0.0`

这意味着问题已经不是“生成得不够好”，而是“链路根本跑不通”。

更关键的是，两个混合系统在这一场景族上的失败标签高度一致：

- `technical_failure = 11`
- `missing_required_cards = 9`
- `missing_required_actions = 9`
- `missing_confirmation_buttons = 9`

这组组合标签非常重要。它说明不是只差一个“确认按钮没渲染出来”，而是上游草案或动作生成阶段先发生了技术故障，导致后续需要的卡片、动作、按钮全部缺失。

## 6. 失败模式分析

![独占主失败原因分布饼图](benchmark/results/20260417_222317_paper_system_benchmark/analysis/charts/exclusive_failure_pie.svg)

![多标签失败诊断柱状图](benchmark/results/20260417_222317_paper_system_benchmark/analysis/charts/failure_flags_bar.svg)

本轮实验里最关键的失败模式可以归纳成四类。

### 6.1 纯 Rasa 在扩展能力上主要是“不支持”

`agent_extension / rasa_only` 的主失败原因中：

- `unsupported = 25`，占比 `86.21%`

因此这部分结论不能写成“纯 Rasa 生成质量差”，更准确的说法是：

- 当前纯 Rasa 几乎不具备附件、图片、知识库策略、待确认动作等扩展能力。
- 它在扩展榜单只能作为下限基线，不能作为主系统方案。

### 6.2 混合系统在共享核心上最严重的问题是幻觉订单号

`shared_core` 里两个混合系统的主失败原因完全一致：

- `hallucinated_order_id = 12`，占失败的 `75%`
- `technical_failure = 2`
- `login_block_failure = 2`

这说明共享核心链路当前最危险的风险不是“答非所问”，而是“编造本不该出现的订单标识或状态关联”。这类问题一旦进入真实客服流程，业务风险远高于普通格式错误。

从会话级样本看，问题集中出现在以下样本：

| 样本 ID | 系统 | 主失败原因 | 含义 |
| --- | --- | --- | --- |
| `order_query_specific_extended` | 两个混合系统 | `hallucinated_order_id` | 指向具体订单时仍会编造订单信息 |
| `logistics_query_no_record_extended` | 两个混合系统 | `hallucinated_order_id` | 明明应答“无记录”，却仍生成订单相关内容 |
| `logistics_query_recent_extended` | 两个混合系统 | `hallucinated_order_id` | 最近物流查询没有被严格约束到真实记录 |
| `after_sales_refund_status_extended` | 两个混合系统 | `hallucinated_order_id` | 售后状态查询也存在同类幻觉 |
| `order_query_requires_login_extended` | 两个混合系统 | `login_block_failure` | 登录态约束还没有被稳定执行 |

这类问题的根因大概率不是“模型不会回答”，而是缺乏足够强的事实绑定和拒答约束。系统现在更像是在“生成一个看上去合理的客服回复”，而不是“只基于已认证、已命中的订单实体作答”。

### 6.3 纯 Rasa 在共享核心上的问题更偏输出结构

`shared_core / rasa_only` 的主要失败原因是：

- `missing_required_cards = 8`
- `format_error = 6`

这与混合系统形成了鲜明对比。纯 Rasa 更多是在“该展示什么结构、该带什么字段”上失分，而不是在事实层面乱说。

这也是为什么它会出现一个看似矛盾的现象：

- `conversation_success_rate` 很高，很多场景甚至是 `1.0`
- 但 `pass_rate` 仍然明显偏低

根本原因是规则系统能稳定返回一个结果，但这份结果不一定符合新的评测格式和卡片要求。

### 6.4 扩展链路的技术失败已经压过了内容质量问题

两个混合系统在 `agent_extension` 上的主失败原因第一位都是 `technical_failure = 11`。

其中最典型的是事务性动作链路。会话级数据表明：

| 样本 ID | 系统 | 延迟 | HTTP 错误 | 主失败原因 |
| --- | --- | ---: | ---: | --- |
| `transaction_pending_action_expired_extended` | Rasa + LLM | 305251.46 ms | 1 | `technical_failure` |
| `transaction_pending_action_expired_extended` | Rasa + LoRA LLM | 305251.44 ms | 1 | `technical_failure` |
| `transaction_update_shipping_confirm_extended` | 两个混合系统 | 226-243 ms | 1 | `technical_failure` |
| `transaction_after_sales_draft_extended` | 两个混合系统 | 194-195 ms | 1 | `technical_failure` |
| `transaction_cancel_draft_cancel_extended` | 两个混合系统 | 239-246 ms | 1 | `technical_failure` |

这些失败同时伴随：

- `missing_required_cards = True`
- `missing_required_actions = True`
- `missing_confirmation_buttons = True`

所以当前事务性动作的首要任务不是提示词微调，而是把后端草案生成、待确认动作状态机、确认按钮渲染链路先修通。

## 7. 时延分析：能力提升已经开始明显吞噬交互体验

本轮实验的另一个重要结论是，混合系统虽然在部分能力上更强，但时延成本已经非常高。

### 7.1 纯 Rasa 速度稳定，基本在 2 秒级

在 `shared_core` 里，纯 Rasa 的 p95 基本稳定在：

- 推荐：`2080 ms` 左右
- 订单：`2250-2267 ms`
- 物流：`2255-2259 ms`
- 售后：`2245-2261 ms`

它的优势非常明确：速度快、波动小、重复稳定性高。

### 7.2 混合系统在推荐和知识类场景上已经进入“秒级偏重”区间

几个最典型的 p95 指标如下：

- `shared_core / recommendation`
  - Rasa + LLM：`24430-30183 ms`
  - Rasa + LoRA LLM：`22132-24555 ms`
- `agent_extension / knowledge_and_multimodal`
  - Rasa + LLM：`15634-23131 ms`
  - Rasa + LoRA LLM：`14302-16991 ms`
- `agent_extension / recommendation`
  - Rasa + LLM：`7980-17803 ms`
  - Rasa + LoRA LLM：`17335-24791 ms`

这意味着当前扩展能力虽然“能做”，但交互代价已经很高。如果直接用于人工客服辅助，客服会明显感受到等待；如果直接用于用户侧自助问答，体验风险更大。

### 7.3 事务性动作的长尾时延已经接近不可接受

`agent_extension / transactional_action` 中，两套混合系统在一轮重复里的 p95 都达到：

- `244249 ms` 左右

即约 `244 秒`，超过 4 分钟。

从会话级数据看，这个长尾基本由 `transaction_pending_action_expired_extended` 这一类故障会话拖高。即使不看聚合指标，单条会话 305 秒的延迟本身也足以判定该链路当前不可上线。

因此从工程优先级看，事务性动作不是“效果还差一点”，而是“系统可靠性不达标”。

## 8. 对架构策略的实际启示

这轮实验对整体架构给出的信号很明确。

### 8.1 纯 Rasa 不该被完全替代，而应退回它擅长的位置

它仍然适合承担：

- 强结构化查询
- 确定性流程控制
- 快速响应的兜底链路

特别是在物流查询这种规则边界明确的场景下，它仍然优于当前混合系统。

### 8.2 LLM 价值已经被证明，但必须被约束而不是放大

LLM 的增益主要体现在：

- 推荐理解与组合
- 知识融合
- 多模态理解

但订单、物流、售后状态这类任务不能只靠“生成能力”解决，必须进一步强化：

- 检索结果到答案字段的强绑定
- 登录态与权限校验
- 空结果显式拒答
- 订单号、售后单号的白名单化引用

### 8.3 LoRA 的投资方向应该更聚焦

当前 LoRA 的收益集中在推荐扩展场景：

- `agent_extension / recommendation`
  - Base LLM：`0.3333`
  - LoRA LLM：`0.6667`

但在其他场景上：

- `knowledge_and_multimodal` 两者相同，都是 `0.5`
- `transactional_action` 两者都 `0.0`
- `shared_core` 两者总体完全相同

所以 LoRA 不是“全局增强器”，更像是对推荐任务的局部增强。后续如果继续训练，样本和目标都应该更聚焦，避免把它包装成普适升级。

## 9. 后续迭代优先级

基于当前结果，建议的改进顺序如下。

### 优先级 1：先修事务性动作链路的技术可靠性

目标不是提分，而是先把链路跑通：

- 排查草案生成接口的 HTTP 错误和超时
- 排查 pending action 状态机
- 保证卡片、动作、确认按钮在技术成功后可完整返回
- 为事务链路增加更细粒度的埋点，区分“草案失败”“确认失败”“渲染失败”

如果这一层不修，继续调提示词基本不会产生有效收益。

### 优先级 2：治理共享核心中的订单号幻觉

应优先处理：

- 订单查询
- 物流查询
- 售后状态查询

建议方向：

- 改成“检索结果为空则显式拒答”
- 输出中的订单号只允许来自检索命中结果
- 登录态不满足时，直接走阻断模板，禁止模型补全

这是当前最直接的业务风险点。

### 优先级 3：把 LoRA 资源继续押注在推荐链路

现有数据已经说明推荐是 LoRA 最有价值的方向。下一轮优化应优先关注：

- 约束词理解
- 多条件排序
- 比较型推荐
- 售后政策联动推荐

不建议在事务链路尚未修复前，把主要精力放在 LoRA 全面扩展上。

### 优先级 4：保留纯 Rasa 作为结构化兜底

建议不要把纯 Rasa 直接移除，而是把它保留为：

- 物流、订单、售后等结构化查询的兜底路径
- LLM 失败时的快速降级通道
- 对关键字段做最终校验的规则层

## 10. 最终结论

如果只用一句话概括本轮实验：

当前系统已经证明“Rasa + LLM”路线对推荐和扩展能力是必要的，但还没有证明“LLM 主导的客服系统已经足够稳定”；尤其在订单事实约束和事务性动作链路上，系统离可上线状态还有明显距离。

更具体一点：

- 当前最佳整体方案是 `Rasa + LoRA LLM`，但优势主要集中在扩展推荐场景。
- `shared_core` 里 LoRA 没有带来额外收益。
- 纯 Rasa 不适合作为扩展能力主方案，但在窄域结构化任务上仍然有价值。
- 目前最需要投入的不是继续追求排行榜分差，而是先把“技术失败”和“事实幻觉”这两个上线阻塞项压下去。

在下一轮实验之前，如果事务性动作还存在 HTTP 错误、超时、卡片缺失、确认按钮缺失这类故障，那么无论模型本身再强，系统也很难在真实客服流程中稳定落地。
