import base64
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.conversations.service import (
    ConversationNotFoundError,
    NotFriendsError,
    get_conversation,
)
from app.friends.service import friendship_exists
from app.models import Message, User


class MessageNotFoundError(Exception):
    """Raised when a message does not exist or is not accessible."""


class InvalidCursorError(Exception):
    """Raised when a message history cursor cannot be decoded."""


def _encode_cursor(created_at: datetime, message_id: UUID) -> str:
    raw = f"{created_at.isoformat()}|{message_id}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        padding = "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode((cursor + padding).encode("ascii")).decode("utf-8")
        created_at_text, message_id_text = raw.split("|", 1)
        created_at = datetime.fromisoformat(created_at_text)
        if created_at.tzinfo is None:
            raise ValueError("cursor timestamp must be timezone-aware")
        message_id = UUID(message_id_text)
    except (ValueError, TypeError) as exc:
        raise InvalidCursorError("Invalid message history cursor") from exc
    return created_at, message_id


async def _get_message_by_id(
    session: AsyncSession,
    message_id,
) -> Message | None:
    result = await session.execute(
        select(Message)
        .options(selectinload(Message.sender))
        .where(Message.id == message_id)
    )
    return result.scalar_one_or_none()


async def send_message(
    session: AsyncSession,
    conversation_id,
    current_user: User,
    payload: Any,
    *,
    reply_to_message_id=None,
) -> Message:
    """Send a validated message to a conversation."""
    conversation = await get_conversation(session, conversation_id, current_user)

    if not await friendship_exists(
        session, conversation.user_one_id, conversation.user_two_id
    ):
        raise NotFriendsError("Users must be friends to send messages")

    if reply_to_message_id is not None:
        reply = await _get_message_by_id(session, reply_to_message_id)
        if reply is None or reply.conversation_id != conversation.id:
            raise MessageNotFoundError("Reply target message not found")

    message = Message(
        conversation_id=conversation.id,
        sender_id=current_user.id,
        type=payload.type,
        schema_version=1,
        payload=payload.model_dump(mode="json"),
        reply_to_message_id=reply_to_message_id,
        created_at=datetime.now(timezone.utc),
    )
    session.add(message)
    await session.flush()

    created = await _get_message_by_id(session, message.id)
    if created is None:
        raise MessageNotFoundError("Message could not be created")
    await session.commit()
    return created


async def list_messages(
    session: AsyncSession,
    conversation_id,
    current_user: User,
    *,
    limit: int = 50,
    cursor: str | None = None,
) -> tuple[list[Message], str | None]:
    """Return one page of messages in chronological order."""
    conversation = await get_conversation(session, conversation_id, current_user)

    statement = (
        select(Message)
        .options(selectinload(Message.sender))
        .where(Message.conversation_id == conversation.id)
    )

    if cursor is not None:
        created_at, message_id = _decode_cursor(cursor)
        cursor_message = await _get_message_by_id(session, message_id)
        if cursor_message is None or cursor_message.conversation_id != conversation.id:
            raise InvalidCursorError("Invalid message history cursor")
        created_at = cursor_message.created_at
        message_id = cursor_message.id
        statement = statement.where(
            or_(
                Message.created_at < created_at,
                and_(
                    Message.created_at == created_at,
                    Message.id < message_id,
                ),
            )
        )

    statement = statement.order_by(
        Message.created_at.desc(), Message.id.desc()
    ).limit(limit + 1)

    result = await session.execute(statement)
    messages = list(result.scalars().all())
    has_more = len(messages) > limit
    page = messages[:limit]
    page.reverse()

    next_cursor = None
    if has_more and page:
        next_cursor = _encode_cursor(page[0].created_at, page[0].id)

    return page, next_cursor
