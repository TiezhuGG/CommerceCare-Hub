import uuid
from collections.abc import Sequence
from typing import cast

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.factory import build_agent_service
from app.agents.schemas import (
    ContextResult,
    ObservedFact,
    PolicyResult,
    ReplyResult,
    ResolutionPlan,
    RiskDecisionResult,
    RouterDecision,
)
from app.agents.service import AgentInvocation, StructuredAgentService
from app.core.enums import Intent, RiskDecision, TicketState, WorkflowStatus
from app.models import (
    AgentRun,
    Conversation,
    Message,
    RetrievalEvidence,
    Ticket,
    ToolCall,
    WorkflowRun,
)
from app.providers.contracts import ShipmentFact
from app.providers.mock import DeterministicMockCommerceProvider
from app.services.policy_retrieval import PolicyRetrievalResult, PolicyRetrievalService
from app.services.tickets import TicketDomainService
from app.services.workflow_models import WorkflowResult, observed_now


class OrderStatusWorkflowService:
    """Read-only workflow orchestrating schema-bound agents without granting write capabilities."""

    def __init__(
        self,
        agents: StructuredAgentService | None = None,
        tickets: TicketDomainService | None = None,
        policy_retrieval: PolicyRetrievalService | None = None,
    ) -> None:
        self._agents = agents or build_agent_service()
        self._tickets = tickets or TicketDomainService()
        self._policy_retrieval = policy_retrieval or PolicyRetrievalService()

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
            trace_id=ticket.trace_id, ticket_id=ticket.id, status=WorkflowStatus.RUNNING
        )
        session.add(workflow)
        session.flush()

        router = cast(
            RouterDecision | None,
            self._invoke(
                session,
                workflow,
                agent_name="RouterAgent",
                task="router",
                prompt_key="router_agent",
                payload={"message": customer_message},
                output_model=RouterDecision,
                input_summary={"message_length": len(customer_message)},
            ),
        )
        self._tickets.transition(
            session,
            ticket=ticket,
            to_state=TicketState.CLASSIFIED,
            event_type="INTENT_CLASSIFIED",
            actor_id=customer_actor_id,
        )
        if router is None:
            return self._safe_escalate(
                session,
                workflow=workflow,
                ticket=ticket,
                conversation=conversation,
                actor_id=customer_actor_id,
                reason_code="ROUTER_SCHEMA_UNAVAILABLE",
            )
        if (
            router.intent not in {Intent.ORDER_STATUS, Intent.DELIVERY_DELAY}
            or router.order_number is None
        ):
            return self._need_more_info(
                session,
                workflow=workflow,
                ticket=ticket,
                conversation=conversation,
                actor_id=customer_actor_id,
            )

        if "prompt_injection_detected" in router.risk_tags:
            self._invoke(
                session,
                workflow,
                agent_name="RiskComplianceAgent",
                task="risk",
                prompt_key="risk_compliance_agent",
                payload={"prompt_injection_detected": True, "confidence": router.confidence},
                output_model=RiskDecisionResult,
                input_summary={"signal_count": 1, "confidence": router.confidence},
            )
            return self._safe_escalate(
                session,
                workflow=workflow,
                ticket=ticket,
                conversation=conversation,
                actor_id=customer_actor_id,
                reason_code="PROMPT_INJECTION_DETECTED",
            )

        provider = DeterministicMockCommerceProvider(session)
        order = provider.get_order(router.order_number)
        self._record_tool(
            session,
            workflow,
            "get_order",
            {"order_number": router.order_number},
            {"found": order is not None},
        )
        if order is None or order.customer_id != str(conversation.customer_id):
            return self._need_more_info(
                session,
                workflow=workflow,
                ticket=ticket,
                conversation=conversation,
                actor_id=customer_actor_id,
            )

        shipment = provider.get_shipment(router.order_number)
        self._record_tool(
            session,
            workflow,
            "get_shipment",
            {"order_number": router.order_number},
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
        context = cast(
            ContextResult | None,
            self._invoke(
                session,
                workflow,
                agent_name="ContextAgent",
                task="context",
                prompt_key="context_agent",
                payload={"facts": [fact.model_dump(mode="json") for fact in facts]},
                output_model=ContextResult,
                input_summary={"fact_count": len(facts)},
            ),
        )
        if context is None:
            return self._safe_escalate(
                session,
                workflow=workflow,
                ticket=ticket,
                conversation=conversation,
                actor_id=customer_actor_id,
                reason_code="CONTEXT_SCHEMA_UNAVAILABLE",
            )
        if context.missing_facts or context.conflicting_facts:
            return self._safe_escalate(
                session,
                workflow=workflow,
                ticket=ticket,
                conversation=conversation,
                actor_id=customer_actor_id,
                reason_code="CONTEXT_EVIDENCE_UNVERIFIABLE",
            )
        self._tickets.transition(
            session,
            ticket=ticket,
            to_state=TicketState.CONTEXT_READY,
            event_type="CONTEXT_RETRIEVED",
            actor_id=customer_actor_id,
        )

        retrieval = self._retrieve_policy(session, workflow, router.intent)
        policy = cast(
            PolicyResult | None,
            self._invoke(
                session,
                workflow,
                agent_name="PolicyAgent",
                task="policy",
                prompt_key="policy_agent",
                payload={"evidence": [item.model_dump(mode="json") for item in retrieval.evidence]},
                output_model=PolicyResult,
                input_summary={"evidence_count": len(retrieval.evidence)},
            ),
        )
        if policy is None:
            return self._safe_escalate(
                session,
                workflow=workflow,
                ticket=ticket,
                conversation=conversation,
                actor_id=customer_actor_id,
                reason_code="POLICY_SCHEMA_UNAVAILABLE",
            )
        self._tickets.transition(
            session,
            ticket=ticket,
            to_state=TicketState.SOLUTION_PROPOSED,
            event_type="READ_ONLY_SOLUTION_PROPOSED",
            actor_id=customer_actor_id,
        )

        plan = cast(
            ResolutionPlan | None,
            self._invoke(
                session,
                workflow,
                agent_name="ResolutionPlannerAgent",
                task="planner",
                prompt_key="resolution_planner_agent",
                payload={"intent": router.intent.value, "fact_count": len(context.facts)},
                output_model=ResolutionPlan,
                input_summary={"intent": router.intent.value, "fact_count": len(context.facts)},
            ),
        )
        if plan is None:
            return self._safe_escalate(
                session,
                workflow=workflow,
                ticket=ticket,
                conversation=conversation,
                actor_id=customer_actor_id,
                reason_code="PLANNER_SCHEMA_UNAVAILABLE",
            )
        risk = cast(
            RiskDecisionResult | None,
            self._invoke(
                session,
                workflow,
                agent_name="RiskComplianceAgent",
                task="risk",
                prompt_key="risk_compliance_agent",
                payload={
                    "confidence": router.confidence,
                    "policy_conflict": retrieval.conflict_detected or policy.conflict_detected,
                    "policy_missing": router.requires_evidence and not policy.applicable,
                    "prompt_injection_detected": False,
                },
                output_model=RiskDecisionResult,
                input_summary={
                    "confidence": router.confidence,
                    "policy_conflict": retrieval.conflict_detected,
                },
            ),
        )
        if risk is None or risk.decision is not RiskDecision.ALLOW:
            return self._safe_escalate(
                session,
                workflow=workflow,
                ticket=ticket,
                conversation=conversation,
                actor_id=customer_actor_id,
                reason_code="RISK_REQUIRES_ESCALATION",
            )

        draft_reply = self._reply(order.order_number, order.status, shipment, policy.evidence)
        reply = cast(
            ReplyResult | None,
            self._invoke(
                session,
                workflow,
                agent_name="ReplyAgent",
                task="reply",
                prompt_key="reply_agent",
                payload={
                    "customer_reply": draft_reply,
                    "cited_sources": [item.document_id for item in policy.evidence],
                    "next_step": "Reply in this conversation if you need more help.",
                },
                output_model=ReplyResult,
                input_summary={
                    "fact_count": len(context.facts),
                    "evidence_count": len(policy.evidence),
                },
            ),
        )
        if reply is None:
            return self._safe_escalate(
                session,
                workflow=workflow,
                ticket=ticket,
                conversation=conversation,
                actor_id=customer_actor_id,
                reason_code="REPLY_SCHEMA_UNAVAILABLE",
            )
        session.add(
            Message(
                conversation_id=conversation.id,
                sender_type="assistant",
                body_redacted=reply.customer_reply,
            )
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
            customer_reply=reply.customer_reply,
        )

    def _need_more_info(
        self,
        session: Session,
        *,
        workflow: WorkflowRun,
        ticket: Ticket,
        conversation: Conversation,
        actor_id: uuid.UUID,
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
        fallback = "Please provide the order number (for example CC-1001) so I can check it safely."
        reply = cast(
            ReplyResult | None,
            self._invoke(
                session,
                workflow,
                agent_name="ReplyAgent",
                task="reply",
                prompt_key="reply_agent",
                payload={
                    "customer_reply": fallback,
                    "cited_sources": [],
                    "next_step": "Provide an order number.",
                },
                output_model=ReplyResult,
                input_summary={"missing_information": True},
            ),
        )
        customer_reply = reply.customer_reply if reply is not None else fallback
        session.add(
            Message(
                conversation_id=conversation.id,
                sender_type="assistant",
                body_redacted=customer_reply,
            )
        )
        workflow.status = WorkflowStatus.SUCCEEDED
        workflow.final_result_code = "NEED_MORE_INFO"
        return WorkflowResult(
            conversation_id=conversation.id,
            ticket_id=ticket.id,
            trace_id=ticket.trace_id,
            workflow_status=workflow.status.value,
            customer_reply=customer_reply,
        )

    def _safe_escalate(
        self,
        session: Session,
        *,
        workflow: WorkflowRun,
        ticket: Ticket,
        conversation: Conversation,
        actor_id: uuid.UUID,
        reason_code: str,
    ) -> WorkflowResult:
        self._tickets.transition(
            session,
            ticket=ticket,
            to_state=TicketState.ESCALATED,
            event_type="SAFE_AGENT_ESCALATION",
            actor_id=actor_id,
        )
        customer_reply = "Your request needs human review. We have not taken any external action."
        session.add(
            Message(
                conversation_id=conversation.id,
                sender_type="assistant",
                body_redacted=customer_reply,
            )
        )
        workflow.status = WorkflowStatus.ESCALATED
        workflow.final_result_code = reason_code
        return WorkflowResult(
            conversation_id=conversation.id,
            ticket_id=ticket.id,
            trace_id=ticket.trace_id,
            workflow_status=workflow.status.value,
            customer_reply=customer_reply,
        )

    def _retrieve_policy(
        self, session: Session, workflow: WorkflowRun, intent: Intent
    ) -> PolicyRetrievalResult:
        if intent is not Intent.DELIVERY_DELAY:
            return PolicyRetrievalResult(evidence=[], conflict_detected=False)
        retrieval = self._policy_retrieval.retrieve(session, document_key="delivery-delay")
        self._record_tool(
            session,
            workflow,
            "search_policy",
            {"document_key": "delivery-delay", "region": "CN"},
            {
                "evidence_count": len(retrieval.evidence),
                "conflict_detected": retrieval.conflict_detected,
            },
        )
        for evidence in retrieval.evidence:
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
        return retrieval

    def _invoke(
        self,
        session: Session,
        workflow: WorkflowRun,
        *,
        agent_name: str,
        task: str,
        prompt_key: str,
        payload: dict[str, object],
        output_model: type[BaseModel],
        input_summary: dict[str, object],
    ) -> BaseModel | None:
        invocation = self._agents.invoke(
            session,
            task=task,
            prompt_key=prompt_key,
            payload=payload,
            output_model=output_model,
        )
        self._record_agent(session, workflow, agent_name, invocation, input_summary)
        return invocation.execution.output

    def _record_agent(
        self,
        session: Session,
        workflow: WorkflowRun,
        agent_name: str,
        invocation: AgentInvocation,
        input_summary: dict[str, object],
    ) -> None:
        output = invocation.execution.output
        output_summary = (
            output.model_dump(mode="json")
            if output is not None
            else {
                "safe_escalation": True,
                "validation_error_codes": invocation.execution.validation_error_codes,
            }
        )
        session.add(
            AgentRun(
                workflow_run_id=workflow.id,
                agent_name=agent_name,
                provider_name=self._agents.provider_name,
                model_name=self._agents.model_name,
                prompt_key=invocation.prompt.key if invocation.prompt else None,
                prompt_version=invocation.prompt.version if invocation.prompt else None,
                attempt_count=invocation.execution.attempt_count,
                input_summary=input_summary,
                output_summary=output_summary,
                latency_ms=invocation.execution.latency_ms,
                token_usage=0,
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

    @staticmethod
    def _reply(
        order_number: str,
        order_status: str,
        shipment: ShipmentFact | None,
        evidence: Sequence[object],
    ) -> str:
        if shipment is None:
            return (
                f"Order {order_number} is currently {order_status}. "
                "Shipment information is unavailable."
            )
        if evidence:
            return (
                f"Order {order_number} is currently {order_status}; "
                f"shipment {shipment.tracking_number} is {shipment.status}. "
                "The current delivery-delay policy supports waiting for the next update."
            )
        return (
            f"Order {order_number} is currently {order_status}; "
            f"shipment {shipment.tracking_number} is {shipment.status}."
        )
