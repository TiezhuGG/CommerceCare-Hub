import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import Role, TicketState
from app.core.errors import InvalidStateTransitionError
from app.core.security import hash_password
from app.models import Conversation, Customer, Ticket, User
from app.services.seed import DEMO_PASSWORD, seed_demo_data
from app.services.tickets import TicketDomainService


def _customer_headers(client: TestClient) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/token",
        json={"email": "customer1@demo.local", "password": DEMO_PASSWORD},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _conversation(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post(
        "/api/v1/conversations",
        headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_delivery_delay_workflow_returns_grounded_reply_and_trace(
    client: TestClient, session: Session
) -> None:
    seed_demo_data(session)
    session.commit()
    headers = _customer_headers(client)
    conversation_id = _conversation(client, headers)

    response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers={**headers, "Idempotency-Key": "message-delay-1"},
        json={"message": "订单 CC-1001 为什么还没到？", "client_message_id": "client-delay-1"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "延迟" in payload["customer_reply"]
    trace = client.get(f"/api/v1/workflow-runs/{payload['trace_id']}", headers=headers)
    assert trace.status_code == 200
    assert "RouterAgent" in trace.json()["agents"]
    assert "get_order" in trace.json()["tools"]
    assert trace.json()["evidence"]
    assert trace.json()["state_transitions"][-1] == "solution_proposed->resolved"


def test_missing_order_reference_safely_waits_for_customer(
    client: TestClient, session: Session
) -> None:
    seed_demo_data(session)
    session.commit()
    headers = _customer_headers(client)
    conversation_id = _conversation(client, headers)

    response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers={**headers, "Idempotency-Key": "message-missing-1"},
        json={"message": "我的订单什么时候到？", "client_message_id": "client-missing-1"},
    )

    assert response.status_code == 200
    assert "订单号" in response.json()["customer_reply"]
    detail = client.get(f"/api/v1/conversations/{conversation_id}", headers=headers)
    assert detail.json()["ticket_state"] == "waiting_customer"


def test_message_idempotency_replays_workflow_response(
    client: TestClient, session: Session
) -> None:
    seed_demo_data(session)
    session.commit()
    headers = _customer_headers(client)
    conversation_id = _conversation(client, headers)
    request_headers = {**headers, "Idempotency-Key": "message-replay-1"}
    payload = {"message": "查询 CC-1001", "client_message_id": "client-replay-1"}

    first = client.post(
        f"/api/v1/conversations/{conversation_id}/messages", headers=request_headers, json=payload
    )
    second = client.post(
        f"/api/v1/conversations/{conversation_id}/messages", headers=request_headers, json=payload
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()


def test_customer_cannot_read_another_customers_conversation(
    client: TestClient, session: Session
) -> None:
    seed_demo_data(session)
    other_customer = Customer(external_id="CUS-EXTRA", tier="standard", pii_token="pii_demo_extra")
    session.add(other_customer)
    session.flush()
    session.add(
        User(
            email="customer2@demo.local",
            password_hash=hash_password(DEMO_PASSWORD),
            role=Role.CUSTOMER,
            customer_id=other_customer.id,
        )
    )
    session.commit()
    first_headers = _customer_headers(client)
    conversation_id = _conversation(client, first_headers)
    second_login = client.post(
        "/api/v1/auth/token",
        json={"email": "customer2@demo.local", "password": DEMO_PASSWORD},
    )
    second_headers = {"Authorization": f"Bearer {second_login.json()['access_token']}"}

    denied = client.get(f"/api/v1/conversations/{conversation_id}", headers=second_headers)

    assert denied.status_code == 403


def test_ticket_domain_service_rejects_illegal_transition(session: Session) -> None:
    seed_demo_data(session)
    conversation = Conversation(customer_id=session.scalar(select(Customer.id).limit(1)))
    session.add(conversation)
    session.flush()
    ticket = Ticket(conversation_id=conversation.id, reason_code="TEST")
    session.add(ticket)
    session.flush()

    with pytest.raises(InvalidStateTransitionError):
        TicketDomainService().transition(
            session,
            ticket=ticket,
            to_state=TicketState.RESOLVED,
            event_type="ILLEGAL_TEST",
            actor_id=None,
        )


def test_duplicate_client_message_id_is_rejected_for_a_different_request(
    client: TestClient, session: Session
) -> None:
    seed_demo_data(session)
    session.commit()
    headers = _customer_headers(client)
    conversation_id = _conversation(client, headers)
    payload = {"message": "查询 CC-1001", "client_message_id": "client-duplicate-1"}
    first = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers={**headers, "Idempotency-Key": "message-duplicate-1"},
        json=payload,
    )
    second = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers={**headers, "Idempotency-Key": "message-duplicate-2"},
        json=payload,
    )

    assert first.status_code == 200
    assert second.status_code == 409
