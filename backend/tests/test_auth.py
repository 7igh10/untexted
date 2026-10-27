import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.accounts.passwords import (
    DUMMY_PASSWORD_HASH,
    hash_password,
    verify_password,
)
from app.accounts.sessions import hash_session_token
from app.accounts.rate_limit import LoginRateLimiter
from app.accounts.schemas import LoginRequest
from app.accounts.sessions import (
    SESSION_COOKIE_NAME,
    SESSION_LIFETIME,
    SESSION_RENEWAL_THRESHOLD,
    allowed_origins,
    clear_session_cookie,
    set_session_cookie,
    validate_csrf,
)
from app.database import get_db_session
from app.main import app


def test_verify_password_accepts_correct_password() -> None:
    password = "correct horse battery staple"
    password_hash = hash_password(password)

    assert verify_password(password, password_hash) is True


def test_verify_password_rejects_wrong_password() -> None:
    password_hash = hash_password("correct horse battery staple")

    assert verify_password("wrong password", password_hash) is False


def test_verify_password_rejects_invalid_hash() -> None:
    assert verify_password("password", "not-an-argon2-hash") is False


def test_dummy_password_hash_is_verifiable() -> None:
    assert DUMMY_PASSWORD_HASH.startswith("$argon2id$")
    assert verify_password("not-a-real-password", DUMMY_PASSWORD_HASH) is True


def test_session_token_hash_is_deterministic_and_not_raw_token() -> None:
    token = "raw-session-token"

    assert hash_session_token(token) == hash_session_token(token)
    assert hash_session_token(token) != token
    assert len(hash_session_token(token)) == 64


def test_login_request_rejects_empty_and_too_long_values() -> None:
    with pytest.raises(ValueError):
        LoginRequest(username="alice", password="")

    with pytest.raises(ValueError):
        LoginRequest(username="a" * 33, password="password")


def test_rate_limiter_blocks_after_account_limit() -> None:
    limiter = LoginRateLimiter(
        account_limit=2,
        account_window_minutes=15,
        ip_limit=10,
        ip_window_minutes=15,
    )

    async def run() -> None:
        assert await limiter.check("alice", "127.0.0.1") == (True, 0)
        await limiter.record_failure("alice", "127.0.0.1")
        await limiter.record_failure("alice", "127.0.0.1")

        allowed, retry_after = await limiter.check("alice", "127.0.0.1")
        assert allowed is False
        assert retry_after >= 1

    asyncio.run(run())


def test_rate_limiter_blocks_after_ip_limit() -> None:
    limiter = LoginRateLimiter(
        account_limit=10,
        account_window_minutes=15,
        ip_limit=2,
        ip_window_minutes=15,
    )

    async def run() -> None:
        await limiter.record_failure("alice", "127.0.0.1")
        await limiter.record_failure("bob", "127.0.0.1")

        allowed, retry_after = await limiter.check("charlie", "127.0.0.1")
        assert allowed is False
        assert retry_after >= 1

    asyncio.run(run())


def test_rate_limiter_resets_account_after_success() -> None:
    limiter = LoginRateLimiter(
        account_limit=2,
        account_window_minutes=15,
        ip_limit=10,
        ip_window_minutes=15,
    )

    async def run() -> None:
        await limiter.record_failure("alice", "127.0.0.1")
        await limiter.record_failure("alice", "127.0.0.1")
        await limiter.record_success("alice", "127.0.0.1")

        allowed, _ = await limiter.check("alice", "127.0.0.1")
        assert allowed is True

    asyncio.run(run())


def test_csrf_allows_missing_origin_by_default() -> None:
    request = Mock(spec=Request)
    request.method = "POST"
    request.headers = {}
    request.url.scheme = "http"
    request.url.netloc = "localhost:8000"

    validate_csrf(request)


def test_csrf_rejects_disallowed_origin() -> None:
    request = Mock(spec=Request)
    request.method = "POST"
    request.headers = {"origin": "https://evil.example"}
    request.url.scheme = "http"
    request.url.netloc = "localhost:8000"

    with pytest.raises(Exception):
        validate_csrf(request)


def test_csrf_allows_configured_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://app.example")
    request = Mock(spec=Request)
    request.method = "POST"
    request.headers = {"origin": "https://app.example"}
    request.url.scheme = "http"
    request.url.netloc = "localhost:8000"

    validate_csrf(request)


def test_cookie_attributes_are_set_correctly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COOKIE_SECURE", "false")
    response = Mock()
    expires_at = datetime.now(timezone.utc) + SESSION_LIFETIME

    set_session_cookie(response, "raw-token", expires_at)
    response.set_cookie.assert_called_once()
    kwargs = response.set_cookie.call_args.kwargs
    assert kwargs["key"] == "session"
    assert kwargs["value"] == "raw-token"
    assert kwargs["httponly"] is True
    assert kwargs["secure"] is False
    assert kwargs["samesite"] == "lax"
    assert kwargs["path"] == "/"
    assert kwargs["max_age"] >= 0

    clear_session_cookie(response)
    response.delete_cookie.assert_called_once()
    delete_kwargs = response.delete_cookie.call_args.kwargs
    assert delete_kwargs["key"] == "session"
    assert delete_kwargs["path"] == "/"
    assert delete_kwargs["samesite"] == "lax"


def test_validation_error_handler_still_redacts_password(
    client: TestClient,
) -> None:
    async def override_get_db_session():
        yield None

    app.dependency_overrides[get_db_session] = override_get_db_session
    try:
        response = client.post(
            "/auth/register",
            json={"username": "alice", "password": "super-secret-password"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert "super-secret-password" not in response.text
    assert response.json()["detail"][0]["input"]["password"] == "[redacted]"