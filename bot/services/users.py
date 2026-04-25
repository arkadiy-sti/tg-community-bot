"""Работа с пользователями в БД."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import User


async def upsert_user(
    session: AsyncSession,
    tg_id: int,
    username: str | None,
    full_name: str | None,
) -> User:
    """Создать или обновить пользователя, вернуть его."""
    result = await session.execute(select(User).where(User.tg_id == tg_id))
    user = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if user is None:
        user = User(
            tg_id=tg_id,
            username=username,
            full_name=full_name,
            joined_at=now,
            last_active_at=now,
        )
        session.add(user)
        await session.flush()
    else:
        user.username = username
        user.full_name = full_name
        user.last_active_at = now
    await session.commit()
    return user


async def get_user(session: AsyncSession, tg_id: int) -> User | None:
    result = await session.execute(select(User).where(User.tg_id == tg_id))
    return result.scalar_one_or_none()


async def mark_captcha_passed(session: AsyncSession, tg_id: int) -> None:
    await session.execute(
        update(User).where(User.tg_id == tg_id).values(captcha_passed=True)
    )
    await session.commit()


async def ban_user(session: AsyncSession, tg_id: int) -> None:
    await session.execute(
        update(User).where(User.tg_id == tg_id).values(is_banned=True)
    )
    await session.commit()


async def unban_user(session: AsyncSession, tg_id: int) -> None:
    await session.execute(
        update(User).where(User.tg_id == tg_id).values(is_banned=False, warnings=0)
    )
    await session.commit()


async def add_warning(session: AsyncSession, tg_id: int) -> int:
    user = await get_user(session, tg_id)
    if user is None:
        return 0
    user.warnings += 1
    await session.commit()
    return user.warnings


async def is_new_user(session: AsyncSession, tg_id: int, hours: int) -> bool:
    """True, если пользователь в сообществе меньше N часов."""
    user = await get_user(session, tg_id)
    if user is None:
        return True
    threshold = datetime.now(timezone.utc) - timedelta(hours=hours)
    joined = user.joined_at
    # SQLite возвращает naive datetime — привести к UTC
    if joined.tzinfo is None:
        joined = joined.replace(tzinfo=timezone.utc)
    return joined > threshold


async def get_stats(session: AsyncSession) -> dict:
    """Агрегированная статистика для /stats."""
    total = await session.scalar(select(func.count()).select_from(User))
    banned = await session.scalar(
        select(func.count()).select_from(User).where(User.is_banned.is_(True))
    )
    now = datetime.now(timezone.utc)
    active_7d = await session.scalar(
        select(func.count())
        .select_from(User)
        .where(User.last_active_at >= now - timedelta(days=7))
    )
    new_24h = await session.scalar(
        select(func.count())
        .select_from(User)
        .where(User.joined_at >= now - timedelta(hours=24))
    )
    return {
        "total": total or 0,
        "banned": banned or 0,
        "active_7d": active_7d or 0,
        "new_24h": new_24h or 0,
    }


async def list_users_for_broadcast(
    session: AsyncSession, segment: str = "all"
) -> list[int]:
    """Список tg_id для рассылки по сегменту."""
    stmt = select(User.tg_id).where(User.is_banned.is_(False))
    now = datetime.now(timezone.utc)
    if segment == "active_7d":
        stmt = stmt.where(User.last_active_at >= now - timedelta(days=7))
    elif segment == "new_users":
        stmt = stmt.where(User.joined_at >= now - timedelta(days=7))
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]
