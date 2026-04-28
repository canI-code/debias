from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.database import Base


@pytest.fixture()
def fake_redis() -> object:
    class FakeRedis:
        def __init__(self) -> None:
            self.store: dict[str, int] = {}

        def incr(self, key: str) -> int:
            self.store[key] = self.store.get(key, 0) + 1
            return self.store[key]

        def expire(self, key: str, ttl: int) -> bool:  # noqa: ARG002
            return True

        def ping(self) -> bool:
            return True

        def llen(self, key: str) -> int:
            return self.store.get(key, 0)

        def close(self) -> None:
            return None

    return FakeRedis()


@pytest.fixture()
async def sqlite_session_maker(tmp_path) -> Generator[async_sessionmaker, None, None]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}", future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    yield session_maker
    await engine.dispose()
