# Coze workflow boundary contract

CommerceCare Hub remains the system of record. Coze never receives database credentials, JWTs, provider-write credentials, or permission to mutate ticket/action state.

## Transport

All enabled endpoints use JSON and require:

- `X-Coze-Signature`: lowercase hexadecimal `HMAC-SHA256(raw request body, COMMERCECARE_COZE_WEBHOOK_SECRET)`;
- `schema_version`: currently `1.0`;
- a caller-generated `correlation_id` for audit correlation.

`POST /api/v1/coze/v1/wf_customer_intake` is the first executable contract:

```json
{
  "schema_version": "1.0",
  "correlation_id": "coze-demo-001",
  "message": "Please check order CC-1001"
}
```

It returns a Router decision such as:

```json
{
  "schema_version": "1.0",
  "correlation_id": "coze-demo-001",
  "intent": "order_status",
  "order_number": "CC-1001",
  "missing_fields": [],
  "requires_evidence": false,
  "safe_outcome": "allow",
  "audit_id": "9fa3e88c-23f2-4cf7-a13d-08422a1557a4"
}
```

## Documented sub-flows

The following contracts are versioned design interfaces. They are not granted direct data or write access in Phase 4.

| Flow | Required input | Structured output | Boundary rule |
| --- | --- | --- | --- |
| `wf_customer_intake` | `message`, `correlation_id` | Router decision | Executable, signed, stateless |
| `wf_order_context` | owned `order_number`, scoped actor reference | observed facts | Internal read facade only |
| `wf_policy_retrieval` | policy type, region, order time | evidence/applicability | Internal retrieval service only |
| `wf_resolution_plan` | facts and evidence references | 1–3 non-executable plans | No write capability |
| `wf_risk_gate` | plan summary and deterministic signals | `ALLOW`/`REQUIRE_APPROVAL`/`ESCALATE` | Cannot override domain rules |
| `wf_execute_action` | approved domain command reference | dispatch receipt | Domain service only; not externally exposed |
| `wf_ticket_sync` | ticket reference | timeline summary | Domain service only; not externally exposed |
| `wf_customer_reply` | confirmed facts/results | grounded reply | No internal-risk disclosure |
| `wf_quality_review` | redacted trace summary | evaluation summary | Read-only |

Every future exposed sub-flow must first add a dedicated Pydantic request/response schema, HMAC verification, audit event, authorization scope, and regression tests.
