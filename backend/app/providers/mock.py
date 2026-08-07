from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ProviderTimeoutError
from app.models import Customer, Order, PolicyDocument, Product, Shipment, Sku
from app.providers.contracts import (
    CommerceReadPort,
    CommerceWritePort,
    CustomerFact,
    InventoryFact,
    OrderFact,
    PolicyFact,
    ProductFact,
    ShipmentFact,
    WriteCommand,
    WriteResult,
)


class DeterministicMockCommerceProvider(CommerceReadPort):
    """Database-backed local adapter with no network calls or nondeterminism."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_customer(self, external_id: str) -> CustomerFact | None:
        customer = self._session.scalar(select(Customer).where(Customer.external_id == external_id))
        if customer is None:
            return None
        return CustomerFact(external_id=customer.external_id, tier=customer.tier)

    def get_order(self, order_number: str) -> OrderFact | None:
        order = self._session.scalar(select(Order).where(Order.order_number == order_number))
        if order is None:
            return None
        return OrderFact(
            order_number=order.order_number,
            customer_id=str(order.customer_id),
            status=order.status,
            ordered_at=order.ordered_at,
        )

    def search_products(self, query: str) -> list[ProductFact]:
        products = self._session.scalars(
            select(Product).where(Product.title.ilike(f"%{query.strip()}%")).limit(20)
        ).all()
        facts: list[ProductFact] = []
        for product in products:
            sku = self._session.scalar(select(Sku).where(Sku.product_id == product.id))
            if sku is not None:
                facts.append(
                    ProductFact(
                        sku_code=sku.sku_code,
                        title=product.title,
                        price_minor=sku.price_minor,
                        currency=sku.currency,
                    )
                )
        return facts

    def get_inventory(self, sku_code: str) -> InventoryFact | None:
        sku = self._session.scalar(select(Sku).where(Sku.sku_code == sku_code))
        if sku is None:
            return None
        return InventoryFact(
            sku_code=sku.sku_code,
            available_quantity=50,
            observed_at=datetime.now(UTC),
        )

    def get_shipment(self, order_number: str) -> ShipmentFact | None:
        shipment = self._session.scalar(
            select(Shipment).join(Order).where(Order.order_number == order_number)
        )
        if shipment is None:
            return None
        return ShipmentFact(
            tracking_number=shipment.tracking_number,
            status=shipment.status,
            eta_at=shipment.eta_at,
        )

    def search_policy(self, document_key: str) -> list[PolicyFact]:
        documents = self._session.scalars(
            select(PolicyDocument).where(PolicyDocument.document_key == document_key)
        ).all()
        return [
            PolicyFact(
                document_key=document.document_key,
                version=document.version,
                effective_from=document.effective_from,
                effective_to=document.effective_to,
            )
            for document in documents
        ]


class DeterministicMockWriteProvider(CommerceWritePort):
    """Deterministic adapter contract; Phase 3 domain services will invoke these methods."""

    @staticmethod
    def _result(action: str, command: WriteCommand) -> WriteResult:
        if command.simulate_timeout:
            raise ProviderTimeoutError(f"Mock provider timed out while executing {action}")
        return WriteResult(
            action=action,
            status="accepted",
            external_reference=f"mock:{action}:{command.idempotency_key}",
        )

    def create_ticket(self, command: WriteCommand) -> WriteResult:
        return self._result("create_ticket", command)

    def update_ticket(self, command: WriteCommand) -> WriteResult:
        return self._result("update_ticket", command)

    def update_address(self, command: WriteCommand) -> WriteResult:
        return self._result("update_address", command)

    def request_refund(self, command: WriteCommand) -> WriteResult:
        return self._result("request_refund", command)

    def request_return(self, command: WriteCommand) -> WriteResult:
        return self._result("request_return", command)

    def create_carrier_inquiry(self, command: WriteCommand) -> WriteResult:
        return self._result("create_carrier_inquiry", command)

    def send_customer_message(self, command: WriteCommand) -> WriteResult:
        return self._result("send_customer_message", command)

    def request_human_approval(self, command: WriteCommand) -> WriteResult:
        return self._result("request_human_approval", command)
