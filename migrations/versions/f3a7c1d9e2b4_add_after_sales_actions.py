"""add durable after-sales action workflow

Revision ID: f3a7c1d9e2b4
Revises: 70c061baad39
Create Date: 2026-08-05 21:15:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f3a7c1d9e2b4"
down_revision: str | Sequence[str] | None = "70c061baad39"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "service_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_run_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column(
            "action_type",
            sa.Enum(
                "REFUND",
                "RETURN",
                "ADDRESS_UPDATE",
                "DAMAGED_ITEM",
                name="actiontype",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING_APPROVAL",
                "APPROVED",
                "QUEUED",
                "EXECUTING",
                "COMPLETED",
                "REJECTED",
                "FAILED",
                name="actionstatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("payload_redacted", sa.JSON(), nullable=False),
        sa.Column("external_reference", sa.String(length=128), nullable=True),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["order_id"], ["orders.id"], name=op.f("fk_service_actions_order_id_orders")
        ),
        sa.ForeignKeyConstraint(
            ["requested_by"], ["users.id"], name=op.f("fk_service_actions_requested_by_users")
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"], ["tickets.id"], name=op.f("fk_service_actions_ticket_id_tickets")
        ),
        sa.ForeignKeyConstraint(
            ["workflow_run_id"],
            ["workflow_runs.id"],
            name=op.f("fk_service_actions_workflow_run_id_workflow_runs"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_service_actions")),
        sa.UniqueConstraint("ticket_id", name=op.f("uq_service_actions_ticket_id")),
        sa.UniqueConstraint("workflow_run_id", name=op.f("uq_service_actions_workflow_run_id")),
        sa.UniqueConstraint(
            "action_type",
            "order_id",
            "idempotency_key",
            name=op.f("uq_service_actions_action_type"),
        ),
    )
    op.create_index(
        op.f("ix_service_actions_order_id"), "service_actions", ["order_id"], unique=False
    )
    with op.batch_alter_table("approval_requests") as batch_op:
        batch_op.add_column(sa.Column("action_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            op.f("fk_approval_requests_action_id_service_actions"),
            "service_actions",
            ["action_id"],
            ["id"],
        )
        batch_op.create_unique_constraint(op.f("uq_approval_requests_action_id"), ["action_id"])
    with op.batch_alter_table("outbox_events") as batch_op:
        batch_op.add_column(
            sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0"))
        )
        batch_op.add_column(sa.Column("last_error_code", sa.String(length=64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("outbox_events") as batch_op:
        batch_op.drop_column("last_error_code")
        batch_op.drop_column("attempts")
    with op.batch_alter_table("approval_requests") as batch_op:
        batch_op.drop_constraint(op.f("uq_approval_requests_action_id"), type_="unique")
        batch_op.drop_constraint(
            op.f("fk_approval_requests_action_id_service_actions"), type_="foreignkey"
        )
        batch_op.drop_column("action_id")
    op.drop_index(op.f("ix_service_actions_order_id"), table_name="service_actions")
    op.drop_table("service_actions")
