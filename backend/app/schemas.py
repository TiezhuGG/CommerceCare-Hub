import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import (
    ActionStatus,
    ActionType,
    ApprovalDecision,
    ApprovalStatus,
    Role,
    TicketState,
    WorkflowStatus,
)


class LoginRequest(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(min_length=12, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUserResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: Role
    customer_id: uuid.UUID | None

    model_config = ConfigDict(from_attributes=True)


class SeedResponse(BaseModel):
    status: str
    customers: int
    products: int
    orders: int
    shipments: int


class OrderResponse(BaseModel):
    order_number: str
    status: str
    ordered_at: datetime
    shipment_status: str | None
    tracking_number: str | None


class AuditLogResponse(BaseModel):
    event_type: str
    resource_type: str
    resource_id: str
    occurred_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):
    code: str
    message: str
    trace_id: str
    details: dict[str, object] | None = None


class ConversationResponse(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SendMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2_000)
    client_message_id: str = Field(min_length=1, max_length=64)


class SendMessageResponse(BaseModel):
    conversation_id: uuid.UUID
    ticket_id: uuid.UUID
    trace_id: uuid.UUID
    workflow_status: WorkflowStatus
    customer_reply: str


class MessageResponse(BaseModel):
    id: uuid.UUID
    sender_type: str
    body_redacted: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationDetailResponse(ConversationResponse):
    messages: list[MessageResponse]
    ticket_state: TicketState | None
    trace_id: uuid.UUID | None


class WorkflowTraceResponse(BaseModel):
    trace_id: uuid.UUID
    status: WorkflowStatus
    ticket_id: uuid.UUID | None
    final_result_code: str | None
    agents: list[str]
    tools: list[str]
    evidence: list[str]
    state_transitions: list[str]


class TicketSummaryResponse(BaseModel):
    id: uuid.UUID
    state: TicketState
    reason_code: str
    trace_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActionRequest(BaseModel):
    action_type: ActionType
    order_number: str = Field(pattern=r"^CC-\d{4,}$", max_length=64)
    reason_code: str = Field(pattern=r"^[A-Z0-9_]{3,64}$")
    amount_minor: int | None = Field(default=None, gt=0)
    address_reference: str | None = Field(default=None, min_length=3, max_length=128)
    simulate_timeout: bool = False


class ActionResponse(BaseModel):
    action_id: uuid.UUID
    ticket_id: uuid.UUID
    trace_id: uuid.UUID
    status: ActionStatus
    approval_id: uuid.UUID | None


class ApprovalDecisionRequest(BaseModel):
    decision: ApprovalDecision
    reason_code: str = Field(pattern=r"^[A-Z0-9_]{3,64}$")
    comment: str | None = Field(default=None, max_length=500)


class ApprovalResponse(BaseModel):
    id: uuid.UUID
    action_id: uuid.UUID | None
    status: ApprovalStatus
    action_status: ActionStatus


class DispatchResponse(BaseModel):
    dispatched: int
    retried: int
    failed: int
