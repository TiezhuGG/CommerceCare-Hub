import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import ActionStatus, ActionType, TicketState, WorkflowStatus
from app.core.errors import ProviderTimeoutError
from app.models import OutboxEvent, ServiceAction, Ticket, ToolCall, WorkflowRun
from app.providers.contracts import WriteCommand, WriteResult
from app.providers.mock import DeterministicMockWriteProvider
from app.schemas import DispatchResponse
from app.services.audit import record_audit
from app.services.tickets import TicketDomainService

MAX_PROVIDER_ATTEMPTS = 3


class OutboxDispatcher:
    """Retries durable action events; a successful provider call is never repeated."""

    def __init__(self, tickets: TicketDomainService | None = None) -> None:
        self._tickets = tickets or TicketDomainService()
        self._provider = DeterministicMockWriteProvider()

    def dispatch(self, session: Session) -> DispatchResponse:
        dispatched = 0
        retried = 0
        failed = 0
        events = session.scalars(
            select(OutboxEvent)
            .where(OutboxEvent.event_type == "SERVICE_ACTION_EXECUTE")
            .where(OutboxEvent.published_at.is_(None))
            .order_by(OutboxEvent.created_at)
        ).all()
        for event in events:
            action = session.get(ServiceAction, uuid.UUID(event.aggregate_id))
            if action is None or action.status in {
                ActionStatus.COMPLETED,
                ActionStatus.REJECTED,
                ActionStatus.FAILED,
            }:
                event.published_at = datetime.now(UTC)
                continue
            ticket = session.get(Ticket, action.ticket_id)
            workflow = session.get(WorkflowRun, action.workflow_run_id)
            if ticket is None or workflow is None:
                event.published_at = datetime.now(UTC)
                failed += 1
                continue
            action.status = ActionStatus.EXECUTING
            event.attempts += 1
            try:
                result = self._call_provider(action)
            except ProviderTimeoutError:
                event.last_error_code = "PROVIDER_TIMEOUT"
                if event.attempts >= MAX_PROVIDER_ATTEMPTS:
                    action.status = ActionStatus.FAILED
                    action.failure_code = "PROVIDER_TIMEOUT"
                    event.published_at = datetime.now(UTC)
                    self._tickets.transition(
                        session,
                        ticket=ticket,
                        to_state=TicketState.FAILED,
                        event_type="ACTION_RETRY_EXHAUSTED",
                        actor_id=action.requested_by,
                    )
                    workflow.final_result_code = "PROVIDER_TIMEOUT"
                    workflow.status = WorkflowStatus.FAILED
                    failed += 1
                else:
                    action.status = ActionStatus.QUEUED
                    retried += 1
                record_audit(
                    session,
                    event_type="SERVICE_ACTION_PROVIDER_TIMEOUT",
                    resource_type="service_action",
                    resource_id=str(action.id),
                    actor_id=action.requested_by,
                    trace_id=ticket.trace_id,
                    payload_redacted={"attempt": event.attempts},
                )
                continue
            action.status = ActionStatus.COMPLETED
            action.external_reference = result.external_reference
            event.published_at = datetime.now(UTC)
            session.add(
                ToolCall(
                    workflow_run_id=workflow.id,
                    tool_name=result.action,
                    request_summary={"action_id": str(action.id)},
                    result_summary={"external_reference": result.external_reference},
                    idempotency_key=action.idempotency_key,
                    status="succeeded",
                )
            )
            self._tickets.transition(
                session,
                ticket=ticket,
                to_state=TicketState.RESOLVED,
                event_type="ACTION_EXECUTED",
                actor_id=action.requested_by,
            )
            workflow.final_result_code = "ACTION_EXECUTED"
            workflow.status = WorkflowStatus.SUCCEEDED
            record_audit(
                session,
                event_type="SERVICE_ACTION_COMPLETED",
                resource_type="service_action",
                resource_id=str(action.id),
                actor_id=action.requested_by,
                trace_id=ticket.trace_id,
                payload_redacted={"action_type": action.action_type.value},
            )
            dispatched += 1
        return DispatchResponse(dispatched=dispatched, retried=retried, failed=failed)

    def _call_provider(self, action: ServiceAction) -> WriteResult:
        command = WriteCommand(
            actor_id=str(action.requested_by),
            reason_code=action.reason_code,
            idempotency_key=action.idempotency_key,
            simulate_timeout=bool(action.payload_redacted.get("simulate_timeout", False)),
        )
        if action.action_type is ActionType.REFUND:
            return self._provider.request_refund(command)
        if action.action_type is ActionType.RETURN:
            return self._provider.request_return(command)
        if action.action_type is ActionType.ADDRESS_UPDATE:
            return self._provider.update_address(command)
        return self._provider.create_carrier_inquiry(command)
