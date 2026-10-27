from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.dependencies import get_current_user
from app.accounts.sessions import validate_csrf
from app.accounts.schemas import UserPublic
from app.database import get_db_session
from app.models.user import User
from app.users.schemas import UserSearchQuery
from app.users.service import search_users

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


@router.get("/search", response_model=list[UserPublic])
async def search_users_endpoint(
    query: Annotated[UserSearchQuery, Query()],
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[UserPublic]:
    """Search users by a case-insensitive username substring."""
    users = await search_users(session, current_user, query.q)
    return [UserPublic.model_validate(user) for user in users]