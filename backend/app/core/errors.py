class DomainError(Exception):
    """Base error exposed through the API with a stable machine-readable code."""

    code = "DOMAIN_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidStateTransitionError(DomainError):
    code = "INVALID_STATE_TRANSITION"


class AuthorizationError(DomainError):
    code = "FORBIDDEN"


class IdempotencyConflictError(DomainError):
    code = "IDEMPOTENCY_CONFLICT"


class ApprovalNotActionableError(DomainError):
    code = "APPROVAL_NOT_ACTIONABLE"


class PolicyViolationError(DomainError):
    code = "POLICY_VIOLATION"


class ProviderTimeoutError(DomainError):
    code = "PROVIDER_TIMEOUT"
