"""add password hash to users

Revision ID: 20261026_0003
Revises: 20261026_0002
Create Date: 2026-10-26 21:26:20.579021

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261026_0003"
down_revision: Union[str, Sequence[str], None] = "20261026_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the required Argon2id password hash column."""
    # Registration did not exist before this revision, so there are no users
    # that would need a generated or migrated password hash.
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(length=255), nullable=False),
    )


def downgrade() -> None:
    """Remove the password hash column."""
    op.drop_column("users", "password_hash")
