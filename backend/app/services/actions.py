import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import (
    ActionStatus,
    ActionType,
    ApprovalDecision,
    ApprovalStatus,
    TicketState,
    WorkflowStatus,
)
from app.core.errors import ApprovalNotActionableError, PolicyViolationError
from app.models import (
    ApprovalRequest,
    Conversation,
    Order,
    OrderItem,
    ServiceAction,
    Ticket,
    WorkflowRun,
)
from app.schemas import ActionRequest
from app.services.audit import enqueue_outbox, record_audit
from app.services.tickets import TicketDomainService


@dataclass(frozen=True)
class CreatedAction:
    action: ServiceAction
    approval: ApprovalRequest | None


class AfterSalesActionService:
    """Domain-owned, policy-gated creator for all Phase 3 write actions."""

    _approval_required = {ActionType.REFUND, ActionType.ADDRESS_UPDATE}

    def __init__(self, tickets: TicketDomainService | None = None) -> None:
        self._tickets = tickets or TicketDomainService()

    def create(
        self,
        session: Session,
        *,
        conversation: Conversation,
        actor_id: uuid.UUID,
        order: Order,
        command: ActionRequest,
        idempotency_key: str,
    ) -> CreatedAction:
        self._validate(command, order, session)
        ticket = Ticket(
            conversation_id=conversation.id, reason_code=command.action_type.value.upper()
        )
        session.add(ticket)
        session.flush()
        workflow = WorkflowRun(
            trace_id=ticket.trace_id,
            ticket_id=ticket.id,
            status=WorkflowStatus.RUNNING,
        )
        session.add(workflow)
        session.flush()
        self._tickets.transition(
            session,
            ticket=ticket,
            to_state=TicketState.CLASSIFIED,
            event_type="AFTER_SALES_ACTION_CLASSIFIED",
            actor_id=actor_id,
        )
        self._tickets.transition(
            session,
            ticket=ticket,
            to_state=TicketState.CONTEXT_READY,
            event_type="AFTER_SALES_ORDER_VALIDATED",
            actor_id=actor_id,
        )
        self._tickets.transition(
            session,
            ticket=ticket,
            to_state=TicketState.SOLUTION_PROPOSED,
            event_type="AFTER_SALES_ACTION_PROPOSED",
            actor_id=actor_id,
        )
        requires_approval = command.action_type in self._approval_required
        action = ServiceAction(
            ticket_id=ticket.id,
            workflow_run_id=workflow.id,
            order_id=order.id,
            requested_by=actor_id,
            action_type=command.action_type,
            status=ActionStatus.PENDING_APPROVAL if requires_approval else ActionStatus.QUEUED,
            reason_code=command.reason_code,
            idempotency_key=idempotency_key,
            payload_redacted=self._redacted_payload(command),
        )
        session.add(action)
        session.flush()
        approval: ApprovalRequest | None = None
        if requires_approval:
            self._tickets.transition(
                session,
                ticket=ticket,
                to_state=TicketState.PENDING_APPROVAL,
                event_type="ACTION_REQUIRES_APPROVAL",
                actor_id=actor_id,
            )
            approval = ApprovalRequest(
                ticket_id=ticket.id,
                action_id=action.id,
                action_type=command.action_type.value,
                status=ApprovalStatus.PENDING,
                expires_at=datetime.now(UTC) + timedelta(minutes=15),
            )
            session.add(approval)
            workflow.final_result_code = "PENDING_APPROVAL"
        else:
            self._tickets.transition(
                session,
                ticket=ticket,
                to_state=TicketState.EXECUTING,
                event_type="LOW_RISK_ACTION_QUEUED",
                actor_id=actor_id,
            )
            enqueue_outbox(
                session,
                event_type="SERVICE_ACTION_EXECUTE",
                aggregate_type="service_action",
                aggregate_id=str(action.id),
                payload={"action_id": str(action.id)},
            )
            workflow.final_result_code = "ACTION_QUEUED"
        record_audit(
            session,
            event_type="SERVICE_ACTION_CREATED",
            resource_type="service_action",
            resource_id=str(action.id),
            actor_id=actor_id,
            trace_id=ticket.trace_id,
            payload_redacted={
                "action_type": command.action_type.value,
                "requires_approval": requires_approval,
                "reason_code": command.reason_code,
            },
        )
        return CreatedAction(action=action, approval=approval)

    def decide(
        self,
        session: Session,
        *,
        approval: ApprovalRequest,
        supervisor_id: uuid.UUID,
        decision: ApprovalDecision,
        reason_code: str,
    ) -> ServiceAction:
        action = session.get(ServiceAction, approval.action_id)
        ticket = session.get(Ticket, approval.ticket_id)
        workflow = session.get(WorkflowRun, action.workflow_run_id) if action is not None else None
        if action is None or ticket is None or workflow is None:
            raise ApprovalNotActionableError("Approval does not reference an active action")
        if approval.status is not ApprovalStatus.PENDING:
            raise ApprovalNotActionableError("Approval has already been decided")
        if self._is_expired(approval.expires_at):
            approval.status = ApprovalStatus.EXPIRED
            action.status = ActionStatus.REJECTED
            self._tickets.transition(
                session,
                ticket=ticket,
                to_state=TicketState.ESCALATED,
                event_type="APPROVAL_EXPIRED",
                actor_id=supervisor_id,
            )
            record_audit(
                session,
                event_type="APPROVAL_EXPIRED",
                resource_type="approval_request",
                resource_id=str(approval.id),
                actor_id=supervisor_id,
                trace_id=ticket.trace_id,
            )
            workflow.status = WorkflowStatus.ESCALATED
            workflow.final_result_code = "APPROVAL_EXPIRED"
            raise ApprovalNotActionableError("Approval has expired")
        approval.decided_by = supervisor_id
        if decision is ApprovalDecision.REJECT:
            approval.status = ApprovalStatus.REJECTED
            action.status = ActionStatus.REJECTED
            self._tickets.transition(
                session,
                ticket=ticket,
                to_state=TicketState.ESCALATED,
                event_type="ACTION_REJECTED",
                actor_id=supervisor_id,
            )
            workflow.status = WorkflowStatus.ESCALATED
            workflow.final_result_code = "ACTION_REJECTED"
        else:
            approval.status = ApprovalStatus.APPROVED
            action.status = ActionStatus.QUEUED
            self._tickets.transition(
                session,
                ticket=ticket,
                to_state=TicketState.EXECUTING,
                event_type="ACTION_APPROVED_AND_QUEUED",
                actor_id=supervisor_id,
            )
            enqueue_outbox(
                session,
                event_type="SERVICE_ACTION_EXECUTE",
                aggregate_type="service_action",
                aggregate_id=str(action.id),
                payload={"action_id": str(action.id)},
            )
        record_audit(
            session,
            event_type="APPROVAL_DECIDED",
            resource_type="approval_request",
            resource_id=str(approval.id),
            actor_id=supervisor_id,
            trace_id=ticket.trace_id,
            payload_redacted={"decision": decision.value, "reason_code": reason_code},
        )
        return action

    def expire_pending(self, session: Session) -> int:
        expired = session.scalars(
            select(ApprovalRequest)
            .where(ApprovalRequest.status == ApprovalStatus.PENDING)
            .where(ApprovalRequest.expires_at <= datetime.now(UTC))
        ).all()
        for approval in expired:
            action = session.get(ServiceAction, approval.action_id)
            ticket = session.get(Ticket, approval.ticket_id)
            workflow = (
                session.get(WorkflowRun, action.workflow_run_id) if action is not None else None
            )
            if action is None or ticket is None or workflow is None:
                continue
            approval.status = ApprovalStatus.EXPIRED
            action.status = ActionStatus.REJECTED
            if ticket.state is TicketState.PENDING_APPROVAL:
                self._tickets.transition(
                    session,
                    ticket=ticket,
                    to_state=TicketState.ESCALATED,
                    event_type="APPROVAL_EXPIRED",
                    actor_id=None,
                )
            record_audit(
                session,
                event_type="APPROVAL_EXPIRED",
                resource_type="approval_request",
                resource_id=str(approval.id),
                trace_id=ticket.trace_id,
            )
            workflow.status = WorkflowStatus.ESCALATED
            workflow.final_result_code = "APPROVAL_EXPIRED"
        return len(expired)

    @staticmethod
    def _validate(command: ActionRequest, order: Order, session: Session) -> None:
        if command.action_type is ActionType.REFUND:
            if command.amount_minor is None:
                raise PolicyViolationError("Refund requests require amount_minor")
            order_total = session.scalar(
                select(
                    func.coalesce(func.sum(OrderItem.quantity * OrderItem.unit_price_minor), 0)
                ).where(OrderItem.order_id == order.id)
            )
            if command.amount_minor > int(order_total or 0):
                raise PolicyViolationError("Refund amount exceeds order total")
        elif command.amount_minor is not None:
            raise PolicyViolationError("Only refund requests can include amount_minor")
        if command.action_type is ActionType.ADDRESS_UPDATE and command.address_reference is None:
            raise PolicyViolationError("Address update requires address_reference")
        if command.action_type is ActionType.RETURN and order.status != "delivered":
            raise PolicyViolationError("Returns can only be requested after delivery")

    @staticmethod
    def _redacted_payload(command: ActionRequest) -> dict[str, object]:
        payload: dict[str, object] = {"simulate_timeout": command.simulate_timeout}
        if command.amount_minor is not None:
            payload["amount_minor"] = command.amount_minor
        if command.address_reference is not None:
            payload["address_reference_fingerprint"] = hashlib.sha256(
                command.address_reference.encode()
            ).hexdigest()
        return payload

    @staticmethod
    def _is_expired(expires_at: datetime) -> bool:
        """SQLite test storage can return a naive timestamp; production storage is UTC-aware."""

        normalized = expires_at.replace(tzinfo=UTC) if expires_at.tzinfo is None else expires_at
        return normalized <= datetime.now(UTC)
