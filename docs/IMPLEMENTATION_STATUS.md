# Implementation Status

## Current status

**Phase 6 complete (2026-08-08).** The demo has six navigable, role-aware pages backed exclusively by controlled APIs. A scoped ticket-detail endpoint exposes state events without bypassing RBAC, and a locked Playwright suite verifies a customer consultation through the local reliability dashboard.

### Phase 6 delivered

- Customer Chat, Agent Workspace, Supervisor Approvals, Ticket Timeline, Trace & Audit, and Reliability Metrics are reachable from one responsive navigation shell.
- `GET /api/v1/tickets/{ticket_id}` returns a bounded ticket event timeline after the existing server-side conversation ownership/RBAC check. It never returns message bodies, prompts, risk scores, or private reasoning.
- The demo package includes role accounts, a runbook, screenshot capture guidance, known limitations, and a roadmap for interview handoff.
- `@playwright/test` is locked in the frontend package. `npm --prefix frontend run test:e2e` passed against the running Compose environment, including customer workflow execution and 100-case `healthy` evaluation verification.
- Validation completed: Ruff, strict mypy, 27 backend tests, frontend typecheck/production build, Compose rebuild, Alembic upgrade to `c5d9e7a3f1b2`, and the Playwright smoke flow.

**Phase 5 complete (2026-08-08).** The local demo can run a persisted, deterministic 100-case evaluation suite without business side effects. Critical safety regressions block the SLO, while a minimal staff dashboard exposes only bounded reliability aggregates.

### Phase 5 delivered

- Synthetic seed data now includes exactly 100 active `2026.08` evaluation cases across the documented six categories.
- `EvaluationService` invokes schema-bound analysis only, saves run/result reports and redacted audit records, and has no action, approval, outbox, customer-message, or write-provider capability.
- `deterministic-v1` grades intent, fields, tool/parameter plans, policy evidence, authorization blocking, completion, grounded response, and duplicate-action protection. Critical failures mark a run `blocked`; non-critical quality below 90% marks `attention`.
- `POST /api/v1/admin/evaluations/run` is Admin-only and idempotent; `GET /api/v1/metrics/dashboard` is restricted to Supervisor/Admin. The `/metrics` page runs and displays the suite locally.
- Validation completed: Ruff, strict mypy, 34 backend tests, frontend typecheck/build, SQLite migration upgrade/downgrade/upgrade, Compose reset/seed plus 100-case API smoke test, and browser interaction that ran the dashboard suite to `healthy`.

### Phase 5 gap closed in Phase 6

- The standalone Playwright package/test suite is now committed and is run against local Compose as part of the Phase 6 rehearsal.

**Phase 4 complete (2026-08-08).** CommerceCare Hub now runs six schema-bound, read-only AI agents behind a provider abstraction. It records minimized execution metadata, retries one invalid model response, safely escalates unsafe or unverifiable cases, and exposes a signed, stateless Coze intake boundary without permitting Coze business-state writes.

### Phase 4 delivered

- Router, Context, Policy, Resolution Planner, Risk/Compliance, and Reply agents use versioned prompts and Pydantic output schemas; the deterministic mock is the local default.
- `b4f8e2a6c9d1` adds provider, model, and attempt-count metadata to auditable `agent_runs`.
- Effective policy retrieval filters by time and scope. Missing or conflicting evidence, schema failure after one retry, and prompt-injection signals safely escalate without write-provider access.
- `POST /api/v1/coze/v1/wf_customer_intake` verifies HMAC-SHA256, returns only a structured intake decision, performs no business-state write, and creates a redacted audit record.
- Validation completed: Ruff, strict mypy, 26 backend tests, SQLite migration upgrade/downgrade/upgrade, Compose rebuild, demo reset/seed, customer delivery-delay workflow smoke test, and signed Coze intake smoke test.

### Remaining known gap

- Browser-driven Playwright coverage remains pending because the local browser automation runtime previously could not initialize its kernel assets. API, Docker, backend regression, and frontend production-build validation are complete.

