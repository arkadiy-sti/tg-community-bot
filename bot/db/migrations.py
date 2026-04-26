"""Idempotent миграции схемы.

Стратегия MVP без Alembic: при старте бота проверяем наличие колонок
и добавляем недостающие через ALTER TABLE. Подходит для PostgreSQL и SQLite.

В будущем (после MVP) — заменить на полноценный Alembic.
"""
from __future__ import annotations

import logging
from typing import Iterable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

log = logging.getLogger(__name__)


# (table, column, ddl_type) — ddl_type — string для ALTER TABLE
_USER_COLUMNS: list[tuple[str, str, str]] = [
    ("users", "language", "VARCHAR(8) NOT NULL DEFAULT 'ru'"),
    ("users", "role", "VARCHAR(32)"),
    ("users", "display_name", "VARCHAR(128)"),
    ("users", "area", "VARCHAR(256)"),
    ("users", "phone", "VARCHAR(64)"),
    ("users", "bio", "TEXT"),
    ("users", "registered_at", "TIMESTAMP WITH TIME ZONE"),
]


async def _existing_columns(conn, table: str) -> set[str]:
    """Вернуть множество имён колонок для таблицы (PostgreSQL information_schema)."""
    dialect = conn.dialect.name
    if dialect == "postgresql":
        rs = await conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = :t"
            ),
            {"t": table},
        )
        return {row[0] for row in rs}
    if dialect == "sqlite":
        rs = await conn.execute(text(f"PRAGMA table_info({table})"))
        return {row[1] for row in rs}
    log.warning("Неизвестный диалект %s — пропускаю check колонок", dialect)
    return set()


async def _ensure_columns(conn, columns: Iterable[tuple[str, str, str]]) -> None:
    seen_cache: dict[str, set[str]] = {}
    for table, column, ddl in columns:
        if table not in seen_cache:
            seen_cache[table] = await _existing_columns(conn, table)
        if column in seen_cache[table]:
            continue
        log.info("MIGRATION: ALTER TABLE %s ADD COLUMN %s %s", table, column, ddl)
        # IF NOT EXISTS не поддерживается SQLite — мы уже проверили существование выше.
        await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
        seen_cache[table].add(column)


async def run_migrations(engine: AsyncEngine) -> None:
    """Прогнать все idempotent миграции. Безопасно вызывать на каждом старте."""
    async with engine.begin() as conn:
        # 1. Колонки в users (могут отсутствовать в проде)
        await _ensure_columns(conn, _USER_COLUMNS)
    log.info("Миграции применены")
