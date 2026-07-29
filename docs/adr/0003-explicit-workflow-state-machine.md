# ADR-0003: 显式工作流状态机

**状态：Accepted；日期：2026-07-30**

## 决策

工单工作流采用 `NEW`、`CLASSIFIED`、`NEED_MORE_INFO`、`CONTEXT_READY`、`SOLUTION_PROPOSED`、`PENDING_APPROVAL`、`EXECUTING`、`WAITING_CUSTOMER`、`RESOLVED`、`ESCALATED`、`FAILED`、`CANCELLED` 状态。转换使用 allow-list，并将 from/to 状态写入 ticket event 和 audit log。

## 后果

流程需要更多显式建模，但非法跃迁能被拒绝、重试能恢复、UI 和审计可一致展示。
