from datetime import datetime
from typing import Protocol

from pydantic import BaseModel


class OrderFact(BaseModel):
    order_number: str
    customer_id: str
    status: str
    ordered_at: datetime


class ShipmentFact(BaseModel):
    tracking_number: str
    status: str
    eta_at: datetime | None


class CustomerFact(BaseModel):
    external_id: str
    tier: str


class ProductFact(BaseModel):
    sku_code: str
    title: str
    price_minor: int
    currency: str


class InventoryFact(BaseModel):
    sku_code: str
    available_quantity: int
    observed_at: datetime


class PolicyFact(BaseModel):
    document_key: str
    version: str
    effective_from: datetime
    effective_to: datetime | None


class WriteCommand(BaseModel):
    """Required metadata for every provider write; domain services authorize it first."""

    actor_id: str
    reason_code: str
    idempotency_key: str
    simulate_timeout: bool = False


class WriteResult(BaseModel):
    action: str
    status: str
    external_reference: str


class CommerceReadPort(Protocol):
    def get_customer(self, external_id: str) -> CustomerFact | None: ...

    def get_order(self, order_number: str) -> OrderFact | None: ...

    def search_products(self, query: str) -> list[ProductFact]: ...

    def get_inventory(self, sku_code: str) -> InventoryFact | None: ...

    def get_shipment(self, order_number: str) -> ShipmentFact | None: ...

    def search_policy(self, document_key: str) -> list[PolicyFact]: ...


class CommerceWritePort(Protocol):
    def create_ticket(self, command: WriteCommand) -> WriteResult: ...

    def update_ticket(self, command: WriteCommand) -> WriteResult: ...

    def update_address(self, command: WriteCommand) -> WriteResult: ...

    def request_refund(self, command: WriteCommand) -> WriteResult: ...

    def request_return(self, command: WriteCommand) -> WriteResult: ...

    def create_carrier_inquiry(self, command: WriteCommand) -> WriteResult: ...

    def send_customer_message(self, command: WriteCommand) -> WriteResult: ...

    def request_human_approval(self, command: WriteCommand) -> WriteResult: ...
