import asyncio
import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.database import create_database_engine
from app.models import Friendship, User

from tests.test_friends_database import _unique_username


def _register(db_client: TestClient, username: str) -> None:
    response = db_client.post(
        "/auth/register",
        json={
            "username": username,
            "display_name": f"Display {username}",
            "password": "correct horse battery staple",
        },
    )
    assert response.status_code == 201, response.text


def _login(db_client: TestClient, username: str) -> None:
    response = db_client.post(
        "/auth/login",
        json={"username": username, "password": "correct horse battery staple"},
    )
    assert response.status_code == 200, response.text


def _make_friends(db_client: TestClient, first: str, second: str) -> None:
    _register(db_client, first)
    _register(db_client, second)
    _login(db_client, first)
    request_response = db_client.post("/friends/requests", json={"username": second})
    assert request_response.status_code == 201
    request_id = request_response.json()["id"]
    db_client.post("/auth/logout")
    _login(db_client, second)
    accept_response = db_client.post(f"/friends/requests/{request_id}/accept")
    assert accept_response.status_code == 200
    db_client.post("/auth/logout")



def _add_friend(db_client: TestClient, requester: str, recipient: str) -> None:
    _login(db_client, requester)
    request_response = db_client.post("/friends/requests", json={"username": recipient})
    assert request_response.status_code == 201
    request_id = request_response.json()["id"]
    db_client.post("/auth/logout")
    _login(db_client, recipient)
    accept_response = db_client.post(f"/friends/requests/{request_id}/accept")
    assert accept_response.status_code == 200
    db_client.post("/auth/logout")


@pytest.fixture
def db_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    import os

    from app.main import app

    test_database_url = os.getenv("TEST_DATABASE_URL")
    if not test_database_url:
        pytest.skip("TEST_DATABASE_URL is not set")

    application_database_url = os.getenv("DATABASE_URL")
    from sqlalchemy.engine import make_url

    if (
        application_database_url
        and make_url(application_database_url).database
        == make_url(test_database_url).database
    ):
        pytest.skip("TEST_DATABASE_URL must not point to the application database")

    monkeypatch.setenv("DATABASE_URL", test_database_url)
    monkeypatch.setenv("CSRF_STRICT", "false")
    app.dependency_overrides.clear()

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_create_conversation_between_friends_returns_201(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)

    _login(db_client, first)
    response = db_client.post("/conversations", json={"username": second})

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "created_at", "other_user"}
    assert body["other_user"]["username"] == second


def test_create_conversation_by_user_id(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)

    _login(db_client, first)
    second_id = None
    # Find the friend's id through search.
    search_response = db_client.get("/users/search", params={"q": second})
    assert search_response.status_code == 200
    second_id = search_response.json()[0]["id"]

    response = db_client.post("/conversations", json={"user_id": second_id})
    assert response.status_code == 201
    assert response.json()["other_user"]["username"] == second


