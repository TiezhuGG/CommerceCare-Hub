from sqlalchemy.orm import Session

from app.providers.mock import DeterministicMockCommerceProvider
from app.services.idempotency import execute_idempotent
from app.services.seed import seed_demo_data


def test_idempotent_command_replays_original_response(session: Session) -> None:
    calls = 0

    def command() -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"calls": calls}

    first = execute_idempotent(
        session,
        action_type="test",
        target_resource_id="resource",
        idempotency_key="same-key",
        action=command,
    )
    session.commit()
    second = execute_idempotent(
        session,
        action_type="test",
        target_resource_id="resource",
        idempotency_key="same-key",
        action=command,
    )

    assert first == {"calls": 1}
    assert second == {"calls": 1}
    assert calls == 1


def test_mock_provider_returns_seeded_order_and_shipment(session: Session) -> None:
    seed_demo_data(session)
    session.commit()
    provider = DeterministicMockCommerceProvider(session)

    order = provider.get_order("CC-1005")
    shipment = provider.get_shipment("CC-1005")

    assert order is not None
    assert order.status == "in_transit"
    assert shipment is not None
    assert shipment.status == "delayed"
