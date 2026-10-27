import asyncio
import os
from collections.abc import Iterator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, insert, select, text
from sqlalchemy.engine import make_url

from app.database import create_database_engine
from app.main import app
from app.models import FriendRequest, Friendship, User
from app.friends.service import (
    AlreadyFriendsError,
    FriendRequestConflictError,
    PendingRequestExistsError,
    accept_friend_request,
    reject_friend_request,
    send_friend_request,
)

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


async def _get_user(username: str) -> User:
    engine = create_database_engine(_test_database_url())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            result = await session.execute(select(User).where(User.username == username))
            return result.scalar_one()
    finally:
        await engine.dispose()


async def _count_friendships(first_username: str, second_username: str) -> int:
    engine = create_database_engine(_test_database_url())
    try:
        async with engine.connect() as connection:
            first_id = (await connection.execute(select(User.id).where(User.username == first_username))).scalar_one()
            second_id = (await connection.execute(select(User.id).where(User.username == second_username))).scalar_one()
            low, high = sorted((first_id, second_id))
            result = await connection.execute(
                select(func.count())
                .select_from(Friendship)
                .where(Friendship.user_id == low, Friendship.friend_id == high)
            )
            return result.scalar_one()
    finally:
        await engine.dispose()


async def _count_pending_requests(first_username: str, second_username: str) -> int:
    engine = create_database_engine(_test_database_url())
    try:
        async with engine.connect() as connection:
            first_id = (await connection.execute(select(User.id).where(User.username == first_username))).scalar_one()
            second_id = (await connection.execute(select(User.id).where(User.username == second_username))).scalar_one()
            result = await connection.execute(
                select(func.count())
                .select_from(FriendRequest)
                .where(
                    ((FriendRequest.requester_id == first_id) & (FriendRequest.recipient_id == second_id))
                    | ((FriendRequest.requester_id == second_id) & (FriendRequest.recipient_id == first_id))
                )
                .where(FriendRequest.status == "pending")
            )
            return result.scalar_one()
    finally:
        await engine.dispose()


def _unique_username(prefix: str = "friend") -> str:
    return f"{prefix}{uuid4().hex[:20]}"


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


