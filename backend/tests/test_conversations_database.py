import asyncio
import os

import pytest
from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.conversations.service import get_or_create_conversation
from app.database import create_database_engine
from app.friends.service import friendship_exists
from app.models import Conversation, Friendship, User

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL is not set",
)


def _test_database_url() -> str:
    assert TEST_DATABASE_URL is not None
    return TEST_DATABASE_URL


async def _create_users(usernames: list[str]) -> None:
    engine = create_database_engine(_test_database_url())
    try:
        async with engine.begin() as connection:
            await connection.execute(
                insert(User).values(
                    [
                        {
                            "username": username,
                            "display_name": f"Display {username}",
                            "password_hash": "test-password-hash",
                        }
                        for username in usernames
                    ]
                )
            )
    finally:
        await engine.dispose()


async def _get_user(username: str) -> User:
    engine = create_database_engine(_test_database_url())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            result = await session.execute(select(User).where(User.username == username))
            return result.scalar_one()
    finally:
        await engine.dispose()


async def _create_friendship(first: str, second: str) -> None:
    first_user = await _get_user(first)
    second_user = await _get_user(second)
    low, high = sorted((first_user.id, second_user.id))
    engine = create_database_engine(_test_database_url())
    try:
        async with engine.begin() as connection:
            await connection.execute(
                insert(Friendship).values(user_id=low, friend_id=high)
            )
    finally:
        await engine.dispose()


async def _count_conversations(first: str, second: str) -> int:
    first_user = await _get_user(first)
    second_user = await _get_user(second)
    low, high = sorted((first_user.id, second_user.id))
    engine = create_database_engine(_test_database_url())
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                select(func.count())
                .select_from(Conversation)
                .where(
                    Conversation.user_one_id == low,
                    Conversation.user_two_id == high,
                )
            )
            return result.scalar_one()
    finally:
        await engine.dispose()


async def _create_conversation(username: str, recipient: str) -> tuple[str, bool]:
    user = await _get_user(username)
    engine = create_database_engine(_test_database_url())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            conversation, created = await get_or_create_conversation(
                session, user, username=recipient
            )
            await session.commit()
            return str(conversation.id), created
    finally:
        await engine.dispose()


def test_conversation_participants_are_normalized() -> None:
    first = f"normfirst{__import__('uuid').uuid4().hex[:8]}"
    second = f"normsecond{__import__('uuid').uuid4().hex[:8]}"
    asyncio.run(_create_users([first, second]))
    asyncio.run(_create_friendship(first, second))

    conversation_id, created = asyncio.run(_create_conversation(first, second))
    assert created is True

    async def check() -> None:
        first_user = await _get_user(first)
        second_user = await _get_user(second)
        low, high = sorted((first_user.id, second_user.id))
        engine = create_database_engine(_test_database_url())
        try:
            async with engine.connect() as connection:
                row = (
                    await connection.execute(
                        select(Conversation.user_one_id, Conversation.user_two_id).where(
                            Conversation.id == __import__("uuid").UUID(conversation_id)
                        )
                    )
                ).one()
                assert row.user_one_id == low
                assert row.user_two_id == high
                assert row.user_one_id < row.user_two_id
        finally:
            await engine.dispose()

    asyncio.run(check())


def test_concurrent_conversation_creation() -> None:
    first = f"convfirst{__import__('uuid').uuid4().hex[:8]}"
    second = f"convsecond{__import__('uuid').uuid4().hex[:8]}"
    asyncio.run(_create_users([first, second]))
    asyncio.run(_create_friendship(first, second))

    async def run() -> None:
        results = await asyncio.gather(
            _create_conversation(first, second),
            _create_conversation(second, first),
            return_exceptions=True,
        )
        assert all(not isinstance(result, Exception) for result in results)
        ids = {result[0] for result in results}
        assert len(ids) == 1

    asyncio.run(run())

    assert asyncio.run(_count_conversations(first, second)) == 1
