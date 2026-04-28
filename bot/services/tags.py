"""Сервис тегов: справочник + пользовательские (custom) теги + облако фидбэка.

Ключевые правила:
- Лимит на профиль: 6 тегов всего (включая primary).
- Custom-теги создаются с is_approved=False и попадают в общий пул только
  после ручной модерации админом (`tags.approve_tag`).
- Custom-теги rate-limited: не более CUSTOM_TAG_LIMIT_PER_USER на юзера.
- Whitelist символов в normalize_custom_tag — никаких эмодзи, RTL, инъекций.
"""
from __future__ import annotations

import logging
import re
from typing import Iterable

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Feedback, FeedbackTag, Tag, User, UserTag

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Константы
# ---------------------------------------------------------------------------

USER_TAGS_LIMIT = 6                # макс тегов на профиль (включая primary)
CUSTOM_TAG_LIMIT_PER_USER = 3       # макс custom-тегов на юзера за всё время
CUSTOM_TAG_MIN_LEN = 2
CUSTOM_TAG_MAX_LEN = 30
CLOUD_TOP_N = 30                    # сколько тегов в облаке профиля

# Whitelist: латиница + кириллица + цифры + пробел + дефис.
# Никаких эмодзи, zero-width, RTL-override, точек и т.п.
_CUSTOM_TAG_RE = re.compile(
    r"^[a-zA-Zа-яА-ЯёЁ0-9 \-]{%d,%d}$" % (CUSTOM_TAG_MIN_LEN, CUSTOM_TAG_MAX_LEN)
)


# ---------------------------------------------------------------------------
# Нормализация
# ---------------------------------------------------------------------------


def normalize_custom_tag(raw: str | None) -> str | None:
    """Привести введённый custom-тег к каноническому виду.

    - strip + collapse пробелов
    - lowercase
    - whitelist символов
    - длина 2..30

    Возвращает нормализованную строку или None если невалидно.
    """
    if not raw:
        return None
    s = raw.strip()
    s = re.sub(r"\s+", " ", s)
    s = s.lower()
    if not _CUSTOM_TAG_RE.match(s):
        return None
    return s


