import asyncio
import os
from collections.abc import Iterator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, insert, select
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


async def _create_users(usernames: list[str]) -> None:
    engine = create_database_engine(_test_database_url())
    try:
        async with engine.begin() as connection:
            await connection.execute(
                insert(User).values(
                    [
                        {
                            "username": username,
                            "display_name": f"Display {username}",
                            "password_hash": "test-password-hash",
                        }
                        for username in usernames
                    ]
                )
            )
    finally:
        await engine.dispose()


def _unique_username(prefix: str = "search") -> str:
    return f"{prefix}_{uuid4().hex[:20]}"


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
    monkeypatch.setenv("CSRF_STRICT", "false")
    app.dependency_overrides.clear()

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        asyncio.run(_delete_new_users(existing_ids))


def _register_and_login(db_client: TestClient, username: str) -> None:
    response = db_client.post(
        "/auth/register",
        json={
            "username": username,
            "display_name": "Search Test",
            "password": "correct horse battery staple",
        },
    )
    assert response.status_code == 201
    login_response = db_client.post(
        "/auth/login",
        json={"username": username, "password": "correct horse battery staple"},
    )
    assert login_response.status_code == 200


def test_search_requires_authentication(db_client: TestClient) -> None:
    response = db_client.get("/users/search", params={"q": "alice"})

    assert response.status_code == 401


def test_search_returns_matching_users(db_client: TestClient) -> None:
    current_username = _unique_username("current")
    _register_and_login(db_client, current_username)
    match_one = _unique_username("match")
    match_two = _unique_username("match")
    asyncio.run(_create_users([match_one, match_two]))

    response = db_client.get("/users/search", params={"q": "match"})

    assert response.status_code == 200
    usernames = [user["username"] for user in response.json()]
    assert match_one in usernames
    assert match_two in usernames
    assert current_username not in usernames


def test_search_excludes_current_user(db_client: TestClient) -> None:
    current_username = _unique_username("needle")
    _register_and_login(db_client, current_username)

    response = db_client.get("/users/search", params={"q": "needle"})

    assert response.status_code == 200
    assert response.json() == []


def test_search_returns_empty_list_without_matches(db_client: TestClient) -> None:
    current_username = _unique_username("current")
    _register_and_login(db_client, current_username)

    response = db_client.get("/users/search", params={"q": "zzzzzzzz"})

    assert response.status_code == 200
    assert response.json() == []


def test_search_is_case_insensitive(db_client: TestClient) -> None:
    current_username = _unique_username("current")
    _register_and_login(db_client, current_username)
    target_username = "alice_search_target"
    asyncio.run(_create_users([target_username]))

    response = db_client.get("/users/search", params={"q": "ALICE"})

    assert response.status_code == 200
    usernames = [user["username"] for user in response.json()]
    assert target_username in usernames


def test_search_trims_query(db_client: TestClient) -> None:
    current_username = _unique_username("current")
    _register_and_login(db_client, current_username)
    target_username = _unique_username("trimmed")
    asyncio.run(_create_users([target_username]))

    response = db_client.get("/users/search", params={"q": f"  {target_username[:6]}  "})

    assert response.status_code == 200
    usernames = [user["username"] for user in response.json()]
    assert target_username in usernames


def test_search_rejects_empty_query(db_client: TestClient) -> None:
    current_username = _unique_username("current")
    _register_and_login(db_client, current_username)

    response = db_client.get("/users/search", params={"q": ""})

    assert response.status_code == 422


def test_search_rejects_whitespace_query(db_client: TestClient) -> None:
    current_username = _unique_username("current")
    _register_and_login(db_client, current_username)

    response = db_client.get("/users/search", params={"q": "   "})

    assert response.status_code == 422


def test_search_rejects_too_long_query(db_client: TestClient) -> None:
    current_username = _unique_username("current")
    _register_and_login(db_client, current_username)

    response = db_client.get("/users/search", params={"q": "a" * 33})

    assert response.status_code == 422


def test_search_does_not_treat_percent_as_wildcard(db_client: TestClient) -> None:
    current_username = _unique_username("current")
    _register_and_login(db_client, current_username)
    target_username = _unique_username("special")
    asyncio.run(_create_users([target_username]))

    response = db_client.get("/users/search", params={"q": "%"})

    assert response.status_code == 200
    assert response.json() == []


def test_search_does_not_treat_underscore_as_wildcard(db_client: TestClient) -> None:
    current_username = _unique_username("current")
    _register_and_login(db_client, current_username)
    with_underscore = f"wu_{uuid4().hex[:8]}"
    without_underscore = f"wo{uuid4().hex[:8]}"
    asyncio.run(_create_users([with_underscore, without_underscore]))

    response = db_client.get("/users/search", params={"q": "_"})

    assert response.status_code == 200
    usernames = [user["username"] for user in response.json()]
    assert with_underscore in usernames
    assert without_underscore not in usernames


def test_search_does_not_treat_backslash_as_wildcard(db_client: TestClient) -> None:
    current_username = _unique_username("current")
    _register_and_login(db_client, current_username)
    target_username = _unique_username("backslash")
    asyncio.run(_create_users([target_username]))

    response = db_client.get("/users/search", params={"q": "\\"})

    assert response.status_code == 200
    assert response.json() == []


def test_search_rejects_sql_like_input_safely(db_client: TestClient) -> None:
    current_username = _unique_username("current")
    _register_and_login(db_client, current_username)

    response = db_client.get(
        "/users/search",
        params={"q": "'; DROP TABLE users; --"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_search_limits_results_to_twenty(db_client: TestClient) -> None:
    current_username = _unique_username("current")
    _register_and_login(db_client, current_username)
    usernames = [f"many_{index:02d}_{uuid4().hex[:8]}" for index in range(25)]
    asyncio.run(_create_users(usernames))

    response = db_client.get("/users/search", params={"q": "many"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) <= 20
    assert current_username not in [user["username"] for user in body]
    assert all(set(user) == {"id", "username", "display_name", "created_at"} for user in body)


def test_search_sorts_results_by_username(db_client: TestClient) -> None:
    current_username = _unique_username("current")
    _register_and_login(db_client, current_username)
    usernames = [_unique_username("sort_b"), _unique_username("sort_a")]
    asyncio.run(_create_users(usernames))

    response = db_client.get("/users/search", params={"q": "sort"})

    assert response.status_code == 200
    result_usernames = [user["username"] for user in response.json()]
    assert result_usernames == sorted(result_usernames)


def test_health_and_ready_remain_available(db_client: TestClient) -> None:
    assert db_client.get("/health").status_code == 200
    assert db_client.get("/health").json() == {"status": "ok"}
    ready_response = db_client.get("/ready")
    assert ready_response.status_code == 200
    assert ready_response.json() == {"status": "ok"}