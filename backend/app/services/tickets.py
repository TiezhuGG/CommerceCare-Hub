import uuid

from sqlalchemy.orm import Session

from app.core.enums import TicketState
from app.core.errors import InvalidStateTransitionError
from app.models import Ticket, TicketEvent
from app.services.audit import record_audit

ALLOWED_TRANSITIONS: dict[TicketState, set[TicketState]] = {
    TicketState.NEW: {TicketState.CLASSIFIED, TicketState.CANCELLED},
    TicketState.CLASSIFIED: {
        TicketState.NEED_MORE_INFO,
        TicketState.CONTEXT_READY,
        TicketState.ESCALATED,
    },
    TicketState.NEED_MORE_INFO: {TicketState.WAITING_CUSTOMER, TicketState.ESCALATED},
    TicketState.WAITING_CUSTOMER: {TicketState.CLASSIFIED, TicketState.CANCELLED},
    TicketState.CONTEXT_READY: {TicketState.SOLUTION_PROPOSED, TicketState.ESCALATED},
    TicketState.SOLUTION_PROPOSED: {
        TicketState.RESOLVED,
        TicketState.PENDING_APPROVAL,
        TicketState.EXECUTING,
        TicketState.ESCALATED,
    },
    TicketState.PENDING_APPROVAL: {TicketState.EXECUTING, TicketState.ESCALATED},
    TicketState.EXECUTING: {TicketState.RESOLVED, TicketState.FAILED},
    TicketState.RESOLVED: set(),
    TicketState.ESCALATED: set(),
    TicketState.FAILED: set(),
    TicketState.CANCELLED: set(),
}


class TicketDomainService:
    def transition(
        self,
        session: Session,
        *,
        ticket: Ticket,
        to_state: TicketState,
        event_type: str,
        actor_id: uuid.UUID | None,
    ) -> None:
        if to_state not in ALLOWED_TRANSITIONS[ticket.state]:
            raise InvalidStateTransitionError(f"Cannot transition {ticket.state} to {to_state}")
        from_state = ticket.state
        ticket.state = to_state
        session.add(
            TicketEvent(
                ticket_id=ticket.id,
                event_type=event_type,
                from_state=from_state,
                to_state=to_state,
                actor_id=actor_id,
            )
        )
        record_audit(
            session,
            event_type="TICKET_STATE_TRANSITION",
            resource_type="ticket",
            resource_id=str(ticket.id),
            actor_id=actor_id,
            trace_id=ticket.trace_id,
            payload_redacted={"from_state": from_state.value, "to_state": to_state.value},
        )
