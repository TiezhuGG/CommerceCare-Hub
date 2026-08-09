# Changelog

## 2026-08-08

### Added

- Phase 6 interview demo shell with six navigable pages: Customer Chat, Agent Workspace, Supervisor Approvals, Ticket Timeline, Trace & Audit, and Reliability Metrics.
- Owner/RBAC-scoped `GET /api/v1/tickets/{ticket_id}` endpoint with a bounded, auditable ticket-state event timeline and cross-customer denial coverage.
- Locked Playwright dependency, local-Compose customer-to-SLO regression flow, demo accounts/runbook, screenshot guidance, known limitations, and roadmap documents.
- Phase 5 versioned 100-case synthetic evaluation suite, deterministic graders, persistent evaluation reports, critical safety release gate, and redacted SLO metrics.
- Admin evaluation API, Supervisor/Admin metrics API, and local Reliability Metrics page with browser-verified evaluation interaction.
- Reliability coverage for schema regressions, policy-text injection, unreadable context evidence, duplicate action replay, provider timeout, approval expiry, and cross-customer access.
- Alembic migration `c5d9e7a3f1b2` for evaluation runs/results and ADR-0008 for deterministic release gates.
- Phase 4 structured Agent runtime with Pydantic-validated Router, Context, Policy, Resolution Planner, Risk/Compliance, and Reply decisions.
- Active versioned prompt registry, deterministic structured-output mock provider, optional OpenAI-compatible adapter, and audit metadata for provider/model/prompt/retry details.
- Effective scoped policy retrieval with explicit escalation for missing or conflicting evidence, plus injection-safe workflow fallbacks.
- Signed, stateless Coze customer-intake contract and documentation for nine bounded Coze sub-flows.
- Alembic migration `b4f8e2a6c9d1` and regression tests covering validation retry/failure, prompt injection, policy conflicts/missing evidence, and Coze HMAC rejection.

## 2026-08-05

### Added

- Phase 3 after-sales action workflow for refunds, returns, address updates, and damaged-item reports.
- Durable `service_actions` records, approval-to-action linkage, outbox attempt tracking, and Alembic migration `f3a7c1d9e2b4`.
- Supervisor approval queue and customer after-sales UI backed by idempotent APIs.
- Deterministic mock write-provider dispatch, timeout retry/exhaustion behavior, and redacted address-reference fingerprints.
- Regression coverage for approval, replay, provider timeout, customer-order authorization, return eligibility, and expired approvals.

## 2026-07-30

### Added

- CommerceCare Hub Phase 0 specification set.
- Product, architecture, data, API, security, evaluation, demo and acceptance documentation.
- ADRs for workflow boundaries, provider abstraction, state, idempotency/audit and PII/untrusted input.
- Phase 1 backend/frontend skeleton, Compose, Makefile, environment template and lockfiles.
- Initial Alembic schema, synthetic seed/reset scripts, JWT/RBAC, audit/idempotency/outbox foundation and deterministic providers.
- Backend and frontend validation coverage.
- Phase 2 customer conversation/message APIs, deterministic order-status and delivery-delay workflow, ticket state transitions, trace/evidence views, and minimal Customer/Operator UI.
- Reproducible Docker image builds through `.dockerignore` and lockfile-based `npm ci`; Compose runtime smoke test.
