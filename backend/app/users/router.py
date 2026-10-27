from typing import Annotated

from fastapi import APIRouter, Depends

from app.accounts.dependencies import get_current_user
from app.accounts.sessions import validate_csrf
from app.accounts.schemas import UserPublic
from app.models.user import User

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(validate_csrf)],
)


@router.get("/me", response_model=UserPublic)
async def read_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserPublic:
    """Return the authenticated user's public profile."""
    return UserPublic.model_validate(current_user)