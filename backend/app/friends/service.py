import asyncio
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.accounts.schemas import UserPublic
from app.models import FriendRequest, Friendship, User

USERNAME_LOOKUP_ERROR = "User not found"


class FriendRequestNotFoundError(Exception):
    """Raised when a friend request does not exist."""


class FriendRequestForbiddenError(Exception):
    """Raised when the current user cannot access a friend request."""


class FriendRequestConflictError(Exception):
    """Raised when a friend request cannot be processed in its current state."""


class UserNotFoundError(Exception):
    """Raised when a recipient cannot be found."""


class SelfFriendRequestError(Exception):
    """Raised when a user tries to befriend themselves."""


class AlreadyFriendsError(Exception):
    """Raised when users are already friends."""


class PendingRequestExistsError(Exception):
    """Raised when an identical pending request already exists."""


async def _get_user_by_username(session: AsyncSession, username: str) -> User | None:
    result = await session.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def _get_user_by_id(session: AsyncSession, user_id) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def resolve_recipient(
    session: AsyncSession,
    *,
    username: str | None = None,
    user_id=None,
    recipient_id=None,
) -> User | None:
    if username is not None:
        return await _get_user_by_username(session, username.strip())
    target_id = user_id if user_id is not None else recipient_id
    if target_id is None:
        return None
    return await _get_user_by_id(session, target_id)


async def _get_request(
    session: AsyncSession,
    requester_id,
    recipient_id,
) -> FriendRequest | None:
    result = await session.execute(
        select(FriendRequest)
        .options(
            selectinload(FriendRequest.requester),
            selectinload(FriendRequest.recipient),
        )
        .where(
            FriendRequest.requester_id == requester_id,
            FriendRequest.recipient_id == recipient_id,
        )
    )
    return result.scalar_one_or_none()


async def _get_request_by_id(
    session: AsyncSession,
    request_id,
) -> FriendRequest | None:
    result = await session.execute(
        select(FriendRequest)
        .options(
            selectinload(FriendRequest.requester),
            selectinload(FriendRequest.recipient),
        )
        .where(FriendRequest.id == request_id)
    )
    return result.scalar_one_or_none()


async def _get_request_by_id_for_update(
    session: AsyncSession,
    request_id,
) -> FriendRequest | None:
    result = await session.execute(
        select(FriendRequest)
        .options(
            selectinload(FriendRequest.requester),
            selectinload(FriendRequest.recipient),
        )
        .where(FriendRequest.id == request_id)
        .with_for_update()
    )
    return result.scalar_one_or_none()


async def _get_friendship(session: AsyncSession, first_id, second_id):
    low, high = sorted((first_id, second_id))
    result = await session.execute(
        select(Friendship).where(
            Friendship.user_id == low,
            Friendship.friend_id == high,
        )
    )
    return result.scalar_one_or_none()


async def _lock_friend_pair(session: AsyncSession, first_id, second_id) -> None:
    # A transaction-level advisory lock serializes all friend operations for
    # the same unordered user pair without adding schema or infrastructure.
    lock_key = f"{min(str(first_id), str(second_id))}:{max(str(first_id), str(second_id))}"
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
        {"lock_key": lock_key},
    )


async def _ensure_friendship(session: AsyncSession, first_id, second_id) -> Friendship:
    low, high = sorted((first_id, second_id))
    existing = await _get_friendship(session, low, high)
    if existing is not None:
        return existing

    friendship = Friendship(user_id=low, friend_id=high)
    session.add(friendship)
    try:
        async with session.begin_nested():
            await session.flush()
        return friendship
    except IntegrityError:
        existing = await _get_friendship(session, low, high)
        if existing is not None:
            return existing
        raise


async def _auto_accept_reverse_request(
    session: AsyncSession,
    reverse_request: FriendRequest,
) -> FriendRequest:
    now = datetime.now(timezone.utc)
    reverse_request.status = "accepted"
    reverse_request.updated_at = now

    await _ensure_friendship(
        session,
        reverse_request.requester_id,
        reverse_request.recipient_id,
    )

    refreshed = await _get_request_by_id(session, reverse_request.id)
    if refreshed is not None:
        if refreshed.status != "accepted":
            refreshed.status = "accepted"
            refreshed.updated_at = now
        reverse_request = refreshed

    await session.flush()
    await session.commit()
    return reverse_request


