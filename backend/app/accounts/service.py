import asyncio

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.passwords import (
    DUMMY_PASSWORD_HASH,
    hash_password,
    verify_password,
)
from app.accounts.schemas import RegisterRequest
from app.accounts.sessions import create_session, get_user_by_username
from app.models import User

USERNAME_UNIQUE_CONSTRAINT = "uq_users_username"


class UsernameAlreadyExistsError(Exception):
    """Raised when the username unique constraint is violated."""


class RegistrationError(Exception):
    """Raised when a user cannot be persisted."""


def _is_username_conflict(error: IntegrityError) -> bool:
    original = error.orig
    return (
        getattr(original, "constraint_name", None) == USERNAME_UNIQUE_CONSTRAINT
        or USERNAME_UNIQUE_CONSTRAINT in str(original)
    )


async def create_user(session: AsyncSession, request: RegisterRequest) -> User:
    """Hash the password and persist a new user, mapping database errors."""
    password_hash = await asyncio.to_thread(
        hash_password,
        request.password.get_secret_value(),
    )
    user = User(
        username=request.username,
        display_name=request.display_name,
        password_hash=password_hash,
    )
    session.add(user)

    try:
        await session.flush()
        await session.commit()
    except IntegrityError as error:
        is_username_conflict = _is_username_conflict(error)
        await session.rollback()
        if is_username_conflict:
            raise UsernameAlreadyExistsError from error
        raise RegistrationError from error
    except SQLAlchemyError as error:
        await session.rollback()
        raise RegistrationError from error

    return user


async def authenticate_user(
    session: AsyncSession,
    username: str,
    password: str,
) -> User | None:
    """Verify credentials without revealing whether the username exists."""
    user = await get_user_by_username(session, username)
    if user is None:
        verify_password(password, DUMMY_PASSWORD_HASH)
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


async def login_user(
    session: AsyncSession,
    username: str,
    password: str,
):
    """Authenticate and create an independent server-side session."""
    user = await authenticate_user(session, username, password)
    if user is None:
        return None
    token, user_session = await create_session(session, user.id)
    return user, token, user_session