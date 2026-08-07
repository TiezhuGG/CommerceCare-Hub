import json
import re
import time
import urllib.error
import urllib.request
from collections.abc import Mapping
from typing import Any, Protocol

from pydantic import BaseModel, Field

from app.core.errors import StructuredProviderError

ORDER_NUMBER_PATTERN = re.compile(r"\bCC-\d{4,}\b", re.IGNORECASE)
INJECTION_MARKERS = (
    "ignore previous",
    "system prompt",
    "developer message",
    "忽略之前",
    "系统提示",
)


class StructuredGenerationRequest(BaseModel):
    task: str
    prompt_key: str
    prompt_version: str
    prompt_template: str
    input: dict[str, Any] = Field(default_factory=dict)
    retry_feedback: str | None = None


class StructuredOutputProvider(Protocol):
    provider_name: str
    model_name: str

    def generate(self, request: StructuredGenerationRequest) -> dict[str, Any]: ...


class DeterministicMockStructuredProvider:
    """Offline provider for schema-bound agent tests and local demos."""

    provider_name = "deterministic_mock"
    model_name = "rule-based-v1"

    def generate(self, request: StructuredGenerationRequest) -> dict[str, Any]:
        data = request.input
        if request.task == "router":
            message = str(data.get("message", ""))
            normalized = message.lower()
            order_match = ORDER_NUMBER_PATTERN.search(message)
            order_number = order_match.group(0).upper() if order_match else None
            injection = any(marker in normalized for marker in INJECTION_MARKERS)
            delayed = any(
                token in normalized for token in ("delay", "late", "延迟", "没到", "晚到")
            )
            return {
                "intent": "delivery_delay"
                if order_number and delayed
                else "order_status"
                if order_number
                else "unknown",
                "order_number": order_number,
                "missing_fields": [] if order_number else ["order_number"],
                "requires_evidence": delayed,
                "sentiment": "urgent"
                if "urgent" in normalized or "着急" in normalized
                else "frustrated"
                if delayed
                else "neutral",
                "urgency": "high" if "urgent" in normalized or "着急" in normalized else "normal",
                "risk_tags": ["prompt_injection_detected"] if injection else [],
                "confidence": 1.0,
                "decision_summary": "Deterministic classification from the untrusted message.",
            }
        if request.task == "context":
            facts = list(data.get("facts", []))
            return {
                "facts": facts,
                "missing_facts": list(data.get("missing_facts", [])),
                "conflicting_facts": list(data.get("conflicting_facts", [])),
                "decision_summary": "Read-only provider facts were normalized.",
            }
        if request.task == "policy":
            evidence = list(data.get("evidence", []))
            return {
                "evidence": evidence,
                "applicable": bool(evidence),
                "conflict_detected": len(evidence) > 1,
                "decision_summary": (
                    "Effective policy candidates were assessed without executing their text."
                ),
            }
        if request.task == "planner":
            return {
                "options": [
                    {
                        "title": "Provide grounded status update",
                        "rationale": "Use observed order facts and applicable evidence.",
                        "required_inputs": [],
                        "risk_summary": "Read-only response; no external action.",
                        "requires_approval": False,
                    }
                ],
                "decision_summary": "A non-executable resolution option was prepared.",
            }
        if request.task == "risk":
            if data.get("prompt_injection_detected"):
                return {
                    "decision": "escalate",
                    "reason_codes": ["PROMPT_INJECTION_DETECTED"],
                    "decision_summary": "Untrusted instructions require human review.",
                }
            if data.get("policy_conflict"):
                return {
                    "decision": "escalate",
                    "reason_codes": ["POLICY_CONFLICT"],
                    "decision_summary": (
                        "Conflicting effective policy evidence requires human review."
                    ),
                }
            if data.get("policy_missing"):
                return {
                    "decision": "escalate",
                    "reason_codes": ["POLICY_EVIDENCE_MISSING"],
                    "decision_summary": (
                        "Required policy evidence is unavailable for a customer claim."
                    ),
                }
            if float(data.get("confidence", 0)) < 0.75:
                return {
                    "decision": "escalate",
                    "reason_codes": ["LOW_CONFIDENCE"],
                    "decision_summary": "Low-confidence analysis requires human review.",
                }
            return {
                "decision": "allow",
                "reason_codes": [],
                "decision_summary": "Read-only workflow is allowed.",
            }
        if request.task == "reply":
            return {
                "customer_reply": str(data["customer_reply"]),
                "cited_sources": list(data.get("cited_sources", [])),
                "next_step": str(
                    data.get("next_step", "Reply to this conversation if you need more help.")
                ),
            }
        raise StructuredProviderError(f"Unsupported deterministic task: {request.task}")


class ScriptedStructuredOutputProvider:
    """Inject deterministic malformed or delayed outputs while retaining a mock fallback."""

    provider_name = "scripted_mock"
    model_name = "scripted-v1"

    def __init__(self, scripted_outputs: Mapping[str, list[dict[str, Any]]] | None = None) -> None:
        self._scripted_outputs = {
            key: list(values) for key, values in (scripted_outputs or {}).items()
        }
        self._fallback = DeterministicMockStructuredProvider()

    def generate(self, request: StructuredGenerationRequest) -> dict[str, Any]:
        outputs = self._scripted_outputs.get(request.task)
        if outputs:
            return outputs.pop(0)
        return self._fallback.generate(request)


class OpenAICompatibleStructuredProvider:
    """Optional JSON-object adapter; never selected by default in local runs."""

    provider_name = "openai_compatible"

    def __init__(
        self, *, base_url: str, api_key: str, model_name: str, timeout_seconds: float = 15
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self.model_name = model_name
        self._timeout_seconds = timeout_seconds

    def generate(self, request: StructuredGenerationRequest) -> dict[str, Any]:
        payload = {
            "model": self.model_name,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": request.prompt_template},
                {"role": "user", "content": json.dumps(request.input, ensure_ascii=False)},
            ],
        }
        encoded = json.dumps(payload).encode("utf-8")
        http_request = urllib.request.Request(
            f"{self._base_url}/chat/completions",
            data=encoded,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        started_at = time.monotonic()
        try:
            with urllib.request.urlopen(http_request, timeout=self._timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            raise StructuredProviderError("OpenAI-compatible provider request failed") from error
        if time.monotonic() - started_at > self._timeout_seconds:
            raise StructuredProviderError("OpenAI-compatible provider exceeded timeout")
        try:
            content = body["choices"][0]["message"]["content"]
            parsed = json.loads(content)
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise StructuredProviderError(
                "OpenAI-compatible provider returned invalid JSON"
            ) from error
        if not isinstance(parsed, dict):
            raise StructuredProviderError("OpenAI-compatible provider result was not an object")
        return parsed