def test_send_friend_request_creates_pending_request(db_client: TestClient) -> None:
    requester = _unique_username("requester")
    recipient = _unique_username("recipient")
    _register(db_client, requester)
    _register(db_client, recipient)
    _login(db_client, requester)

    response = db_client.post(
        "/friends/requests",
        json={"username": recipient},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["requester"]["username"] == requester
    assert body["recipient"]["username"] == recipient
    assert set(body["requester"]) == {"id", "username", "display_name", "created_at"}
    assert set(body["recipient"]) == {"id", "username", "display_name", "created_at"}


def test_cannot_send_friend_request_to_self(db_client: TestClient) -> None:
    username = _unique_username("self")
    _register(db_client, username)
    _login(db_client, username)

    response = db_client.post(
        "/friends/requests",
        json={"username": username},
    )

    assert response.status_code == 400


def test_cannot_duplicate_pending_friend_request(db_client: TestClient) -> None:
    requester = _unique_username("requester")
    recipient = _unique_username("recipient")
    _register(db_client, requester)
    _register(db_client, recipient)
    _login(db_client, requester)

    first = db_client.post("/friends/requests", json={"username": recipient})
    assert first.status_code == 201

    second = db_client.post("/friends/requests", json={"username": recipient})
    assert second.status_code == 409


def test_cannot_send_request_to_existing_friend(db_client: TestClient) -> None:
    requester = _unique_username("requester")
    recipient = _unique_username("recipient")
    _register(db_client, requester)
    _register(db_client, recipient)
    _login(db_client, requester)

    request_response = db_client.post("/friends/requests", json={"username": recipient})
    assert request_response.status_code == 201
    request_id = request_response.json()["id"]

    db_client.post("/auth/logout")
    _login(db_client, recipient)
    accept_response = db_client.post(f"/friends/requests/{request_id}/accept")
    assert accept_response.status_code == 200

    db_client.post("/auth/logout")
    _login(db_client, requester)
    duplicate_response = db_client.post("/friends/requests", json={"username": recipient})
    assert duplicate_response.status_code == 409


def test_incoming_and_outgoing_requests_are_visible_to_participants(
    db_client: TestClient,
) -> None:
    requester = _unique_username("requester")
    recipient = _unique_username("recipient")
    _register(db_client, requester)
    _register(db_client, recipient)
    _login(db_client, requester)
    create_response = db_client.post("/friends/requests", json={"username": recipient})
    assert create_response.status_code == 201

    outgoing = db_client.get("/friends/requests/outgoing")
    assert outgoing.status_code == 200
    assert [item["recipient"]["username"] for item in outgoing.json()] == [recipient]

    db_client.post("/auth/logout")
    _login(db_client, recipient)
    incoming = db_client.get("/friends/requests/incoming")
    assert incoming.status_code == 200
    assert [item["requester"]["username"] for item in incoming.json()] == [requester]


def test_accept_friend_request_creates_friendship(db_client: TestClient) -> None:
    requester = _unique_username("requester")
    recipient = _unique_username("recipient")
    _register(db_client, requester)
    _register(db_client, recipient)
    _login(db_client, requester)

    request_response = db_client.post("/friends/requests", json={"username": recipient})
    assert request_response.status_code == 201
    request_id = request_response.json()["id"]

    db_client.post("/auth/logout")
    _login(db_client, recipient)
    accept_response = db_client.post(f"/friends/requests/{request_id}/accept")
    assert accept_response.status_code == 200
    assert accept_response.json()["status"] == "accepted"

    incoming = db_client.get("/friends/requests/incoming")
    assert incoming.status_code == 200
    assert incoming.json() == []

    friends_response = db_client.get("/friends")
    assert friends_response.status_code == 200
    friend_usernames = [friend["username"] for friend in friends_response.json()]
    assert requester in friend_usernames

    db_client.post("/auth/logout")
    _login(db_client, requester)
    requester_friends = db_client.get("/friends")
    assert recipient in [friend["username"] for friend in requester_friends.json()]


def test_reject_friend_request_allows_resend(db_client: TestClient) -> None:
    requester = _unique_username("requester")
    recipient = _unique_username("recipient")
    _register(db_client, requester)
    _register(db_client, recipient)
    _login(db_client, requester)

    request_response = db_client.post("/friends/requests", json={"username": recipient})
    assert request_response.status_code == 201
    request_id = request_response.json()["id"]

    db_client.post("/auth/logout")
    _login(db_client, recipient)
    reject_response = db_client.post(f"/friends/requests/{request_id}/reject")
    assert reject_response.status_code == 204

    incoming = db_client.get("/friends/requests/incoming")
    assert incoming.json() == []

    db_client.post("/auth/logout")
    _login(db_client, requester)
    resend_response = db_client.post("/friends/requests", json={"username": recipient})
    assert resend_response.status_code in {200, 201}
    assert resend_response.json()["status"] == "pending"

    friends_response = db_client.get("/friends")
    assert friends_response.json() == []


def test_mutual_friend_requests_create_one_friendship(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _register(db_client, first)
    _register(db_client, second)

    _login(db_client, first)
    first_response = db_client.post("/friends/requests", json={"username": second})
    assert first_response.status_code == 201
    assert first_response.json()["status"] == "pending"

    db_client.post("/auth/logout")
    _login(db_client, second)
    second_response = db_client.post("/friends/requests", json={"username": first})
    assert second_response.status_code == 200
    assert second_response.json()["status"] == "accepted"

    second_friends = db_client.get("/friends")
    assert {friend["username"] for friend in second_friends.json()} == {first}

    db_client.post("/auth/logout")
    _login(db_client, first)
    first_friends_after = db_client.get("/friends")
    assert {friend["username"] for friend in first_friends_after.json()} == {second}


def test_only_recipient_can_accept_or_reject(db_client: TestClient) -> None:
    requester = _unique_username("requester")
    recipient = _unique_username("recipient")
    _register(db_client, requester)
    _register(db_client, recipient)
    _login(db_client, requester)

    request_response = db_client.post("/friends/requests", json={"username": recipient})
    request_id = request_response.json()["id"]

    forbidden_accept = db_client.post(f"/friends/requests/{request_id}/accept")
    assert forbidden_accept.status_code == 403

    forbidden_reject = db_client.post(f"/friends/requests/{request_id}/reject")
    assert forbidden_reject.status_code == 403


def test_processed_request_cannot_be_processed_again(db_client: TestClient) -> None:
    requester = _unique_username("requester")
    recipient = _unique_username("recipient")
    _register(db_client, requester)
    _register(db_client, recipient)
    _login(db_client, requester)

    request_id = db_client.post("/friends/requests", json={"username": recipient}).json()["id"]

    db_client.post("/auth/logout")
    _login(db_client, recipient)
    assert db_client.post(f"/friends/requests/{request_id}/accept").status_code == 200

    second_accept = db_client.post(f"/friends/requests/{request_id}/accept")
    assert second_accept.status_code == 409

    second_reject = db_client.post(f"/friends/requests/{request_id}/reject")
    assert second_reject.status_code == 409


def test_friends_list_has_no_duplicates(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _register(db_client, first)
    _register(db_client, second)

    _login(db_client, first)
    request_id = db_client.post("/friends/requests", json={"username": second}).json()["id"]

    db_client.post("/auth/logout")
    _login(db_client, second)
    db_client.post(f"/friends/requests/{request_id}/accept")

    friends = db_client.get("/friends").json()
    assert len(friends) == 1
    assert friends[0]["username"] == first
    assert set(friends[0]) == {"id", "username", "display_name", "created_at"}


def test_unknown_friend_request_returns_404(db_client: TestClient) -> None:
    username = _unique_username("user")
    _register(db_client, username)
    _login(db_client, username)

    response = db_client.post("/friends/requests/00000000-0000-0000-0000-000000000000/accept")

    assert response.status_code == 404


from sqlalchemy.ext.asyncio import async_sessionmaker

from app.friends.service import (
    accept_friend_request,
    reject_friend_request,
    send_friend_request,
)


async def _send_request(username: str, recipient: str) -> object:
    requester = await _get_user(username)
    engine = create_database_engine(_test_database_url())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            return await send_friend_request(session, requester, username=recipient)
    finally:
        await engine.dispose()


async def _accept_request(request_id, username: str) -> object:
    user = await _get_user(username)
    engine = create_database_engine(_test_database_url())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            return await accept_friend_request(session, request_id, user)
    finally:
        await engine.dispose()


async def _reject_request(request_id, username: str) -> object:
    user = await _get_user(username)
    engine = create_database_engine(_test_database_url())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            return await reject_friend_request(session, request_id, user)
    finally:
        await engine.dispose()


async def _create_pending_request(requester: str, recipient: str) -> str:
    requester_user = await _get_user(requester)
    engine = create_database_engine(_test_database_url())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            request, result = await send_friend_request(session, requester_user, username=recipient)
            await session.commit()
            return str(request.id)
    finally:
        await engine.dispose()


def test_resend_rejected_request_with_reverse_pending() -> None:
    requester = _unique_username("requester")
    recipient = _unique_username("recipient")
    asyncio.run(_create_users([requester, recipient]))

    request_id = asyncio.run(_create_pending_request(requester, recipient))
    recipient_user = asyncio.run(_get_user(recipient))
    asyncio.run(_reject_with_session(request_id, recipient_user))

    reverse_request_id = asyncio.run(_create_pending_request(recipient, requester))

    async def run() -> None:
        result = await _send_request(requester, recipient)
        assert result[1] == "accepted"

    asyncio.run(run())

    assert asyncio.run(_count_pending_requests(requester, recipient)) == 0
    assert asyncio.run(_count_friendships(requester, recipient)) == 1


async def _reject_with_session(request_id, recipient) -> None:
    engine = create_database_engine(_test_database_url())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            await reject_friend_request(session, request_id, recipient)
    finally:
        await engine.dispose()


def test_concurrent_mutual_friend_requests() -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    asyncio.run(_create_users([first, second]))

    async def run() -> None:
        results = await asyncio.gather(
            _send_request(first, second),
            _send_request(second, first),
            return_exceptions=True,
        )
        assert all(not isinstance(result, Exception) for result in results)

    asyncio.run(run())

    assert asyncio.run(_count_pending_requests(first, second)) == 0
    assert asyncio.run(_count_friendships(first, second)) == 1


def test_concurrent_accept_and_reject_same_request() -> None:
    requester = _unique_username("requester")
    recipient = _unique_username("recipient")
    asyncio.run(_create_users([requester, recipient]))

    request_id = asyncio.run(_create_pending_request(requester, recipient))

    async def run() -> None:
        results = await asyncio.gather(
            _accept_request(request_id, recipient),
            _reject_request(request_id, recipient),
            return_exceptions=True,
        )
        exceptions = [result for result in results if isinstance(result, Exception)]
        assert len(exceptions) == 1
        assert any(type(exc).__name__ == "FriendRequestConflictError" for exc in exceptions)

    asyncio.run(run())

    assert asyncio.run(_count_pending_requests(requester, recipient)) == 0


def test_concurrent_resend_and_reverse_request() -> None:
    requester = _unique_username("requester")
    recipient = _unique_username("recipient")
    asyncio.run(_create_users([requester, recipient]))

    request_id = asyncio.run(_create_pending_request(requester, recipient))
    recipient_user = asyncio.run(_get_user(recipient))
    asyncio.run(_reject_with_session(request_id, recipient_user))

    async def run() -> None:
        results = await asyncio.gather(
            _send_request(requester, recipient),
            _send_request(recipient, requester),
            return_exceptions=True,
        )
        assert all(not isinstance(result, Exception) for result in results)

    asyncio.run(run())

    assert asyncio.run(_count_pending_requests(requester, recipient)) == 0
    assert asyncio.run(_count_friendships(requester, recipient)) == 1


def test_health_and_ready_remain_available(db_client: TestClient) -> None:
    assert db_client.get("/health").status_code == 200
    assert db_client.get("/health").json() == {"status": "ok"}
    ready_response = db_client.get("/ready")
    assert ready_response.status_code == 200
    assert ready_response.json() == {"status": "ok"}