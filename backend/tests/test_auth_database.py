import asyncio
import os
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.engine import make_url

from app.accounts.sessions import hash_session_token
from app.accounts.rate_limit import login_rate_limiter
from app.accounts.sessions import SESSION_COOKIE_NAME
from app.database import create_database_engine
from app.main import app
from app.models import User, UserSession

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL is not set",
)


def _test_database_url() -> str:
    assert TEST_DATABASE_URL is not None
    return TEST_DATABASE_URL


def _database_identity(value: str) -> tuple[str | None, int | None, str | None]:
    url = make_url(value)
    return url.host, url.port, url.database


async def _fetch_user_ids() -> set[UUID]:
    engine = create_database_engine(_test_database_url())
    try:
        async with engine.connect() as connection:
            result = await connection.execute(select(User.id))
            return set(result.scalars().all())
    finally:
        await engine.dispose()


async def _delete_new_users(existing_ids: set[UUID]) -> None:
    engine = create_database_engine(_test_database_url())
    try:
        async with engine.begin() as connection:
            statement = delete(User)
            if existing_ids:
                statement = statement.where(User.id.not_in(existing_ids))
            await connection.execute(statement)
    finally:
        await engine.dispose()


async def _count_sessions(username: str) -> int:
    engine = create_database_engine(_test_database_url())
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                select(func.count())
                .select_from(UserSession)
                .join(User, User.id == UserSession.user_id)
                .where(User.username == username)
            )
            return result.scalar_one()
    finally:
        await engine.dispose()


async def _create_session_for_user(
    username: str,
    *,
    token: str,
    expires_at: datetime,
) -> None:
    engine = create_database_engine(_test_database_url())
    try:
        async with engine.begin() as connection:
            result = await connection.execute(
                select(User.id).where(User.username == username)
            )
            user_id = result.scalar_one()
            await connection.execute(
                __import__("sqlalchemy").insert(UserSession).values(
                    user_id=user_id,
                    token_hash=hash_session_token(token),
                    expires_at=expires_at,
                    last_used_at=datetime.now(timezone.utc),
                )
            )
    finally:
        await engine.dispose()


def _unique_username() -> str:
    return f"auth_{uuid4().hex[:20]}"


def _registration_payload(username: str, password: str = "correct horse battery staple") -> dict[str, str]:
    return {
        "username": username,
        "display_name": "Auth Test",
        "password": password,
    }


@pytest.fixture
def db_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    test_database_url = _test_database_url()
    application_database_url = os.getenv("DATABASE_URL")
    if (
        application_database_url
        and _database_identity(application_database_url)
        == _database_identity(test_database_url)
    ):
        pytest.skip("TEST_DATABASE_URL must not point to the application database")

    existing_ids = asyncio.run(_fetch_user_ids())
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    app.dependency_overrides.clear()
    login_rate_limiter.reset()

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        asyncio.run(_delete_new_users(existing_ids))
        login_rate_limiter.reset()


def test_login_success_sets_cookie_and_returns_public_user(db_client: TestClient) -> None:
    username = _unique_username()
    password = "correct horse battery staple"
    register_response = db_client.post(
        "/auth/register",
        json=_registration_payload(username, password),
    )
    assert register_response.status_code == 201

    response = db_client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"id", "username", "display_name", "created_at"}
    assert body["username"] == username
    assert "password" not in body
    assert "password_hash" not in body
    assert "session" in response.cookies
    set_cookie = response.headers.get("set-cookie", "")
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Path=/" in set_cookie
    assert "Max-Age=1209" in set_cookie


