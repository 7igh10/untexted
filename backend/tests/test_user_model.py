from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base
from app.models import User


def test_user_model_uses_expected_table_and_primary_key() -> None:
    table = User.__table__

    assert User.__tablename__ == "users"
    assert table.name == "users"
    assert [column.name for column in table.primary_key.columns] == ["id"]
    assert isinstance(table.c.id.type, UUID)


def test_user_model_declares_required_columns_and_constraints() -> None:
    table = User.__table__

    assert set(table.columns.keys()) == {
        "id",
        "username",
        "display_name",
        "password_hash",
        "created_at",
        "updated_at",
    }
    assert isinstance(table.c.username.type, String)
    assert table.c.username.type.length == 32
    assert table.c.username.nullable is False
    assert isinstance(table.c.display_name.type, String)
    assert table.c.display_name.type.length == 100
    assert table.c.display_name.nullable is False
    assert isinstance(table.c.password_hash.type, String)
    assert table.c.password_hash.type.length == 255
    assert table.c.password_hash.nullable is False

    for name in ("created_at", "updated_at"):
        column = table.c[name]
        assert isinstance(column.type, DateTime)
        assert column.type.timezone is True
        assert column.nullable is False
        assert column.server_default is not None

    assert table.c.updated_at.onupdate is not None

    unique_constraints = [
        constraint
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    ]
    assert any(
        constraint.name == "uq_users_username"
        and [column.name for column in constraint.columns] == ["username"]
        for constraint in unique_constraints
    )


def test_user_model_is_registered_in_base_metadata() -> None:
    assert Base.metadata.tables["users"] is User.__table__


def test_user_repr_does_not_expose_password_hash() -> None:
    user = User(
        username="alice",
        display_name="Alice",
        password_hash="$argon2id$secret-hash",
    )

    assert "$argon2id$secret-hash" not in repr(user)
