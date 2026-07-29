# ADR-0004: 幂等、事务 outbox 与审计

**状态：Accepted；日期：2026-07-30**

## 决策

每一个写命令携带 actor、reason code 和 idempotency key。领域服务在一个数据库事务中持久化命令结果、状态事件、审计记录和 outbox event；worker 再投递外部副作用。相同作用域的幂等键返回先前结果。

## 后果

客户端断开或 worker 重试不会重复退款/更新；系统需实现 outbox dispatcher、状态持久化和重放语义。