async def send_friend_request(
    session: AsyncSession,
    requester: User,
    *,
    username: str | None = None,
    user_id=None,
    recipient_id=None,
) -> tuple[FriendRequest, str]:
    """Create, resend, or auto-accept a friend request."""
    recipient = await resolve_recipient(
        session,
        username=username,
        user_id=user_id,
        recipient_id=recipient_id,
    )
    if recipient is None:
        raise UserNotFoundError(USERNAME_LOOKUP_ERROR)
    requester_pk = requester.id
    recipient_pk = recipient.id

    if recipient_pk == requester_pk:
        raise SelfFriendRequestError("Cannot send a friend request to yourself")

    if await _friendship_exists(session, requester_pk, recipient_pk):
        raise AlreadyFriendsError("Users are already friends")

    now = datetime.now(timezone.utc)

    await _lock_friend_pair(session, requester_pk, recipient_pk)

    if await _friendship_exists(session, requester_pk, recipient_pk):
        raise AlreadyFriendsError("Users are already friends")

    existing = await _get_request(session, requester_pk, recipient_pk)
    if existing is not None:
        if existing.status == "pending":
            raise PendingRequestExistsError("Friend request already pending")
        if existing.status == "accepted":
            await _ensure_friendship(session, requester_pk, recipient_pk)
            await session.commit()
            raise AlreadyFriendsError("Users are already friends")
        if existing.status == "rejected":
            reverse = await _get_request(session, recipient_pk, requester_pk)
            if reverse is not None and reverse.status == "pending":
                accepted_request = await _auto_accept_reverse_request(session, reverse)
                return accepted_request, "accepted"

            existing.status = "pending"
            existing.created_at = now
            existing.updated_at = now
            try:
                async with session.begin_nested():
                    await session.flush()
            except IntegrityError:
                await session.rollback()
                await _lock_friend_pair(session, requester_pk, recipient_pk)
                existing = await _get_request(session, requester_pk, recipient_pk)
                if existing is not None:
                    if existing.status == "pending":
                        raise PendingRequestExistsError("Friend request already pending")
                    if existing.status == "accepted":
                        await _ensure_friendship(session, requester_pk, recipient_pk)
                        await session.commit()
                        raise AlreadyFriendsError("Users are already friends")
                    if existing.status == "rejected":
                        existing.status = "pending"
                        existing.created_at = now
                        existing.updated_at = now
                        await session.flush()
                        await session.commit()
                        return existing, "resent"
                reverse = await _get_request(session, recipient_pk, requester_pk)
                if reverse is not None and reverse.status == "pending":
                    accepted_request = await _auto_accept_reverse_request(session, reverse)
                    return accepted_request, "accepted"
                if reverse is not None and reverse.status == "accepted":
                    await _ensure_friendship(session, requester_pk, recipient_pk)
                    await session.commit()
                    raise AlreadyFriendsError("Users are already friends")
                if await _friendship_exists(session, requester_pk, recipient_pk):
                    raise AlreadyFriendsError("Users are already friends")
                raise FriendRequestConflictError("Friend request could not be created")
            await session.commit()
            return existing, "resent"

    reverse = await _get_request(session, recipient_pk, requester_pk)
    if reverse is not None and reverse.status == "pending":
        accepted_request = await _auto_accept_reverse_request(session, reverse)
        return accepted_request, "accepted"

    if reverse is not None and reverse.status == "accepted":
        await _ensure_friendship(session, requester_pk, recipient_pk)
        await session.commit()
        raise AlreadyFriendsError("Users are already friends")

    friend_request = FriendRequest(
        requester_id=requester_pk,
        recipient_id=recipient_pk,
        status="pending",
    )
    session.add(friend_request)

    try:
        async with session.begin_nested():
            await session.flush()
            await session.refresh(
                friend_request,
                attribute_names=["requester", "recipient"],
            )
        await session.commit()
        return friend_request, "created"
    except IntegrityError:
        await session.rollback()
        await _lock_friend_pair(session, requester_pk, recipient_pk)
        existing = await _get_request(session, requester_pk, recipient_pk)
        if existing is not None:
            if existing.status == "pending":
                raise PendingRequestExistsError("Friend request already pending")
            if existing.status == "accepted":
                await _ensure_friendship(session, requester_pk, recipient_pk)
                await session.commit()
                raise AlreadyFriendsError("Users are already friends")
            if existing.status == "rejected":
                existing.status = "pending"
                existing.created_at = now
                existing.updated_at = now
                await session.flush()
                await session.commit()
                return existing, "resent"

        reverse = await _get_request(session, recipient_pk, requester_pk)
        if reverse is not None and reverse.status == "pending":
            accepted_request = await _auto_accept_reverse_request(session, reverse)
            return accepted_request, "accepted"
        if reverse is not None and reverse.status == "accepted":
            await _ensure_friendship(session, requester_pk, recipient_pk)
            await session.commit()
            raise AlreadyFriendsError("Users are already friends")

        if await _friendship_exists(session, requester_pk, recipient_pk):
            raise AlreadyFriendsError("Users are already friends")

        raise FriendRequestConflictError("Friend request could not be created")



