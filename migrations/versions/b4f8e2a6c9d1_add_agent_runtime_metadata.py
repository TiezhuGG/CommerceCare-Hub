"""add structured agent runtime metadata

Revision ID: b4f8e2a6c9d1
Revises: f3a7c1d9e2b4
Create Date: 2026-08-08 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b4f8e2a6c9d1"
down_revision: str | Sequence[str] | None = "f3a7c1d9e2b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("agent_runs") as batch_op:
        batch_op.add_column(sa.Column("provider_name", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("model_name", sa.String(length=128), nullable=True))
        batch_op.add_column(
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default=sa.text("1"))
        )


def downgrade() -> None:
    with op.batch_alter_table("agent_runs") as batch_op:
        batch_op.drop_column("attempt_count")
        batch_op.drop_column("model_name")
        batch_op.drop_column("provider_name")
