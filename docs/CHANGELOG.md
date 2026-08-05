# Changelog

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
