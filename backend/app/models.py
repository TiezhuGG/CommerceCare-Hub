import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.enums import (
    ActionStatus,
    ActionType,
    ApprovalStatus,
    Role,
    TicketState,
    WorkflowStatus,
)


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(primary_key=True, default=uuid.uuid4)


def created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[Role] = mapped_column(Enum(Role, native_enum=False))
    customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = created_at()


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = uuid_pk()
    external_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    tier: Mapped[str] = mapped_column(String(32), default="standard")
    pii_token: Mapped[str] = mapped_column(String(128), unique=True)
    created_at: Mapped[datetime] = created_at()


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = uuid_pk()
    external_id: Mapped[str] = mapped_column(String(64), unique=True)
    title: Mapped[str] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = created_at()


class Sku(Base):
    __tablename__ = "skus"

    id: Mapped[uuid.UUID] = uuid_pk()
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"))
    sku_code: Mapped[str] = mapped_column(String(64), unique=True)
    price_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="CNY")
    created_at: Mapped[datetime] = created_at()


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = uuid_pk()
    order_number: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    status: Mapped[str] = mapped_column(String(32))
    ordered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = created_at()


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = uuid_pk()
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"))
    sku_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("skus.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price_minor: Mapped[int] = mapped_column(Integer)


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[uuid.UUID] = uuid_pk()
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), index=True)
    tracking_number: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(32))
    eta_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = uuid_pk()
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="open")
    assigned_actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = created_at()


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (UniqueConstraint("conversation_id", "client_message_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id"), index=True)
    sender_type: Mapped[str] = mapped_column(String(32))
    client_message_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    body_redacted: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at()


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = uuid_pk()
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id"), index=True)
    state: Mapped[TicketState] = mapped_column(
        Enum(TicketState, native_enum=False), default=TicketState.NEW
    )
    reason_code: Mapped[str] = mapped_column(String(64))
    trace_id: Mapped[uuid.UUID] = mapped_column(unique=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = created_at()


class TicketEvent(Base):
    __tablename__ = "ticket_events"

    id: Mapped[uuid.UUID] = uuid_pk()
    ticket_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tickets.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(64))
    from_state: Mapped[TicketState | None] = mapped_column(Enum(TicketState, native_enum=False))
    to_state: Mapped[TicketState | None] = mapped_column(Enum(TicketState, native_enum=False))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = created_at()


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[uuid.UUID] = uuid_pk()
    trace_id: Mapped[uuid.UUID] = mapped_column(unique=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tickets.id"), nullable=True)
    status: Mapped[WorkflowStatus] = mapped_column(Enum(WorkflowStatus, native_enum=False))
    final_result_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = created_at()


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = uuid_pk()
    workflow_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflow_runs.id"))
    agent_name: Mapped[str] = mapped_column(String(64))
    prompt_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    input_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    output_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_usage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = created_at()


class RetrievalEvidence(Base):
    __tablename__ = "retrieval_evidence"

    id: Mapped[uuid.UUID] = uuid_pk()
    workflow_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflow_runs.id"))
    document_id: Mapped[str] = mapped_column(String(64))
    document_version: Mapped[str] = mapped_column(String(32))
    matched_section: Mapped[str] = mapped_column(String(128))
    relevance_score: Mapped[int] = mapped_column(Integer)
    observed_at: Mapped[datetime] = created_at()


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id: Mapped[uuid.UUID] = uuid_pk()
    workflow_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workflow_runs.id"), nullable=True
    )
    tool_name: Mapped[str] = mapped_column(String(64))
    request_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = created_at()


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[uuid.UUID] = uuid_pk()
    ticket_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tickets.id"))
    action_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("service_actions.id"), unique=True
    )
    action_type: Mapped[str] = mapped_column(String(64))
    status: Mapped[ApprovalStatus] = mapped_column(Enum(ApprovalStatus, native_enum=False))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class ServiceAction(Base):
    __tablename__ = "service_actions"
    __table_args__ = (UniqueConstraint("action_type", "order_id", "idempotency_key"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    ticket_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tickets.id"), unique=True)
    workflow_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflow_runs.id"), unique=True)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), index=True)
    requested_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    action_type: Mapped[ActionType] = mapped_column(Enum(ActionType, native_enum=False))
    status: Mapped[ActionStatus] = mapped_column(Enum(ActionStatus, native_enum=False))
    reason_code: Mapped[str] = mapped_column(String(64))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    payload_redacted: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    external_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = created_at()


class PolicyDocument(Base):
    __tablename__ = "policy_documents"
    __table_args__ = (UniqueConstraint("document_key", "version"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    document_key: Mapped[str] = mapped_column(String(64))
    version: Mapped[str] = mapped_column(String(32))
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scope: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    body: Mapped[str] = mapped_column(Text)


class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    __table_args__ = (UniqueConstraint("prompt_key", "version"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    prompt_key: Mapped[str] = mapped_column(String(64))
    version: Mapped[str] = mapped_column(String(32))
    template: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=False)


class EvalCase(Base):
    __tablename__ = "eval_cases"

    id: Mapped[uuid.UUID] = uuid_pk()
    category: Mapped[str] = mapped_column(String(64))
    input: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    expected_result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = uuid_pk()
    trace_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    resource_type: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[str] = mapped_column(String(64))
    payload_redacted: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = created_at()


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (UniqueConstraint("action_type", "target_resource_id", "idempotency_key"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    action_type: Mapped[str] = mapped_column(String(64))
    target_resource_id: Mapped[str] = mapped_column(String(64))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    response_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = created_at()


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[uuid.UUID] = uuid_pk()
    event_type: Mapped[str] = mapped_column(String(64))
    aggregate_type: Mapped[str] = mapped_column(String(64))
    aggregate_id: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = created_at()
