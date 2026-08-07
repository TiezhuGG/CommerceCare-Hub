import uuid
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select

from app.agents.factory import build_agent_service
from app.agents.schemas import CozeCustomerIntakeRequest, CozeCustomerIntakeResponse, RouterDecision
from app.api.deps import CurrentUserDep, SessionDep, require_idempotency_key, require_roles
from app.core.config import get_settings
from app.core.enums import ActionStatus, Intent, RiskDecision, Role
from app.core.errors import ApprovalNotActionableError, AuthorizationError
from app.core.security import create_access_token, verify_password
from app.models import (
    AgentRun,
    ApprovalRequest,
    AuditLog,
    Conversation,
    Message,
    Order,
    RetrievalEvidence,
    ServiceAction,
    Shipment,
    Ticket,
    TicketEvent,
    ToolCall,
    User,
    WorkflowRun,
)
from app.schemas import (
    ActionRequest,
    ActionResponse,
    ApprovalDecisionRequest,
    ApprovalResponse,
    AuditLogResponse,
    ConversationDetailResponse,
    ConversationResponse,
    CurrentUserResponse,
    DispatchResponse,
    LoginRequest,
    MessageResponse,
    OrderResponse,
    SeedResponse,
    SendMessageRequest,
    SendMessageResponse,
    TicketSummaryResponse,
    TokenResponse,
    WorkflowTraceResponse,
)
from app.services.actions import AfterSalesActionService
from app.services.audit import record_audit
from app.services.authorization import ensure_conversation_access, ensure_order_access
from app.services.coze import verify_coze_signature
from app.services.idempotency import execute_idempotent
from app.services.order_status_workflow import OrderStatusWorkflowService
from app.services.outbox import OutboxDispatcher
from app.services.redaction import redact_customer_message
from app.services.seed import reset_demo_data, seed_demo_data

router = APIRouter(prefix="/api/v1")


