# Implementation Status

## 当前状态

**Phase 0 — 完成（2026-07-30）**。仓库此前为空；本阶段仅建立规范和决策，不包含应用、迁移、依赖、容器、种子数据或测试代码。

## 交付物

- 产品、架构、数据、API、安全、评估和演示规范。
- 五项 ADR：职责边界、provider 抽象、状态机、幂等与审计、PII/不可信输入。
- Phase 1–6 路线图、验收标准、假设与风险。

## 推荐 Phase 1 顺序

1. 初始化 Python 3.12/FastAPI 与 Next.js/TypeScript 工程、Makefile、Docker Compose、`.env.example` 和 CI 质量脚本。
2. 建立 PostgreSQL/Redis、SQLAlchemy 模型、Alembic 初始迁移和开发环境 seed/reset 命令。
3. 实现 JWT 登录、RBAC、资源归属授权和统一错误契约。
4. 实现 trace、audit log、workflow run、outbox 与幂等基础设施。
5. 定义 provider ports 和 deterministic mock adapters，并生成合成演示数据。
6. 为上述内容添加单元、集成、迁移、鉴权与种子测试，运行格式化、lint、type check、compose smoke test。

## Phase 0 验证命令

当前没有可执行代码或依赖。文档阶段可执行：

```powershell
git diff --check
Get-ChildItem README.md, docs -Recurse -File
```

Phase 1 起，README 将替换为可执行的 `make format`、`make lint`、`make typecheck`、`make test`、`docker compose up`、seed 和 Playwright 命令。
