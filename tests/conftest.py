"""Общие фикстуры для тестов."""
from __future__ import annotations

import os

# Минимальный .env для тестов — до импорта bot.config
os.environ.setdefault("BOT_TOKEN", "123:test-token-for-unit-tests")
os.environ.setdefault("ADMIN_IDS", "111")
os.environ.setdefault("DB_URL", "sqlite+aiosqlite:///:memory:")

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.db import database as db_mod
from bot.db.database import Base


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    """Свежая in-memory БД для каждого теста."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        from bot.db import models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    # Прокидываем factory в модуль, чтобы get_session() работал
    db_mod._engine = engine
    db_mod._session_factory = factory
    async with factory() as s:
        yield s
    await engine.dispose()
    db_mod._engine = None
    db_mod._session_factory = None


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
