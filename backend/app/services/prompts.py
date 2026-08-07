from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.runtime import PromptReference
from app.models import PromptVersion


class PromptRegistry:
    """Resolves active versioned prompts without exposing prompt content in audit records."""

    def resolve(self, session: Session, prompt_key: str) -> PromptReference | None:
        prompt = session.scalar(
            select(PromptVersion)
            .where(PromptVersion.prompt_key == prompt_key)
            .where(PromptVersion.active.is_(True))
            .order_by(PromptVersion.version.desc())
        )
        if prompt is None:
            return None
        return PromptReference(
            key=prompt.prompt_key, version=prompt.version, template=prompt.template
        )