**Phase 3 — complete (2026-08-05).** The local application now supports customer-initiated refunds, returns, address updates, and damaged-item reports. Refunds and address updates wait for a Supervisor decision; low-risk actions dispatch through the durable outbox to the deterministic mock provider. Every mutation is idempotent and auditable.

### Phase 3 delivered

- `AfterSalesActionService` owns policy validation, ticket transitions, workflow records, approval creation, audit records, and outbox enqueueing.
- Durable `service_actions` and approval links are migrated with `f3a7c1d9e2b4`; outbox events retain attempt count and failure code.
- The dispatcher retries provider timeouts up to three attempts, never repeats a successful write, and marks the ticket/workflow failed when retries are exhausted.
- Customer UI can submit the four action types; Supervisor UI can load and decide pending approvals.
- Backend regression suite: 21 passed. Frontend TypeScript check and production build passed. SQLite migration upgrade/downgrade/upgrade and Docker Compose HTTP smoke test passed.

### Remaining known gap

- Browser-driven Playwright coverage remains pending because the local browser automation runtime previously could not initialize its kernel assets. API, Docker, and frontend production-build validation are complete.

## 当前状态

**Phase 2 — 实现完成（2026-08-05）**。Docker Compose 已实际构建并启动 PostgreSQL、Redis、API 与 Web；真实 HTTP smoke test 已验证 seed、认证、Customer conversation、delivery-delay 政策证据、trace 和 Web 页面。

## 交付物

- Python 3.12+ FastAPI backend、Next.js/TypeScript frontend、Docker Compose、Makefile、`.env.example`、`uv.lock` 与前端 lockfile。
- SQLAlchemy 2 模型、Alembic 初始迁移、PostgreSQL/Redis Compose 定义与 30/100/100/100 合成 seed/reset 工具。
- JWT/PBKDF2 认证、RBAC、订单归属授权、trace ID、统一错误契约、audit log、idempotency record 和 outbox 基础。
- 只读/写入 provider ports 与 deterministic mock adapters；7 个后端回归测试和前端编译检查。
- Phase 2 Customer conversation/message APIs、deterministic Router、只读订单/物流/政策上下文、强类型 ticket state service、grounded reply、workflow trace 和最小 Customer chat/Agent workspace UI。
- Docker build context isolation and lockfile-based dependency installation for reproducible API/Web images.

## 已执行的验证

- `uv run ruff format --check backend/app backend/tests`
- `uv run ruff check backend/app backend/tests`
- `uv run mypy backend/app`
- `uv run pytest`（13 passed）
- Alembic SQLite 临时库 `upgrade → seed → downgrade → upgrade`（通过）
- `npm --prefix frontend run check` 与 `npm --prefix frontend run build`（通过）
- `npm audit --omit=dev --audit-level=high`（0 vulnerabilities）
- `docker compose --env-file .env.example config`（通过）
- Phase 2 workflow、越权、缺失订单号、重复 client message ID 与非法状态迁移回归测试（通过）
- Phase 2 前端 Customer chat / Agent workspace TypeScript 与 production build（通过）

`docker compose --env-file .env.example up --build --detach`（通过）。容器内 seed 后，`/healthz`、Customer JWT、conversation/message、delivery-delay policy evidence、workflow trace 与 `http://localhost:3000` 均已 HTTP smoke-tested。浏览器自动化仍待本地浏览器运行时可用后补充。

## 推荐 Phase 3 顺序

1. 先为退款、退货、地址更新和错漏损件更新 policy、command schema、审批规则和失败验收测试。
2. 实现带 actor、reason code、idempotency key、授权和 audit 的 Domain Service 写命令。
3. 接入 approval queue、approval timeout、outbox dispatcher 和 provider retry/replay。
4. 扩展 Customer/Operator UI，并完成重复退款、写后断连和审批超时端到端测试。

完整运行与验证命令见 [README](../README.md)。
