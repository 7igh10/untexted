import os
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.realtime.manager import connection_manager
from tests.test_friends_database import _unique_username

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


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


@pytest.fixture
def db_client(monkeypatch: pytest.MonkeyPatch):
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
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _create_conversation(db_client: TestClient, owner: str, other: str) -> str:
    _login(db_client, owner)
    response = db_client.post("/conversations", json={"username": other})
    assert response.status_code in {200, 201}
    conversation_id = response.json()["id"]
    db_client.post("/auth/logout")
    return conversation_id


def test_websocket_requires_session(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)
    conversation_id = _create_conversation(db_client, first, second)

    with pytest.raises(WebSocketDisconnect) as exc:
        with db_client.websocket_connect(f"/conversations/{conversation_id}/ws"):
            pass
    assert exc.value.code == 4401


def test_websocket_rejects_invalid_session(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)
    conversation_id = _create_conversation(db_client, first, second)

    db_client.cookies.set("session", "invalid-token")
    with pytest.raises(WebSocketDisconnect) as exc:
        with db_client.websocket_connect(f"/conversations/{conversation_id}/ws"):
            pass
    assert exc.value.code == 4401


def test_websocket_rejects_forbidden_origin(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)
    conversation_id = _create_conversation(db_client, first, second)

    _login(db_client, first)
    with pytest.raises(WebSocketDisconnect) as exc:
        with db_client.websocket_connect(
            f"/conversations/{conversation_id}/ws",
            headers={"Origin": "https://evil.example"},
        ):
            pass
    assert exc.value.code == 4403


def test_websocket_rejects_non_participant(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    third = _unique_username("third")
    _make_friends(db_client, first, second)
    _register(db_client, third)
    conversation_id = _create_conversation(db_client, first, second)

    _login(db_client, third)
    with pytest.raises(WebSocketDisconnect) as exc:
        with db_client.websocket_connect(f"/conversations/{conversation_id}/ws"):
            pass
    assert exc.value.code == 4404


def test_websocket_rejects_invalid_conversation_id(db_client: TestClient) -> None:
    username = _unique_username("user")
    _register(db_client, username)
    _login(db_client, username)

    with pytest.raises(WebSocketDisconnect) as exc:
        with db_client.websocket_connect("/conversations/not-a-uuid/ws"):
            pass
    assert exc.value.code == 4404


def test_websocket_successful_connection(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)
    conversation_id = _create_conversation(db_client, first, second)

    _login(db_client, first)
    with db_client.websocket_connect(f"/conversations/{conversation_id}/ws") as websocket:
        event = websocket.receive_json()
        assert event["type"] == "connected"
        assert event["conversation_id"] == conversation_id


def test_websocket_receives_http_message(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)
    conversation_id = _create_conversation(db_client, first, second)

    _login(db_client, first)
    with db_client.websocket_connect(f"/conversations/{conversation_id}/ws") as websocket:
        assert websocket.receive_json()["type"] == "connected"
        response = db_client.post(
            f"/conversations/{conversation_id}/messages",
            json={"payload": {"type": "emoji", "emoji_sequence": "😀"}},
        )
        assert response.status_code == 201
        event = websocket.receive_json()
        assert event["type"] == "message"
        assert event["message"]["id"] == response.json()["id"]
        assert event["message"]["sender"]["username"] == first


def test_websocket_delivers_to_multiple_connections(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)
    conversation_id = _create_conversation(db_client, first, second)

    _login(db_client, first)
    with db_client.websocket_connect(f"/conversations/{conversation_id}/ws") as first_socket:
        assert first_socket.receive_json()["type"] == "connected"
        with db_client.websocket_connect(f"/conversations/{conversation_id}/ws") as second_socket:
            assert second_socket.receive_json()["type"] == "connected"
            response = db_client.post(
                f"/conversations/{conversation_id}/messages",
                json={"payload": {"type": "emoji", "emoji_sequence": "😀"}},
            )
            assert response.status_code == 201
            first_event = first_socket.receive_json()
            second_event = second_socket.receive_json()
            assert first_event["type"] == "message"
            assert second_event["type"] == "message"
            assert first_event["message"]["id"] == response.json()["id"]
            assert second_event["message"]["id"] == response.json()["id"]


def test_websocket_ping_and_unsupported_message(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)
    conversation_id = _create_conversation(db_client, first, second)

    _login(db_client, first)
    with db_client.websocket_connect(f"/conversations/{conversation_id}/ws") as websocket:
        assert websocket.receive_json()["type"] == "connected"
        websocket.send_json({"type": "ping"})
        assert websocket.receive_json() == {"type": "pong"}

        websocket.send_json({"type": "unsupported"})
        with pytest.raises(WebSocketDisconnect) as exc:
            websocket.receive_json()
        assert exc.value.code == 1003


def test_websocket_disconnect_cleans_registry(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)
    conversation_id = _create_conversation(db_client, first, second)

    _login(db_client, first)
    with db_client.websocket_connect(f"/conversations/{conversation_id}/ws") as websocket:
        assert websocket.receive_json()["type"] == "connected"

    assert UUID(conversation_id) not in connection_manager._connections


def test_websocket_does_not_replay_old_messages(db_client: TestClient) -> None:
    first = _unique_username("first")
    second = _unique_username("second")
    _make_friends(db_client, first, second)
    conversation_id = _create_conversation(db_client, first, second)

    _login(db_client, first)
    old_response = db_client.post(
        f"/conversations/{conversation_id}/messages",
        json={"payload": {"type": "emoji", "emoji_sequence": "😀"}},
    )
    assert old_response.status_code == 201

    with db_client.websocket_connect(f"/conversations/{conversation_id}/ws") as websocket:
        assert websocket.receive_json()["type"] == "connected"
        new_response = db_client.post(
            f"/conversations/{conversation_id}/messages",
            json={"payload": {"type": "emoji", "emoji_sequence": "👍"}},
        )
        assert new_response.status_code == 201
        event = websocket.receive_json()
        assert event["type"] == "message"
        assert event["message"]["id"] == new_response.json()["id"]
        assert event["message"]["id"] != old_response.json()["id"]
