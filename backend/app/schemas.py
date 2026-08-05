import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import Role


class LoginRequest(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(min_length=12, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUserResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: Role
    customer_id: uuid.UUID | None

    model_config = ConfigDict(from_attributes=True)


class SeedResponse(BaseModel):
    status: str
    customers: int
    products: int
    orders: int
    shipments: int


class OrderResponse(BaseModel):
    order_number: str
    status: str
    ordered_at: datetime
    shipment_status: str | None
    tracking_number: str | None


class AuditLogResponse(BaseModel):
    event_type: str
    resource_type: str
    resource_id: str
    occurred_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):
    code: str
    message: str
    trace_id: str
    details: dict[str, object] | None = None
