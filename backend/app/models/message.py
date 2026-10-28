import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Message(Base):
    """A message stored in a private conversation."""

    __tablename__ = "messages"

    __table_args__ = (
        CheckConstraint("schema_version > 0", name="ck_messages_schema_version_positive"),
        Index("ix_messages_conversation_created_at_id", "conversation_id", "created_at", "id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(
        "type",
        String(32),
        nullable=False,
    )
    schema_version: Mapped[int] = mapped_column(
        nullable=False,
        server_default=text("1"),
        default=1,
    )
    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )
    reply_to_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        foreign_keys=[conversation_id],
        lazy="raise",
    )
    sender: Mapped["User"] = relationship(
        "User",
        foreign_keys=[sender_id],
        lazy="raise",
    )
    reply_to: Mapped["Message | None"] = relationship(
        "Message",
        remote_side=[id],
        foreign_keys=[reply_to_message_id],
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"Message(id={self.id!r}, type={self.type!r})"
