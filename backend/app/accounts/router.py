from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.schemas import RegisterRequest, UserPublic
from app.accounts.service import (
    RegistrationError,
    UsernameAlreadyExistsError,
    create_user,
)
from app.database import get_db_session

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_409_CONFLICT: {"description": "Username is already taken."},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "The user could not be created."
        },
    },
)
async def register(
    payload: RegisterRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserPublic:
    """Create a user account and return only public fields."""
    try:
        user = await create_user(session, payload)
    except UsernameAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        ) from None
    except RegistrationError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create user",
        ) from None

    return UserPublic.model_validate(user)
