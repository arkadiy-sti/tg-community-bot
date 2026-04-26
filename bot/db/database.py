"""Подключение к БД и sessionmaker."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _ensure_sqlite_dir(db_url: str) -> None:
    """Для SQLite создать директорию, если её нет."""
    if "sqlite" in db_url and ":///" in db_url:
        path_part = db_url.split(":///", 1)[1]
        if path_part and path_part != ":memory:":
            Path(path_part).parent.mkdir(parents=True, exist_ok=True)


async def init_db(db_url: str) -> None:
    """Инициализация движка, create_all для новых таблиц, idempotent миграции."""
    global _engine, _session_factory
    _ensure_sqlite_dir(db_url)
    _engine = create_async_engine(db_url, echo=False, future=True)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)

    # Импорт моделей нужен до create_all
    from bot.db import models  # noqa: F401

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # ALTER TABLE для расширения существующих таблиц (users в проде)
    from bot.db.migrations import run_migrations

    await run_migrations(_engine)

    # Idempotent заливка справочника тегов
    from bot.db.seed_tags import seed_tags

    await seed_tags(_engine)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("DB не инициализирована — вызови init_db() на старте")
    async with _session_factory() as session:
        yield session


async def dispose() -> None:
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
