"""Сервис объявлений: создание, чтение, лимиты, форматирование.

Структурированные поля Listing хранят коды (engagement_kind='one_time' и т.п.).
Render-в-текст для группы и preview — через label-helpers ниже.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Listing, ListingPhoto, ListingTag, Tag, User

log = logging.getLogger(__name__)

# Лимиты
MAX_DESCRIPTION_LEN = 1000
MAX_PHOTOS = 5
MAX_LOCATIONS = 5
MAX_SKILL_TAGS = 5

# Лимит публикаций на 30 дней для бесплатных юзеров (не enforced пока).
MONTHLY_FREE_LIMIT = 2

# Cap откликов = num_people + RESPONSE_CAP_BONUS.
# Защита от сбора базы исполнителей: например нужен 1 человек → макс 4 отклика.
RESPONSE_CAP_BONUS = 3

# Авто-expire через N дней после публикации (не enforced пока).
LISTING_AUTO_EXPIRE_DAYS = 14

# ---------------------------------------------------------------------------
# Лейблы (для preview и публикации в группу)
# ---------------------------------------------------------------------------

KIND_LABELS = {
    "ru": {"offer": "💼 Предлагаю работу", "seek": "🔎 Ищу работу"},
    "en": {"offer": "💼 Offering work", "seek": "🔎 Looking for work"},
}

NUM_PEOPLE_LABELS = {
    1: "1", 2: "2", 3: "3", 4: "4", 5: "5+",
}

ENGAGEMENT_LABELS = {
    "ru": {"one_time": "На один проект", "part_time": "Подработка"},
    "en": {"one_time": "One-off", "part_time": "Part-time / side"},
}

HELPER_LABELS = {
    "ru": {"pro": "🔧 Профессионал", "helper": "🛠 Помощник", "any": "Любой"},
    "en": {"pro": "🔧 Pro", "helper": "🛠 Helper", "any": "Any"},
}

LANGUAGE_OFFER_LABELS = {
    "ru": {
        "none": "Общение не требуется",
        "ru": "Русский",
        "en": "Английский",
        # 'any' оставлен для обратной совместимости со старыми данными
        "any": "Любой язык",
    },
    "en": {
        "none": "No talking needed",
        "ru": "Russian",
        "en": "English",
        "any": "Any language",
    },
}

LANGUAGE_SEEK_LABELS = {
    "ru": {"ru": "Русский", "en": "Английский", "ru_en": "Русский + Английский"},
    "en": {"ru": "Russian", "en": "English", "ru_en": "Russian + English"},
}

DURATION_LABELS = {
    "ru": {
        "hours": "Несколько часов",
        "day": "1 день",
        "few_days": "2–5 дней",
        "week_plus": "Неделя+",
        "longterm": "Долгосрочно",
    },
    "en": {
        "hours": "A few hours",
        "day": "1 day",
        "few_days": "2–5 days",
        "week_plus": "A week or more",
        "longterm": "Long-term",
    },
}

URGENCY_LABELS = {
    "ru": {
        "urgent": "🔥 Срочно",
        "this_week": "📅 На этой неделе",
        "this_month": "🗓 В этом месяце",
        "flexible": "⏳ Не горит",
    },
    "en": {
        "urgent": "🔥 Urgent",
        "this_week": "📅 This week",
        "this_month": "🗓 This month",
        "flexible": "⏳ Flexible",
    },
}

BUDGET_LABELS = {
    "ru": {
        # Без угловой скобки — она ломает HTML-парсер Telegram при <b>{label}</b>
        "under_500": "до $500",
        "500_2k": "$500–2 000",
        "2k_10k": "$2 000–10 000",
        "over_10k": "$10 000+",
        "discuss": "Обсуждаем",
    },
    "en": {
        "under_500": "Under $500",
        "500_2k": "$500–2,000",
        "2k_10k": "$2,000–10,000",
        "over_10k": "$10,000+",
        "discuss": "Discuss",
    },
}


def label(table: dict, lang: str, code: str | None) -> str:
    """Безопасно достать label из вложенного словаря."""
    if not code:
        return "—"
    return table.get(lang, table.get("ru", {})).get(code, code)


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


async def count_recent_listings(
    session: AsyncSession, user_id: int, days: int = 30
) -> int:
    threshold = datetime.now(timezone.utc) - timedelta(days=days)
    n = await session.scalar(
        select(func.count())
        .select_from(Listing)
        .where(
            Listing.user_id == user_id,
            Listing.created_at >= threshold,
            Listing.status.in_(["pending", "approved"]),
        )
    )
    return n or 0


async def create_listing(
    session: AsyncSession,
    *,
    user_id: int,
    kind: str,                                    # 'offer' | 'seek'
    text: str,
    location_tag_ids: Iterable[int],
    skill_tag_ids: Iterable[int],
    num_people: int | None = None,
    engagement_kind: str | None = None,
    helper_kind: str | None = None,
    language_req: str | None = None,
    duration: str | None = None,
    urgency: str | None = None,
    budget: str | None = None,
    contact_override: str | None = None,
    location_freetext: str | None = None,
    photo_file_ids: Iterable[str] | None = None,
) -> Listing:
    """Создать объявление со всеми связанными сущностями. Status='pending'."""
    listing = Listing(
        user_id=user_id,
        kind=kind,
        text=text[:MAX_DESCRIPTION_LEN],
        status="pending",
        num_people=num_people,
        engagement_kind=engagement_kind,
        helper_kind=helper_kind,
        language_req=language_req,
        duration=duration,
        urgency=urgency,
        budget=budget,
        contact_override=contact_override,
        location_freetext=location_freetext,
    )
    session.add(listing)
    await session.flush()

    # Теги (locations + skills, both в одной таблице ListingTag)
    seen: set[int] = set()
    for tag_id in list(location_tag_ids) + list(skill_tag_ids):
        if tag_id in seen:
            continue
        seen.add(tag_id)
        session.add(ListingTag(listing_id=listing.id, tag_id=tag_id))

    # Фото
    if photo_file_ids:
        for fid in list(photo_file_ids)[:MAX_PHOTOS]:
            session.add(ListingPhoto(listing_id=listing.id, file_id=fid))

    await session.commit()
    await session.refresh(listing)
    return listing


async def get_listing_full(session: AsyncSession, listing_id: int) -> Listing | None:
    """Получить объявление с tags+photos+author подгруженными."""
    listing = await session.get(Listing, listing_id)
    return listing


async def get_listing_tags_split(
    session: AsyncSession, listing_id: int
) -> tuple[list[Tag], list[Tag]]:
    """Вернуть (locations, skills) — Tag-объекты, разделённые по category."""
    rs = await session.execute(
        select(Tag)
        .join(ListingTag, ListingTag.tag_id == Tag.id)
        .where(ListingTag.listing_id == listing_id)
    )
    locations: list[Tag] = []
    skills: list[Tag] = []
    for tag in rs.scalars().all():
        if tag.category == "location":
            locations.append(tag)
        else:
            skills.append(tag)
    return locations, skills


# ---------------------------------------------------------------------------
# Формат для preview / публикации в группу
# ---------------------------------------------------------------------------


def _contact_line(user: User, override: str | None, lang: str) -> str:
    """Строка контакта для публикации. Override > priority contact > Telegram."""
    if override:
        return override
    if user.contact_phone:
        return f"📱 {user.contact_phone}"
    if user.contact_whatsapp:
        return f"💬 WhatsApp {user.contact_whatsapp}"
    if user.contact_email:
        return f"✉️ {user.contact_email}"
    if user.username:
        return f"@{user.username} (Telegram)"
    return "Telegram DM"


def _classify_override(override: str, lang: str) -> str:
    """Определить тип override-контакта и вернуть masked-лейбл.

    @username — публичен (это и так видно в Telegram), оставляем.
    Всё остальное (телефон, email) — маскируем «через бота».
    """
    s = (override or "").strip()
    if not s:
        return "📞 Контакт (через бота)" if lang == "ru" else "📞 Contact (via bot)"
    if s.startswith("@") and len(s) > 1 and " " not in s:
        return f"💬 {s} (Telegram)"
    if "@" in s and "." in s.split("@", 1)[-1]:
        return "✉️ Email (через бота)" if lang == "ru" else "✉️ Email (via bot)"
    digits = sum(c.isdigit() for c in s)
    if digits >= 7:
        return "📱 Телефон (через бота)" if lang == "ru" else "📱 Phone (via bot)"
    return "📞 Контакт (через бота)" if lang == "ru" else "📞 Contact (via bot)"


def _contact_line_masked(user: User, override: str | None, lang: str) -> str:
    """Тип контакта без значения — для публичной публикации в группе.

    Реальный номер/email автор получает в DM от бота когда кто-то нажимает
    «📩 Откликнуться» — т.е. контакт никогда не утекает в публичный чат.
    """
    if override:
        return _classify_override(override, lang)
    if user.contact_phone:
        return ("📱 Телефон (через бота)" if lang == "ru"
                else "📱 Phone (via bot)")
    if user.contact_whatsapp:
        return ("💬 WhatsApp (через бота)" if lang == "ru"
                else "💬 WhatsApp (via bot)")
    if user.contact_email:
        return ("✉️ Email (через бота)" if lang == "ru"
                else "✉️ Email (via bot)")
    if user.username:
        return f"@{user.username} (Telegram)"
    return "Telegram DM"


async def render_listing(
    session: AsyncSession,
    listing: Listing,
    lang: str = "ru",
    *,
    include_contact: bool = True,
    mask_contact: bool = False,
) -> str:
    """Сформировать HTML-текст объявления для публикации/preview."""
    locations, skills = await get_listing_tags_split(session, listing.id)
    loc_parts = [t.label_ru if lang == "ru" else t.label_en for t in locations]
    if listing.location_freetext:
        loc_parts.append(listing.location_freetext)
    loc_str = ", ".join(loc_parts) or "—"
    skill_str = ", ".join(t.label_ru if lang == "ru" else t.label_en for t in skills) or "—"

    kind_str = label(KIND_LABELS, lang, listing.kind)
    duration_str = label(DURATION_LABELS, lang, listing.duration)
    urgency_str = label(URGENCY_LABELS, lang, listing.urgency)

    # Поля, специфичные для kind
    extra_lines: list[str] = []
    if listing.kind == "offer":
        if listing.num_people:
            n_label = NUM_PEOPLE_LABELS.get(listing.num_people, str(listing.num_people))
            extra_lines.append(
                f"👥 Нужно человек: <b>{n_label}</b>" if lang == "ru"
                else f"👥 People needed: <b>{n_label}</b>"
            )
        if listing.helper_kind:
            extra_lines.append(
                ("👷 Кто нужен: " if lang == "ru" else "👷 Looking for: ")
                + f"<b>{label(HELPER_LABELS, lang, listing.helper_kind)}</b>"
            )
        if listing.language_req:
            extra_lines.append(
                ("🗣 Язык общения: " if lang == "ru" else "🗣 Language: ")
                + f"<b>{label(LANGUAGE_OFFER_LABELS, lang, listing.language_req)}</b>"
            )
        if listing.budget:
            extra_lines.append(
                ("💵 Бюджет: " if lang == "ru" else "💵 Budget: ")
                + f"<b>{label(BUDGET_LABELS, lang, listing.budget)}</b>"
            )
    else:  # seek
        if listing.engagement_kind:
            extra_lines.append(
                ("📋 Занятость: " if lang == "ru" else "📋 Engagement: ")
                + f"<b>{label(ENGAGEMENT_LABELS, lang, listing.engagement_kind)}</b>"
            )
        if listing.language_req:
            extra_lines.append(
                ("🗣 Языки: " if lang == "ru" else "🗣 Languages: ")
                + f"<b>{label(LANGUAGE_SEEK_LABELS, lang, listing.language_req)}</b>"
            )

    parts: list[str] = [
        f"<b>{kind_str}</b>",
        "",
        ("📍 Район: " if lang == "ru" else "📍 Area: ") + f"<b>{loc_str}</b>",
        ("🏷 Виды работ: " if lang == "ru" else "🏷 Skills: ") + f"<b>{skill_str}</b>",
    ]
    parts.extend(extra_lines)
    parts.append(
        ("⏱ Длительность: " if lang == "ru" else "⏱ Duration: ") + f"<b>{duration_str}</b>"
    )
    parts.append(
        ("⚡ Срочность: " if lang == "ru" else "⚡ Urgency: ") + f"<b>{urgency_str}</b>"
    )
    parts.append("")
    parts.append(listing.text or "—")

    if include_contact and listing.author is not None:
        parts.append("")
        contact_renderer = (
            _contact_line_masked if mask_contact else _contact_line
        )
        parts.append(
            ("📞 Контакт: " if lang == "ru" else "📞 Contact: ")
            + contact_renderer(listing.author, listing.contact_override, lang)
        )

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Модерация
# ---------------------------------------------------------------------------


async def approve_listing(
    session: AsyncSession,
    listing_id: int,
    *,
    moderator_tg_id: int,
    channel_message_id: int | None = None,
) -> Listing | None:
    listing = await session.get(Listing, listing_id)
    if listing is None:
        return None
    listing.status = "approved"
    listing.moderated_at = datetime.now(timezone.utc)
    listing.moderator_tg_id = moderator_tg_id
    listing.channel_message_id = channel_message_id
    await session.commit()
    return listing


async def reject_listing(
    session: AsyncSession,
    listing_id: int,
    *,
    moderator_tg_id: int,
    reason: str | None = None,
) -> Listing | None:
    listing = await session.get(Listing, listing_id)
    if listing is None:
        return None
    listing.status = "rejected"
    listing.moderated_at = datetime.now(timezone.utc)
    listing.moderator_tg_id = moderator_tg_id
    listing.reject_reason = reason
    await session.commit()
    return listing
