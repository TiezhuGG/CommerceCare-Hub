# Acceptance Criteria

## Phase 0

- [x] 产品范围、非目标、角色、审批规则和关键流程已记录。
- [x] Agent、领域服务、provider、Coze 和审计边界已明确。
- [x] 所需数据表、关键约束、状态机与幂等策略已定义。
- [x] API、RBAC、PII、提示词注入和故障安全策略已定义。
- [x] 评估集规模、评分维度、故障模式、演示路径和阶段计划已定义。

## 后续可验收切片

### Phase 1

- [x] FastAPI、Next.js、Docker Compose、Makefile、`.env.example` 与锁文件已建立。
- [x] Alembic 初始迁移可在 SQLite 临时数据库升级、降级、再次升级，并可成功加载 seed。
- [x] 30 customers、100 products/SKUs、100 orders、100 shipments、当前/过期策略和四种演示角色可幂等生成。
- [x] JWT、PBKDF2 密码散列、RBAC、资源归属检查、统一错误/trace 契约和脱敏审计基础可用。
- [x] idempotency records、outbox events、完整 provider ports 与 deterministic mock adapters 已定义。
- [x] 后端 lint、类型检查、7 个回归测试，及前端 TypeScript/production build 均通过。
- [x] Compose 已实际构建并启动，PostgreSQL/Redis 健康，API/Web HTTP smoke test 与合成 seed 通过。

### Phase 2

- [x] Customer 可创建自己的会话并以幂等 `client_message_id` 发送消息；跨客户会话读取和发送必须被拒绝。
- [x] Deterministic Router 必须仅从不可信消息中抽取订单号，并为 `order_status` 或 `delivery_delay` 输出结构化结果；未识别订单号安全转入 `NEED_MORE_INFO`。
- [x] Context 层只能通过 read-only mock provider 读取订单与物流，并为每个事实记录来源和观测时间。
- [x] delivery-delay 场景必须检索当前有效的版本化政策证据，生成不含内部评分的 grounded customer reply。
- [x] Ticket 状态只能经 allow-list Domain Service 从 `NEW` 转换，所有转换、agent run、tool call、evidence 和最终结果均可按 trace 查询。
- [x] API integration、workflow、越权、缺失订单号、物流延迟和状态迁移失败路径都有回归测试。
- [ ] 最小 chat/operator UI 的浏览器自动化待可用浏览器运行时执行；Compose runtime smoke test 已通过。

Phase 3：退款、退货、地址变更、损坏商品遵循审批和幂等；重复退款、审批超时和写后断线被安全处理。

Phase 4–6：所有 Agent 结构化输出与一次重试/安全降级可验证；100 个评估案例、故障注入、指标和演示 UI 可运行。
