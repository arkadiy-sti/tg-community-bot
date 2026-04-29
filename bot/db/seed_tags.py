"""Idempotent заливка справочника тегов в БД.

Теги делятся на категории:
- skill — навыки/виды работ (используются в Listing и Profile)
- location — районы Bay Area (используются в Listing)
- feedback_pos / feedback_neg — теги отзывов (используются в Feedback)

Сид является источником правды для is_predefined=True тегов: на каждом
рестарте лейблы синхронизируются (можно менять текст в TAGS — БД догонит).
Custom-теги (is_predefined=False) seed не трогает.
"""
from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

log = logging.getLogger(__name__)


# (slug, category, label_ru, label_en)
TAGS: list[tuple[str, str, str, str]] = [
    # === Навыки / виды работ (handyman / construction) ===
    ("plumbing", "skill", "Сантехника", "Plumbing"),
    ("electrical", "skill", "Электрика", "Electrical"),
    ("painting", "skill", "Покраска", "Painting"),
    ("drywall", "skill", "Гипсокартон", "Drywall"),
    # Полы — раскладываем на конкретные типы покрытий (плитка отдельно ниже)
    ("hardwood", "skill", "Хардвуд", "Hardwood"),
    ("vinyl_flooring", "skill", "Винил", "Vinyl"),
    ("linoleum_carpet", "skill", "Ковролин", "Carpet"),
    ("tiling", "skill", "Плитка", "Tiling"),
    ("carpentry", "skill", "Столярка", "Carpentry"),
    ("framing", "skill", "Каркас", "Framing"),
    ("roofing", "skill", "Кровля", "Roofing"),
    ("siding", "skill", "Сайдинг", "Siding"),
    ("foundation", "skill", "Фундамент", "Foundation"),
    ("concrete", "skill", "Бетон", "Concrete"),
    ("masonry", "skill", "Камень", "Masonry"),
    ("hvac", "skill", "HVAC", "HVAC"),
    ("appliance_repair", "skill", "Техника", "Appliances"),
    ("kitchen_remodel", "skill", "Кухня", "Kitchen"),
    ("bathroom_remodel", "skill", "Ванная", "Bathroom"),
    ("adu", "skill", "ADU", "ADU"),
    ("deck", "skill", "Декинг", "Deck"),
    ("fence", "skill", "Заборы", "Fence"),
    ("landscaping", "skill", "Ландшафт", "Landscape"),
    ("irrigation", "skill", "Полив", "Irrigation"),
    ("tree_service", "skill", "Деревья", "Tree"),
    ("cleaning", "skill", "Уборка", "Cleaning"),
    ("moving", "skill", "Переезды", "Moving"),
    ("handyman_general", "skill", "Handyman", "Handyman"),
    ("solar", "skill", "Solar", "Solar"),
    ("smart_home", "skill", "Умный дом", "Smart Home"),
    ("locksmith", "skill", "Замки", "Locksmith"),
    ("welding", "skill", "Сварка", "Welding"),
    ("design", "skill", "Дизайн", "Design"),
    ("permits", "skill", "Пермиты", "Permits"),
    # === Районы (крупные регионы; конкретный адрес/ZIP — в описание) ===
    ("loc_sf", "location", "SF", "San Francisco"),
    ("loc_san_jose", "location", "San Jose", "San Jose"),
    ("loc_sacramento", "location", "Sacramento", "Sacramento"),
    ("loc_east_bay", "location", "East Bay", "East Bay"),
    ("loc_south_bay", "location", "South Bay", "South Bay"),
    ("loc_peninsula", "location", "Peninsula", "Peninsula"),
    ("loc_north_bay", "location", "North Bay", "North Bay"),
    # === Теги отзывов: положительные ===
    ("fb_punctual", "feedback_pos", "Пунктуальный", "Punctual"),
    ("fb_quality", "feedback_pos", "Качественно", "Quality work"),
    ("fb_fair_price", "feedback_pos", "Честная цена", "Fair price"),
    ("fb_clean", "feedback_pos", "Чисто оставил", "Clean"),
    ("fb_communicative", "feedback_pos", "На связи", "Communicative"),
    ("fb_pro", "feedback_pos", "Профессионал", "Professional"),
    ("fb_recommend", "feedback_pos", "Рекомендую", "Recommended"),
    # === Теги отзывов: негативные ===
    ("fb_late", "feedback_neg", "Опоздал", "Late"),
    ("fb_rough", "feedback_neg", "Неаккуратно", "Sloppy"),
    ("fb_overpriced", "feedback_neg", "Завысил цену", "Overpriced"),
    ("fb_no_show", "feedback_neg", "Не пришёл", "No-show"),
    ("fb_unresponsive", "feedback_neg", "Не отвечает", "Unresponsive"),
]


