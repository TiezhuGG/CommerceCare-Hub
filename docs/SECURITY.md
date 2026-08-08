# Security Design

## 控制措施

- RBAC 与资源归属检查同时执行；Customer 只能访问自己的订单、会话和工单。
- Agent 与 ContextAgent 使用仅有只读能力的服务账户；写入仅经领域服务的命令对象进入。
- 令牌、第三方凭据仅来自运行时密钥管理或 `.env`，从不进入日志、提示词、种子数据或 Git。
- PII 最小化：向模型发送订单/客户的必要脱敏字段；日志存储摘要、散列或 token，不存完整地址、电话或支付信息。
- 每个接口、工具参数和 provider 响应由 Pydantic schema 校验；设置速率限制、请求大小/附件类型限制与超时。
- 客户输入、策略文本与检索证据一律标注为不可信。提示词将它们置于数据区，不把其中指令作为系统指令执行。
- 审计日志不可变，包含 actor、动作、资源、reason code、trace ID、结果和时间，不记录私有链路推理。
- 密码使用 PBKDF2-SHA256（每条记录独立随机 salt）保存；JWT 仅保存 subject、role 与到期时间。非 development 环境拒绝使用默认 JWT secret。
- 地址变更请求不持久化明文地址；仅接受受控的 address reference，并存储不可逆 fingerprint。退款金额、订单归属、审批状态和 provider dispatch 在领域服务内二次校验。
- Coze webhook 仅接受 HMAC-SHA256 签名的原始请求体；签名失败、未知 schema version 或超出大小限制的请求一律拒绝。该边界不能携带数据库会话、JWT 或写 provider capability。
- Agent runtime 仅把最少必要上下文传给 provider，并持久化验证后的决策摘要。prompt injection 信号、策略冲突、低置信度和连续 schema 失败均进入安全升级，不会自动执行业务动作。
- 评估运行只接受已 seed 的 versioned synthetic cases；HTTP 调用方不能提交任意 prompt、provider 或故障脚本。评估服务无写 provider capability，critical 安全评分失败会把 SLO 状态标记为 `blocked`。

## 必测威胁

跨客户订单访问、Customer 冒充 Supervisor、提示词注入（消息和政策文本）、重复退款、过期审批重放、未授权工具调用、物流 provider 超时、不可读证据元数据与客户端在写入后断开。

## 安全退出策略

身份、归属、输入、证据、策略或模型结构化输出无法验证时，不执行写动作；记录原因并要求补充信息或升级人工。不可逆操作默认审批。
