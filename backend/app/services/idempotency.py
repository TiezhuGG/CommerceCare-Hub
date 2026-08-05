from collections.abc import Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import IdempotencyConflictError
from app.models import IdempotencyRecord


def execute_idempotent(
    session: Session,
    *,
    action_type: str,
    target_resource_id: str,
    idempotency_key: str,
    action: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    """Execute a transaction-local command once and replay its stored response."""

    existing = session.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.action_type == action_type,
            IdempotencyRecord.target_resource_id == target_resource_id,
            IdempotencyRecord.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        return dict(existing.response_payload)

    response = action()
    record = IdempotencyRecord(
        action_type=action_type,
        target_resource_id=target_resource_id,
        idempotency_key=idempotency_key,
        response_payload=response,
    )
    session.add(record)
    try:
        session.flush()
    except IntegrityError as error:
        session.rollback()
        raise IdempotencyConflictError(
            "Concurrent request used the same idempotency key"
        ) from error
    return response
