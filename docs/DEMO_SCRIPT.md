# Demo Script

> Phase 5 已提供可运行的 Customer、Supervisor 与 Reliability Metrics 页面；Phase 6 将扩展为完整展示包。

1. 以 Customer 身份进入 chat，发送“订单 CC-1001 为什么还没到？”。
2. 展示系统识别 `order_status`/物流延迟，读取订单与物流事实，检索 delivery-delay 政策，并创建 trace 与工单。
3. 进入 Agent workspace，展示脱敏客户信息、订单/物流卡、政策证据、建议方案和可见的状态迁移（不展示内部风险分）。
4. 发送一条低金额退款请求；展示规则要求审批而非自动退款。
5. 以 Supervisor 身份在 approval queue 批准或拒绝；展示幂等的执行结果和 ticket timeline。
6. 打开 Trace & Audit 页面，说明每个模型/工具/审批/迁移均可追溯但不保存私有推理。
7. 打开 `/metrics`，以 Admin 运行 100 条合成评估；展示 `healthy` SLO、安全阻断、重复动作防止和失败场景指标。

演示前置条件：docker compose 启动成功、mock providers 启用、seed 已加载、四种演示账号可用。
