import asyncio
import os
from collections.abc import Iterator
from sqlalchemy import delete, insert, select
from uuid import uuid4

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
    from app.main import app
    from sqlalchemy.engine import make_url

    test_database_url = os.getenv("TEST_DATABASE_URL")
    if not test_database_url:
        pytest.skip("TEST_DATABASE_URL is not set")

    application_database_url = os.getenv("DATABASE_URL")
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


def _create_conversation(db_client: TestClient, owner: str, other: str) -> str:
    _login(db_client, owner)
    response = db_client.post("/conversations", json={"username": other})
    assert response.status_code in {200, 201}
    conversation_id = response.json()["id"]
    db_client.post("/auth/logout")
    return conversation_id


def _send_message(
    db_client: TestClient, conversation_id: str, payload: dict, reply_to=None
) -> object:
    body = {"payload": payload}
    if reply_to is not None:
        body["reply_to_message_id"] = reply_to
    return db_client.post(f"/conversations/{conversation_id}/messages", json=body)


def test_send_emoji_message(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)
    conversation_id = _create_conversation(db_client, first, second)

    _login(db_client, first)
    response = _send_message(
        db_client, conversation_id, {"type": "emoji", "emoji_sequence": "😀👍"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["type"] == "emoji"
    assert body["schema_version"] == 1
    assert body["payload"]["emoji_sequence"] == "😀👍"
    assert body["sender"]["username"] == first
    assert body["reply_to_message_id"] is None


def test_send_template_messages(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)
    conversation_id = _create_conversation(db_client, first, second)

    _login(db_client, first)
    cases = [
        ({"type": "template", "template_id": "greeting", "params": {}}, 201),
        ({"type": "template", "template_id": "mood_question", "params": {}}, 201),
        (
            {
                "type": "template",
                "template_id": "meeting_invitation",
                "params": {
                    "activity": "coffee",
                    "occurs_at": "2026-10-28T15:30:00+03:00",
                    "timezone": "Europe/Moscow",
                    "place": "cafe",
                },
            },
            201,
        ),
    ]
    for payload, expected in cases:
        response = _send_message(db_client, conversation_id, payload)
        assert response.status_code == expected, response.text


def test_send_location_message(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)
    conversation_id = _create_conversation(db_client, first, second)

    _login(db_client, first)
    response = _send_message(
        db_client,
        conversation_id,
        {"type": "location", "latitude": 55.7558, "longitude": 37.6173, "label": "point"},
    )
    assert response.status_code == 201


def test_send_time_message(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)
    conversation_id = _create_conversation(db_client, first, second)

    _login(db_client, first)
    response = _send_message(
        db_client,
        conversation_id,
        {"type": "time", "occurs_at": "2026-10-28T15:30:00+03:00", "timezone": "Europe/Moscow"},
    )
    assert response.status_code == 201


def test_send_link_message(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)
    conversation_id = _create_conversation(db_client, first, second)

    _login(db_client, first)
    response = _send_message(
        db_client, conversation_id, {"type": "link", "url": "https://example.com"}
    )
    assert response.status_code == 201


def test_send_rejects_invalid_payloads(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)
    conversation_id = _create_conversation(db_client, first, second)

    _login(db_client, first)
    invalid_payloads = [
        {"type": "emoji", "emoji_sequence": ""},
        {"type": "emoji", "emoji_sequence": "a" * 101},
        {"type": "emoji", "emoji_sequence": "hello"},
        {"type": "template", "template_id": "unknown", "params": {}},
        {"type": "location", "latitude": 100, "longitude": 0},
        {"type": "location", "latitude": 0, "longitude": 200},
        {"type": "time", "occurs_at": "2026-10-28T15:30:00"},
        {"type": "link", "url": "ftp://example.com"},
        {"type": "unsupported", "value": 1},
    ]
    for payload in invalid_payloads:
        response = _send_message(db_client, conversation_id, payload)
        assert response.status_code == 422, (payload, response.text)


def test_send_rejects_too_long_emoji_message(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)
    conversation_id = _create_conversation(db_client, first, second)

    _login(db_client, first)
    response = _send_message(
        db_client, conversation_id, {"type": "emoji", "emoji_sequence": "😀" * 101}
    )
    assert response.status_code == 422


def test_emoji_validation_accepts_composite_sequences(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)
    conversation_id = _create_conversation(db_client, first, second)

    _login(db_client, first)
    sequences = [
        "👨‍👩‍👧‍👦",
        "👍🏽",
        "1️⃣",
        "❤️",
    ]
    for sequence in sequences:
        response = _send_message(
            db_client, conversation_id, {"type": "emoji", "emoji_sequence": sequence}
        )
        assert response.status_code == 201, (sequence, response.text)


def test_reply_to_message_in_same_conversation(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)
    conversation_id = _create_conversation(db_client, first, second)

    _login(db_client, first)
    original = _send_message(
        db_client, conversation_id, {"type": "emoji", "emoji_sequence": "😀"}
    ).json()
    reply = _send_message(
        db_client,
        conversation_id,
        {"type": "emoji", "emoji_sequence": "👍"},
        reply_to=original["id"],
    )
    assert reply.status_code == 201
    assert reply.json()["reply_to_message_id"] == original["id"]


def test_reply_to_foreign_conversation_returns_404(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    third = _unique_username("third")
    _make_friends(db_client, first, second)
    _register(db_client, third)
    _add_friend(db_client, first, third)

    first_second_conversation = _create_conversation(db_client, first, second)
    first_third_conversation = _create_conversation(db_client, first, third)

    _login(db_client, first)
    foreign_message = _send_message(
        db_client, first_third_conversation, {"type": "emoji", "emoji_sequence": "😀"}
    ).json()

    response = _send_message(
        db_client,
        first_second_conversation,
        {"type": "emoji", "emoji_sequence": "👍"},
        reply_to=foreign_message["id"],
    )
    assert response.status_code == 404


def test_reply_to_missing_message_returns_404(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)
    conversation_id = _create_conversation(db_client, first, second)

    _login(db_client, first)
    response = _send_message(
        db_client,
        conversation_id,
        {"type": "emoji", "emoji_sequence": "👍"},
        reply_to="00000000-0000-0000-0000-000000000000",
    )
    assert response.status_code == 404


def test_unauthenticated_user_cannot_send_or_read(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)
    conversation_id = _create_conversation(db_client, first, second)

    send_response = db_client.post(
        f"/conversations/{conversation_id}/messages",
        json={"payload": {"type": "emoji", "emoji_sequence": "😀"}},
    )
    read_response = db_client.get(f"/conversations/{conversation_id}/messages")
    assert send_response.status_code == 401
    assert read_response.status_code == 401


def test_non_participant_cannot_send_or_read(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    third = _unique_username("third")
    _make_friends(db_client, first, second)
    _register(db_client, third)
    conversation_id = _create_conversation(db_client, first, second)

    _login(db_client, third)
    send_response = db_client.post(
        f"/conversations/{conversation_id}/messages",
        json={"payload": {"type": "emoji", "emoji_sequence": "😀"}},
    )
    read_response = db_client.get(f"/conversations/{conversation_id}/messages")
    assert send_response.status_code == 404
    assert read_response.status_code == 404


def test_message_history_pagination(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)
    conversation_id = _create_conversation(db_client, first, second)

    _login(db_client, first)
    sent_ids = []
    for index in range(55):
        response = _send_message(
            db_client, conversation_id, {"type": "emoji", "emoji_sequence": f"😀{index}"}
        )
        assert response.status_code == 201
        sent_ids.append(response.json()["id"])

    first_page = db_client.get(f"/conversations/{conversation_id}/messages", params={"limit": 50})
    assert first_page.status_code == 200
    first_body = first_page.json()
    assert len(first_body["items"]) == 50
    assert first_body["next_cursor"] is not None

    second_page = db_client.get(
        f"/conversations/{conversation_id}/messages",
        params={"limit": 50, "cursor": first_body["next_cursor"]},
    )
    assert second_page.status_code == 200
    second_body = second_page.json()
    assert len(second_body["items"]) == 5
    assert second_body["next_cursor"] is None

    first_ids = {item["id"] for item in first_body["items"]}
    second_ids = {item["id"] for item in second_body["items"]}
    assert first_ids.isdisjoint(second_ids)
    assert first_ids | second_ids == set(sent_ids)

    all_ids = [item["id"] for item in first_body["items"]] + [item["id"] for item in second_body["items"]]
    # The first page contains newer messages; chronological order is preserved inside each page.
    assert first_body["items"] == sorted(first_body["items"], key=lambda item: item["created_at"])
    assert second_body["items"] == sorted(second_body["items"], key=lambda item: item["created_at"])


def test_empty_history(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)
    conversation_id = _create_conversation(db_client, first, second)

    _login(db_client, first)
    response = db_client.get(f"/conversations/{conversation_id}/messages")
    assert response.status_code == 200
    assert response.json() == {"items": [], "next_cursor": None}


async def _delete_friendship(first: str, second: str) -> None:
    from sqlalchemy import delete

    from app.models import Friendship, User

    engine = create_database_engine(os.environ["TEST_DATABASE_URL"])
    try:
        async with engine.begin() as connection:
            first_id = (
                await connection.execute(
                    select(User.id).where(User.username == first)
                )
            ).scalar_one()
            second_id = (
                await connection.execute(
                    select(User.id).where(User.username == second)
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
    from sqlalchemy import insert

    from app.models import Friendship, User

    engine = create_database_engine(os.environ["TEST_DATABASE_URL"])
    try:
        async with engine.begin() as connection:
            first_id = (
                await connection.execute(
                    select(User.id).where(User.username == first)
                )
            ).scalar_one()
            second_id = (
                await connection.execute(
                    select(User.id).where(User.username == second)
                )
            ).scalar_one()
            low, high = sorted((first_id, second_id))
            await connection.execute(
                insert(Friendship).values(user_id=low, friend_id=high)
            )
    finally:
        await engine.dispose()


def test_history_available_after_friendship_ends(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)
    conversation_id = _create_conversation(db_client, first, second)

    _login(db_client, first)
    original = _send_message(
        db_client, conversation_id, {"type": "emoji", "emoji_sequence": "😀"}
    ).json()
    db_client.post("/auth/logout")

    asyncio.run(_delete_friendship(first, second))

    _login(db_client, first)
    response = db_client.get(f"/conversations/{conversation_id}/messages")
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [original["id"]]

    send_response = db_client.post(
        f"/conversations/{conversation_id}/messages",
        json={"payload": {"type": "emoji", "emoji_sequence": "👍"}},
    )
    assert send_response.status_code == 403


def test_sending_restored_after_friendship_restored(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)
    conversation_id = _create_conversation(db_client, first, second)

    _login(db_client, first)
    _send_message(db_client, conversation_id, {"type": "emoji", "emoji_sequence": "😀"})
    db_client.post("/auth/logout")

    asyncio.run(_delete_friendship(first, second))
    asyncio.run(_insert_friendship(first, second))

    _login(db_client, first)
    response = _send_message(
        db_client, conversation_id, {"type": "emoji", "emoji_sequence": "👍"}
    )
    assert response.status_code == 201


def test_invalid_conversation_id_returns_404(db_client: TestClient) -> None:
    username = _unique_username("user")
    _register(db_client, username)
    _login(db_client, username)

    assert db_client.get("/conversations/not-a-uuid/messages").status_code == 404
    assert db_client.post(
        "/conversations/not-a-uuid/messages",
        json={"payload": {"type": "emoji", "emoji_sequence": "😀"}},
    ).status_code == 404


def test_invalid_cursor_returns_400(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)
    conversation_id = _create_conversation(db_client, first, second)

    _login(db_client, first)
    response = db_client.get(
        f"/conversations/{conversation_id}/messages", params={"cursor": "not-a-cursor"}
    )
    assert response.status_code == 400


def test_cursor_from_another_conversation_returns_400(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    third = _unique_username("third")
    _make_friends(db_client, first, second)
    _register(db_client, third)
    _add_friend(db_client, first, third)

    first_second_conversation = _create_conversation(db_client, first, second)
    first_third_conversation = _create_conversation(db_client, first, third)

    _login(db_client, first)
    for _ in range(2):
        _send_message(
            db_client, first_third_conversation, {"type": "emoji", "emoji_sequence": "😀"}
        )
    foreign_page = db_client.get(
        f"/conversations/{first_third_conversation}/messages", params={"limit": 1}
    )
    assert foreign_page.status_code == 200
    foreign_cursor = foreign_page.json()["next_cursor"]
    assert foreign_cursor is not None

    response = db_client.get(
        f"/conversations/{first_second_conversation}/messages",
        params={"cursor": foreign_cursor},
    )
    assert response.status_code == 400


def test_invalid_meeting_invitation_params_rejected(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)
    conversation_id = _create_conversation(db_client, first, second)

    _login(db_client, first)
    invalid_cases = [
        {
            "type": "template",
            "template_id": "meeting_invitation",
            "params": {"activity": "coffee"},
        },
        {
            "type": "template",
            "template_id": "meeting_invitation",
            "params": {
                "activity": "coffee",
                "occurs_at": "2026-10-28T15:30:00",
                "timezone": "Europe/Moscow",
            },
        },
        {
            "type": "template",
            "template_id": "meeting_invitation",
            "params": {
                "activity": "coffee",
                "occurs_at": "2026-10-28T15:30:00+03:00",
                "timezone": "Not/AZone",
            },
        },
        {
            "type": "template",
            "template_id": "meeting_invitation",
            "params": {
                "activity": "",
                "occurs_at": "2026-10-28T15:30:00+03:00",
            },
        },
    ]
    for payload in invalid_cases:
        response = _send_message(db_client, conversation_id, payload)
        assert response.status_code == 422, (payload, response.text)


def test_time_message_rejects_naive_datetime_and_invalid_timezone(
    db_client: TestClient,
) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)
    conversation_id = _create_conversation(db_client, first, second)

    _login(db_client, first)
    naive_response = _send_message(
        db_client,
        conversation_id,
        {"type": "time", "occurs_at": "2026-10-28T15:30:00", "timezone": "Europe/Moscow"},
    )
    assert naive_response.status_code == 422

    invalid_timezone_response = _send_message(
        db_client,
        conversation_id,
        {
            "type": "time",
            "occurs_at": "2026-10-28T15:30:00+03:00",
            "timezone": "Not/AZone",
        },
    )
    assert invalid_timezone_response.status_code == 422


def test_link_message_rejects_too_long_url(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)
    conversation_id = _create_conversation(db_client, first, second)

    _login(db_client, first)
    response = _send_message(
        db_client,
        conversation_id,
        {"type": "link", "url": "https://example.com/" + "a" * 2048},
    )
    assert response.status_code == 422


def test_emoji_message_boundary_and_control_characters(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)
    conversation_id = _create_conversation(db_client, first, second)

    _login(db_client, first)
    assert _send_message(
        db_client, conversation_id, {"type": "emoji", "emoji_sequence": "😀" * 100}
    ).status_code == 201
    assert _send_message(
        db_client, conversation_id, {"type": "emoji", "emoji_sequence": "😀" * 101}
    ).status_code == 422
    assert _send_message(
        db_client, conversation_id, {"type": "emoji", "emoji_sequence": "😀\u0001"}
    ).status_code == 422
