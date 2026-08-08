# API Design

API 前缀为 `/api/v1`，使用 JSON、OpenAPI、OAuth2/JWT（Phase 1）和统一错误格式：`{ "code", "message", "trace_id", "details" }`。所有变更操作要求 `Idempotency-Key`，并返回 `trace_id`。

| 方法 | 路径 | 角色 | 目的 |
| --- | --- | --- | --- |
| GET | `/healthz` | Public | 存活探针 |
| POST | `/auth/token` | Public | 演示/生产身份认证，签发 JWT |
| GET | `/me` | Authenticated | 返回当前身份及角色 |
| GET | `/orders/{order_number}` | Owner/Staff | 验证资源归属后读取订单与物流摘要 |
| GET | `/audit-logs` | Supervisor/Admin | 读取最近的脱敏审计记录 |
| POST | `/conversations` | Customer | 发起会话 |
| POST | `/conversations/{id}/messages` | Customer/Operator | 发送消息并触发工作流 |
| GET | `/conversations/{id}` | Owner/Operator | 读取会话、状态与脱敏消息 |
| GET | `/tickets` | Operator/Supervisor/Admin | 工单列表（受范围过滤） |
| GET | `/tickets/{id}` | Scoped staff | 工单详情及时间线 |
| POST | `/approvals/{id}/decision` | Supervisor | 审批或拒绝动作 |
| POST | `/conversations/{id}/handoff` | Operator/Supervisor | 人工接管 |
| GET | `/workflow-runs/{trace_id}` | Scoped staff | 读取工作流 trace 摘要 |
| POST | `/admin/demo/seed` | Admin | 幂等加载演示数据 |
| POST | `/admin/demo/reset` | Admin | 仅开发环境重置演示数据 |
| POST | `/admin/evaluations/run` | Admin | 运行评估集 |
| GET | `/metrics/dashboard` | Supervisor/Admin | 读取聚合指标 |

## 核心请求契约

`POST /conversations/{id}/messages`：`{message, client_message_id, attachments?}`。消息体限制、附件元数据与客户归属均在 API 层校验；返回 `{conversation_id, ticket_id, trace_id, workflow_status, customer_reply?}`。

### Phase 2 request contract

`POST /conversations` 由 Customer 创建自己的会话，返回 `conversation_id`。`POST /conversations/{id}/messages` 必须带 `Idempotency-Key`，且 `client_message_id` 在会话内唯一。当前只接受纯文本、最大 2,000 字符；附件留待后续阶段。消息触发 order-status/delivery-delay 确定性工作流，返回 ticket、trace 和客户可见回复。

`GET /conversations/{id}`、`GET /workflow-runs/{trace_id}` 和订单事实均执行 Customer 归属或 staff RBAC 检查。Phase 2 不提供退款、地址或承运商写操作。

### Phase 3 request contract

`POST /conversations/{id}/actions` 由 Customer 提交 `{action_type, order_number, reason_code, amount_minor?, address_reference?, simulate_timeout?}`，并要求 `Idempotency-Key`。动作类型为 `refund`、`return`、`address_update`、`damaged_item`；API 返回 action、ticket、trace 和可选 approval ID。

`POST /approvals/{id}/decision` 仅接受 Supervisor 的 `{decision, reason_code, comment?}`，并要求 `Idempotency-Key`。批准只会将动作排队；由 outbox dispatcher 调用 provider。`POST /admin/outbox/dispatch` 仅限 Admin，也要求 `Idempotency-Key`，用于本地演示与可重试投递。

`POST /admin/demo/reset` 在 development 环境中清空并在同一事务内重新加载合成数据，因此调用方需要重新登录；这避免了删除唯一 Admin 身份后无法再次 seed 的死锁。

### Phase 4 Coze contract

`POST /coze/v1/wf_customer_intake` is a stateless, signed integration boundary. It accepts `{schema_version, message, correlation_id}` and requires `X-Coze-Signature = hex(HMAC-SHA256(raw body, COMMERCECARE_COZE_WEBHOOK_SECRET))`. A valid request returns a versioned, validated Router decision and a safe outcome only; it neither receives JWT credentials nor reads/writes customer orders. Invalid signatures return HTTP 403 under the standard error envelope. See `workflows/coze/README.md` for the remaining sub-flow schemas and request examples.

### Phase 5 evaluation and metrics contract

`POST /admin/evaluations/run` requires Admin and `Idempotency-Key`. It runs the active synthetic suite with the deterministic judge, persists an auditable report, and returns its summary. It never triggers a business-state write or external provider side effect. `GET /metrics/dashboard` requires Supervisor or Admin and returns bounded aggregates plus SLO state; it does not include raw customer messages, prompt content, model private reasoning, or credentials.

`POST /approvals/{id}/decision`：`{decision: APPROVE|REJECT, reason_code, comment?}`。决策必须由当前有权限的 Supervisor 作出，过期或已决请求返回 `APPROVAL_NOT_ACTIONABLE`。

`GET /workflow-runs/{trace_id}` 不返回私有推理、提示词全文或未脱敏 PII；只返回 agent/工具/证据/状态迁移的结构化摘要。

## Provider 端口

只读：`get_order`、`get_customer`、`search_products`、`get_inventory`、`get_shipment`、`search_policy`。写入：`create_ticket`、`update_ticket`、`update_address`、`request_refund`、`request_return`、`create_carrier_inquiry`、`send_customer_message`、`request_human_approval`。每个写入命令统一含 `actor`、`reason_code`、`idempotency_key`，并在领域层执行授权检查和审计。
