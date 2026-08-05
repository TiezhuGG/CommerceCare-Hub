"""add conversation message idempotency

Revision ID: 70c061baad39
Revises: 15110a84259c
Create Date: 2026-08-05 20:18:21.846263
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "70c061baad39"
down_revision: str | Sequence[str] | None = "15110a84259c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("messages") as batch_op:
        batch_op.add_column(sa.Column("client_message_id", sa.String(length=64), nullable=True))
        batch_op.create_unique_constraint(
            "uq_messages_conversation_id", ["conversation_id", "client_message_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("messages") as batch_op:
        batch_op.drop_constraint("uq_messages_conversation_id", type_="unique")
        batch_op.drop_column("client_message_id")
