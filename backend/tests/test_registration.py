import asyncio
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from argon2 import PasswordHasher
from pydantic import ValidationError
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.accounts.passwords import hash_password
from app.accounts.schemas import RegisterRequest
from app.accounts.service import (
    RegistrationError,
    UsernameAlreadyExistsError,
    create_user,
)
from app.database import get_db_session
from app.main import app

VALID_PAYLOAD = {
    "username": "alice",
    "display_name": "Alice",
    "password": "correct horse battery staple",
}


class UnusedSession:
    """Fail if validation unexpectedly reaches the database dependency."""

    def add(self, _user: object) -> None:
        raise AssertionError("database session must not be used")

    async def flush(self) -> None:
        raise AssertionError("database session must not be used")

    async def commit(self) -> None:
        raise AssertionError("database session must not be used")

    async def rollback(self) -> None:
        raise AssertionError("database session must not be used")


class WriteFailingSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.committed = False
        self.rolled_back = False

    def add(self, user: object) -> None:
        self.added.append(user)

    async def flush(self) -> None:
        raise SQLAlchemyError("write failed")

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class UsernameConflictSession(WriteFailingSession):
    async def flush(self) -> None:
        original = Exception("duplicate key value")
        original.constraint_name = "uq_users_username"
        raise IntegrityError("INSERT INTO users", {}, original)


@pytest.fixture
def validation_client(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    monkeypatch.setenv("CSRF_STRICT", "false")
    async def override_get_db_session() -> AsyncIterator[UnusedSession]:
        yield UnusedSession()

    app.dependency_overrides[get_db_session] = override_get_db_session
    return client


def _payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = dict(VALID_PAYLOAD)
    payload.update(overrides)
    return payload


@pytest.mark.parametrize(
    "payload",
    [
        {"display_name": "Alice", "password": "correct horse battery staple"},
        {"username": "alice", "password": "correct horse battery staple"},
        {"username": "alice", "display_name": "Alice"},
        _payload(username=""),
        _payload(username="   "),
        _payload(username="Alice"),
        _payload(username="user name"),
        _payload(username="user.name"),
        _payload(username="user😀"),
        _payload(username="a" * 33),
        _payload(display_name=""),
        _payload(display_name=" \t\n "),
        _payload(display_name="a" * 101),
        _payload(display_name="Hi 😀"),
        _payload(password=""),
        _payload(password="        "),
        _payload(password="shortpw"),
        _payload(password="x" * 129),
    ],
)
def test_register_rejects_invalid_payloads(
    validation_client: TestClient,
    payload: dict[str, object],
) -> None:
    response = validation_client.post("/auth/register", json=payload)

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert detail
    for error in detail:
        assert {"type", "loc", "msg"} <= error.keys()
    assert VALID_PAYLOAD["password"] not in response.text


@pytest.mark.parametrize("field", ["id", "created_at", "updated_at"])
def test_register_rejects_server_managed_fields(
    validation_client: TestClient,
    field: str,
) -> None:
    payload = _payload(**{field: str(uuid4())})

    response = validation_client.post("/auth/register", json=payload)

    assert response.status_code == 422
    assert any(field in error["loc"] for error in response.json()["detail"])


def test_validation_error_redacts_password_input(
    validation_client: TestClient,
) -> None:
    password = "shortpw"
    response = validation_client.post(
        "/auth/register",
        json=_payload(password=password),
    )

    assert response.status_code == 422
    assert password not in response.text
    error = response.json()["detail"][0]
    assert error["loc"] == ["body", "password"]
    assert error["input"] == "[redacted]"


def test_validation_error_redacts_password_in_request_body(
    validation_client: TestClient,
) -> None:
    password = "super-secret-password"
    response = validation_client.post(
        "/auth/register",
        json={"username": "alice", "password": password},
    )

    assert response.status_code == 422
    assert password not in response.text
    error = response.json()["detail"][0]
    assert error["input"]["password"] == "[redacted]"


def test_register_request_accepts_allowed_username_and_display_name() -> None:
    request = RegisterRequest.model_validate(
        {
            "username": "алёша_1-2",
            "display_name": "Hi :-)",
            "password": "correct horse battery staple",
        }
    )

    assert request.username == "алёша_1-2"
    assert request.display_name == "Hi :-)"


def test_display_name_validation_accepts_normal_name_and_ascii_smiley() -> None:
    for display_name in ("Alice", "Hi :-)"):
        request = RegisterRequest.model_validate(
            {
                "username": "alice",
                "display_name": display_name,
                "password": "correct horse battery staple",
            }
        )
        assert request.display_name == display_name


def test_display_name_validation_rejects_emoji() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest.model_validate(
            {
                "username": "alice",
                "display_name": "Hi 😀",
                "password": "correct horse battery staple",
            }
        )


def test_hash_password_uses_argon2id() -> None:
    password = "correct horse battery staple"
    password_hash = hash_password(password)

    assert password_hash != password
    assert password_hash.startswith("$argon2id$v=19$m=65536,t=3,p=4$")
    assert len(password_hash) <= 255
    assert PasswordHasher().verify(password_hash, password)
    assert hash_password(password) != password_hash


def test_create_user_rolls_back_on_write_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.accounts.service.hash_password",
        lambda _password: "test-password-hash",
    )
    request = RegisterRequest.model_validate(VALID_PAYLOAD)

    async def run() -> None:
        session = WriteFailingSession()
        with pytest.raises(RegistrationError):
            await create_user(session, request)

        assert session.rolled_back is True
        assert session.committed is False
        assert len(session.added) == 1
        assert session.added[0].password_hash == "test-password-hash"

    asyncio.run(run())


def test_create_user_maps_username_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.accounts.service.hash_password",
        lambda _password: "test-password-hash",
    )
    request = RegisterRequest.model_validate(VALID_PAYLOAD)

    async def run() -> None:
        session = UsernameConflictSession()
        with pytest.raises(UsernameAlreadyExistsError):
            await create_user(session, request)

        assert session.rolled_back is True
        assert session.committed is False

    asyncio.run(run())
