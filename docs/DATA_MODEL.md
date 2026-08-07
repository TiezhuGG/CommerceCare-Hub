# Data Model

## 1. 约定

使用 PostgreSQL、SQLAlchemy 2 和 Alembic。主键采用 UUID；时间采用 UTC 的 `timestamptz`；金额为整数分和 ISO 货币代码。软删除只用于非核心配置，审计与交易事件不可修改。所有外部标识存为受约束的 provider/name + external_id 对。

## 2. MVP 表

| 表 | 关键字段与约束 |
| --- | --- |
| users | `id`, `email` unique, `password_hash`, `role`, optional `customer_id`；RBAC 身份与客户归属绑定 |
| customers | `id`, `external_id` unique, `tier`, `pii_token`；不保存完整 PII 明文 |
| products | `id`, `external_id` unique, `title`, `status` |
| skus | `id`, `product_id`, `sku_code` unique, `price_minor`, `currency` |
| orders | `id`, `order_number` unique, `customer_id`, `status`, `ordered_at` |
| order_items | `id`, `order_id`, `sku_id`, `quantity`, `unit_price_minor` |
| shipments | `id`, `order_id`, `tracking_number` unique, `status`, `eta_at` |
| conversations | `id`, `customer_id`, `status`, `assigned_actor_id` |
| messages | `id`, `conversation_id`, `sender_type`, `body_redacted`, `created_at` |
| tickets | `id`, `conversation_id`, `state`, `reason_code`, `trace_id` unique |
| ticket_events | `id`, `ticket_id`, `event_type`, `from_state`, `to_state`, `actor_id` |
| workflow_runs | `id`, `trace_id` unique, `ticket_id`, `status`, `final_result_code` |
| agent_runs | `id`, `workflow_run_id`, `agent_name`, `prompt_key`, `prompt_version`, `input_summary`, `output_summary`, `latency_ms`, `token_usage` |
| retrieval_evidence | `id`, `workflow_run_id`, `document_id`, `document_version`, `matched_section`, `relevance_score`, `observed_at` |
| tool_calls | `id`, `workflow_run_id`, `tool_name`, `request_summary`, `result_summary`, `idempotency_key`, `status` |
| approval_requests | `id`, `ticket_id`, `action_id`, `action_type`, `status`, `expires_at`, `decided_by` |
| service_actions | `id`, `ticket_id`, `workflow_run_id`, `order_id`, `action_type`, `status`, `reason_code`, `idempotency_key`, redacted payload、provider reference 与 failure code；动作/订单/幂等键联合唯一 |
| policy_documents | `id`, `document_key`, `version`, `effective_from`, `effective_to`, `scope`, `body`, unique(`document_key`,`version`) |
| prompt_versions | `id`, `prompt_key`, `version`, `template`, `active`, unique(`prompt_key`,`version`) |
| eval_cases | `id`, `category`, `input`, `expected_result`, `active` |
| audit_logs | `id`, `trace_id`, `actor_id`, `event_type`, `resource_type`, `resource_id`, `payload_redacted`, `occurred_at` |
| idempotency_records | `action_type`, `target_resource_id`, `idempotency_key` 联合唯一；保存首次响应以安全重放 |
| outbox_events | `event_type`, aggregate 引用、payload、`attempts`、`last_error_code`、`published_at`；与领域写入同事务创建 |

Phase 3 的地址动作仅持久化受控 address reference 的不可逆 fingerprint；明文地址不进入数据库、审计日志或 mock provider。

## 3. 幂等与一致性

每个写操作创建 `tool_calls` 记录，并在其作用域内使用唯一约束 `unique(action_type, target_resource_id, idempotency_key)`（最终迁移中落到专用 `idempotency_records` 或等价约束表）。请求重放返回原有结果，不重复调用 provider。领域写入、ticket event、audit log 和 outbox event 在同一数据库事务完成；异步 provider 调用通过 outbox 重试。

## 4. 策略与证据

策略检索结果必须携带 `document_id`、`version`、`effective_time`、`matched_section`、`relevance_score` 和适用性判断。策略文本、客户消息、OCR/evidence metadata 均是不可信内容，不能改变系统指令或授权结论。

## 5. 演示数据目标

Phase 1 seed：至少 30 customers、100 products/SKUs、100 orders、100 shipments，含正常与异常案例、不同会员等级、不同 ticket 状态、当前与过期策略版本。