@router.post("/coze/v1/wf_customer_intake", response_model=CozeCustomerIntakeResponse)
async def coze_customer_intake(
    request: Request,
    payload: CozeCustomerIntakeRequest,
    session: SessionDep,
) -> CozeCustomerIntakeResponse:
    """Signed, stateless Coze subflow: classify only and never mutate business state."""

    raw_body = await request.body()
    signature = request.headers.get("X-Coze-Signature")
    if not verify_coze_signature(
        raw_body=raw_body,
        signature=signature,
        secret=get_settings().coze_webhook_secret,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Coze signature")

    agents = build_agent_service()
    invocation = agents.invoke(
        session,
        task="router",
        prompt_key="router_agent",
        payload={"message": payload.message},
        output_model=RouterDecision,
    )
    decision = cast(RouterDecision | None, invocation.execution.output)
    if decision is None:
        decision = RouterDecision(
            intent=Intent.UNKNOWN,
            missing_fields=["human_review"],
            requires_evidence=True,
            sentiment="neutral",
            urgency="normal",
            risk_tags=["router_schema_unavailable"],
            confidence=0,
            decision_summary="Structured classification was unavailable.",
        )
        outcome = RiskDecision.ESCALATE
    elif "prompt_injection_detected" in decision.risk_tags:
        outcome = RiskDecision.ESCALATE
    else:
        outcome = RiskDecision.ALLOW
    try:
        trace_id = uuid.UUID(request.state.trace_id)
    except (AttributeError, TypeError, ValueError):
        trace_id = None

    audit = record_audit(
        session,
        event_type="COZE_CUSTOMER_INTAKE_CLASSIFIED",
        resource_type="coze_correlation",
        resource_id=payload.correlation_id,
        trace_id=trace_id,
        payload_redacted={
            "intent": decision.intent.value,
            "has_order_number": decision.order_number is not None,
            "safe_outcome": outcome.value,
            "agent_attempts": invocation.execution.attempt_count,
            "prompt_key": invocation.prompt.key if invocation.prompt else None,
            "prompt_version": invocation.prompt.version if invocation.prompt else None,
            "provider_name": agents.provider_name,
            "model_name": agents.model_name,
        },
    )
    session.flush()
    session.commit()
    return CozeCustomerIntakeResponse(
        correlation_id=payload.correlation_id,
        intent=decision.intent,
        order_number=decision.order_number,
        missing_fields=decision.missing_fields,
        requires_evidence=decision.requires_evidence,
        safe_outcome=outcome,
        audit_id=audit.id,
    )


@router.post("/auth/token", response_model=TokenResponse)
def login(payload: LoginRequest, session: SessionDep) -> TokenResponse:
    user = session.scalar(select(User).where(User.email == payload.email.lower()))
    if (
        user is None
        or not user.is_active
        or not verify_password(payload.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    return TokenResponse(access_token=create_access_token(str(user.id), user.role.value))


@router.get("/me", response_model=CurrentUserResponse)
def current_user(current_user: CurrentUserDep) -> CurrentUserResponse:
    return CurrentUserResponse.model_validate(current_user)


@router.post("/conversations", response_model=ConversationResponse)
def create_conversation(
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> ConversationResponse:
    if current_user.role is not Role.CUSTOMER or current_user.customer_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only customer identities can create customer conversations",
        )
    trace_id = uuid.UUID(request.state.trace_id)

    def command() -> dict[str, object]:
        conversation = Conversation(customer_id=current_user.customer_id)
        session.add(conversation)
        session.flush()
        record_audit(
            session,
            event_type="CONVERSATION_CREATED",
            resource_type="conversation",
            resource_id=str(conversation.id),
            actor_id=current_user.id,
            trace_id=trace_id,
        )
        return {
            "id": str(conversation.id),
            "customer_id": str(conversation.customer_id),
            "status": conversation.status,
            "created_at": conversation.created_at.isoformat(),
        }

    result = execute_idempotent(
        session,
        action_type="create_conversation",
        target_resource_id=str(current_user.customer_id),
        idempotency_key=idempotency_key,
        action=command,
    )
    session.commit()
    return ConversationResponse.model_validate(result)


@router.post("/conversations/{conversation_id}/messages", response_model=SendMessageResponse)
def send_message(
    conversation_id: uuid.UUID,
    payload: SendMessageRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> SendMessageResponse:
    conversation = session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    try:
        ensure_conversation_access(current_user, conversation)
    except AuthorizationError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error.message) from error
    if current_user.role is not Role.CUSTOMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only customer messages can trigger the Phase 2 workflow",
        )

    def command() -> dict[str, object]:
        duplicate = session.scalar(
            select(Message).where(
                Message.conversation_id == conversation.id,
                Message.client_message_id == payload.client_message_id,
            )
        )
        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="client_message_id has already been used for this conversation",
            )
        session.add(
            Message(
                conversation_id=conversation.id,
                sender_type="customer",
                client_message_id=payload.client_message_id,
                body_redacted=redact_customer_message(payload.message),
            )
        )
        workflow = OrderStatusWorkflowService().run(
            session,
            conversation=conversation,
            customer_actor_id=current_user.id,
            customer_message=payload.message,
        )
        record_audit(
            session,
            event_type="CUSTOMER_MESSAGE_PROCESSED",
            resource_type="conversation",
            resource_id=str(conversation.id),
            actor_id=current_user.id,
            trace_id=workflow.trace_id,
            payload_redacted={"client_message_id": payload.client_message_id},
        )
        return workflow.model_dump(mode="json")

    result = execute_idempotent(
        session,
        action_type="send_customer_message",
        target_resource_id=str(conversation.id),
        idempotency_key=idempotency_key,
        action=command,
    )
    session.commit()
    return SendMessageResponse.model_validate(result)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(
    conversation_id: uuid.UUID, session: SessionDep, current_user: CurrentUserDep
) -> ConversationDetailResponse:
    conversation = session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    try:
        ensure_conversation_access(current_user, conversation)
    except AuthorizationError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error.message) from error
    messages = session.scalars(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
    ).all()
    ticket = session.scalar(
        select(Ticket)
        .where(Ticket.conversation_id == conversation.id)
        .order_by(Ticket.created_at.desc())
    )
    return ConversationDetailResponse(
        id=conversation.id,
        customer_id=conversation.customer_id,
        status=conversation.status,
        created_at=conversation.created_at,
        messages=[MessageResponse.model_validate(message) for message in messages],
        ticket_state=ticket.state if ticket else None,
        trace_id=ticket.trace_id if ticket else None,
    )


