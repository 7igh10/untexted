import asyncio
import os
from uuid import uuid4

import pytest
from sqlalchemy import delete, insert, inspect, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.database import async_database_url
from app.models import User

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL is not set",
)


def _create_engine() -> AsyncEngine:
    assert TEST_DATABASE_URL is not None
    return create_async_engine(async_database_url(TEST_DATABASE_URL))


def test_users_table_and_constraints_exist_in_postgresql() -> None:
    asyncio.run(_assert_users_table_and_constraints())


async def _assert_users_table_and_constraints() -> None:
    engine = _create_engine()
    try:
        async with engine.connect() as connection:
            table_names = await connection.run_sync(
                lambda sync_connection: inspect(sync_connection).get_table_names()
            )
            primary_key = await connection.run_sync(
                lambda sync_connection: inspect(sync_connection).get_pk_constraint(
                    "users"
                )
            )
            unique_constraints = await connection.run_sync(
                lambda sync_connection: inspect(sync_connection).get_unique_constraints(
                    "users"
                )
            )
            columns = await connection.run_sync(
                lambda sync_connection: {
                    column["name"]: column
                    for column in inspect(sync_connection).get_columns("users")
                }
            )
    finally:
        await engine.dispose()

    assert "users" in table_names
    assert primary_key["constrained_columns"] == ["id"]
    assert columns["username"]["type"].length == 32
    assert columns["display_name"]["type"].length == 100
    assert any(
        constraint["name"] == "uq_users_username"
        and constraint["column_names"] == ["username"]
        for constraint in unique_constraints
    )


def test_username_unique_constraint_is_enforced_by_postgresql() -> None:
    asyncio.run(_assert_username_unique())


async def _assert_username_unique() -> None:
    engine = _create_engine()
    username = f"user-{uuid4().hex[:20]}"
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                result = await connection.execute(
                    insert(User)
                    .values(username=username, display_name="First")
                    .returning(User.id, User.created_at, User.updated_at)
                )
                inserted = result.one()

                assert inserted.id is not None
                assert inserted.created_at.tzinfo is not None
                assert inserted.updated_at.tzinfo is not None

                with pytest.raises(IntegrityError) as error:
                    await connection.execute(
                        insert(User).values(
                            username=username,
                            display_name="Second",
                        )
                    )

                assert "uq_users_username" in str(error.value)
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()


def test_updated_at_is_refreshed_on_update() -> None:
    asyncio.run(_assert_updated_at_is_refreshed())


async def _assert_updated_at_is_refreshed() -> None:
    engine = _create_engine()
    username = f"user-{uuid4().hex[:20]}"
    user_id = None
    try:
        async with engine.begin() as connection:
            result = await connection.execute(
                insert(User)
                .values(username=username, display_name="Before")
                .returning(User.id, User.updated_at)
            )
            inserted = result.one()
            user_id = inserted.id

        await asyncio.sleep(0.01)

        async with engine.begin() as connection:
            result = await connection.execute(
                update(User)
                .where(User.id == user_id)
                .values(display_name="After")
                .returning(User.updated_at)
            )
            updated_at = result.scalar_one()

        assert updated_at > inserted.updated_at
    finally:
        if user_id is not None:
            async with engine.begin() as connection:
                await connection.execute(delete(User).where(User.id == user_id))
        await engine.dispose()
