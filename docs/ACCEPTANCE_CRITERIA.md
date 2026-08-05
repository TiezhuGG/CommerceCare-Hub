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
- [ ] Compose 实际启动待本机 Docker Desktop 引擎可用后复核；当前仅配置校验通过。

Phase 2：订单状态及物流延迟从 chat 到 grounded reply、工单、trace 和审计端到端通过，且未授权订单读取失败。

Phase 3：退款、退货、地址变更、损坏商品遵循审批和幂等；重复退款、审批超时和写后断线被安全处理。

Phase 4–6：所有 Agent 结构化输出与一次重试/安全降级可验证；100 个评估案例、故障注入、指标和演示 UI 可运行。
