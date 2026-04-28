"""Database engine and session management."""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from backend.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for SQLAlchemy models."""


@lru_cache(maxsize=1)
def _database_url() -> str:
    settings = get_settings()
    database_url = settings.DATABASE_URL.strip()
    if database_url.startswith("sqlite:///") and "+aiosqlite" not in database_url:
        return database_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    if database_url.startswith("postgresql://") and "+asyncpg" not in database_url:
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return database_url


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    """Create a singleton async SQLAlchemy engine."""

    return create_async_engine(_database_url(), future=True, pool_pre_ping=True, echo=False)


@lru_cache(maxsize=1)
def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """Create a singleton async session factory."""

    return async_sessionmaker(bind=get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields an async database session."""

    session_maker = get_session_maker()
    async with session_maker() as session:
        yield session


async def init_db() -> None:
    """Create all tables on startup."""

    from backend import models  # noqa: F401

    engine = get_engine()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def dispose_engine() -> None:
    """Dispose of the SQLAlchemy engine on shutdown."""

    engine = get_engine()
    await engine.dispose()
