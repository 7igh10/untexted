from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from app.models.user import DISPLAY_NAME_MAX_LENGTH, USERNAME_MAX_LENGTH

USERNAME_PATTERN = r"^[a-zа-яё0-9_-]+$"
DISPLAY_NAME_PATTERN = (
    r"^[A-Za-z\u0400-\u04FF0-9 !\"#$%&'()*+,\-./:;<=>?@\[\\\]^_`{|}~]+$"
)
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128


class RegisterRequest(BaseModel):
    """Payload accepted by the registration endpoint."""

    model_config = ConfigDict(extra="forbid")

    username: str = Field(
        min_length=1,
        max_length=USERNAME_MAX_LENGTH,
        pattern=USERNAME_PATTERN,
        description=(
            "Lowercase Latin letters, Cyrillic letters, digits, underscores, "
            "and hyphens, up to 32 characters."
        ),
    )
    display_name: str = Field(
        min_length=1,
        max_length=DISPLAY_NAME_MAX_LENGTH,
        pattern=DISPLAY_NAME_PATTERN,
        description=(
            "Latin and Cyrillic letters, digits, spaces, and printable ASCII "
            "special characters, up to 100 characters; emoji are not allowed."
        ),
    )
    password: SecretStr = Field(
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
        description="Password from 8 to 128 characters.",
    )

    @field_validator("username", "display_name")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty or whitespace-only")
        return value

    @field_validator("password")
    @classmethod
    def reject_blank_password(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("must not be empty or whitespace-only")
        return value


class UserPublic(BaseModel):
    """Public user data returned after registration."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    display_name: str
    created_at: datetime
