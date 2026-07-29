# Implementation Plan

## Phase 1 — 基础设施

**目标：** 在无付费外部依赖的环境中可靠启动服务，并使所有后续垂直切片拥有数据库、认证、审计、provider 与测试基础。

| 工作项 | 产出 | 完成定义 |
| --- | --- | --- |
| 工程骨架 | backend、frontend、compose、Makefile、env example | 新环境可按 README 启动 |
| 持久化 | SQLAlchemy、Alembic、PostgreSQL、Redis | 初始迁移可干净升级/降级 |
| 安全 | JWT、RBAC、资源归属、错误处理 | 跨客户访问与越权测试失败且可审计 |
| 可观测性 | trace、audit、workflow run、outbox、幂等 | 每次写入和运行可按 trace 查询 |
| 适配器 | ports、mock adapters、seed/reset | 无外部服务完成 30/100/100/100 合成数据加载 |
| 质量门禁 | ruff、mypy/pyright、pytest、前端 check | CI 与本地命令均通过 |

## Phase 2 — 首个垂直切片

按以下顺序交付：会话/消息 API → Router schema/mock → 订单和物流只读工具 → ticket state service → delivery policy fixture → grounded reply → Agent workspace 最小 UI → trace/audit UI → 单元、集成、workflow 和 Playwright 测试。只覆盖 `order_status` 和 `delivery-delay`，不提前实现退款。

## Phase 3 — 受控售后动作

依次实现退款、退货、地址变更、损坏/错漏件，随后加入审批队列、幂等重放、outbox retry 与失败场景。每增加一个动作，先更新策略/命令 schema/验收测试，再接入 UI。

## Phase 4 — Agent 与知识库

实现结构化输出 provider、prompt registry、政策检索、五类 Agent 和 Coze HTTP 边界。每个 Agent 都必须有 mock 行为、schema 失败重试一次和安全降级测试。

## Phase 5 — 评估与可靠性

生成 100 条评估案例和 graders，加入故障注入、注入防护、指标聚合、告警/SLO 文档。critical 安全项任何回归均阻断发布。

## Phase 6 — 展示包

完善六个 UI 页面、演示账号、截图占位、最终 demo script、已知限制和 roadmap；在干净环境中完整彩排并记录结果。
