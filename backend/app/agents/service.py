from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.runtime import AgentExecution, PromptReference, StructuredAgentRuntime
from app.services.prompts import PromptRegistry


@dataclass(frozen=True)
class AgentInvocation:
    prompt: PromptReference | None
    execution: AgentExecution


class StructuredAgentService:
    """Coordinates prompt resolution and schema validation, but never business writes."""

    def __init__(
        self, runtime: StructuredAgentRuntime, prompts: PromptRegistry | None = None
    ) -> None:
        self._runtime = runtime
        self._prompts = prompts or PromptRegistry()

    @property
    def provider_name(self) -> str:
        return self._runtime.provider.provider_name

    @property
    def model_name(self) -> str:
        return self._runtime.provider.model_name

    def invoke(
        self,
        session: Session,
        *,
        task: str,
        prompt_key: str,
        payload: dict[str, Any],
        output_model: type[BaseModel],
    ) -> AgentInvocation:
        prompt = self._prompts.resolve(session, prompt_key)
        if prompt is None:
            return AgentInvocation(
                prompt=None,
                execution=AgentExecution(
                    output=None,
                    attempt_count=0,
                    latency_ms=0,
                    validation_error_codes=["PROMPT_NOT_FOUND"],
                ),
            )
        return AgentInvocation(
            prompt=prompt,
            execution=self._runtime.invoke(
                task=task,
                prompt=prompt,
                payload=payload,
                output_model=output_model,
            ),
        )
