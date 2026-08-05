import re
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.core.enums import Intent

ORDER_NUMBER_PATTERN = re.compile(r"\bCC-\d{4,}\b", re.IGNORECASE)


class RouteDecision(BaseModel):
    intent: Intent
    order_number: str | None
    missing_fields: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    decision_summary: str


class ObservedFact(BaseModel):
    fact_type: str
    value: str
    source_type: str
    source_id: str
    observed_at: datetime


class PolicyEvidence(BaseModel):
    document_id: str
    version: str
    effective_time: datetime
    matched_section: str
    relevance_score: int = Field(ge=0, le=100)


class WorkflowResult(BaseModel):
    conversation_id: uuid.UUID
    ticket_id: uuid.UUID
    trace_id: uuid.UUID
    workflow_status: str
    customer_reply: str


class DeterministicRouter:
    """A local structured substitute for the Phase 4 model-backed RouterAgent."""

    def route(self, message: str) -> RouteDecision:
        order_match = ORDER_NUMBER_PATTERN.search(message)
        order_number = order_match.group(0).upper() if order_match else None
        normalized = message.lower()
        is_delay = any(token in normalized for token in ("没到", "延迟", "延误", "晚到", "delay"))
        if order_number is None:
            return RouteDecision(
                intent=Intent.UNKNOWN,
                order_number=None,
                missing_fields=["order_number"],
                confidence=1.0,
                decision_summary="Order reference is required before reading order facts.",
            )
        return RouteDecision(
            intent=Intent.DELIVERY_DELAY if is_delay else Intent.ORDER_STATUS,
            order_number=order_number,
            confidence=1.0,
            decision_summary=(
                "Classified using deterministic order reference and delivery keywords."
            ),
        )


def observed_now() -> datetime:
    return datetime.now(UTC)
