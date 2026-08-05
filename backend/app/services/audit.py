import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog, OutboxEvent


def record_audit(
    session: Session,
    *,
    event_type: str,
    resource_type: str,
    resource_id: str,
    actor_id: uuid.UUID | None = None,
    trace_id: uuid.UUID | None = None,
    payload_redacted: dict[str, Any] | None = None,
) -> AuditLog:
    """Persist an immutable, PII-minimized audit event in the caller transaction."""

    record = AuditLog(
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        actor_id=actor_id,
        trace_id=trace_id,
        payload_redacted=payload_redacted or {},
    )
    session.add(record)
    return record


def enqueue_outbox(
    session: Session,
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    payload: dict[str, Any],
) -> OutboxEvent:
    event = OutboxEvent(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        payload=payload,
    )
    session.add(event)
    return event
