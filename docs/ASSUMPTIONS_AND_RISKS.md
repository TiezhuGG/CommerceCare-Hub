# Assumptions and Unresolved Risks

## Assumptions

- 初始市场使用 CNY，金额按分存储；多币种将在 provider/策略契约中预留字段。
- 订单和承运商外部系统可提供稳定外部 ID；本地演示仅使用 deterministic mock adapters。
- 默认策略由 Admin 发布，政策适用性按生效窗口与范围确定。
- 客户认证可将会话与 customer record 可靠绑定；匿名模式不在 MVP。

## 未解决风险

| 风险 | 影响 | Phase 1/后续缓解 |
| --- | --- | --- |
| 真实电商平台 API 的能力、限流与撤销语义未知 | 写动作契约可能变化 | 用 ports 隔离；先以 mock 合同测试固化 |
| 法律、消费者保护与各平台政策尚未确认 | 自动处置范围不确定 | 默认审批；Phase 3 前完成法务/业务规则审查 |
| PII 保留期限与跨境要求未知 | 数据治理设计可能调整 | Phase 1 定义数据分类、保留期和删除流程 |
| 退款“不可逆”的实际 provider 语义未定 | 审批与补偿流程不同 | provider capability schema + ADR 补充 |
| Coze 的鉴权、重试和可观测性契约未知 | 集成风险 | Phase 4 以签名、schema 版本和幂等边界验证 |
| LLM 成本、延迟和可用性目标未定 | 体验与降级策略不完整 | Phase 4 定义 SLO、预算与 mock/offline fallback |
