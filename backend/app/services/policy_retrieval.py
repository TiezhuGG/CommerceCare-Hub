from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.agents.schemas import PolicyEvidence
from app.models import PolicyDocument


@dataclass(frozen=True)
class PolicyRetrievalResult:
    evidence: list[PolicyEvidence]
    conflict_detected: bool


class PolicyRetrievalService:
    """Read-only retrieval of effective, scoped policy metadata from untrusted documents."""

    def retrieve(
        self,
        session: Session,
        *,
        document_key: str,
        region: str = "CN",
        observed_at: datetime | None = None,
    ) -> PolicyRetrievalResult:
        now = observed_at or datetime.now(UTC)
        documents = session.scalars(
            select(PolicyDocument)
            .where(PolicyDocument.document_key == document_key)
            .where(PolicyDocument.effective_from <= now)
            .where(or_(PolicyDocument.effective_to.is_(None), PolicyDocument.effective_to > now))
            .order_by(PolicyDocument.effective_from.desc(), PolicyDocument.version.desc())
        ).all()
        scoped_documents = [
            document for document in documents if document.scope.get("region") in {None, region}
        ]
        evidence = [
            PolicyEvidence(
                document_id=str(document.id),
                version=document.version,
                effective_time=document.effective_from,
                matched_section=document.document_key,
                relevance_score=100,
            )
            for document in scoped_documents
        ]
        return PolicyRetrievalResult(evidence=evidence, conflict_detected=len(evidence) > 1)