# Slug-и тегов, которые мы выводим из эксплуатации.
# Если на устаревший тег нет user_tags-связей и primary_tag_id — он будет удалён.
# Если есть — оставляем и логируем warning, чтобы админ решил вручную.
OBSOLETE_SLUGS: list[str] = [
    "flooring",  # заменён на hardwood/vinyl_flooring/linoleum_carpet/tiling
    # Конкретные города — теперь покрываются регионами East Bay / Peninsula / etc.
    # Точный адрес/ZIP — пишем в описание объявления.
    "loc_oakland",
    "loc_berkeley",
    "loc_palo_alto",
    "loc_mountain_view",
    "loc_fremont",
    "loc_hayward",
    "loc_daly_city",
    "loc_marin",
    "loc_napa",
]


async def seed_tags(engine: AsyncEngine) -> None:
    """Sync справочника тегов с БД.

    1. INSERT недостающих slug-ов из TAGS.
    2. UPDATE label_ru/label_en/category для предустановленных slug-ов,
       если они отличаются от seed (custom-теги не трогаем).
    3. DELETE устаревших slug-ов из OBSOLETE_SLUGS, если на них нет ссылок.
    """
    from bot.db.models import Tag, UserTag, User  # late import

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:  # type: AsyncSession
        result = await session.execute(select(Tag))
        existing_by_slug: dict[str, Tag] = {t.slug: t for t in result.scalars().all()}

        added = 0
        updated = 0
        for slug, category, ru, en in TAGS:
            tag = existing_by_slug.get(slug)
            if tag is None:
                session.add(Tag(
                    slug=slug,
                    category=category,
                    label_ru=ru,
                    label_en=en,
                    is_predefined=True,
                    is_approved=True,
                ))
                added += 1
                continue
            # Не трогаем custom-теги, даже если slug случайно совпал.
            if not tag.is_predefined:
                continue
            if (tag.label_ru != ru) or (tag.label_en != en) or (tag.category != category):
                tag.label_ru = ru
                tag.label_en = en
                tag.category = category
                updated += 1

        # Безопасное удаление устаревших тегов
        deleted = 0
        kept_with_warning = 0
        for slug in OBSOLETE_SLUGS:
            tag = existing_by_slug.get(slug)
            if tag is None:
                continue
            n_user_tags = await session.scalar(
                select(func.count())
                .select_from(UserTag)
                .where(UserTag.tag_id == tag.id)
            ) or 0
            n_primary = await session.scalar(
                select(func.count())
                .select_from(User)
                .where(User.primary_tag_id == tag.id)
            ) or 0
            if n_user_tags > 0 or n_primary > 0:
                log.warning(
                    "Устаревший тег %s имеет ссылки (user_tags=%d, primary=%d) — оставляю",
                    slug, n_user_tags, n_primary,
                )
                kept_with_warning += 1
                continue
            await session.delete(tag)
            deleted += 1
            log.info("Удалён устаревший тег: %s", slug)

        if added or updated or deleted:
            await session.commit()
            log.info(
                "Tags sync: added=%d, updated=%d, deleted=%d, kept_obsolete=%d, total_in_seed=%d",
                added, updated, deleted, kept_with_warning, len(TAGS),
            )
        else:
            log.debug("Теги уже на месте — словарь насчитывает %d записей", len(TAGS))