@router.post("/conversations/{conversation_id}/actions", response_model=ActionResponse)
def create_after_sales_action(
    conversation_id: uuid.UUID,
    payload: ActionRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> ActionResponse:
    if current_user.role is not Role.CUSTOMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only customer identities can create after-sales actions",
        )
    conversation = session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    try:
        ensure_conversation_access(current_user, conversation)
    except AuthorizationError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error.message) from error
    order = session.scalar(select(Order).where(Order.order_number == payload.order_number))
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    try:
        ensure_order_access(current_user, order)
    except AuthorizationError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error.message) from error

    def response_for(action: ServiceAction) -> ActionResponse:
        approval = session.scalar(
            select(ApprovalRequest).where(ApprovalRequest.action_id == action.id)
        )
        if action.status is ActionStatus.QUEUED:
            OutboxDispatcher().dispatch(session)
            session.commit()
            session.refresh(action)
        ticket = session.get(Ticket, action.ticket_id)
        if ticket is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Action ticket was not persisted",
            )
        return ActionResponse(
            action_id=action.id,
            ticket_id=action.ticket_id,
            trace_id=ticket.trace_id,
            status=action.status,
            approval_id=approval.id if approval else None,
        )

    existing_action = session.scalar(
        select(ServiceAction).where(
            ServiceAction.action_type == payload.action_type,
            ServiceAction.order_id == order.id,
            ServiceAction.idempotency_key == idempotency_key,
        )
    )
    if existing_action is not None:
        return response_for(existing_action)

    def command() -> dict[str, object]:
        created = AfterSalesActionService().create(
            session,
            conversation=conversation,
            actor_id=current_user.id,
            order=order,
            command=payload,
            idempotency_key=idempotency_key,
        )
        return {
            "action_id": str(created.action.id),
            "approval_id": str(created.approval.id) if created.approval else None,
        }

    result = execute_idempotent(
        session,
        action_type="create_after_sales_action",
        target_resource_id=str(conversation.id),
        idempotency_key=idempotency_key,
        action=command,
    )
    session.commit()
    action = session.get(ServiceAction, uuid.UUID(str(result["action_id"])))
    if action is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Action was not persisted"
        )
    return response_for(action)


@router.get("/approvals", response_model=list[ApprovalResponse])
def list_approvals(
    session: SessionDep,
    _: Annotated[User, Depends(require_roles(Role.SUPERVISOR, Role.ADMIN))],
) -> list[ApprovalResponse]:
    approvals = session.scalars(
        select(ApprovalRequest).order_by(ApprovalRequest.expires_at).limit(100)
    ).all()
    responses: list[ApprovalResponse] = []
    for approval in approvals:
        action = session.get(ServiceAction, approval.action_id)
        if action is not None:
            responses.append(
                ApprovalResponse(
                    id=approval.id,
                    action_id=approval.action_id,
                    status=approval.status,
                    action_status=action.status,
                )
            )
    return responses


@router.post("/approvals/{approval_id}/decision", response_model=ApprovalResponse)
def decide_approval(
    approval_id: uuid.UUID,
    payload: ApprovalDecisionRequest,
    session: SessionDep,
    supervisor: Annotated[User, Depends(require_roles(Role.SUPERVISOR))],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> ApprovalResponse:
    approval = session.get(ApprovalRequest, approval_id)
    if approval is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found")

    def command() -> dict[str, object]:
        action = AfterSalesActionService().decide(
            session,
            approval=approval,
            supervisor_id=supervisor.id,
            decision=payload.decision,
            reason_code=payload.reason_code,
        )
        return {"action_id": str(action.id)}

    try:
        result = execute_idempotent(
            session,
            action_type="decide_approval",
            target_resource_id=str(approval.id),
            idempotency_key=idempotency_key,
            action=command,
        )
    except ApprovalNotActionableError:
        session.commit()
        raise
    session.commit()
    action = session.get(ServiceAction, uuid.UUID(str(result["action_id"])))
    if action is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Action was not persisted"
        )
    return ApprovalResponse(
        id=approval.id,
        action_id=approval.action_id,
        status=approval.status,
        action_status=action.status,
    )


