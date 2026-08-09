from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.enums import Role
from app.core.security import hash_password
from app.models import Customer, User
from app.services.seed import DEMO_PASSWORD, seed_demo_data


def _headers(client: TestClient, email: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/token", json={"email": email, "password": DEMO_PASSWORD}
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_ticket_timeline_is_owner_scoped_and_contains_transitions(
    client: TestClient, session: Session
) -> None:
    seed_demo_data(session)
    session.commit()
    customer = _headers(client, "customer1@demo.local")
    conversation = client.post(
        "/api/v1/conversations",
        headers={**customer, "Idempotency-Key": "phase6-timeline-conversation"},
    )
    assert conversation.status_code == 200
    response = client.post(
        f"/api/v1/conversations/{conversation.json()['id']}/messages",
        headers={**customer, "Idempotency-Key": "phase6-timeline-message"},
        json={"message": "Order CC-1001 is delayed.", "client_message_id": "phase6-timeline"},
    )
    assert response.status_code == 200

    detail = client.get(f"/api/v1/tickets/{response.json()['ticket_id']}", headers=customer)

    assert detail.status_code == 200
    assert detail.json()["trace_id"] == response.json()["trace_id"]
    assert detail.json()["events"][-1]["to_state"] == "resolved"


def test_customer_cannot_open_another_customers_ticket_timeline(
    client: TestClient, session: Session
) -> None:
    seed_demo_data(session)
    owner_headers = _headers(client, "customer1@demo.local")
    conversation = client.post(
        "/api/v1/conversations",
        headers={**owner_headers, "Idempotency-Key": "phase6-denied-conversation"},
    )
    response = client.post(
        f"/api/v1/conversations/{conversation.json()['id']}/messages",
        headers={**owner_headers, "Idempotency-Key": "phase6-denied-message"},
        json={"message": "Order CC-1001", "client_message_id": "phase6-denied"},
    )
    other_customer = Customer(external_id="CUS-PHASE6", tier="standard", pii_token="pii_phase6")
    session.add(other_customer)
    session.flush()
    session.add(
        User(
            email="customer-phase6@demo.local",
            password_hash=hash_password(DEMO_PASSWORD),
            role=Role.CUSTOMER,
            customer_id=other_customer.id,
        )
    )
    session.commit()
    denied = client.get(
        f"/api/v1/tickets/{response.json()['ticket_id']}",
        headers=_headers(client, "customer-phase6@demo.local"),
    )

    assert denied.status_code == 403
