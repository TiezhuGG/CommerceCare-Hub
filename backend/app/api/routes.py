import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select

from app.api.deps import CurrentUserDep, SessionDep, require_idempotency_key, require_roles
from app.core.config import get_settings
from app.core.enums import Role
from app.core.errors import AuthorizationError
from app.core.security import create_access_token, verify_password
from app.models import AuditLog, Order, Shipment, User
from app.schemas import (
    AuditLogResponse,
    CurrentUserResponse,
    LoginRequest,
    OrderResponse,
    SeedResponse,
    TokenResponse,
)
from app.services.audit import record_audit
from app.services.authorization import ensure_order_access
from app.services.idempotency import execute_idempotent
from app.services.seed import reset_demo_data, seed_demo_data

router = APIRouter(prefix="/api/v1")


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
        return reset_demo_data(session)

    result = execute_idempotent(
        session,
        action_type="reset_demo",
        target_resource_id="phase_1",
        idempotency_key=idempotency_key,
        action=command,
    )
    session.commit()
    return SeedResponse.model_validate(result)
