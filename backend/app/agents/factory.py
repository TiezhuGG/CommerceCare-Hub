from app.agents.runtime import StructuredAgentRuntime
from app.agents.service import StructuredAgentService
from app.core.config import Settings, get_settings
from app.providers.structured import (
    DeterministicMockStructuredProvider,
    OpenAICompatibleStructuredProvider,
    StructuredOutputProvider,
)


def build_structured_provider(settings: Settings | None = None) -> StructuredOutputProvider:
    resolved_settings = settings or get_settings()
    if (
        resolved_settings.structured_provider == "openai_compatible"
        and resolved_settings.openai_compatible_api_key
        and resolved_settings.openai_compatible_base_url
    ):
        return OpenAICompatibleStructuredProvider(
            base_url=resolved_settings.openai_compatible_base_url,
            api_key=resolved_settings.openai_compatible_api_key,
            model_name=resolved_settings.openai_compatible_model,
            timeout_seconds=resolved_settings.structured_provider_timeout_seconds,
        )
    return DeterministicMockStructuredProvider()


def build_agent_service(settings: Settings | None = None) -> StructuredAgentService:
    return StructuredAgentService(StructuredAgentRuntime(build_structured_provider(settings)))