async def _friendship_exists(session: AsyncSession, first_id, second_id) -> bool:
    friendship = await _get_friendship(session, first_id, second_id)
    return friendship is not None


async def list_incoming_requests(
    session: AsyncSession,
    current_user: User,
) -> list[FriendRequest]:
    result = await session.execute(
        select(FriendRequest)
        .options(
            selectinload(FriendRequest.requester),
            selectinload(FriendRequest.recipient),
        )
        .where(
            FriendRequest.recipient_id == current_user.id,
            FriendRequest.status == "pending",
        )
        .order_by(FriendRequest.created_at.desc())
    )
    return list(result.scalars().all())


async def list_outgoing_requests(
    session: AsyncSession,
    current_user: User,
) -> list[FriendRequest]:
    result = await session.execute(
        select(FriendRequest)
        .options(
            selectinload(FriendRequest.requester),
            selectinload(FriendRequest.recipient),
        )
        .where(
            FriendRequest.requester_id == current_user.id,
            FriendRequest.status == "pending",
        )
        .order_by(FriendRequest.created_at.desc())
    )
    return list(result.scalars().all())


async def accept_friend_request(
    session: AsyncSession,
    request_id,
    current_user: User,
) -> FriendRequest:
    friend_request = await _get_request_by_id_for_update(session, request_id)
    if friend_request is None:
        raise FriendRequestNotFoundError("Friend request not found")
    if friend_request.recipient_id != current_user.id:
        raise FriendRequestForbiddenError("You cannot accept this friend request")
    if friend_request.status != "pending":
        raise FriendRequestConflictError("Friend request is not pending")

    await _lock_friend_pair(
        session,
        friend_request.requester_id,
        friend_request.recipient_id,
    )
    await _ensure_friendship(
        session,
        friend_request.requester_id,
        friend_request.recipient_id,
    )

    # _ensure_friendship may roll back the transaction on a conflict.
    friend_request = await _get_request_by_id(session, request_id)
    if friend_request is None:
        raise FriendRequestNotFoundError("Friend request not found")
    if friend_request.status != "pending":
        if friend_request.status == "accepted":
            return friend_request
        raise FriendRequestConflictError("Friend request is not pending")

    now = datetime.now(timezone.utc)
    reverse = await _get_request(
        session,
        friend_request.recipient_id,
        friend_request.requester_id,
    )
    if reverse is not None and reverse.status == "pending":
        reverse.status = "rejected"
        reverse.updated_at = now

    friend_request.status = "accepted"
    friend_request.updated_at = now
    await session.flush()
    await session.commit()
    return friend_request


async def reject_friend_request(
    session: AsyncSession,
    request_id,
    current_user: User,
) -> None:
    friend_request = await _get_request_by_id_for_update(session, request_id)
    if friend_request is None:
        raise FriendRequestNotFoundError("Friend request not found")
    if friend_request.recipient_id != current_user.id:
        raise FriendRequestForbiddenError("You cannot reject this friend request")
    if friend_request.status != "pending":
        raise FriendRequestConflictError("Friend request is not pending")

    await _lock_friend_pair(
        session,
        friend_request.requester_id,
        friend_request.recipient_id,
    )
    friend_request.status = "rejected"
    friend_request.updated_at = datetime.now(timezone.utc)
    await session.flush()
    await session.commit()


async def list_friends(session: AsyncSession, current_user: User) -> list[User]:
    friend_ids = (
        select(Friendship.friend_id).where(Friendship.user_id == current_user.id)
    ).union(
        select(Friendship.user_id).where(Friendship.friend_id == current_user.id)
    )
    result = await session.execute(
        select(User).where(User.id.in_(friend_ids)).order_by(User.username)
    )
    return list(result.scalars().all())


async def revoke_all_friendships_for_user(session: AsyncSession, user_id) -> None:
    await session.execute(
        delete(Friendship).where(
            (Friendship.user_id == user_id) | (Friendship.friend_id == user_id)
        )
    )
    await session.commit()