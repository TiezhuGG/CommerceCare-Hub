# ADR-0002: Provider 接口与 deterministic mock

**状态：Accepted；日期：2026-07-30**

## 决策

订单、库存、物流、退款、退货、消息与承运商能力使用应用定义的 port；生产 SDK 位于 adapter，测试和演示使用 deterministic mock adapter。port 输入输出均为 Pydantic DTO，不泄漏 SDK 类型。

## 后果

本地环境无需付费服务，并能以合同测试验证 adapter；代价是维护 adapter 映射与能力差异。
