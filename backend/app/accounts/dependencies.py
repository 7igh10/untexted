from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.sessions import (
    SESSION_COOKIE_NAME,
    get_authenticated_user,
    set_session_cookie,
)
from app.database import get_db_session
from app.models.user import User


async def get_current_user(
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    """Return the authenticated user or raise 401."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    user, user_session, renewed = await get_authenticated_user(session, token)
    if user is None or user_session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    if renewed:
        set_session_cookie(response, token, user_session.expires_at)
    return user