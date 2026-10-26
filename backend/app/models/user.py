import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

USERNAME_MAX_LENGTH = 32
DISPLAY_NAME_MAX_LENGTH = 100


class User(Base):
    """A registered Untexted user."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("username", name="uq_users_username"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    username: Mapped[str] = mapped_column(
        String(USERNAME_MAX_LENGTH),
        nullable=False,
    )
    display_name: Mapped[str] = mapped_column(
        String(DISPLAY_NAME_MAX_LENGTH),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    # SQLAlchemy emits now() on UPDATE, so PostgreSQL refreshes the value.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
