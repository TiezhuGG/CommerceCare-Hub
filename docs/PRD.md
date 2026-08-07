# Product Requirements Document

## Phase 3 after-sales policy decision

The interview-demo implementation uses a deliberately conservative approval rule: every refund and address update requires Supervisor approval, regardless of amount. Returns are accepted only for delivered orders, and damaged-item reports are automatically queued as a reversible carrier inquiry. This narrower policy is intentional until Phase 4 policy evaluation and confidence/risk signals are available; the action domain service, rather than an LLM or HTTP handler, enforces it.

## Phase 4 structured-agent decision

Phase 4 adds model-like structured analysis, not autonomous transaction execution. A schema-validated Risk/Compliance decision can explain whether a workflow should allow, request approval, or escalate, but it cannot directly alter an order, approval, or action. During this phase, policy/risk signals may make existing conservative rules stricter; they never relax the Phase 3 domain-service checks.

## 1. 目标与边界

CommerceCare Hub 为电商客户提供售前、售后和工单协同服务。它不是 FAQ 聊天机器人：每一项可改变外部或业务状态的建议都必须经过确定性业务规则、授权和审计。

MVP 支持的意图：`product_question`、`stock_and_delivery_question`、`order_status`、`update_address`、`refund_request`、`return_request`、`missing_wrong_or_damaged_item`、`invoice_or_price_protection`。

本项目不在 MVP 内实现真实支付扣款、真实承运商写入、自由文本自动承诺赔付，或由模型直接操作数据库。

## 2. 用户与权限

| 角色 | 可做的事 |
| --- | --- |
| Customer | 发起并查看自己的会话、订单相关回复和工单状态 |
| AgentOperator | 查看被授权会话，执行已获准的低风险动作，发起审批与人工接管 |
| Supervisor | 审批或拒绝高风险动作，查看队列、工单与审计 |
| Admin | 管理用户、角色、策略、提示词版本、演示数据和评估 |

## 3. 核心工作流

1. API 校验、标准化客户输入并创建带 `trace_id` 的 workflow run。
2. RouterAgent 输出受 Pydantic schema 校验的意图、字段缺失、情绪、紧急度、风险标签与置信度。
3. ContextAgent 仅调用只读工具，返回带来源和观测时间的事实；缺失或冲突事实显式标记。
4. PolicyAgent 按平台、店铺、地区、下单时间和策略类型检索已版本化的证据。
5. ResolutionPlannerAgent 提出 1–3 个不可执行的方案。
6. RiskComplianceAgent 给出 `ALLOW`、`REQUIRE_APPROVAL` 或 `ESCALATE`。
7. 领域服务在授权通过后执行幂等写动作；否则创建审批或升级记录。
8. ReplyAgent 仅基于已确认事实和真实动作结果生成客户可见答复。
9. 创建或更新工单，并记录完整审计轨迹与评估所需的结构化摘要。

## 4. 默认审批规则

下列任一条件成立即至少 `REQUIRE_APPROVAL`：退款金额大于 CNY 100、超出标准政策、重复退款风险、VIP 额外补偿、模型置信度低于 0.75、客户描述与订单事实冲突、法律责任或平台外交易承诺、任何不可逆动作。无法安全判定时返回 `ESCALATE`。

## 5. 质量与验收

- 客户面回复必须可追溯到事实、政策证据或已执行动作，且不暴露内部评分、风险标签、提示词或私有推理。
- 同一业务动作使用相同幂等键重试不得重复执行。
- 任何非法状态迁移返回机器可读的 typed domain error。
- mock provider 下的本地环境可独立完成关键演示流程。
- 失败模式至少覆盖重复退款、物流超时、策略冲突、客户端断开、审批超时、不可读证据、提示词注入和跨客户越权。

完整可验证条目见 [验收标准](ACCEPTANCE_CRITERIA.md)。
