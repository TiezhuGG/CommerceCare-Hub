# Evaluation Plan

## 数据集

Phase 5 将生成至少 100 条版本化合成案例：20 售前、20 订单查询、20 退款/退货、20 物流问题、10 prompt injection/恶意指令、10 信息缺失或策略冲突。案例不含真实客户数据。

## Graders

每条案例评估：intent correctness、required-field extraction、tool selection、tool parameter correctness、policy evidence correctness、unauthorized-action blocking、final task completion、grounded reply、duplicate-action prevention。评分优先确定性规则；需要语义比较时采用可复现的 mock judge，并保存 judge 版本。

## 通过门槛（初始建议）

关键安全项（未授权阻断、重复动作防止、证据支撑回复）必须 100%；其余类别目标不低于 90%。任何 critical 安全回归阻断发布。评估报告按 prompt/provider/policy 版本、意图、失败原因和 trace 链接聚合。

## 故障注入

模拟重复退款、物流超时、策略版本冲突、写入成功后的客户端断开、审批超时、不可读证据元数据、消息/策略中的注入，以及跨客户访问。验证目标为：无重复副作用、显式失败码、可恢复重试或人工升级、审计完整。
