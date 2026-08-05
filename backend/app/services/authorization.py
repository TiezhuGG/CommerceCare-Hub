from app.core.enums import Role
from app.core.errors import AuthorizationError
from app.models import Conversation, Order, User


def ensure_order_access(actor: User, order: Order) -> None:
    if actor.role in {Role.ADMIN, Role.SUPERVISOR, Role.AGENT_OPERATOR}:
        return
    if actor.role is Role.CUSTOMER and actor.customer_id == order.customer_id:
        return
    raise AuthorizationError("You are not authorized to access this order")


def ensure_conversation_access(actor: User, conversation: Conversation) -> None:
    if actor.role in {Role.ADMIN, Role.SUPERVISOR, Role.AGENT_OPERATOR}:
        return
    if actor.role is Role.CUSTOMER and actor.customer_id == conversation.customer_id:
        return
    raise AuthorizationError("You are not authorized to access this conversation")
