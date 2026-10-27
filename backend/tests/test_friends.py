import pytest
from pydantic import ValidationError

from app.friends.schemas import FriendRequestCreate


def test_friend_request_create_requires_exactly_one_identifier() -> None:
    with pytest.raises(ValidationError):
        FriendRequestCreate()

    with pytest.raises(ValidationError):
        FriendRequestCreate(username="alice", user_id="5f0c1c1e-7d1a-4e4a-9c7e-3f0b1a2c3d4e")


def test_friend_request_create_accepts_username() -> None:
    request = FriendRequestCreate(username="alice")

    assert request.username == "alice"
    assert request.user_id is None


def test_friend_request_create_accepts_user_id() -> None:
    user_id = "5f0c1c1e-7d1a-4e4a-9c7e-3f0b1a2c3d4e"
    request = FriendRequestCreate(user_id=user_id)

    assert str(request.user_id) == user_id
    assert request.username is None


def test_friend_request_create_rejects_mismatched_identifiers() -> None:
    with pytest.raises(ValidationError):
        FriendRequestCreate(
            username="alice",
            user_id="5f0c1c1e-7d1a-4e4a-9c7e-3f0b1a2c3d4e",
            recipient_id="6f0c1c1e-7d1a-4e4a-9c7e-3f0b1a2c3d4f",
        )