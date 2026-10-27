"""create conversations table

Revision ID: 20261027_0006
Revises: 20261026_0005
Create Date: 2026-10-27 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20261027_0006"
down_revision: Union[str, Sequence[str], None] = "20261026_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the conversations table."""
    op.create_table(
        "conversations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_one_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_two_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "user_one_id < user_two_id",
            name="ck_conversations_ordered_participants",
        ),
        sa.ForeignKeyConstraint(
            ["user_one_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_two_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_one_id",
            "user_two_id",
            name="uq_conversations_participants",
        ),
    )
    op.create_index(
        "ix_conversations_user_two_id",
        "conversations",
        ["user_two_id"],
    )


def downgrade() -> None:
    """Drop the conversations table."""
    op.drop_table("conversations")
