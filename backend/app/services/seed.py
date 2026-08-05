from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import Role
from app.core.security import hash_password
from app.models import (
    ApprovalRequest,
    AuditLog,
    Conversation,
    Customer,
    EvalCase,
    IdempotencyRecord,
    Message,
    Order,
    OrderItem,
    OutboxEvent,
    PolicyDocument,
    Product,
    PromptVersion,
    Shipment,
    Sku,
    Ticket,
    TicketEvent,
    ToolCall,
    User,
    WorkflowRun,
)
from app.services.audit import record_audit

DEMO_PASSWORD = get_settings().demo_password


def _count(session: Session, model: type[object]) -> int:
    return int(session.scalar(select(func.count()).select_from(model)) or 0)


def seed_demo_data(session: Session) -> dict[str, object]:
    """Create the documented synthetic dataset once; repeated calls have no side effect."""

    if _count(session, Customer) > 0:
        return demo_counts(session, status="already_seeded")

    now = datetime.now(UTC)
    customers: list[Customer] = []
    for index in range(1, 31):
        customer = Customer(
            external_id=f"CUS-{index:03d}",
            tier=("vip" if index % 10 == 0 else "standard"),
            pii_token=f"pii_demo_{index:03d}",
        )
        customers.append(customer)
        session.add(customer)
    session.flush()

    skus: list[Sku] = []
    for index in range(1, 101):
        product = Product(external_id=f"PROD-{index:03d}", title=f"Demo Product {index:03d}")
        session.add(product)
        session.flush()
        sku = Sku(product_id=product.id, sku_code=f"SKU-{index:03d}", price_minor=1_000 + index)
        skus.append(sku)
        session.add(sku)
    session.flush()

    for index in range(1, 101):
        customer = customers[(index - 1) % len(customers)]
        order = Order(
            order_number=f"CC-{1000 + index}",
            customer_id=customer.id,
            status="in_transit" if index % 5 == 1 else "delivered",
            ordered_at=now - timedelta(days=index),
        )
        session.add(order)
        session.flush()
        session.add(
            OrderItem(
                order_id=order.id,
                sku_id=skus[index - 1].id,
                quantity=1,
                unit_price_minor=1_000 + index,
            )
        )
        session.add(
            Shipment(
                order_id=order.id,
                tracking_number=f"TRACK-{index:04d}",
                status="delayed" if index % 5 == 1 else "delivered",
                eta_at=now + timedelta(days=2) if index % 5 == 1 else None,
            )
        )

    session.add_all(
        [
            PolicyDocument(
                document_key="delivery-delay",
                version="2026.1",
                effective_from=now - timedelta(days=1),
                effective_to=None,
                scope={"region": "CN"},
                body="Current synthetic delivery-delay policy.",
            ),
            PolicyDocument(
                document_key="refunds",
                version="2025.4",
                effective_from=now - timedelta(days=365),
                effective_to=now - timedelta(days=1),
                scope={"region": "CN"},
                body="Expired synthetic refund policy.",
            ),
            PromptVersion(
                prompt_key="router",
                version="1",
                template="Synthetic deterministic router prompt",
                active=True,
            ),
        ]
    )
    users = [
        User(email="admin@demo.local", password_hash=hash_password(DEMO_PASSWORD), role=Role.ADMIN),
        User(
            email="supervisor@demo.local",
            password_hash=hash_password(DEMO_PASSWORD),
            role=Role.SUPERVISOR,
        ),
        User(
            email="operator@demo.local",
            password_hash=hash_password(DEMO_PASSWORD),
            role=Role.AGENT_OPERATOR,
        ),
        User(
            email="customer1@demo.local",
            password_hash=hash_password(DEMO_PASSWORD),
            role=Role.CUSTOMER,
            customer_id=customers[0].id,
        ),
    ]
    session.add_all(users)
    session.flush()
    record_audit(
        session,
        event_type="DEMO_DATA_SEEDED",
        resource_type="demo_dataset",
        resource_id="phase_1",
        actor_id=users[0].id,
        payload_redacted={"customers": 30, "products": 100, "orders": 100, "shipments": 100},
    )
    return demo_counts(session, status="seeded")


def demo_counts(session: Session, *, status: str) -> dict[str, object]:
    return {
        "status": status,
        "customers": _count(session, Customer),
        "products": _count(session, Product),
        "orders": _count(session, Order),
        "shipments": _count(session, Shipment),
    }


def reset_demo_data(session: Session) -> dict[str, object]:
    """Development-only reset; callers must enforce environment and Admin authorization."""

    models = [
        ApprovalRequest,
        TicketEvent,
        Ticket,
        Message,
        Conversation,
        ToolCall,
        WorkflowRun,
        OrderItem,
        Shipment,
        Order,
        Sku,
        Product,
        PolicyDocument,
        PromptVersion,
        EvalCase,
        OutboxEvent,
        IdempotencyRecord,
        AuditLog,
        User,
        Customer,
    ]
    for model in models:
        session.execute(delete(model))
    return {"status": "reset", "customers": 0, "products": 0, "orders": 0, "shipments": 0}
