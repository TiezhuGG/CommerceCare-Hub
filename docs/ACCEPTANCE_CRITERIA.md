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

### Phase 3

- [x] Customer 只能为自己的订单和会话创建 `refund`、`return`、`address_update` 或 `damaged_item` 动作；每个请求含原因码和幂等键。
- [x] 退款与地址变更必须创建可过期的审批请求；退货和损坏商品仅在确定性政策允许时自动排队执行。
- [x] 所有动作经 Domain Service 写入 action record、ticket transition、audit log 和 outbox event；HTTP handler、Agent 和 provider 不得绕过该服务写业务状态。
- [x] Supervisor 只能审批待处理且未过期的请求；拒绝和超时应安全终止/升级，不得执行 provider 写入。
- [x] dispatch 仅执行一次成功的 provider 写入；相同动作/幂等键重放不产生第二次副作用，超时可重试并在耗尽后失败。
- [x] 退款金额、订单归属、订单状态与动作类型均由确定性规则校验；地址仅保存引用 fingerprint，不保存明文。
- [x] 正常、重复退款、provider timeout、审批超时、跨客户越权和写后重放均有回归测试与 Compose smoke test。

### Phase 4

- [x] Router、Context、Policy、Resolution Planner、Risk/Compliance 和 Reply Agent 均通过结构化 provider interface 产出 Pydantic 校验结果；本地 deterministic mock 可端到端运行。
- [x] 每次 Agent 调用记录 agent 名称、provider/model、prompt key/version、尝试次数、最小化输入/输出摘要、延迟与 token usage；不保存私有推理或完整 PII。
- [x] schema 校验失败携带验证摘要重试一次；第二次失败或风险判定为 `ESCALATE` 时，工作流安全升级且绝不触发写 provider。
- [x] Policy retrieval 只返回当前生效且 scope 匹配的版本化文档；缺失或冲突证据必须显式升级。
- [x] Prompt registry 只解析 active 的版本化 prompt；缺失 prompt 或 provider 配置时安全降级到 deterministic mock 或人工升级。
- [x] Coze intake 使用 HMAC 签名和版本化 schema；其 HTTP 边界无状态、无数据库业务写入，且每次调用有脱敏审计记录。
- [x] 覆盖正常结构化流程、一次重试成功、两次 schema 失败、客户/政策 prompt injection、冲突策略和签名拒绝的单元/集成/工作流测试。

### Phase 5

- [x] Seed 幂等加载 100 条版本化合成评估案例，类别严格为 20 售前、20 订单、20 退款/退货、20 物流、10 注入、10 信息缺失/策略冲突。
- [x] Deterministic grader 覆盖意图、字段、工具/参数、策略证据、未授权阻断、完成度、grounded reply 与重复动作防止，并记录可读 failure code。
- [x] 每次评估持久化 run/result、provider/model/judge 版本与最小化摘要；评估不产生业务 action、approval、outbox 或 provider 写副作用。
- [x] critical 安全项必须 100%；低于 90% 的非 critical 质量项为 `attention`，critical failure 为 `blocked`。
- [x] Admin 可幂等运行评估；Supervisor/Admin 可读取脱敏 metrics dashboard 与 SLO 状态。
- [x] 覆盖重复退款、物流超时、策略冲突、写后客户端断开、审批超时、不可读证据、客户/策略注入与跨客户访问的故障/安全回归。
- [x] 指标页可在本地 demo 加载评估与可靠性摘要；关键 API 与 UI 流程具有自动化验证。

### Phase 6

- [x] 六个可导航页面覆盖 Customer Chat、Agent Workspace、Supervisor Approvals、Ticket Timeline、Trace & Audit 和 Reliability Metrics；展示数据始终通过受控 API 获取。
- [x] Ticket Timeline、Trace 与 Audit 继续执行服务端 RBAC/归属校验；页面不显示完整敏感字段、提示词或私有推理。
- [x] README、演示账号、架构图、最终 demo script、截图占位、已知限制和 roadmap 均可供面试演示使用。
- [x] Playwright 作为锁定开发依赖，关键 UI 流程可在本地 Compose 环境重复执行。
- [x] 在 reset/seed 后完成一次完整彩排：客户物流咨询、主管审批、timeline/trace、100 条评估和 dashboard SLO 均可展示。
