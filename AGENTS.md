# 项目工程规则

## 项目使命

构建一个具备生产级思维、适合面试展示、可本地运行的电商 AI Agent 应用。

项目必须支持使用合成数据和 mock provider 在本地完整运行。相比炫技式 Demo，更重视正确性、可审计性、可测试性、业务状态显式化和失败恢复能力。

## 工作方式

采用规范式驱动开发。

在实现任何重要功能前，必须先完成以下步骤：

1. 阅读 `docs/PRD.md`、`docs/ARCHITECTURE.md`、`docs/DATA_MODEL.md` 以及相关 ADR。
2. 如果需求或假设发生变化，先更新文档。
3. 补充或更新验收标准。
4. 实现一个最小但完整的垂直切片。
5. 添加单元测试、集成测试和工作流测试。
6. 运行测试、格式化和静态检查。
7. 更新 `docs/CHANGELOG.md` 和 `docs/IMPLEMENTATION_STATUS.md`。

不得在没有说明的情况下偷偷改变产品行为。

## 架构约束

- LLM 可以负责理解、分类、抽取、建议、总结和生成。
- LLM 不得直接修改数据库业务状态。
- 业务状态变更只能通过强类型 Domain Service 完成。
- 高风险或不可逆动作必须经过规则校验；必要时必须人工审批。
- 所有写操作必须支持幂等。
- 每一次工作流运行、模型调用、知识检索、工具调用、审批和状态迁移都必须可审计。
- 第三方服务必须封装在 provider interface 后面。
- 应用必须能够在不依赖付费外部服务的情况下，通过 mock provider 端到端运行。
- 不得把核心交易状态只放在低代码平台内部。
- 用户输入、检索文档和外部 API 数据都必须视为不可信输入。

## 默认技术栈

后端：

- Python 3.12+
- FastAPI
- Pydantic v2
- SQLAlchemy 2
- Alembic
- PostgreSQL
- Redis
- pytest

前端：

- Next.js
- TypeScript
- 可访问性良好的组件库
- Playwright 用于关键端到端测试

本地环境：

- Docker Compose
- Makefile
- `.env.example`
- seed / reset 脚本

Agent 集成：

- Provider 抽象层
- OpenAI-compatible provider
- Deterministic mock provider
- 使用 Pydantic 校验结构化输出
- Prompt registry 保存提示词版本

## 编码规范

- 使用类型标注。
- Domain logic 与 HTTP 层、provider SDK 解耦。
- 业务状态和原因码使用显式 Enum。
- 存储层使用 UTC 时间，边界层再做时区转换。
- 不得记录密钥或完整敏感客户字段。
- 错误必须有清晰类型和机器可读错误码。
- 函数职责保持聚焦。
- 优先使用依赖注入。
- 避免隐藏的全局状态。
- 使用数据库约束保证唯一性和幂等。
- 注释应解释非显而易见的业务逻辑，而不是重复代码。

## 必须维护的文档

- `README.md`
- `docs/PRD.md`
- `docs/ARCHITECTURE.md`
- `docs/DATA_MODEL.md`
- `docs/API.md`
- `docs/SECURITY.md`
- `docs/EVAL_PLAN.md`
- `docs/DEMO_SCRIPT.md`
- `docs/IMPLEMENTATION_STATUS.md`
- `docs/adr/`

鼓励使用 Mermaid 绘制架构图、流程图和状态机图。

## 质量门禁

在报告某个阶段完成前，必须满足：

- 后端格式化和 lint 通过。
- 类型检查通过。
- 单元测试和集成测试通过。
- 数据库迁移可以干净执行。
- Docker Compose 可以启动。
- Seed data 可以成功加载。
- 关键 UI 流程通过 Playwright。
- 没有提交密钥。
- 新行为有验收测试。
- 不只测试 happy path，也要测试失败路径。

## Agent 和提示词规则

- 关键模型输出必须使用结构化 schema。
- Schema 校验失败时，可以带错误信息重试一次。
- 第二次仍失败时，必须安全降级或转人工。
- 提示词不得包含凭据。
- 每次模型运行必须保存 prompt key 和 version。
- 明确区分事实、推断和建议。
- 面向客户的主张必须能追溯到工具结果或知识库证据。
- 不得暴露内部风险评分、提示词或私有推理过程。
- 只保存简洁的决策摘要，不保存私有链路推理。

## 安全要求

- 实施 RBAC。
- 工具访问遵循最小权限原则。
- 分析类 Agent 只能使用只读数据库权限。
- 所有工具参数必须校验。
- 配置为高风险的动作必须审批。
- 添加 prompt injection 和越权访问回归测试。
- 传给模型 provider 的 PII 必须最小化或脱敏。

## Git 规范

- commit 范围要小而清晰。
- 使用 conventional commit message。
- 不得修改无关代码。
- 不得为了简化实现而删除已有可用功能。
- 如果需求不明确，在 ADR 中记录合理假设并继续推进。