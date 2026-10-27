from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.dependencies import get_current_user
from app.accounts.rate_limit import login_rate_limiter
from app.accounts.sessions import client_ip
from app.accounts.schemas import LoginRequest, RegisterRequest, UserPublic
from app.accounts.service import (
    RegistrationError,
    UsernameAlreadyExistsError,
    authenticate_user,
    create_user,
    login_user,
)
from app.accounts.sessions import (
    SESSION_COOKIE_NAME,
    clear_session_cookie,
    revoke_session,
    set_session_cookie,
    validate_csrf,
)
from app.database import get_db_session
from app.models.user import User

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    dependencies=[Depends(validate_csrf)],
)


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


@router.post("/login", response_model=UserPublic, status_code=status.HTTP_200_OK)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserPublic:
    """Authenticate a user and create a server-side session."""
    ip = client_ip(request)
    allowed, retry_after = await login_rate_limiter.check(
        payload.username, ip
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts",
            headers={"Retry-After": str(retry_after)},
        )

    result = await login_user(
        session,
        payload.username,
        payload.password.get_secret_value(),
    )
    if result is None:
        await login_rate_limiter.record_failure(payload.username, ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    user, token, user_session = result
    await login_rate_limiter.record_success(payload.username, ip)
    set_session_cookie(response, token, user_session.expires_at)
    return UserPublic.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    """Revoke the current session and clear its cookie."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    await revoke_session(session, token)
    clear_session_cookie(response)