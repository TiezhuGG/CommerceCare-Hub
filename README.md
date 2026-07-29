# CommerceCare Hub

CommerceCare Hub 是一个可本地运行的电商服务 AI Agent 系统，覆盖售前咨询、订单与物流查询，以及受控的售后处置。它面向面试演示，但以生产级的正确性、可审计性、可恢复性与安全边界为优先。

当前仓库处于 **Phase 0（规格设计）**：尚未提供可执行应用。产品范围、架构、数据模型、安全策略与后续实施顺序均已固化在 `docs/`。

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
2. Phase 1：基础设施、认证、审计、迁移与 mock provider
3. Phase 2：订单状态与物流延迟的端到端垂直切片
4. Phase 3：售后动作、审批、幂等与重试
5. Phase 4：结构化 Agent、知识库、提示词注册表与 Coze 边界
6. Phase 5：评估、故障注入、安全回归与指标
7. Phase 6：演示包装与可视化材料

详见 [实施状态](docs/IMPLEMENTATION_STATUS.md)。
