import asyncio
import os
import uuid

from sqlalchemy import func, insert, select
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.conversations.service import get_or_create_conversation
from app.database import create_database_engine
from app.friends.service import friendship_exists
from app.messages.schemas import EmojiMessagePayload
from app.messages.service import send_message
from app.models import Conversation, Friendship, Message, User

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


def test_message_is_persisted_with_sender_and_conversation() -> None:
    first = f"msgfirst{uuid4().hex[:8]}"
    second = f"msgsecond{uuid4().hex[:8]}"
    asyncio.run(_create_users([first, second]))
    asyncio.run(_create_friendship(first, second))

    async def run() -> str:
        first_user = await _get_user(first)
        engine = create_database_engine(_test_database_url())
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with session_factory() as session:
                conversation, _ = await get_or_create_conversation(
                    session, first_user, username=second
                )
                await session.commit()
                message = await send_message(
                    session,
                    conversation.id,
                    first_user,
                    EmojiMessagePayload(type="emoji", emoji_sequence="😀"),
                )
                await session.commit()
                return str(message.id)
        finally:
            await engine.dispose()

    message_id = asyncio.run(run())

    async def check() -> None:
        engine = create_database_engine(_test_database_url())
        try:
            async with engine.connect() as connection:
                row = (
                    await connection.execute(
                        select(Message.type, Message.payload, Message.schema_version).where(
                            Message.id == uuid.UUID(message_id)
                        )
                    )
                ).one()
                assert row.type == "emoji"
                assert row.payload == {"type": "emoji", "emoji_sequence": "😀"}
                assert row.schema_version == 1
        finally:
            await engine.dispose()

    asyncio.run(check())


def test_message_count_for_conversation() -> None:
    first = f"msgcountfirst{uuid4().hex[:8]}"
    second = f"msgcountsecond{uuid4().hex[:8]}"
    asyncio.run(_create_users([first, second]))
    asyncio.run(_create_friendship(first, second))

    async def run() -> None:
        first_user = await _get_user(first)
        engine = create_database_engine(_test_database_url())
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with session_factory() as session:
                conversation, _ = await get_or_create_conversation(
                    session, first_user, username=second
                )
                await session.commit()
                for _ in range(3):
                    await send_message(
                        session,
                        conversation.id,
                        first_user,
                        EmojiMessagePayload(type="emoji", emoji_sequence="😀"),
                    )
                    await session.commit()
        finally:
            await engine.dispose()

    asyncio.run(run())

    async def check() -> int:
        first_user = await _get_user(first)
        second_user = await _get_user(second)
        low, high = sorted((first_user.id, second_user.id))
        engine = create_database_engine(_test_database_url())
        try:
            async with engine.connect() as connection:
                conversation_id = (
                    await connection.execute(
                        select(Conversation.id).where(
                            Conversation.user_one_id == low,
                            Conversation.user_two_id == high,
                        )
                    )
                ).scalar_one()
                count = (
                    await connection.execute(
                        select(func.count())
                        .select_from(Message)
                        .where(Message.conversation_id == conversation_id)
                    )
                ).scalar_one()
                return count
        finally:
            await engine.dispose()

    assert asyncio.run(check()) == 3
