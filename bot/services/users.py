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


async def set_language(session: AsyncSession, tg_id: int, lang: str) -> None:
    """Сохранить язык интерфейса пользователя."""
    await session.execute(
        update(User).where(User.tg_id == tg_id).values(language=lang)
    )
    await session.commit()


async def save_registration(
    session: AsyncSession,
    tg_id: int,
    *,
    role: str,
    display_name: str,
    area: str | None,
    phone: str | None,
    bio: str | None,
) -> User | None:
    """Legacy save_registration v1 — для обратной совместимости тестов."""
    user = await get_user(session, tg_id)
    if user is None:
        return None
    user.role = role
    user.display_name = display_name
    user.area = area
    user.phone = phone
    user.bio = bio
    user.registered_at = datetime.now(timezone.utc)
    await session.commit()
    return user


async def save_registration_v2(
    session: AsyncSession,
    tg_id: int,
    *,
    role: str,                      # 'coworker' | 'guest'
    display_name: str | None = None,
    area: str | None = None,
    bio: str | None = None,
    contact_phone: str | None = None,       # E.164
    contact_whatsapp: str | None = None,    # E.164
    contact_email: str | None = None,
    is_licensed_contractor: bool = False,
    license_number: str | None = None,
    consent_data: bool = False,
    consent_notifications: bool = False,
) -> User | None:
    """Сохранить v2-регистрацию. consent_data обязателен для role=coworker."""
    user = await get_user(session, tg_id)
    if user is None:
        return None
    if role == "coworker" and not consent_data:
        # без согласия не сохраняем профиль
        return None
    now = datetime.now(timezone.utc)
    user.role = role
    user.display_name = display_name
    user.area = area
    user.bio = bio
    user.contact_phone = contact_phone
    user.contact_whatsapp = contact_whatsapp
    user.contact_email = contact_email
    user.is_licensed_contractor = is_licensed_contractor
    user.license_number = license_number
    user.consent_data = consent_data
    user.consent_notifications = consent_notifications
    if consent_data:
        user.consent_at = now
    user.registered_at = now
    await session.commit()
    return user


async def update_profile_field(
    session: AsyncSession,
    tg_id: int,
    field: str,
    value,
) -> bool:
    """Точечный update одного поля для /edit. Безопасно — whitelist полей."""
    ALLOWED = {
        "display_name",
        "area",
        "bio",
        "contact_phone",
        "contact_whatsapp",
        "contact_email",
        "is_licensed_contractor",
        "license_number",
        "language",
    }
    if field not in ALLOWED:
        return False
    rs = await session.execute(
        update(User).where(User.tg_id == tg_id).values({field: value})
    )
    await session.commit()
    return rs.rowcount > 0


async def delete_user(session: AsyncSession, tg_id: int) -> bool:
    """Полное удаление пользователя (каскадно: tags, listings, subscriptions)."""
    user = await get_user(session, tg_id)
    if user is None:
        return False
    await session.delete(user)
    await session.commit()
    return True


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
