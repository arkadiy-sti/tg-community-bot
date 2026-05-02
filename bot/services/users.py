"""Работа с пользователями в БД."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import BannedTgId, User


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
    # v3 soft-delete: при re-register снимаем флаг (delete_count сохраняется
    # как метка модератору о повторных удалениях)
    user.is_deleted = False
    user.deleted_at = None
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
    """Soft-delete: чистим личные поля, помечаем is_deleted=True.

    Сохраняем: tg_id, joined_at, warnings, is_banned, captcha_passed, language
    Стираем: display_name, area, bio, contact_*, role, primary_tag_id,
             is_licensed_contractor, license_number, consent_*
    Каскад user_tags — physical delete (теги вернутся при re-register).

    Активные объявления юзера переводятся в status='closed'.
    """
    user = await get_user(session, tg_id)
    if user is None:
        return False
    now = datetime.now(timezone.utc)

    # Чистим личные поля
    user.display_name = None
    user.area = None
    user.bio = None
    user.contact_phone = None
    user.contact_whatsapp = None
    user.contact_email = None
    user.role = None
    user.primary_tag_id = None
    user.is_licensed_contractor = False
    user.license_number = None
    user.consent_data = False
    user.consent_notifications = False
    user.consent_at = None
    user.is_deleted = True
    user.deleted_at = now
    user.delete_count = (user.delete_count or 0) + 1
    user.registered_at = None

    # Удаляем теги (это связи, не данные — вернутся при re-register)
    from bot.db.models import UserTag, Listing
    await session.execute(
        UserTag.__table__.delete().where(UserTag.user_id == user.id)
    )

    # Активные объявления → closed (чтобы не висели в группе)
    await session.execute(
        update(Listing)
        .where(Listing.user_id == user.id, Listing.status == "approved")
        .values(status="closed")
    )

    await session.commit()
    return True


# ---------------------------------------------------------------------------
# Ban-list (постоянный бан по tg_id, переживает delete+register)
# ---------------------------------------------------------------------------


async def is_tg_id_banned(session: AsyncSession, tg_id: int) -> bool:
    """True если tg_id в banned_tg_ids."""
    rs = await session.execute(
        select(BannedTgId).where(BannedTgId.tg_id == tg_id)
    )
    return rs.scalar_one_or_none() is not None


async def ban_tg_id(
    session: AsyncSession, tg_id: int, *,
    by_admin: int, reason: str | None = None,
) -> BannedTgId | None:
    """Внести tg_id в ban-list. Возвращает BannedTgId или None если уже забанен."""
    rs = await session.execute(
        select(BannedTgId).where(BannedTgId.tg_id == tg_id)
    )
    existing = rs.scalar_one_or_none()
    if existing is not None:
        return None
    entry = BannedTgId(
        tg_id=tg_id,
        banned_by_admin_id=by_admin,
        reason=reason,
    )
    session.add(entry)
    # Также пометим User.is_banned=True если есть row
    user = await get_user(session, tg_id)
    if user is not None:
        user.is_banned = True
    await session.commit()
    await session.refresh(entry)
    return entry


async def unban_tg_id(session: AsyncSession, tg_id: int) -> bool:
    """Снять с ban-list. Возвращает True если был забанен."""
    rs = await session.execute(
        select(BannedTgId).where(BannedTgId.tg_id == tg_id)
    )
    entry = rs.scalar_one_or_none()
    if entry is None:
        return False
    await session.delete(entry)
    user = await get_user(session, tg_id)
    if user is not None:
        user.is_banned = False
    await session.commit()
    return True


async def list_banned(session: AsyncSession, limit: int = 50) -> list[BannedTgId]:
    rs = await session.execute(
        select(BannedTgId).order_by(BannedTgId.banned_at.desc()).limit(limit)
    )
    return list(rs.scalars().all())


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
