import re

EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
PHONE_PATTERN = re.compile(r"(?<!\d)1\d{10}(?!\d)")


def redact_customer_message(message: str) -> str:
    """Keep operational references while preventing common PII from entering transcript storage."""

    redacted = EMAIL_PATTERN.sub("[redacted-email]", message)
    return PHONE_PATTERN.sub("[redacted-phone]", redacted)