def test_login_rejects_wrong_password_with_generic_error(db_client: TestClient) -> None:
    username = _unique_username()
    db_client.post(
        "/auth/register",
        json=_registration_payload(username, "correct horse battery staple"),
    )

    response = db_client.post(
        "/auth/login",
        json={"username": username, "password": "wrong password"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid username or password"}


def test_login_rejects_unknown_username_with_same_error(db_client: TestClient) -> None:
    response = db_client.post(
        "/auth/login",
        json={"username": "definitely_missing_user", "password": "wrong password"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid username or password"}


def test_users_me_requires_session(db_client: TestClient) -> None:
    response = db_client.get("/users/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


def test_users_me_returns_current_user(db_client: TestClient) -> None:
    username = _unique_username()
    password = "correct horse battery staple"
    db_client.post("/auth/register", json=_registration_payload(username, password))
    login_response = db_client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    assert login_response.status_code == 200

    response = db_client.get("/users/me")

    assert response.status_code == 200
    assert response.json()["username"] == username


def test_users_me_rejects_invalid_cookie(db_client: TestClient) -> None:
    db_client.cookies.set("session", "not-a-valid-session-token")

    response = db_client.get("/users/me")

    assert response.status_code == 401


def test_logout_revokes_only_current_session(db_client: TestClient) -> None:
    username = _unique_username()
    password = "correct horse battery staple"
    db_client.post("/auth/register", json=_registration_payload(username, password))

    first_login = db_client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    assert first_login.status_code == 200
    first_cookie = first_login.cookies.get("session")
    assert first_cookie is not None

    second_token = "second-independent-session-token"
    expires_at = datetime.now(timezone.utc) + timedelta(days=14)
    asyncio.run(
        _create_session_for_user(username, token=second_token, expires_at=expires_at)
    )

    logout_response = db_client.post(
        "/auth/logout",
        headers={"Cookie": f"session={first_cookie}"},
    )
    assert logout_response.status_code == 204
    assert "session=" in logout_response.headers.get("set-cookie", "")

    first_me = db_client.get(
        "/users/me",
        headers={"Cookie": f"session={first_cookie}"},
    )
    assert first_me.status_code == 401

    second_me = db_client.get(
        "/users/me",
        headers={"Cookie": f"session={second_token}"},
    )
    assert second_me.status_code == 200
    assert second_me.json()["username"] == username


def test_logout_is_idempotent_without_cookie(db_client: TestClient) -> None:
    response = db_client.post("/auth/logout")

    assert response.status_code == 204
    assert "session=" in response.headers.get("set-cookie", "")


def test_expired_session_is_rejected_and_removed(db_client: TestClient) -> None:
    username = _unique_username()
    password = "correct horse battery staple"
    db_client.post("/auth/register", json=_registration_payload(username, password))

    token = "expired-session-token"
    expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    asyncio.run(_create_session_for_user(username, token=token, expires_at=expires_at))

    response = db_client.get("/users/me", headers={"Cookie": f"session={token}"})

    assert response.status_code == 401
    assert asyncio.run(_count_sessions(username)) == 0


def test_session_token_is_stored_only_as_hash(db_client: TestClient) -> None:
    username = _unique_username()
    password = "correct horse battery staple"
    db_client.post("/auth/register", json=_registration_payload(username, password))
    login_response = db_client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    assert login_response.status_code == 200
    raw_token = login_response.cookies.get("session")
    assert raw_token is not None

    async def fetch_token_hashes() -> list[str]:
        engine = create_database_engine(_test_database_url())
        try:
            async with engine.connect() as connection:
                result = await connection.execute(
                    select(UserSession.token_hash).join(
                        User, User.id == UserSession.user_id
                    ).where(User.username == username)
                )
                return list(result.scalars().all())
        finally:
            await engine.dispose()

    hashes = asyncio.run(fetch_token_hashes())
    assert hashes
    assert raw_token not in hashes
    assert all(len(value) == 64 for value in hashes)


def test_sliding_renewal_updates_session_and_cookie(db_client: TestClient) -> None:
    username = _unique_username()
    password = "correct horse battery staple"
    db_client.post("/auth/register", json=_registration_payload(username, password))

    token = "near-expiry-session-token"
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    asyncio.run(_create_session_for_user(username, token=token, expires_at=expires_at))

    response = db_client.get("/users/me", headers={"Cookie": f"session={token}"})

    assert response.status_code == 200
    set_cookie = response.headers.get("set-cookie", "")
    assert "Max-Age=1209" in set_cookie

    async def fetch_expiry() -> datetime:
        engine = create_database_engine(_test_database_url())
        try:
            async with engine.connect() as connection:
                result = await connection.execute(
                    select(UserSession.expires_at)
                    .join(User, User.id == UserSession.user_id)
                    .where(User.username == username)
                )
                return result.scalar_one()
        finally:
            await engine.dispose()

    new_expiry = asyncio.run(fetch_expiry())
    assert new_expiry > expires_at


def test_rate_limit_returns_429_and_retry_after(db_client: TestClient) -> None:
    username = "rate_limit_test_user"

    for _ in range(5):
        response = db_client.post(
            "/auth/login",
            json={"username": username, "password": "wrong password"},
        )
        assert response.status_code == 401

    response = db_client.post(
        "/auth/login",
        json={"username": username, "password": "wrong password"},
    )

    assert response.status_code == 429
    assert "Retry-After" in response.headers
    assert int(response.headers["Retry-After"]) >= 1


def test_rate_limit_resets_after_successful_login(db_client: TestClient) -> None:
    username = _unique_username()
    password = "correct horse battery staple"
    db_client.post("/auth/register", json=_registration_payload(username, password))

    for _ in range(2):
        db_client.post(
            "/auth/login",
            json={"username": username, "password": "wrong password"},
        )

    success = db_client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    assert success.status_code == 200

    for _ in range(5):
        response = db_client.post(
            "/auth/login",
            json={"username": username, "password": "wrong password"},
        )
        assert response.status_code == 401


def test_csrf_rejects_disallowed_origin(db_client: TestClient) -> None:
    response = db_client.post(
        "/auth/login",
        json={"username": "alice", "password": "password"},
        headers={"Origin": "https://evil.example"},
    )

    assert response.status_code == 403


def test_csrf_allows_missing_origin_in_development(db_client: TestClient) -> None:
    response = db_client.post(
        "/auth/login",
        json={"username": "alice", "password": "password"},
    )

    assert response.status_code in {401, 429}


def test_health_and_ready_remain_available(db_client: TestClient) -> None:
    assert db_client.get("/health").status_code == 200
    assert db_client.get("/health").json() == {"status": "ok"}
    ready_response = db_client.get("/ready")
    assert ready_response.status_code == 200
    assert ready_response.json() == {"status": "ok"}