import hashlib
import hmac
import json

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AuditLog, Conversation, Ticket
from app.services.seed import seed_demo_data


def _signed_headers(body: bytes) -> dict[str, str]:
    signature = hmac.new(
        get_settings().coze_webhook_secret.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()
    return {"Content-Type": "application/json", "X-Coze-Signature": signature}


def test_coze_customer_intake_requires_valid_hmac_and_is_stateless(
    client: TestClient, session: Session
) -> None:
    seed_demo_data(session)
    session.commit()
    payload = {
        "schema_version": "1.0",
        "correlation_id": "coze-case-1",
        "message": "Order CC-1001",
    }
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")

    denied = client.post(
        "/api/v1/coze/v1/wf_customer_intake",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert denied.status_code == 403
    assert session.scalars(select(Conversation)).all() == []
    assert session.scalars(select(Ticket)).all() == []

    accepted = client.post(
        "/api/v1/coze/v1/wf_customer_intake", content=body, headers=_signed_headers(body)
    )
    assert accepted.status_code == 200
    response = accepted.json()
    assert response["correlation_id"] == "coze-case-1"
    assert response["intent"] == "order_status"
    assert response["safe_outcome"] == "allow"
    audit = session.scalar(
        select(AuditLog).where(AuditLog.event_type == "COZE_CUSTOMER_INTAKE_CLASSIFIED")
    )
    assert audit is not None
    assert session.scalars(select(Conversation)).all() == []
    assert session.scalars(select(Ticket)).all() == []
