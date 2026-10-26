from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_db_session
from app.main import app


class FakeSession:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.statements: list[object] = []

    async def execute(self, statement: object) -> None:
        if self.error is not None:
            raise self.error
        self.statements.append(statement)


def _use_session(session: FakeSession) -> None:
    async def override_get_db_session() -> AsyncIterator[FakeSession]:
        yield session

    app.dependency_overrides[get_db_session] = override_get_db_session


def test_ready_returns_ok_when_database_is_available(client: TestClient) -> None:
    session = FakeSession()
    _use_session(session)

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert len(session.statements) == 1
    assert str(session.statements[0]) == "SELECT 1"


@pytest.mark.parametrize(
    "error",
    [
        SQLAlchemyError("connection failed"),
        ConnectionRefusedError(61, "connection refused"),
    ],
)
def test_ready_returns_503_when_database_is_unavailable(
    client: TestClient,
    error: Exception,
) -> None:
    session = FakeSession(error=error)
    _use_session(session)

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
    assert "connection failed" not in response.text
    assert "connection refused" not in response.text


def test_ready_returns_503_without_database_configuration(client: TestClient) -> None:
    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}
