# Implementation Status

## Current status

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