def slug_from_label(label: str) -> str:
    """Сгенерировать slug из нормализованного label (для custom-тегов)."""
    s = label.lower().strip()
    s = re.sub(r"[^a-zа-яё0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return f"custom_{s}"[:64]


# ---------------------------------------------------------------------------
# Справочник
# ---------------------------------------------------------------------------


async def get_tag(session: AsyncSession, tag_id: int) -> Tag | None:
    return await session.get(Tag, tag_id)


async def get_tag_by_slug(session: AsyncSession, slug: str) -> Tag | None:
    rs = await session.execute(select(Tag).where(Tag.slug == slug))
    return rs.scalar_one_or_none()


async def list_tags_by_category(
    session: AsyncSession,
    category: str,
    *,
    only_approved: bool = True,
) -> list[Tag]:
    stmt = select(Tag).where(Tag.category == category)
    if only_approved:
        stmt = stmt.where(Tag.is_approved.is_(True))
    stmt = stmt.order_by(Tag.label_ru)
    rs = await session.execute(stmt)
    return list(rs.scalars().all())


# ---------------------------------------------------------------------------
# Custom-теги (создаются юзерами через "Свой вариант")
# ---------------------------------------------------------------------------


async def count_custom_tags_by_user(session: AsyncSession, user_id: int) -> int:
    rs = await session.scalar(
        select(func.count())
        .select_from(Tag)
        .where(Tag.created_by_user_id == user_id, Tag.is_predefined.is_(False))
    )
    return rs or 0


async def create_custom_tag(
    session: AsyncSession,
    *,
    raw_label: str,
    category: str,
    created_by_user_id: int,
) -> Tag | None:
    """Создать custom-тег от юзера (is_approved=False).

    Возвращает:
    - существующий Tag, если slug совпал с уже существующим;
    - новый Tag, если ввод валиден и юзер не превысил лимит;
    - None, если ввод невалиден или лимит исчерпан.
    """
    label = normalize_custom_tag(raw_label)
    if label is None:
        log.info("custom tag rejected (invalid): %r", raw_label)
        return None

    slug = slug_from_label(label)

    # Если slug уже есть — просто реюзаем
    existing = await get_tag_by_slug(session, slug)
    if existing is not None:
        return existing

    used = await count_custom_tags_by_user(session, created_by_user_id)
    if used >= CUSTOM_TAG_LIMIT_PER_USER:
        log.info(
            "custom tag rate-limit hit: user_id=%s used=%s",
            created_by_user_id,
            used,
        )
        return None

    tag = Tag(
        slug=slug,
        label_ru=label,
        label_en=label,
        category=category,
        is_predefined=False,
        is_approved=False,
        created_by_user_id=created_by_user_id,
    )
    session.add(tag)
    await session.commit()
    await session.refresh(tag)
    log.info(
        "custom tag created: id=%s slug=%s by_user=%s",
        tag.id,
        slug,
        created_by_user_id,
    )
    return tag


async def approve_tag(session: AsyncSession, tag_id: int) -> bool:
    rs = await session.execute(
        update(Tag).where(Tag.id == tag_id).values(is_approved=True)
    )
    await session.commit()
    return rs.rowcount > 0


async def list_pending_tags(session: AsyncSession) -> list[Tag]:
    rs = await session.execute(
        select(Tag).where(Tag.is_approved.is_(False)).order_by(Tag.created_at)
    )
    return list(rs.scalars().all())


# ---------------------------------------------------------------------------
# User ↔ Tag
# ---------------------------------------------------------------------------


async def get_user_tags(session: AsyncSession, user_id: int) -> list[UserTag]:
    rs = await session.execute(
        select(UserTag)
        .where(UserTag.user_id == user_id)
        .order_by(UserTag.is_primary.desc(), UserTag.created_at)
    )
    return list(rs.scalars().all())


async def set_primary_tag(
    session: AsyncSession, user_id: int, tag_id: int
) -> bool:
    """Установить тег как primary. Если связи UserTag нет — создаст."""
    # Сбросить старый primary
    await session.execute(
        update(UserTag)
        .where(UserTag.user_id == user_id, UserTag.is_primary.is_(True))
        .values(is_primary=False)
    )

    # Найти/создать связь
    rs = await session.execute(
        select(UserTag).where(
            UserTag.user_id == user_id, UserTag.tag_id == tag_id
        )
    )
    link = rs.scalar_one_or_none()
    if link is None:
        # Лимит проверяем — primary занимает слот
        existing = await session.scalar(
            select(func.count())
            .select_from(UserTag)
            .where(UserTag.user_id == user_id)
        )
        if (existing or 0) >= USER_TAGS_LIMIT:
            return False
        link = UserTag(user_id=user_id, tag_id=tag_id, is_primary=True)
        session.add(link)
    else:
        link.is_primary = True

    # Дубль на User.primary_tag_id для быстрых селектов в /profile
    await session.execute(
        update(User).where(User.id == user_id).values(primary_tag_id=tag_id)
    )
    # Учёт usages
    await session.execute(
        update(Tag).where(Tag.id == tag_id).values(usages_count=Tag.usages_count + 1)
    )
    await session.commit()
    return True


async def add_user_tag(
    session: AsyncSession, user_id: int, tag_id: int
) -> bool:
    """Добавить дополнительный (не-primary) тег. Возвращает True если добавлен."""
    existing_count = await session.scalar(
        select(func.count())
        .select_from(UserTag)
        .where(UserTag.user_id == user_id)
    )
    if (existing_count or 0) >= USER_TAGS_LIMIT:
        return False

    rs = await session.execute(
        select(UserTag).where(
            UserTag.user_id == user_id, UserTag.tag_id == tag_id
        )
    )
    if rs.scalar_one_or_none() is not None:
        return False  # уже есть

    session.add(UserTag(user_id=user_id, tag_id=tag_id, is_primary=False))
    await session.execute(
        update(Tag).where(Tag.id == tag_id).values(usages_count=Tag.usages_count + 1)
    )
    await session.commit()
    return True


async def remove_user_tag(
    session: AsyncSession, user_id: int, tag_id: int
) -> bool:
    rs = await session.execute(
        select(UserTag).where(
            UserTag.user_id == user_id, UserTag.tag_id == tag_id
        )
    )
    link = rs.scalar_one_or_none()
    if link is None:
        return False
    was_primary = link.is_primary
    await session.delete(link)
    if was_primary:
        await session.execute(
            update(User).where(User.id == user_id).values(primary_tag_id=None)
        )
    await session.commit()
    return True


async def replace_user_tags(
    session: AsyncSession,
    user_id: int,
    primary_tag_id: int | None,
    secondary_tag_ids: Iterable[int],
) -> None:
    """Атомарно перезаписать набор тегов пользователя (для /register и /edit)."""
    # 1) Снести существующие
    await session.execute(
        UserTag.__table__.delete().where(UserTag.user_id == user_id)
    )
    # 2) Записать primary первым
    seen: set[int] = set()
    if primary_tag_id is not None:
        session.add(
            UserTag(user_id=user_id, tag_id=primary_tag_id, is_primary=True)
        )
        seen.add(primary_tag_id)
        await session.execute(
            update(User).where(User.id == user_id).values(primary_tag_id=primary_tag_id)
        )
    else:
        await session.execute(
            update(User).where(User.id == user_id).values(primary_tag_id=None)
        )
    # 3) Дополнительные (с учётом лимита)
    added = 1 if primary_tag_id else 0
    for tid in secondary_tag_ids:
        if tid in seen:
            continue
        if added >= USER_TAGS_LIMIT:
            break
        session.add(UserTag(user_id=user_id, tag_id=tid, is_primary=False))
        seen.add(tid)
        added += 1
    await session.commit()


# ---------------------------------------------------------------------------
# Облако тегов из Feedback
# ---------------------------------------------------------------------------


async def get_feedback_tag_cloud(
    session: AsyncSession, to_user_id: int, *, lang: str = "ru", top_n: int = CLOUD_TOP_N
) -> list[tuple[str, int]]:
    """Аггрегировать теги отзывов на пользователя → [(label, count), ...]."""
    label_col = Tag.label_ru if lang == "ru" else Tag.label_en
    stmt = (
        select(label_col, func.count())
        .select_from(FeedbackTag)
        .join(Feedback, Feedback.id == FeedbackTag.feedback_id)
        .join(Tag, Tag.id == FeedbackTag.tag_id)
        .where(Feedback.to_user_id == to_user_id)
        .group_by(label_col)
        .order_by(func.count().desc())
        .limit(top_n)
    )
    rs = await session.execute(stmt)
    return [(label, int(cnt)) for label, cnt in rs.all()]


def render_tag_cloud(pairs: list[tuple[str, int]]) -> str:
    """Текстовое псевдо-облако для Telegram (HTML parse_mode).

    Самый частый: <b>UPPERCASE</b>, средний: <b>label</b>, редкий: label.
    """
    if not pairs:
        return "—"
    max_n = pairs[0][1] or 1
    parts = []
    for label, n in pairs:
        ratio = n / max_n
        if ratio > 0.66:
            parts.append(f"<b>{label.upper()}</b> ×{n}")
        elif ratio > 0.33:
            parts.append(f"<b>{label}</b> ×{n}")
        else:
            parts.append(f"{label} ×{n}")
    return "  ·  ".join(parts)
