import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import Intent, TicketState, WorkflowStatus
from app.models import (
    AgentRun,
    Conversation,
    Message,
    PolicyDocument,
    RetrievalEvidence,
    Ticket,
    ToolCall,
    WorkflowRun,
)
from app.providers.contracts import ShipmentFact
from app.providers.mock import DeterministicMockCommerceProvider
from app.services.tickets import TicketDomainService
from app.services.workflow_models import (
    DeterministicRouter,
    ObservedFact,
    PolicyEvidence,
    WorkflowResult,
    observed_now,
)


class OrderStatusWorkflowService:
    """Phase 2 read-only workflow for order status and delivery delays."""

    def __init__(
        self,
        router: DeterministicRouter | None = None,
        tickets: TicketDomainService | None = None,
    ) -> None:
        self._router = router or DeterministicRouter()
        self._tickets = tickets or TicketDomainService()

    def run(
        self,
        session: Session,
        *,
        conversation: Conversation,
        customer_actor_id: uuid.UUID,
        customer_message: str,
    ) -> WorkflowResult:
        ticket = Ticket(conversation_id=conversation.id, reason_code="CUSTOMER_MESSAGE")
        session.add(ticket)
        session.flush()
        workflow = WorkflowRun(
            trace_id=ticket.trace_id,
            ticket_id=ticket.id,
            status=WorkflowStatus.RUNNING,
        )
        session.add(workflow)
        session.flush()

        decision = self._router.route(customer_message)
        self._record_agent(
            session,
            workflow,
            "RouterAgent",
            input_summary={"message_length": len(customer_message)},
            output_summary=decision.model_dump(mode="json"),
        )
        self._tickets.transition(
            session,
            ticket=ticket,
            to_state=TicketState.CLASSIFIED,
            event_type="INTENT_CLASSIFIED",
            actor_id=customer_actor_id,
        )

        if decision.intent is Intent.UNKNOWN or decision.order_number is None:
            return self._need_more_info(
                session,
                workflow=workflow,
                ticket=ticket,
                conversation=conversation,
                actor_id=customer_actor_id,
                reason="请提供订单号（例如 CC-1001），我才能查询订单和物流状态。",
            )

        provider = DeterministicMockCommerceProvider(session)
        order = provider.get_order(decision.order_number)
        self._record_tool(
            session,
            workflow,
            "get_order",
            {"order_number": decision.order_number},
            {"found": order is not None},
        )
        if order is None or order.customer_id != str(conversation.customer_id):
            # Do not distinguish a missing reference from another customer's order.
            return self._need_more_info(
                session,
                workflow=workflow,
                ticket=ticket,
                conversation=conversation,
                actor_id=customer_actor_id,
                reason="未找到可供当前会话查询的订单，请核对订单号后重试。",
            )

        shipment = provider.get_shipment(decision.order_number)
        self._record_tool(
            session,
            workflow,
            "get_shipment",
            {"order_number": decision.order_number},
            {"found": shipment is not None},
        )
        facts = [
            ObservedFact(
                fact_type="order_status",
                value=order.status,
                source_type="commerce_order",
                source_id=order.order_number,
                observed_at=observed_now(),
            )
        ]
        if shipment is not None:
            facts.append(
                ObservedFact(
                    fact_type="shipment_status",
                    value=shipment.status,
                    source_type="commerce_shipment",
                    source_id=shipment.tracking_number,
                    observed_at=observed_now(),
                )
            )
        self._record_agent(
            session,
            workflow,
            "ContextAgent",
            input_summary={"order_number": decision.order_number},
            output_summary={"facts": [fact.model_dump(mode="json") for fact in facts]},
        )
        self._tickets.transition(
            session,
            ticket=ticket,
            to_state=TicketState.CONTEXT_READY,
            event_type="CONTEXT_RETRIEVED",
            actor_id=customer_actor_id,
        )

        evidence = self._retrieve_policy(session, workflow, decision.intent)
        self._record_agent(
            session,
            workflow,
            "PolicyAgent",
            input_summary={"intent": decision.intent.value},
            output_summary={"evidence": evidence.model_dump(mode="json") if evidence else None},
        )
        self._tickets.transition(
            session,
            ticket=ticket,
            to_state=TicketState.SOLUTION_PROPOSED,
            event_type="READ_ONLY_SOLUTION_PROPOSED",
            actor_id=customer_actor_id,
        )

        reply = self._reply(order.order_number, order.status, shipment, evidence)
        self._record_agent(
            session,
            workflow,
            "ReplyAgent",
            input_summary={"fact_count": len(facts), "policy_evidence": evidence is not None},
            output_summary={"grounded": True, "reply_length": len(reply)},
        )
        session.add(
            Message(conversation_id=conversation.id, sender_type="assistant", body_redacted=reply)
        )
        self._tickets.transition(
            session,
            ticket=ticket,
            to_state=TicketState.RESOLVED,
            event_type="READ_ONLY_REPLY_SENT",
            actor_id=customer_actor_id,
        )
        workflow.status = WorkflowStatus.SUCCEEDED
        workflow.final_result_code = "READ_ONLY_REPLY_SENT"
        return WorkflowResult(
            conversation_id=conversation.id,
            ticket_id=ticket.id,
            trace_id=ticket.trace_id,
            workflow_status=workflow.status.value,
            customer_reply=reply,
        )

    def _need_more_info(
        self,
        session: Session,
        *,
        workflow: WorkflowRun,
        ticket: Ticket,
        conversation: Conversation,
        actor_id: uuid.UUID,
        reason: str,
    ) -> WorkflowResult:
        self._tickets.transition(
            session,
            ticket=ticket,
            to_state=TicketState.NEED_MORE_INFO,
            event_type="REQUIRED_CONTEXT_MISSING",
            actor_id=actor_id,
        )
        self._tickets.transition(
            session,
            ticket=ticket,
            to_state=TicketState.WAITING_CUSTOMER,
            event_type="WAITING_FOR_CUSTOMER",
            actor_id=actor_id,
        )
        self._record_agent(
            session,
            workflow,
            "ReplyAgent",
            input_summary={"grounded": True, "missing_information": True},
            output_summary={"grounded": True, "reply_length": len(reason)},
        )
        session.add(
            Message(conversation_id=conversation.id, sender_type="assistant", body_redacted=reason)
        )
        workflow.status = WorkflowStatus.SUCCEEDED
        workflow.final_result_code = "NEED_MORE_INFO"
        return WorkflowResult(
            conversation_id=conversation.id,
            ticket_id=ticket.id,
            trace_id=ticket.trace_id,
            workflow_status=workflow.status.value,
            customer_reply=reason,
        )

    def _retrieve_policy(
        self, session: Session, workflow: WorkflowRun, intent: Intent
    ) -> PolicyEvidence | None:
        if intent is not Intent.DELIVERY_DELAY:
            return None
        document = session.scalar(
            select(PolicyDocument)
            .where(PolicyDocument.document_key == "delivery-delay")
            .where(PolicyDocument.effective_to.is_(None))
            .order_by(PolicyDocument.effective_from.desc())
        )
        self._record_tool(
            session,
            workflow,
            "search_policy",
            {"document_key": "delivery-delay"},
            {"found": document is not None},
        )
        if document is None:
            return None
        evidence = PolicyEvidence(
            document_id=str(document.id),
            version=document.version,
            effective_time=document.effective_from,
            matched_section="delivery-delay",
            relevance_score=100,
        )
        session.add(
            RetrievalEvidence(
                workflow_run_id=workflow.id,
                document_id=evidence.document_id,
                document_version=evidence.version,
                matched_section=evidence.matched_section,
                relevance_score=evidence.relevance_score,
                observed_at=evidence.effective_time,
            )
        )
        return evidence

    @staticmethod
    def _reply(
        order_number: str,
        order_status: str,
        shipment: ShipmentFact | None,
        evidence: PolicyEvidence | None,
    ) -> str:
        if shipment is None:
            return f"订单 {order_number} 当前状态为 {order_status}。暂未查询到物流信息。"
        tracking_number = shipment.tracking_number
        shipment_status = shipment.status
        if evidence is not None:
            return (
                f"订单 {order_number} 当前状态为 {order_status}；物流单 {tracking_number} 标记为"
                f"{shipment_status}。依据当前配送延迟政策（版本 {evidence.version}），"
                "请您等待物流状态更新；如状态持续未更新，可回复本会话继续协助。"
            )
        return (
            f"订单 {order_number} 当前状态为 {order_status}；物流单 {tracking_number} "
            f"状态为 {shipment_status}。"
        )

    @staticmethod
    def _record_agent(
        session: Session,
        workflow: WorkflowRun,
        agent_name: str,
        *,
        input_summary: dict[str, object],
        output_summary: dict[str, object],
    ) -> None:
        session.add(
            AgentRun(
                workflow_run_id=workflow.id,
                agent_name=agent_name,
                prompt_key="deterministic-phase-2",
                prompt_version="1",
                input_summary=input_summary,
                output_summary=output_summary,
            )
        )

    @staticmethod
    def _record_tool(
        session: Session,
        workflow: WorkflowRun,
        tool_name: str,
        request_summary: dict[str, object],
        result_summary: dict[str, object],
    ) -> None:
        session.add(
            ToolCall(
                workflow_run_id=workflow.id,
                tool_name=tool_name,
                request_summary=request_summary,
                result_summary=result_summary,
                status="succeeded",
            )
        )
