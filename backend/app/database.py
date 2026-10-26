import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

SessionFactory = async_sessionmaker[AsyncSession]


class Base(DeclarativeBase):
    """Base class for future SQLAlchemy models."""


def database_url_from_env() -> str | None:
    value = os.getenv("DATABASE_URL")
    return value or None


def async_database_url(value: str) -> URL:
    url = make_url(value)
    if url.drivername in {"postgres", "postgresql"}:
        return url.set(drivername="postgresql+asyncpg")
    return url


def create_database_engine(database_url: str) -> AsyncEngine:
    """Create the async engine for a PostgreSQL database URL."""
    return create_async_engine(
        async_database_url(database_url),
        pool_pre_ping=True,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    database_url = database_url_from_env()
    engine = create_database_engine(database_url) if database_url else None
    app.state.db_engine = engine
    app.state.db_session_factory = (
        async_sessionmaker(engine, expire_on_commit=False) if engine else None
    )

    try:
        yield
    finally:
        if engine is not None:
            await engine.dispose()


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory: SessionFactory | None = getattr(
        request.app.state,
        "db_session_factory",
        None,
    )
    if session_factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )

    async with session_factory() as session:
        yield session


async def database_is_ready(session: AsyncSession) -> bool:
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        # Connection failures are not consistently wrapped in SQLAlchemyError.
        return False
    return True
