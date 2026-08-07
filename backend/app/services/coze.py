import hashlib
import hmac


def verify_coze_signature(*, raw_body: bytes, signature: str | None, secret: str) -> bool:
    """Verify an HMAC-SHA256 webhook signature without parsing untrusted content first."""

    if not signature:
        return False
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
