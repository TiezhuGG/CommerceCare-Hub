# Changelog

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
