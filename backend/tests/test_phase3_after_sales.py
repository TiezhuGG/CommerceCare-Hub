import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import ActionStatus, ApprovalStatus, Role, TicketState
from app.core.security import hash_password
from app.models import ApprovalRequest, Customer, ServiceAction, Ticket, ToolCall, User
from app.services.seed import DEMO_PASSWORD, reset_demo_data, seed_demo_data


def _headers(client: TestClient, email: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/token", json={"email": email, "password": DEMO_PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _customer_conversation(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post(
        "/api/v1/conversations",
        headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert response.status_code == 200
    return response.json()["id"]


def _create_action(
    client: TestClient,
    conversation_id: str,
    headers: dict[str, str],
    *,
    key: str,
    action_type: str,
    order_number: str = "CC-1001",
    **extra: object,
):
    return client.post(
        f"/api/v1/conversations/{conversation_id}/actions",
        headers={**headers, "Idempotency-Key": key},
        json={
            "action_type": action_type,
            "order_number": order_number,
            "reason_code": "CUSTOMER_REQUEST",
            **extra,
        },
    )


def test_damaged_item_is_dispatched_once_and_replayed_after_client_disconnect(
    client: TestClient, session: Session
) -> None:
    seed_demo_data(session)
    session.commit()
    customer = _headers(client, "customer1@demo.local")
    conversation = _customer_conversation(client, customer)

    first = _create_action(
        client, conversation, customer, key="damaged-replay-1", action_type="damaged_item"
    )
    replay = _create_action(
        client, conversation, customer, key="damaged-replay-1", action_type="damaged_item"
    )

    assert first.status_code == 200, first.json()
    assert replay.status_code == 200
    assert first.json() == replay.json()
    assert first.json()["status"] == "completed"
    action = session.get(ServiceAction, uuid.UUID(first.json()["action_id"]))
    assert action is not None
    calls = session.scalars(
        select(ToolCall).where(ToolCall.workflow_run_id == action.workflow_run_id)
    ).all()
    assert [call.tool_name for call in calls] == ["create_carrier_inquiry"]


def test_refund_needs_supervisor_approval_then_admin_dispatches(
    client: TestClient, session: Session
) -> None:
    seed_demo_data(session)
    session.commit()
    customer = _headers(client, "customer1@demo.local")
    supervisor = _headers(client, "supervisor@demo.local")
    admin = _headers(client, "admin@demo.local")
    conversation = _customer_conversation(client, customer)

    created = _create_action(
        client,
        conversation,
        customer,
        key="refund-approval-1",
        action_type="refund",
        amount_minor=500,
    )
    assert created.status_code == 200, created.json()
    assert created.json()["status"] == "pending_approval"
    approval_id = created.json()["approval_id"]
    assert approval_id
    replayed = _create_action(
        client,
        conversation,
        customer,
        key="refund-approval-1",
        action_type="refund",
        amount_minor=500,
    )
    assert replayed.status_code == 200
    assert replayed.json() == created.json()

    approved = client.post(
        f"/api/v1/approvals/{approval_id}/decision",
        headers={**supervisor, "Idempotency-Key": "approve-refund-1"},
        json={"decision": "approve", "reason_code": "POLICY_CONFIRMED"},
    )
    assert approved.status_code == 200
    assert approved.json()["action_status"] == "queued"
    dispatched = client.post(
        "/api/v1/admin/outbox/dispatch",
        headers={**admin, "Idempotency-Key": "dispatch-refund-1"},
    )
    assert dispatched.status_code == 200
    assert dispatched.json()["dispatched"] == 1
    approvals = client.get("/api/v1/approvals", headers=supervisor)
    record = next(item for item in approvals.json() if item["id"] == approval_id)
    assert record["status"] == "approved"
    assert record["action_status"] == "completed"


def test_return_for_a_delivered_customer_order_is_dispatched(
    client: TestClient, session: Session
) -> None:
    seed_demo_data(session)
    session.commit()
    customer = _headers(client, "customer1@demo.local")
    conversation = _customer_conversation(client, customer)

    created = _create_action(
        client,
        conversation,
        customer,
        key="return-delivered-1",
        action_type="return",
        order_number="CC-1031",
    )

    assert created.status_code == 200, created.json()
    assert created.json()["status"] == "completed"


def test_provider_timeout_retries_then_marks_ticket_failed(
    client: TestClient, session: Session
) -> None:
    seed_demo_data(session)
    session.commit()
    customer = _headers(client, "customer1@demo.local")
    admin = _headers(client, "admin@demo.local")
    conversation = _customer_conversation(client, customer)

    created = _create_action(
        client,
        conversation,
        customer,
        key="timeout-action-1",
        action_type="damaged_item",
        simulate_timeout=True,
    )
    assert created.status_code == 200
    assert created.json()["status"] == "queued"
    for key in ("timeout-dispatch-2", "timeout-dispatch-3"):
        response = client.post(
            "/api/v1/admin/outbox/dispatch", headers={**admin, "Idempotency-Key": key}
        )
        assert response.status_code == 200
    ticket = session.get(Ticket, uuid.UUID(created.json()["ticket_id"]))
    action = session.get(ServiceAction, uuid.UUID(created.json()["action_id"]))
    assert ticket is not None and ticket.state is TicketState.FAILED
    assert action is not None and action.status is ActionStatus.FAILED
    assert action.failure_code == "PROVIDER_TIMEOUT"


def test_expired_approval_is_safe_and_address_is_only_fingerprinted(
    client: TestClient, session: Session
) -> None:
    seed_demo_data(session)
    session.commit()
    customer = _headers(client, "customer1@demo.local")
    supervisor = _headers(client, "supervisor@demo.local")
    conversation = _customer_conversation(client, customer)
    created = _create_action(
        client,
        conversation,
        customer,
        key="address-expired-1",
        action_type="address_update",
        address_reference="ADDR-REF-DO-NOT-PERSIST",
    )
    assert created.status_code == 200
    approval = session.get(ApprovalRequest, uuid.UUID(created.json()["approval_id"]))
    action = session.get(ServiceAction, uuid.UUID(created.json()["action_id"]))
    assert approval is not None and action is not None
    assert "ADDR-REF-DO-NOT-PERSIST" not in str(action.payload_redacted)
    assert "address_reference_fingerprint" in action.payload_redacted
    approval.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    session.commit()

    expired = client.post(
        f"/api/v1/approvals/{approval.id}/decision",
        headers={**supervisor, "Idempotency-Key": "expired-decision-1"},
        json={"decision": "approve", "reason_code": "POLICY_CONFIRMED"},
    )
    assert expired.status_code == 400
    assert expired.json()["code"] == "APPROVAL_NOT_ACTIONABLE"
    session.refresh(approval)
    session.refresh(action)
    ticket = session.get(Ticket, action.ticket_id)
    assert approval.status is ApprovalStatus.EXPIRED
    assert action.status is ActionStatus.REJECTED
    assert ticket is not None and ticket.state is TicketState.ESCALATED


def test_customer_cannot_create_action_for_someone_elses_order(
    client: TestClient, session: Session
) -> None:
    seed_demo_data(session)
    customer2 = Customer(
        external_id="CUS-ACTION-DENIED", tier="standard", pii_token="pii_action_denied"
    )
    session.add(customer2)
    session.flush()
    session.add(
        User(
            email="customer-action-denied@demo.local",
            password_hash=hash_password(DEMO_PASSWORD),
            role=Role.CUSTOMER,
            customer_id=customer2.id,
        )
    )
    session.commit()
    headers = _headers(client, "customer-action-denied@demo.local")
    conversation = _customer_conversation(client, headers)

    denied = _create_action(
        client, conversation, headers, key="cross-customer-action-1", action_type="damaged_item"
    )

    assert denied.status_code == 403


def test_reset_removes_phase_three_workflow_dependents(
    client: TestClient, session: Session
) -> None:
    seed_demo_data(session)
    session.commit()
    customer = _headers(client, "customer1@demo.local")
    conversation = _customer_conversation(client, customer)
    created = _create_action(
        client, conversation, customer, key="reset-phase-three-1", action_type="damaged_item"
    )
    assert created.status_code == 200, created.json()

    result = reset_demo_data(session)
    session.commit()

    assert result["status"] == "reset"
    assert session.scalar(select(ServiceAction)) is None
    assert session.scalar(select(Ticket)) is None


def test_demo_reset_api_reseeds_an_administrator(client: TestClient, session: Session) -> None:
    seed_demo_data(session)
    session.commit()
    admin = _headers(client, "admin@demo.local")

    reset = client.post(
        "/api/v1/admin/demo/reset",
        headers={**admin, "Idempotency-Key": "reset-reseed-1"},
    )

    assert reset.status_code == 200
    assert reset.json()["status"] == "seeded"
    refreshed_admin = _headers(client, "admin@demo.local")
    assert client.get("/api/v1/me", headers=refreshed_admin).status_code == 200
