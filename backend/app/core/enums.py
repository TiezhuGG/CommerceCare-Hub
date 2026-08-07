from enum import StrEnum


class Role(StrEnum):
    CUSTOMER = "customer"
    AGENT_OPERATOR = "agent_operator"
    SUPERVISOR = "supervisor"
    ADMIN = "admin"


class TicketState(StrEnum):
    NEW = "new"
    CLASSIFIED = "classified"
    NEED_MORE_INFO = "need_more_info"
    CONTEXT_READY = "context_ready"
    SOLUTION_PROPOSED = "solution_proposed"
    PENDING_APPROVAL = "pending_approval"
    EXECUTING = "executing"
    WAITING_CUSTOMER = "waiting_customer"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ESCALATED = "escalated"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class Intent(StrEnum):
    ORDER_STATUS = "order_status"
    DELIVERY_DELAY = "delivery_delay"
    UNKNOWN = "unknown"


class ActionType(StrEnum):
    REFUND = "refund"
    RETURN = "return"
    ADDRESS_UPDATE = "address_update"
    DAMAGED_ITEM = "damaged_item"


class ActionStatus(StrEnum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    QUEUED = "queued"
    EXECUTING = "executing"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"


class ApprovalDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"


class RiskDecision(StrEnum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    ESCALATE = "escalate"
