import asyncio
import os
from collections.abc import Iterator
from datetime import datetime
from uuid import UUID, uuid4

import pytest
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.engine import make_url

from app.database import create_database_engine
from app.main import app
from app.models import User

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


async def _fetch_user(username: str):
    engine = create_database_engine(_test_database_url())
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                select(
                    User.id,
                    User.username,
                    User.display_name,
                    User.password_hash,
                    User.created_at,
                ).where(User.username == username)
            )
            return result.one_or_none()
    finally:
        await engine.dispose()


async def _count_users(username: str) -> int:
    engine = create_database_engine(_test_database_url())
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                select(func.count())
                .select_from(User)
                .where(User.username == username)
            )
            return result.scalar_one()
    finally:
        await engine.dispose()


def _unique_username() -> str:
    return f"reg_{uuid4().hex[:20]}"


def _registration_payload(
    username: str,
    *,
    display_name: str = "Alice",
    password: str = "correct horse battery staple",
) -> dict[str, str]:
    return {
        "username": username,
        "display_name": display_name,
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

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        asyncio.run(_delete_new_users(existing_ids))


def test_register_creates_user_and_stores_password_hash(
    db_client: TestClient,
) -> None:
    username = _unique_username()
    password = "correct horse battery staple"

    response = db_client.post(
        "/auth/register",
        json=_registration_payload(username, password=password),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert set(body) == {"id", "username", "display_name", "created_at"}
    assert UUID(body["id"])
    assert body["username"] == username
    assert body["display_name"] == "Alice"
    assert datetime.fromisoformat(body["created_at"]).tzinfo is not None
    assert "password" not in body
    assert "password_hash" not in body
    assert password not in response.text

    row = asyncio.run(_fetch_user(username))
    assert row is not None
    assert row.password_hash != password
    assert row.password_hash.startswith("$argon2id$v=19$m=65536,t=3,p=4$")
    assert PasswordHasher().verify(row.password_hash, password)
    assert row.created_at.tzinfo is not None


def test_register_accepts_cyrillic_username_and_ascii_smiley(
    db_client: TestClient,
) -> None:
    username = f"рег_{uuid4().hex[:12]}"
    display_name = "Hi :-)"

    response = db_client.post(
        "/auth/register",
        json=_registration_payload(
            username,
            display_name=display_name,
            password="another secure password",
        ),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["username"] == username
    assert body["display_name"] == display_name

    row = asyncio.run(_fetch_user(username))
    assert row is not None
    assert row.display_name == display_name


def test_register_rejects_emoji_display_name(
    db_client: TestClient,
) -> None:
    response = db_client.post(
        "/auth/register",
        json=_registration_payload(
            _unique_username(),
            display_name="Hi 😀",
        ),
    )

    assert response.status_code == 422
    assert any(
        "display_name" in error["loc"]
        for error in response.json()["detail"]
    )


def test_register_preserves_password_whitespace(
    db_client: TestClient,
) -> None:
    username = _unique_username()
    password = "  space-preserved  "

    response = db_client.post(
        "/auth/register",
        json=_registration_payload(username, password=password),
    )

    assert response.status_code == 201, response.text
    row = asyncio.run(_fetch_user(username))
    assert row is not None
    assert PasswordHasher().verify(row.password_hash, password)
    with pytest.raises(VerifyMismatchError):
        PasswordHasher().verify(row.password_hash, password.strip())


def test_register_returns_409_for_duplicate_username(
    db_client: TestClient,
) -> None:
    username = _unique_username()
    first_response = db_client.post(
        "/auth/register",
        json=_registration_payload(username),
    )
    assert first_response.status_code == 201

    second_password = "another secure password"
    second_response = db_client.post(
        "/auth/register",
        json=_registration_payload(
            username,
            display_name="Other Alice",
            password=second_password,
        ),
    )

    assert second_response.status_code == 409
    assert second_response.json() == {"detail": "Username already taken"}
    assert "uq_users_username" not in second_response.text
    assert "INSERT" not in second_response.text.upper()
    assert second_password not in second_response.text
    assert asyncio.run(_count_users(username)) == 1


def test_register_returns_500_and_rolls_back_on_database_error(
    db_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    username = _unique_username()
    monkeypatch.setattr(
        "app.accounts.service.hash_password",
        lambda _password: "x" * 256,
    )

    response = db_client.post(
        "/auth/register",
        json=_registration_payload(username),
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Could not create user"}
    assert "INSERT" not in response.text.upper()
    assert "varchar" not in response.text.lower()
    assert asyncio.run(_count_users(username)) == 0


def test_health_and_ready_remain_available(db_client: TestClient) -> None:
    health_response = db_client.get("/health")
    ready_response = db_client.get("/ready")

    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}
    assert ready_response.status_code == 200
    assert ready_response.json() == {"status": "ok"}
