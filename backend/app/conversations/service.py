from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.friends.service import (
    UserNotFoundError,
    friendship_exists,
    lock_user_pair,
    resolve_recipient,
)
from app.models import Conversation, User

USERNAME_LOOKUP_ERROR = "User not found"


class SelfConversationError(Exception):
    """Raised when a user tries to create a conversation with themselves."""


class NotFriendsError(Exception):
    """Raised when users are not friends."""


class ConversationNotFoundError(Exception):
    """Raised when a conversation does not exist."""


class ConversationConflictError(Exception):
    """Raised when a conversation cannot be created or read consistently."""


async def _get_conversation_by_id(
    session: AsyncSession,
    conversation_id,
) -> Conversation | None:
    result = await session.execute(
        select(Conversation)
        .options(
            selectinload(Conversation.user_one),
            selectinload(Conversation.user_two),
        )
        .where(Conversation.id == conversation_id)
    )
    return result.scalar_one_or_none()


async def _get_conversation_by_participants(
    session: AsyncSession,
    first_id,
    second_id,
) -> Conversation | None:
    low, high = sorted((first_id, second_id))
    result = await session.execute(
        select(Conversation)
        .options(
            selectinload(Conversation.user_one),
            selectinload(Conversation.user_two),
        )
        .where(
            Conversation.user_one_id == low,
            Conversation.user_two_id == high,
        )
    )
    return result.scalar_one_or_none()


async def get_or_create_conversation(
    session: AsyncSession,
    current_user: User,
    *,
    username: str | None = None,
    user_id: Any = None,
    recipient_id: Any = None,
) -> tuple[Conversation, bool]:
    """Return an existing conversation or create one between friends."""
    recipient = await resolve_recipient(
        session,
        username=username,
        user_id=user_id,
        recipient_id=recipient_id,
    )
    if recipient is None:
        raise UserNotFoundError(USERNAME_LOOKUP_ERROR)

    current_user_id = current_user.id
    target_user_id = recipient.id

    if target_user_id == current_user_id:
        raise SelfConversationError("Cannot create a conversation with yourself")

    existing = await _get_conversation_by_participants(
        session, current_user_id, target_user_id
    )
    if existing is not None:
        return existing, False

    if not await friendship_exists(session, current_user_id, target_user_id):
        raise NotFriendsError("Users must be friends to create a conversation")

    await lock_user_pair(session, current_user_id, target_user_id)

    existing = await _get_conversation_by_participants(
        session, current_user_id, target_user_id
    )
    if existing is not None:
        return existing, False

    if not await friendship_exists(session, current_user_id, target_user_id):
        raise NotFriendsError("Users must be friends to create a conversation")

    low, high = sorted((current_user_id, target_user_id))
    conversation = Conversation(user_one_id=low, user_two_id=high)
    session.add(conversation)

    try:
        async with session.begin_nested():
            await session.flush()
        await session.commit()
        created = await _get_conversation_by_id(session, conversation.id)
        if created is None:
            raise ConversationConflictError("Conversation could not be created")
        return created, True
    except IntegrityError:
        await session.rollback()
        await lock_user_pair(session, current_user_id, target_user_id)

        existing = await _get_conversation_by_participants(
            session, current_user_id, target_user_id
        )
        if existing is not None:
            return existing, False

        if not await friendship_exists(session, current_user_id, target_user_id):
            raise NotFriendsError("Users must be friends to create a conversation")

        raise ConversationConflictError("Conversation could not be created")


async def list_conversations(
    session: AsyncSession,
    current_user: User,
) -> list[Conversation]:
    """Return conversations where the current user is a participant."""
    result = await session.execute(
        select(Conversation)
        .options(
            selectinload(Conversation.user_one),
            selectinload(Conversation.user_two),
        )
        .where(
            (Conversation.user_one_id == current_user.id)
            | (Conversation.user_two_id == current_user.id)
        )
        .order_by(Conversation.created_at.asc(), Conversation.id.asc())
    )
    return list(result.scalars().all())


async def get_conversation(
    session: AsyncSession,
    conversation_id,
    current_user: User,
) -> Conversation:
    """Return a conversation if the current user is a participant."""
    conversation = await _get_conversation_by_id(session, conversation_id)
    if conversation is None:
        raise ConversationNotFoundError("Conversation not found")
    if current_user.id not in (conversation.user_one_id, conversation.user_two_id):
        raise ConversationNotFoundError("Conversation not found")
    return conversation
