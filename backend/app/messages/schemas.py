import unicodedata
from datetime import datetime
from typing import Annotated, Literal, Union
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from app.accounts.schemas import UserPublic


class EmojiMessagePayload(BaseModel):
    """Payload for an emoji message."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["emoji"]
    emoji_sequence: str = Field(min_length=1, max_length=100)

    @field_validator("emoji_sequence")
    @classmethod
    def validate_emoji_sequence(cls, value: str) -> str:
        if not value or len(value) > 100:
            raise ValueError("must contain 1 to 100 code points")
        if any(
            character.isspace()
            or unicodedata.category(character) == "Cc"
            for character in value
        ):
            raise ValueError("must not contain whitespace or control characters")
        if any(character.isalpha() for character in value):
            raise ValueError("must not contain letters")
        if not any(
            unicodedata.category(character).startswith(("S", "M"))
            for character in value
        ):
            raise ValueError("must contain at least one emoji symbol")
        for character in value:
            category = unicodedata.category(character)
            if not (
                category.startswith(("S", "M"))
                or category == "Cf"
                or character in "0123456789#*"
            ):
                raise ValueError("contains an unsupported character")
        return value


class MeetingInvitationParams(BaseModel):
    """Structured parameters for a meeting invitation template."""

    model_config = ConfigDict(extra="forbid")

    activity: str = Field(min_length=1, max_length=64)
    occurs_at: datetime
    timezone: str | None = Field(default=None, max_length=64)
    place: str | None = Field(default=None, max_length=128)

    @field_validator("occurs_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("occurs_at must include a timezone")
        return value

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                ZoneInfo(value)
            except (ValueError, LookupError) as exc:
                raise ValueError("timezone must be a valid IANA timezone") from exc
        return value


class TemplateMessagePayload(BaseModel):
    """Discriminated template payload."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["template"]
    template_id: str = Field(min_length=1, max_length=64)
    params: dict[str, str | int | float | bool | None] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_template(self) -> "TemplateMessagePayload":
        if self.template_id == "greeting":
            if self.params:
                raise ValueError("greeting does not accept parameters")
        elif self.template_id == "mood_question":
            if self.params:
                raise ValueError("mood_question does not accept parameters")
        elif self.template_id == "meeting_invitation":
            try:
                MeetingInvitationParams.model_validate(self.params)
            except Exception as exc:
                raise ValueError("invalid meeting_invitation parameters") from exc
        else:
            raise ValueError("unsupported template_id")
        return self


class LocationMessagePayload(BaseModel):
    """Payload for a static location."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["location"]
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    label: str | None = Field(default=None, max_length=128)


class TimeMessagePayload(BaseModel):
    """Payload for a selected time."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["time"]
    occurs_at: datetime
    timezone: str | None = Field(default=None, max_length=64)
    # occurs_at is an absolute instant. timezone is an optional IANA name for
    # display context and may describe the same instant in another zone.

    @field_validator("occurs_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("occurs_at must include a timezone")
        return value

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                ZoneInfo(value)
            except (ValueError, LookupError) as exc:
                raise ValueError("timezone must be a valid IANA timezone") from exc
        return value


class LinkMessagePayload(BaseModel):
    """Payload for an external link."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["link"]
    url: HttpUrl

    @model_validator(mode="after")
    def validate_url_length(self) -> "LinkMessagePayload":
        if len(str(self.url)) > 2048:
            raise ValueError("url must be at most 2048 characters")
        return self


MessagePayload = Annotated[
    Union[
        EmojiMessagePayload,
        TemplateMessagePayload,
        LocationMessagePayload,
        TimeMessagePayload,
        LinkMessagePayload,
    ],
    Field(discriminator="type"),
]


class MessageCreate(BaseModel):
    """Payload for sending a message."""

    model_config = ConfigDict(extra="forbid")

    payload: MessagePayload
    reply_to_message_id: UUID | None = None


class MessagePublic(BaseModel):
    """Public representation of a message."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    sender: UserPublic
    type: str
    schema_version: int
    payload: dict
    reply_to_message_id: UUID | None
    created_at: datetime


class MessagePage(BaseModel):
    """A page of messages in chronological order."""

    items: list[MessagePublic]
    next_cursor: str | None = None
