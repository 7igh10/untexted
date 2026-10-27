from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.accounts.schemas import UserPublic


class FriendRequestCreate(BaseModel):
    """Payload for creating a friend request."""

    model_config = ConfigDict(extra="forbid")

    username: str | None = Field(default=None, min_length=1, max_length=32)
    user_id: UUID | None = None
    recipient_id: UUID | None = None

    @model_validator(mode="after")
    def validate_recipient_identifier(self) -> "FriendRequestCreate":
        identifiers = [value for value in (self.user_id, self.recipient_id) if value is not None]
        if self.username is not None and identifiers:
            raise ValueError("provide either username or user_id, not both")
        if self.username is None and not identifiers:
            raise ValueError("username or user_id is required")
        if len(identifiers) > 1 and len(set(identifiers)) != 1:
            raise ValueError("user_id and recipient_id must be the same")
        return self


class FriendRequestPublic(BaseModel):
    """Public representation of a friend request."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    requester: UserPublic
    recipient: UserPublic
    status: Literal["pending", "accepted", "rejected"]
    created_at: datetime
    updated_at: datetime