@router.post("/admin/outbox/dispatch", response_model=DispatchResponse)
def dispatch_outbox(
    session: SessionDep,
    _: Annotated[User, Depends(require_roles(Role.ADMIN))],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> DispatchResponse:
    def command() -> dict[str, int]:
        AfterSalesActionService().expire_pending(session)
        result = OutboxDispatcher().dispatch(session)
        record_audit(
            session,
            event_type="OUTBOX_DISPATCH_REQUESTED",
            resource_type="outbox",
            resource_id=idempotency_key,
            payload_redacted=result.model_dump(),
        )
        return result.model_dump()

    result = execute_idempotent(
        session,
        action_type="dispatch_outbox",
        target_resource_id="service_action_outbox",
        idempotency_key=idempotency_key,
        action=command,
    )
    session.commit()
    return DispatchResponse.model_validate(result)


@router.get("/tickets", response_model=list[TicketSummaryResponse])
def list_tickets(
    session: SessionDep,
    _: Annotated[User, Depends(require_roles(Role.AGENT_OPERATOR, Role.SUPERVISOR, Role.ADMIN))],
) -> list[TicketSummaryResponse]:
    tickets = session.scalars(select(Ticket).order_by(Ticket.created_at.desc()).limit(100)).all()
    return [TicketSummaryResponse.model_validate(ticket) for ticket in tickets]


@router.get("/workflow-runs/{trace_id}", response_model=WorkflowTraceResponse)
def get_workflow_trace(
    trace_id: uuid.UUID, session: SessionDep, current_user: CurrentUserDep
) -> WorkflowTraceResponse:
    workflow = session.scalar(select(WorkflowRun).where(WorkflowRun.trace_id == trace_id))
    if workflow is None or workflow.ticket_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workflow trace not found"
        )
    ticket = session.get(Ticket, workflow.ticket_id)
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workflow ticket not found"
        )
    conversation = session.get(Conversation, ticket.conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workflow conversation not found"
        )
    try:
        ensure_conversation_access(current_user, conversation)
    except AuthorizationError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error.message) from error
    agents = session.scalars(
        select(AgentRun.agent_name).where(AgentRun.workflow_run_id == workflow.id)
    ).all()
    tools = session.scalars(
        select(ToolCall.tool_name).where(ToolCall.workflow_run_id == workflow.id)
    ).all()
    evidence = session.scalars(
        select(RetrievalEvidence).where(RetrievalEvidence.workflow_run_id == workflow.id)
    ).all()
    events = session.scalars(
        select(TicketEvent)
        .where(TicketEvent.ticket_id == ticket.id)
        .order_by(TicketEvent.created_at)
    ).all()
    return WorkflowTraceResponse(
        trace_id=workflow.trace_id,
        status=workflow.status,
        ticket_id=workflow.ticket_id,
        final_result_code=workflow.final_result_code,
        agents=list(agents),
        tools=list(tools),
        evidence=[f"{item.document_id}@{item.document_version}" for item in evidence],
        state_transitions=[
            f"{item.from_state.value if item.from_state else 'none'}->"
            f"{item.to_state.value if item.to_state else 'none'}"
            for item in events
        ],
    )


@router.get("/orders/{order_number}", response_model=OrderResponse)
def get_order(
    order_number: str, session: SessionDep, current_user: CurrentUserDep
) -> OrderResponse:
    order = session.scalar(select(Order).where(Order.order_number == order_number))
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    try:
        ensure_order_access(current_user, order)
    except AuthorizationError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error.message) from error
    shipment = session.scalar(select(Shipment).where(Shipment.order_id == order.id))
    return OrderResponse(
        order_number=order.order_number,
        status=order.status,
        ordered_at=order.ordered_at,
        shipment_status=shipment.status if shipment else None,
        tracking_number=shipment.tracking_number if shipment else None,
    )


@router.get("/audit-logs", response_model=list[AuditLogResponse])
def list_audit_logs(
    session: SessionDep,
    _: Annotated[User, Depends(require_roles(Role.SUPERVISOR, Role.ADMIN))],
) -> list[AuditLogResponse]:
    records = session.scalars(
        select(AuditLog).order_by(AuditLog.occurred_at.desc()).limit(100)
    ).all()
    return [AuditLogResponse.model_validate(record) for record in records]


@router.post("/admin/demo/seed", response_model=SeedResponse)
def seed_demo(
    request: Request,
    session: SessionDep,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN))],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> SeedResponse:
    trace_id = uuid.UUID(request.state.trace_id)

    def command() -> dict[str, object]:
        result = seed_demo_data(session)
        record_audit(
            session,
            event_type="DEMO_SEED_REQUESTED",
            resource_type="demo_dataset",
            resource_id="phase_1",
            actor_id=actor.id,
            trace_id=trace_id,
        )
        return result

    result = execute_idempotent(
        session,
        action_type="seed_demo",
        target_resource_id="phase_1",
        idempotency_key=idempotency_key,
        action=command,
    )
    session.commit()
    return SeedResponse.model_validate(result)


@router.post("/admin/demo/reset", response_model=SeedResponse)
def reset_demo(
    session: SessionDep,
    _: Annotated[User, Depends(require_roles(Role.ADMIN))],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> SeedResponse:
    if get_settings().environment != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Reset is development-only"
        )

    def command() -> dict[str, object]:
        reset_demo_data(session)
        # Re-seed in the same transaction so the authenticated administrator is never locked out.
        return seed_demo_data(session)

    result = execute_idempotent(
        session,
        action_type="reset_demo",
        target_resource_id="phase_1",
        idempotency_key=idempotency_key,
        action=command,
    )
    session.commit()
    return SeedResponse.model_validate(result)
