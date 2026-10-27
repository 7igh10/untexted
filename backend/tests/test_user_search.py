import pytest
from pydantic import ValidationError

from app.users.schemas import UserSearchQuery


def test_user_search_query_normalizes_and_validates() -> None:
    query = UserSearchQuery(q="  AlIcE  ")

    assert query.q == "alice"


@pytest.mark.parametrize("value", ["", "   "])
def test_user_search_query_rejects_blank_values(value: str) -> None:
    with pytest.raises(ValidationError):
        UserSearchQuery(q=value)


def test_user_search_query_rejects_too_long_value() -> None:
    with pytest.raises(ValidationError):
        UserSearchQuery(q="a" * 33)


def test_user_search_query_accepts_special_characters() -> None:
    for value in ["a%b", "a_b", "a\\b", "alice-test_1"]:
        query = UserSearchQuery(q=value)
        assert query.q == value.casefold().strip()


def test_user_search_requires_authentication() -> None:
    from unittest.mock import Mock

    from fastapi.testclient import TestClient

    from app.database import get_db_session
    from app.main import app

    class EmptySession:
        async def execute(self, _statement: object) -> Mock:
            result = Mock()
            result.scalar_one_or_none.return_value = None
            return result

    async def override_get_db_session():
        yield EmptySession()

    app.dependency_overrides[get_db_session] = override_get_db_session
    try:
        with TestClient(app) as client:
            response = client.get("/users/search", params={"q": "alice"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}