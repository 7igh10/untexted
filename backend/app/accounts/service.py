import asyncio

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.passwords import hash_password
from app.accounts.schemas import RegisterRequest
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
