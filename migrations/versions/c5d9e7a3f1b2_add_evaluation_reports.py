"""add persisted evaluation reports

Revision ID: c5d9e7a3f1b2
Revises: b4f8e2a6c9d1
Create Date: 2026-08-08 11:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c5d9e7a3f1b2"
down_revision: str | Sequence[str] | None = "b4f8e2a6c9d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("suite_version", sa.String(length=32), nullable=False),
        sa.Column("provider_name", sa.String(length=64), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("judge_version", sa.String(length=32), nullable=False),
        sa.Column(
            "status",
            sa.Enum("running", "succeeded", "attention", "blocked", native_enum=False),
            nullable=False,
        ),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "evaluation_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("evaluation_run_id", sa.Uuid(), nullable=False),
        sa.Column("eval_case_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("scores", sa.JSON(), nullable=False),
        sa.Column("failure_codes", sa.JSON(), nullable=False),
        sa.Column("output_summary", sa.JSON(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["eval_case_id"], ["eval_cases.id"]),
        sa.ForeignKeyConstraint(["evaluation_run_id"], ["evaluation_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evaluation_run_id", "eval_case_id"),
    )
    op.create_index(
        "ix_evaluation_results_evaluation_run_id", "evaluation_results", ["evaluation_run_id"]
    )
    op.create_index("ix_evaluation_results_eval_case_id", "evaluation_results", ["eval_case_id"])


def downgrade() -> None:
    op.drop_index("ix_evaluation_results_eval_case_id", table_name="evaluation_results")
    op.drop_index("ix_evaluation_results_evaluation_run_id", table_name="evaluation_results")
    op.drop_table("evaluation_results")
    op.drop_table("evaluation_runs")
