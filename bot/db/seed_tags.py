"""Idempotent заливка справочника тегов в БД.

Теги делятся на категории:
- skill — навыки/виды работ (используются в Listing и Profile)
- location — районы Bay Area (используются в Listing)
- feedback_pos / feedback_neg — теги отзывов (используются в Feedback)
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

log = logging.getLogger(__name__)


# (slug, category, label_ru, label_en)
TAGS: list[tuple[str, str, str, str]] = [
    # === Навыки / виды работ (handyman / construction) ===
    ("plumbing", "skill", "Сантехника", "Plumbing"),
    ("electrical", "skill", "Электрика", "Electrical"),
    ("painting", "skill", "Покраска", "Painting"),
    ("drywall", "skill", "Гипсокартон / drywall", "Drywall"),
    ("flooring", "skill", "Полы / напольные покрытия", "Flooring"),
    ("tiling", "skill", "Плитка", "Tiling"),
    ("carpentry", "skill", "Столярные работы", "Carpentry"),
    ("framing", "skill", "Каркасные работы", "Framing"),
    ("roofing", "skill", "Кровля", "Roofing"),
    ("siding", "skill", "Сайдинг / фасад", "Siding"),
    ("foundation", "skill", "Фундамент", "Foundation"),
    ("concrete", "skill", "Бетон / заливка", "Concrete"),
    ("masonry", "skill", "Каменные работы", "Masonry"),
    ("hvac", "skill", "Отопление и вентиляция (HVAC)", "HVAC"),
    ("appliance_repair", "skill", "Ремонт техники", "Appliance Repair"),
    ("kitchen_remodel", "skill", "Ремонт кухни", "Kitchen Remodel"),
    ("bathroom_remodel", "skill", "Ремонт ванной", "Bathroom Remodel"),
    ("adu", "skill", "ADU / гостевой дом", "ADU"),
    ("deck", "skill", "Декинг / террасы", "Deck"),
    ("fence", "skill", "Заборы", "Fence"),
    ("landscaping", "skill", "Ландшафт / двор", "Landscaping"),
    ("irrigation", "skill", "Поливная система", "Irrigation"),
    ("tree_service", "skill", "Деревья / спил", "Tree Service"),
    ("cleaning", "skill", "Уборка / клининг", "Cleaning"),
    ("moving", "skill", "Переезды / грузчики", "Moving"),
    ("handyman_general", "skill", "Мелкий ремонт (handyman)", "General Handyman"),
    ("solar", "skill", "Солнечные панели", "Solar"),
    ("smart_home", "skill", "Умный дом", "Smart Home"),
    ("locksmith", "skill", "Замки / locksmith", "Locksmith"),
    ("welding", "skill", "Сварка", "Welding"),
    ("design", "skill", "Дизайн / planning", "Design / Planning"),
    ("permits", "skill", "Пермиты / документы", "Permits"),
    # === Районы Bay Area ===
    ("loc_sf", "location", "Сан-Франциско (SF)", "San Francisco"),
    ("loc_oakland", "location", "Окленд", "Oakland"),
    ("loc_berkeley", "location", "Беркли", "Berkeley"),
    ("loc_san_jose", "location", "Сан-Хосе", "San Jose"),
    ("loc_palo_alto", "location", "Пало-Альто", "Palo Alto"),
    ("loc_mountain_view", "location", "Маунтин-Вью", "Mountain View"),
    ("loc_fremont", "location", "Фримонт", "Fremont"),
    ("loc_hayward", "location", "Хейворд", "Hayward"),
    ("loc_daly_city", "location", "Дейли-Сити", "Daly City"),
    ("loc_marin", "location", "Округ Марин", "Marin County"),
    ("loc_napa", "location", "Напа / Сонома", "Napa / Sonoma"),
    ("loc_peninsula", "location", "Полуостров (Peninsula)", "Peninsula"),
    ("loc_east_bay", "location", "East Bay", "East Bay"),
    ("loc_south_bay", "location", "South Bay", "South Bay"),
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


async def seed_tags(engine: AsyncEngine) -> None:
    """Создаёт недостающие теги в БД (idempotent по slug)."""
    from bot.db.models import Tag  # late import: модели подключаются в init_db

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:  # type: AsyncSession
        existing = await session.execute(select(Tag.slug))
        existing_slugs = {row[0] for row in existing}

        added = 0
        for slug, category, ru, en in TAGS:
            if slug in existing_slugs:
                continue
            session.add(
                Tag(slug=slug, category=category, label_ru=ru, label_en=en)
            )
            added += 1
        if added:
            await session.commit()
            log.info("Залито новых тегов: %d (всего в словаре %d)", added, len(TAGS))
        else:
            log.debug("Теги уже на месте — словарь насчитывает %d записей", len(TAGS))
