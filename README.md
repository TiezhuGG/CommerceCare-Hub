# CommerceCare Hub

CommerceCare Hub 是一个可本地运行的电商服务 AI Agent 系统，覆盖售前咨询、订单与物流查询，以及受控的售后处置。它面向面试演示，但以生产级的正确性、可审计性、可恢复性与安全边界为优先。

当前仓库已完成 **Phase 6（演示包装与可视化材料）**：六个可导航页面将客户咨询、运营工单、主管审批、状态时间线、Trace/Audit 和可靠性指标串成一套可本地复跑的面试演示。所有展示数据仍经由已授权的 API 获取；模型、提示词、完整敏感字段和私有推理均不在 UI 暴露。

## 核心原则

- 模型只做理解、抽取、建议和生成；只有领域服务可修改业务状态。
- 高风险、不可逆或低置信度动作先经过确定性规则，并在需要时进入人工审批。
- 每个工作流、模型、检索、工具、审批和状态迁移都可按 trace ID 审计。
- 所有外部能力由 provider 接口隔离；deterministic mock provider 支持本地端到端演示。
- 所有写操作具备幂等键、授权校验、原因码和审计记录。

## 文档入口

- [产品需求](docs/PRD.md)
- [系统架构](docs/ARCHITECTURE.md)
- [数据模型](docs/DATA_MODEL.md)
- [接口设计](docs/API.md)
- [安全设计](docs/SECURITY.md)
- [验收标准](docs/ACCEPTANCE_CRITERIA.md)
- [实施状态与计划](docs/IMPLEMENTATION_STATUS.md)
- [分阶段实施计划](docs/IMPLEMENTATION_PLAN.md)
- [架构决策记录](docs/adr/README.md)

## 阶段

1. Phase 0：规格设计（完成）
2. Phase 1：基础设施、认证、审计、迁移与 mock provider（实现完成）
3. Phase 2：订单状态与物流延迟的端到端垂直切片（实现完成）
4. Phase 3：售后动作、审批、幂等与重试（实现完成）
5. Phase 4：结构化 Agent、知识库、提示词注册表与 Coze 边界（实现完成）
6. Phase 5：评估、故障注入、安全回归与指标（实现完成）
7. Phase 6：演示包装与可视化材料（实现完成）

详见 [实施状态](docs/IMPLEMENTATION_STATUS.md)。

## 本地运行

前置条件：Python 3.12+ 与 `uv`、Node.js 24+、Docker Desktop（用于完整 Compose 环境）。从 `.env.example` 创建仅限本地的 `.env` 后执行：

```powershell
Copy-Item .env.example .env
uv sync --all-groups
uv run alembic upgrade head
uv run python scripts/seed.py
uv run uvicorn app.main:app --app-dir backend --reload
```

API 文档位于 `http://localhost:8000/docs`。合成演示账号是 `admin@demo.local`、`supervisor@demo.local`、`operator@demo.local`、`customer1@demo.local`；密码使用 `.env` 中的 `COMMERCECARE_DEMO_PASSWORD`。这些账号仅能用于本地合成数据。

启动后，Admin 可在 `http://localhost:3000/metrics` 运行合成评估并查看 SLO。评估仅使用已 seed 的测试用例和 deterministic mock；不会创建售后动作或调用写 provider。

面试演示入口、账户与边界说明见 [演示脚本](docs/DEMO_SCRIPT.md)、[演示账号](docs/DEMO_ACCOUNTS.md)、[已知限制](docs/KNOWN_LIMITATIONS.md)、[后续路线图](docs/ROADMAP.md) 和 [截图目录](docs/assets/screenshots/README.md)。

完整容器启动：

```powershell
docker compose up --build
```

## 验证命令

```powershell
uv run ruff format --check backend/app backend/tests
uv run ruff check backend/app backend/tests
uv run mypy backend/app
uv run pytest
npm --prefix frontend run check
npm --prefix frontend run build
npm --prefix frontend run test:e2e
docker compose --env-file .env.example config
```
