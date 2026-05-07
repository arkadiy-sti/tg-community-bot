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
    # v2 регистрации
    ("users", "contact_phone", "VARCHAR(16)"),
    ("users", "contact_whatsapp", "VARCHAR(16)"),
    ("users", "contact_email", "VARCHAR(254)"),
    ("users", "consent_data", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("users", "consent_notifications", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("users", "consent_at", "TIMESTAMP WITH TIME ZONE"),
    ("users", "is_licensed_contractor", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("users", "license_number", "VARCHAR(64)"),
    ("users", "primary_tag_id", "INTEGER"),
    # v3 soft-delete
    ("users", "is_deleted", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("users", "deleted_at", "TIMESTAMP WITH TIME ZONE"),
    ("users", "delete_count", "INTEGER NOT NULL DEFAULT 0"),
    # v4 community badges
    ("users", "badge_verified", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("users", "badge_trusted", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("users", "badge_top", "BOOLEAN NOT NULL DEFAULT FALSE"),
]

_TAG_COLUMNS: list[tuple[str, str, str]] = [
    ("tags", "is_predefined", "BOOLEAN NOT NULL DEFAULT TRUE"),
    ("tags", "is_approved", "BOOLEAN NOT NULL DEFAULT TRUE"),
    ("tags", "created_by_user_id", "INTEGER"),
    ("tags", "created_at", "TIMESTAMP WITH TIME ZONE"),
    ("tags", "usages_count", "INTEGER NOT NULL DEFAULT 0"),
]

_RESPONSE_COLUMNS: list[tuple[str, str, str]] = [
    ("responses", "is_hired", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("responses", "hired_at", "TIMESTAMP WITH TIME ZONE"),
]

_LISTING_COLUMNS: list[tuple[str, str, str]] = [
    ("listings", "num_people", "INTEGER"),
    ("listings", "engagement_kind", "VARCHAR(16)"),
    ("listings", "helper_kind", "VARCHAR(16)"),
    ("listings", "language_req", "VARCHAR(16)"),
    ("listings", "duration", "VARCHAR(16)"),
    ("listings", "urgency", "VARCHAR(16)"),
    ("listings", "budget", "VARCHAR(16)"),
    ("listings", "contact_override", "VARCHAR(254)"),
    ("listings", "location_freetext", "VARCHAR(256)"),
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


async def _ensure_table(conn, table: str, create_sql: str) -> None:
    """Создать таблицу, если её нет (idempotent для PG/SQLite)."""
    dialect = conn.dialect.name
    if dialect == "postgresql":
        rs = await conn.execute(
            text("SELECT to_regclass(:t) IS NOT NULL"),
            {"t": f"public.{table}"},
        )
        exists = bool(rs.scalar())
    elif dialect == "sqlite":
        rs = await conn.execute(
            text(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=:t"
            ),
            {"t": table},
        )
        exists = rs.first() is not None
    else:
        log.warning("Неизвестный диалект %s — пропускаю create %s", dialect, table)
        return
    if not exists:
        log.info("MIGRATION: CREATE TABLE %s", table)
        await conn.execute(text(create_sql))


_USER_TAGS_DDL_PG = """
CREATE TABLE user_tags (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uix_user_tag UNIQUE (user_id, tag_id)
)
""".strip()

_USER_TAGS_DDL_SQLITE = """
CREATE TABLE user_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    is_primary BOOLEAN NOT NULL DEFAULT 0,
    created_at TIMESTAMP,
    UNIQUE (user_id, tag_id)
)
""".strip()

_LISTING_PHOTOS_DDL_PG = """
CREATE TABLE listing_photos (
    id SERIAL PRIMARY KEY,
    listing_id INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    file_id VARCHAR(256) NOT NULL,
    caption VARCHAR(256),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
)
""".strip()

_LISTING_PHOTOS_DDL_SQLITE = """
CREATE TABLE listing_photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    file_id VARCHAR(256) NOT NULL,
    caption VARCHAR(256),
    created_at TIMESTAMP
)
""".strip()

_SUGGESTIONS_DDL_PG = """
CREATE TABLE suggestions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    text TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_resolved BOOLEAN NOT NULL DEFAULT FALSE,
    admin_note TEXT
)
""".strip()

_SUGGESTIONS_DDL_SQLITE = """
CREATE TABLE suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    text TEXT NOT NULL,
    created_at TIMESTAMP,
    is_resolved BOOLEAN NOT NULL DEFAULT 0,
    admin_note TEXT
)
""".strip()

_BANNED_TG_IDS_DDL_PG = """
CREATE TABLE banned_tg_ids (
    id SERIAL PRIMARY KEY,
    tg_id BIGINT NOT NULL UNIQUE,
    banned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    banned_by_admin_id BIGINT NOT NULL,
    reason TEXT
)
""".strip()

_BANNED_TG_IDS_DDL_SQLITE = """
CREATE TABLE banned_tg_ids (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id BIGINT NOT NULL UNIQUE,
    banned_at TIMESTAMP,
    banned_by_admin_id BIGINT NOT NULL,
    reason TEXT
)
""".strip()


async def run_migrations(engine: AsyncEngine) -> None:
    """Прогнать все idempotent миграции. Безопасно вызывать на каждом старте."""
    async with engine.begin() as conn:
        # 1. Колонки в users (могут отсутствовать в проде)
        await _ensure_columns(conn, _USER_COLUMNS)
        # 2. Колонки в tags (v2 — модерация custom тегов)
        await _ensure_columns(conn, _TAG_COLUMNS)
        # 3. Колонки в listings (v2 — структурированные поля /post)
        await _ensure_columns(conn, _LISTING_COLUMNS)
        # 3a. Колонки в responses (v2 — отметка «нанят»)
        await _ensure_columns(conn, _RESPONSE_COLUMNS)
        # 4. Таблица user_tags (v2)
        ut_ddl = (
            _USER_TAGS_DDL_PG
            if conn.dialect.name == "postgresql"
            else _USER_TAGS_DDL_SQLITE
        )
        await _ensure_table(conn, "user_tags", ut_ddl)
        # 5. Таблица listing_photos (v2)
        lp_ddl = (
            _LISTING_PHOTOS_DDL_PG
            if conn.dialect.name == "postgresql"
            else _LISTING_PHOTOS_DDL_SQLITE
        )
        await _ensure_table(conn, "listing_photos", lp_ddl)
        # 6. Таблица suggestions (фидбек о боте от юзеров)
        sg_ddl = (
            _SUGGESTIONS_DDL_PG
            if conn.dialect.name == "postgresql"
            else _SUGGESTIONS_DDL_SQLITE
        )
        await _ensure_table(conn, "suggestions", sg_ddl)
        # 7. Таблица banned_tg_ids (постоянный бан, переживает delete+register)
        bn_ddl = (
            _BANNED_TG_IDS_DDL_PG
            if conn.dialect.name == "postgresql"
            else _BANNED_TG_IDS_DDL_SQLITE
        )
        await _ensure_table(conn, "banned_tg_ids", bn_ddl)
    log.info("Миграции применены")
