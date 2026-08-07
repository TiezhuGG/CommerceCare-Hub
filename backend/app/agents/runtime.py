import time
from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.core.errors import StructuredProviderError
from app.providers.structured import StructuredGenerationRequest, StructuredOutputProvider

OutputModel = TypeVar("OutputModel", bound=BaseModel)


@dataclass(frozen=True)
class PromptReference:
    key: str
    version: str
    template: str


@dataclass(frozen=True)
class AgentExecution:
    output: BaseModel | None
    attempt_count: int
    latency_ms: int
    validation_error_codes: list[str]


class StructuredAgentRuntime:
    """Validates one structured response retry and never manufactures a fallback result."""

    def __init__(self, provider: StructuredOutputProvider) -> None:
        self.provider = provider

    def invoke(
        self,
        *,
        task: str,
        prompt: PromptReference,
        payload: dict[str, Any],
        output_model: type[OutputModel],
    ) -> AgentExecution:
        started_at = time.perf_counter()
        errors: list[str] = []
        for attempt in range(1, 3):
            try:
                raw = self.provider.generate(
                    StructuredGenerationRequest(
                        task=task,
                        prompt_key=prompt.key,
                        prompt_version=prompt.version,
                        prompt_template=prompt.template,
                        input=payload,
                        retry_feedback="; ".join(errors) if errors else None,
                    )
                )
                return AgentExecution(
                    output=output_model.model_validate(raw),
                    attempt_count=attempt,
                    latency_ms=int((time.perf_counter() - started_at) * 1_000),
                    validation_error_codes=errors,
                )
            except ValidationError as error:
                errors = [item["type"] for item in error.errors()[:5]]
            except StructuredProviderError as error:
                errors = [error.code]
        return AgentExecution(
            output=None,
            attempt_count=2,
            latency_ms=int((time.perf_counter() - started_at) * 1_000),
            validation_error_codes=errors or ["provider_error"],
        )
