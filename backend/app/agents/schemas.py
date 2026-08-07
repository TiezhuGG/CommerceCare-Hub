import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.core.enums import Intent, RiskDecision


class RouterDecision(BaseModel):
    intent: Intent
    order_number: str | None = None
    missing_fields: list[str] = Field(default_factory=list)
    requires_evidence: bool
    sentiment: Literal["neutral", "frustrated", "urgent"]
    urgency: Literal["low", "normal", "high"]
    risk_tags: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    decision_summary: str


class ObservedFact(BaseModel):
    fact_type: str
    value: str
    source_type: str
    source_id: str
    observed_at: datetime


class ContextResult(BaseModel):
    facts: list[ObservedFact] = Field(default_factory=list)
    missing_facts: list[str] = Field(default_factory=list)
    conflicting_facts: list[str] = Field(default_factory=list)
    decision_summary: str


class PolicyEvidence(BaseModel):
    document_id: str
    version: str
    effective_time: datetime
    matched_section: str
    relevance_score: int = Field(ge=0, le=100)


class PolicyResult(BaseModel):
    evidence: list[PolicyEvidence] = Field(default_factory=list)
    applicable: bool
    conflict_detected: bool
    decision_summary: str


class ResolutionOption(BaseModel):
    title: str
    rationale: str
    required_inputs: list[str] = Field(default_factory=list)
    risk_summary: str
    requires_approval: bool


class ResolutionPlan(BaseModel):
    options: list[ResolutionOption] = Field(min_length=1, max_length=3)
    decision_summary: str


class RiskDecisionResult(BaseModel):
    decision: RiskDecision
    reason_codes: list[str] = Field(default_factory=list)
    decision_summary: str


class ReplyResult(BaseModel):
    customer_reply: str = Field(min_length=1, max_length=2_000)
    cited_sources: list[str] = Field(default_factory=list)
    next_step: str


class CozeCustomerIntakeRequest(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    correlation_id: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=2_000)


class CozeCustomerIntakeResponse(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    correlation_id: str
    intent: Intent
    order_number: str | None
    missing_fields: list[str]
    requires_evidence: bool
    safe_outcome: RiskDecision
    audit_id: uuid.UUID
