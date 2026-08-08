from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import ActionStatus, EvaluationRunStatus, WorkflowStatus
from app.models import AgentRun, AuditLog, EvaluationRun, OutboxEvent, ServiceAction, WorkflowRun


class MetricsService:
    """Returns bounded aggregates for the staff dashboard without exposing raw content."""

    def dashboard(self, session: Session) -> dict[str, Any]:
        latest_evaluation = session.scalar(
            select(EvaluationRun).order_by(
                EvaluationRun.completed_at.desc(), EvaluationRun.started_at.desc()
            )
        )
        workflow_counts = {
            status.value: int(
                session.scalar(
                    select(func.count())
                    .select_from(WorkflowRun)
                    .where(WorkflowRun.status == status)
                )
                or 0
            )
            for status in (
                WorkflowStatus.SUCCEEDED,
                WorkflowStatus.ESCALATED,
                WorkflowStatus.FAILED,
            )
        }
        action_counts = {
            status.value: int(
                session.scalar(
                    select(func.count())
                    .select_from(ServiceAction)
                    .where(ServiceAction.status == status)
                )
                or 0
            )
            for status in (
                ActionStatus.PENDING_APPROVAL,
                ActionStatus.QUEUED,
                ActionStatus.COMPLETED,
                ActionStatus.FAILED,
            )
        }
        outbox_retries = int(
            session.scalar(
                select(func.count()).select_from(OutboxEvent).where(OutboxEvent.attempts > 1)
            )
            or 0
        )
        average_latency = session.scalar(select(func.avg(AgentRun.latency_ms)))
        latest_summary = latest_evaluation.summary if latest_evaluation else {}
        return {
            "generated_at": datetime.now(UTC),
            "workflow_counts": workflow_counts,
            "action_counts": action_counts,
            "outbox_retry_count": outbox_retries,
            "audit_event_count": int(
                session.scalar(select(func.count()).select_from(AuditLog)) or 0
            ),
            "agent_latency_avg_ms": round(float(average_latency or 0), 2),
            "evaluation": {
                "run_id": str(latest_evaluation.id) if latest_evaluation else None,
                "status": latest_evaluation.status.value if latest_evaluation else "not_run",
                "suite_version": latest_evaluation.suite_version if latest_evaluation else None,
                "summary": latest_summary,
            },
            "slo_status": self._slo_status(latest_evaluation),
        }

    @staticmethod
    def _slo_status(latest_evaluation: EvaluationRun | None) -> str:
        if latest_evaluation is None:
            return "attention"
        if latest_evaluation.status is EvaluationRunStatus.BLOCKED:
            return "blocked"
        if latest_evaluation.status is EvaluationRunStatus.ATTENTION:
            return "attention"
        return "healthy"
