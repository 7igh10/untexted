from pydantic import BaseModel, Field, field_validator

from app.models.user import USERNAME_MAX_LENGTH


class UserSearchQuery(BaseModel):
    """Query parameters for username search."""

    q: str = Field(min_length=1, max_length=USERNAME_MAX_LENGTH)

    @field_validator("q")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        value = value.strip().casefold()
        if not value:
            raise ValueError("must not be empty or whitespace-only")
        if len(value) > USERNAME_MAX_LENGTH:
            raise ValueError(f"must be at most {USERNAME_MAX_LENGTH} characters")
        return value
