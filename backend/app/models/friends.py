import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FriendRequest(Base):
    """A directed friendship request between two users."""

    __tablename__ = "friend_requests"

    __table_args__ = (
        CheckConstraint(
            "requester_id <> recipient_id",
            name="ck_friend_requests_not_self",
        ),
        UniqueConstraint(
            "requester_id",
            "recipient_id",
            name="uq_friend_requests_requester_recipient",
        ),
        Index("ix_friend_requests_recipient_status", "recipient_id", "status"),
        Index("ix_friend_requests_requester_status", "requester_id", "status"),
        Index(
            "uq_pending_friend_request_pair",
            text("LEAST(requester_id, recipient_id)"),
            text("GREATEST(requester_id, recipient_id)"),
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    requester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    requester: Mapped["User"] = relationship(
        "User",
        foreign_keys=[requester_id],
        lazy="raise",
    )
    recipient: Mapped["User"] = relationship(
        "User",
        foreign_keys=[recipient_id],
        lazy="raise",
    )


class Friendship(Base):
    """A normalized, unique friendship between two users."""

    __tablename__ = "friendships"

    __table_args__ = (
        CheckConstraint("user_id < friend_id", name="ck_friendships_ordered_pair"),
        UniqueConstraint("user_id", "friend_id", name="uq_friendships_pair"),
        Index("ix_friendships_friend_id", "friend_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    friend_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )