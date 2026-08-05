from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Customer, Order, Product, Shipment
from app.services.seed import DEMO_PASSWORD, seed_demo_data


def test_seed_creates_documented_synthetic_counts(session: Session) -> None:
    result = seed_demo_data(session)
    session.commit()

    assert result == {
        "status": "seeded",
        "customers": 30,
        "products": 100,
        "orders": 100,
        "shipments": 100,
    }
    assert len(session.scalars(select(Customer)).all()) == 30
    assert len(session.scalars(select(Product)).all()) == 100
    assert len(session.scalars(select(Order)).all()) == 100
    assert len(session.scalars(select(Shipment)).all()) == 100
    assert (
        session.scalar(select(AuditLog).where(AuditLog.event_type == "DEMO_DATA_SEEDED"))
        is not None
    )


def test_seed_is_idempotent(session: Session) -> None:
    seed_demo_data(session)
    session.commit()

    second = seed_demo_data(session)

    assert second["status"] == "already_seeded"
    assert second["orders"] == 100


def test_login_and_order_ownership_are_enforced(client: TestClient, session: Session) -> None:
    seed_demo_data(session)
    session.commit()
    login = client.post(
        "/api/v1/auth/token",
        json={"email": "customer1@demo.local", "password": DEMO_PASSWORD},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    own_order = client.get("/api/v1/orders/CC-1001", headers=headers)
    other_order = client.get("/api/v1/orders/CC-1002", headers=headers)

    assert own_order.status_code == 200
    assert other_order.status_code == 403


def test_seed_endpoint_requires_admin_and_idempotency_key(
    client: TestClient, session: Session
) -> None:
    seed_demo_data(session)
    session.commit()
    admin_login = client.post(
        "/api/v1/auth/token",
        json={"email": "admin@demo.local", "password": DEMO_PASSWORD},
    )
    token = admin_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "seed-test-1"}

    first = client.post("/api/v1/admin/demo/seed", headers=headers)
    second = client.post("/api/v1/admin/demo/seed", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert second.json()["status"] == "already_seeded"


def test_authentication_errors_use_the_documented_error_contract(client: TestClient) -> None:
    response = client.get("/api/v1/me")

    assert response.status_code == 401
    assert response.json()["code"] == "HTTP_ERROR"
    assert response.headers["X-Trace-ID"] == response.json()["trace_id"]