def test_create_conversation_validation_rejects_ambiguous_identifier(
    db_client: TestClient,
) -> None:
    username = _unique_username("user")
    _register(db_client, username)
    _login(db_client, username)

    response = db_client.post(
        "/conversations",
        json={"username": username, "user_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert response.status_code == 422


def test_create_conversation_with_self_returns_400(db_client: TestClient) -> None:
    username = _unique_username("self")
    _register(db_client, username)
    _login(db_client, username)

    response = db_client.post("/conversations", json={"username": username})
    assert response.status_code == 400


def test_create_conversation_with_unknown_user_returns_404(
    db_client: TestClient,
) -> None:
    username = _unique_username("user")
    _register(db_client, username)
    _login(db_client, username)

    response = db_client.post(
        "/conversations",
        json={"username": _unique_username("missing")},
    )
    assert response.status_code == 404


def test_create_conversation_with_non_friend_returns_403(
    db_client: TestClient,
) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _register(db_client, first)
    _register(db_client, second)
    _login(db_client, first)

    response = db_client.post("/conversations", json={"username": second})
    assert response.status_code == 403


def test_repeated_conversation_creation_returns_200_and_same_id(
    db_client: TestClient,
) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)

    _login(db_client, first)
    first_response = db_client.post("/conversations", json={"username": second})
    assert first_response.status_code == 201
    conversation_id = first_response.json()["id"]

    second_response = db_client.post("/conversations", json={"username": second})
    assert second_response.status_code == 200
    assert second_response.json()["id"] == conversation_id


def test_list_conversations_returns_only_current_users_conversations(
    db_client: TestClient,
) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    third = _unique_username("third")
    _register(db_client, first)
    _register(db_client, second)
    _register(db_client, third)
    _add_friend(db_client, first, second)
    _add_friend(db_client, first, third)

    _login(db_client, first)
    first_conversation = db_client.post("/conversations", json={"username": second}).json()["id"]
    second_conversation = db_client.post("/conversations", json={"username": third}).json()["id"]

    response = db_client.get("/conversations")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    ids = {item["id"] for item in body}
    assert ids == {first_conversation, second_conversation}
    assert all(item["other_user"]["username"] in {second, third} for item in body)

    db_client.post("/auth/logout")
    _login(db_client, second)
    second_list = db_client.get("/conversations").json()
    assert len(second_list) == 1
    assert second_list[0]["id"] == first_conversation
    assert second_list[0]["other_user"]["username"] == first


def test_list_conversations_empty(db_client: TestClient) -> None:
    username = _unique_username("user")
    _register(db_client, username)
    _login(db_client, username)

    response = db_client.get("/conversations")
    assert response.status_code == 200
    assert response.json() == []


def test_get_own_conversation(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)

    _login(db_client, first)
    conversation_id = db_client.post("/conversations", json={"username": second}).json()["id"]

    response = db_client.get(f"/conversations/{conversation_id}")
    assert response.status_code == 200
    assert response.json()["id"] == conversation_id
    assert response.json()["other_user"]["username"] == second


def test_get_foreign_conversation_returns_404(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    third = _unique_username("third")
    _register(db_client, first)
    _register(db_client, second)
    _register(db_client, third)
    _add_friend(db_client, first, second)
    _add_friend(db_client, first, third)

    _login(db_client, first)
    foreign_conversation_id = db_client.post(
        "/conversations", json={"username": third}
    ).json()["id"]

    db_client.post("/auth/logout")
    _login(db_client, second)
    response = db_client.get(f"/conversations/{foreign_conversation_id}")
    assert response.status_code == 404


def test_get_missing_conversation_returns_404(db_client: TestClient) -> None:
    username = _unique_username("user")
    _register(db_client, username)
    _login(db_client, username)

    response = db_client.get("/conversations/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


async def _delete_friendship(first: str, second: str) -> None:
    import os

    from sqlalchemy import delete

    from app.database import create_database_engine
    from app.models import Friendship, User

    engine = create_database_engine(os.environ["TEST_DATABASE_URL"])
    try:
        async with engine.begin() as connection:
            first_id = (
                await connection.execute(
                    __import__("sqlalchemy").select(User.id).where(User.username == first)
                )
            ).scalar_one()
            second_id = (
                await connection.execute(
                    __import__("sqlalchemy").select(User.id).where(User.username == second)
                )
            ).scalar_one()
            low, high = sorted((first_id, second_id))
            await connection.execute(
                delete(Friendship).where(
                    Friendship.user_id == low, Friendship.friend_id == high
                )
            )
    finally:
        await engine.dispose()


async def _insert_friendship(first: str, second: str) -> None:
    import os

    from sqlalchemy import insert

    from app.database import create_database_engine
    from app.models import Friendship, User

    engine = create_database_engine(os.environ["TEST_DATABASE_URL"])
    try:
        async with engine.begin() as connection:
            first_id = (
                await connection.execute(
                    __import__("sqlalchemy").select(User.id).where(User.username == first)
                )
            ).scalar_one()
            second_id = (
                await connection.execute(
                    __import__("sqlalchemy").select(User.id).where(User.username == second)
                )
            ).scalar_one()
            low, high = sorted((first_id, second_id))
            await connection.execute(
                insert(Friendship).values(user_id=low, friend_id=high)
            )
    finally:
        await engine.dispose()


def test_existing_conversation_remains_readable_after_friendship_ends(
    db_client: TestClient,
) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)

    _login(db_client, first)
    conversation_id = db_client.post("/conversations", json={"username": second}).json()["id"]
    db_client.post("/auth/logout")

    asyncio.run(_delete_friendship(first, second))

    _login(db_client, first)
    response = db_client.get(f"/conversations/{conversation_id}")
    assert response.status_code == 200

    create_response = db_client.post("/conversations", json={"username": second})
    assert create_response.status_code == 200
    assert create_response.json()["id"] == conversation_id


def test_restored_friendship_does_not_create_second_conversation(
    db_client: TestClient,
) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)

    _login(db_client, first)
    conversation_id = db_client.post("/conversations", json={"username": second}).json()["id"]
    db_client.post("/auth/logout")

    asyncio.run(_delete_friendship(first, second))
    asyncio.run(_insert_friendship(first, second))

    _login(db_client, first)
    create_response = db_client.post("/conversations", json={"username": second})
    assert create_response.status_code == 200
    assert create_response.json()["id"] == conversation_id

    list_response = db_client.get("/conversations")
    assert len(list_response.json()) == 1
