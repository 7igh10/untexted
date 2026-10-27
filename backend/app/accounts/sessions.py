import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

from fastapi import HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import UserSession
from app.models.user import User

SESSION_COOKIE_NAME = "session"
SESSION_LIFETIME = timedelta(days=14)
SESSION_RENEWAL_THRESHOLD = timedelta(hours=24)
SESSION_COOKIE_MAX_AGE = int(SESSION_LIFETIME.total_seconds())


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def cookie_secure() -> bool:
    return os.getenv("COOKIE_SECURE", "false").lower() == "true"


def set_session_cookie(response, token: str, expires_at: datetime) -> None:
    max_age = int((expires_at - datetime.now(timezone.utc)).total_seconds())
    if max_age < 0:
        max_age = 0
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=cookie_secure(),
        samesite="lax",
        max_age=max_age,
        path="/",
    )


def clear_session_cookie(response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=cookie_secure(),
        httponly=True,
        samesite="lax",
    )


def allowed_origins(request: Request) -> set[str]:
    configured = os.getenv("ALLOWED_ORIGINS")
    if configured:
        return {origin.strip() for origin in configured.split(",") if origin.strip()}
    return {f"{request.url.scheme}://{request.url.netloc}"}


def validate_csrf(request: Request) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return

    origin = request.headers.get("origin")
    if origin is None:
        referer = request.headers.get("referer")
        if referer:
            parsed = urlsplit(referer)
            if parsed.scheme and parsed.netloc:
                origin = f"{parsed.scheme}://{parsed.netloc}"

    if origin is None:
        strict = (
            os.getenv("CSRF_STRICT", "false").lower() == "true"
            or os.getenv("ENVIRONMENT", "").lower() == "production"
        )
        if strict:
            raise HTTPException(status_code=403, detail="CSRF validation failed")
        return

    if origin not in allowed_origins(request):
        raise HTTPException(status_code=403, detail="CSRF validation failed")


def client_ip(request: Request) -> str:
    host = request.client.host if request.client else "unknown"
    trusted = {
        item.strip()
        for item in os.getenv("TRUSTED_PROXIES", "").split(",")
        if item.strip()
    }
    if host in trusted:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            candidate = forwarded.split(",")[0].strip()
            if candidate:
                return candidate
    return host


async def create_session(db_session: AsyncSession, user_id) -> tuple[str, UserSession]:
    token = generate_session_token()
    now = datetime.now(timezone.utc)
    user_session = UserSession(
        user_id=user_id,
        token_hash=hash_session_token(token),
        expires_at=now + SESSION_LIFETIME,
        last_used_at=now,
    )
    db_session.add(user_session)
    await db_session.flush()
    await db_session.commit()
    return token, user_session


async def get_session(db_session: AsyncSession, token: str | None):
    if not token:
        return None, False

    token_hash = hash_session_token(token)
    now = datetime.now(timezone.utc)
    result = await db_session.execute(
        select(UserSession).where(UserSession.token_hash == token_hash)
    )
    user_session = result.scalar_one_or_none()
    if user_session is None:
        return None, False

    if user_session.expires_at <= now:
        await db_session.execute(
            delete(UserSession).where(UserSession.id == user_session.id)
        )
        await db_session.commit()
        return None, False

    renewed = False
    if user_session.expires_at - now <= SESSION_RENEWAL_THRESHOLD:
        user_session.expires_at = now + SESSION_LIFETIME
        user_session.last_used_at = now
        await db_session.commit()
        renewed = True

    return user_session, renewed


async def get_authenticated_user(db_session: AsyncSession, token: str | None):
    user_session, renewed = await get_session(db_session, token)
    if user_session is None:
        return None, None, False

    result = await db_session.execute(
        select(User).where(User.id == user_session.user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        await db_session.execute(
            delete(UserSession).where(UserSession.id == user_session.id)
        )
        await db_session.commit()
        return None, None, False

    return user, user_session, renewed


async def revoke_session(db_session: AsyncSession, token: str | None) -> None:
    if not token:
        return
    await db_session.execute(
        delete(UserSession).where(UserSession.token_hash == hash_session_token(token))
    )
    await db_session.commit()


async def revoke_all_sessions(db_session: AsyncSession, user_id) -> None:
    await db_session.execute(
        delete(UserSession).where(UserSession.user_id == user_id)
    )
    await db_session.commit()


async def get_user_by_username(db_session: AsyncSession, username: str):
    result = await db_session.execute(
        select(User).where(User.username == username)
    )
    return result.scalar_one_or_none()