import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Conversation(Base):
    """A private one-to-one conversation between two users."""

    __tablename__ = "conversations"

    __table_args__ = (
        CheckConstraint(
            "user_one_id < user_two_id",
            name="ck_conversations_ordered_participants",
        ),
        UniqueConstraint(
            "user_one_id",
            "user_two_id",
            name="uq_conversations_participants",
        ),
        Index("ix_conversations_user_two_id", "user_two_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_one_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_two_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user_one: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_one_id],
        lazy="raise",
    )
    user_two: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_two_id],
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"Conversation(id={self.id!r})"
