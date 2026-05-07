"""Тесты Customer-роли: регистрация, /post, гейтинг."""
from __future__ import annotations

import pytest

from bot.services import users
from bot.services import listings as listings_svc
from bot.services import tags as tags_svc


# ---------------------------------------------------------------------------
# Регистрация Customer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_customer_registration_saves_role(session) -> None:
    await users.upsert_user(session, tg_id=100, username="cust1", full_name="Alice")
    u = await users.save_registration_v2(
        session,
        tg_id=100,
        role="customer",
        display_name="Alice",
        contact_phone="+12125550100",
        consent_data=True,
    )
    assert u is not None
    assert u.role == "customer"
    assert u.contact_phone == "+12125550100"
    assert u.consent_data is True
    assert u.consent_at is not None
    # Поля, которых у customer нет — должны быть None/False
    assert u.area is None
    assert u.bio is None
    assert u.is_licensed_contractor is False


@pytest.mark.asyncio
async def test_customer_requires_consent(session) -> None:
    await users.upsert_user(session, tg_id=101, username="cust2", full_name="Bob")
    u = await users.save_registration_v2(
        session,
        tg_id=101,
        role="customer",
        display_name="Bob",
        consent_data=False,  # не согласился
    )
    assert u is None  # без согласия не сохраняем


@pytest.mark.asyncio
async def test_customer_contact_can_be_email(session) -> None:
    await users.upsert_user(session, tg_id=102, username="cust3", full_name="Carol")
    u = await users.save_registration_v2(
        session,
        tg_id=102,
        role="customer",
        display_name="Carol",
        contact_email="carol@example.com",
        consent_data=True,
    )
    assert u is not None
    assert u.contact_email == "carol@example.com"
    assert u.contact_phone is None


@pytest.mark.asyncio
async def test_customer_can_reregister_after_soft_delete(session) -> None:
    """Повторная регистрация после soft-delete сохраняет delete_count."""
    await users.upsert_user(session, tg_id=103, username=None, full_name="Dave")
    u = await users.save_registration_v2(
        session, tg_id=103, role="customer",
        display_name="Dave", contact_phone="+12125550103", consent_data=True,
    )
    assert u is not None
    await users.delete_user(session, 103)  # принимает tg_id
    u2 = await users.get_user(session, 103)
    assert u2 is not None and u2.is_deleted is True

    u3 = await users.save_registration_v2(
        session, tg_id=103, role="customer",
        display_name="Dave2", contact_phone="+12125550104", consent_data=True,
    )
    assert u3 is not None
    assert u3.role == "customer"
    assert u3.is_deleted is False
    assert (u3.delete_count or 0) >= 1


# ---------------------------------------------------------------------------
# Customer /post — создание объявления
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_customer_can_create_listing(session) -> None:
    await users.upsert_user(session, tg_id=200, username="cust_post", full_name="Erin")
    u = await users.save_registration_v2(
        session, tg_id=200, role="customer",
        display_name="Erin", contact_phone="+12125550200", consent_data=True,
    )
    assert u is not None

    # Убеждаемся, что теги инициализированы (seed нужен)
    from bot.db.seed_tags import TAGS
    from bot.db.models import Tag
    from sqlalchemy import select
    rs = await session.execute(select(Tag).limit(1))
    if rs.scalar_one_or_none() is None:
        # Добавим минимальный тег вручную
        tag = Tag(slug="cleaning", label_ru="Уборка", label_en="Cleaning",
                  category="skill", is_predefined=True, is_approved=True)
        session.add(tag)
        await session.commit()
        await session.refresh(tag)
        skill_tag_id = tag.id
    else:
        rs2 = await session.execute(
            select(Tag).where(Tag.category == "skill").limit(1)
        )
        skill_tag_id = rs2.scalar_one().id

    loc_tag = Tag(slug="sf_test", label_ru="SF", label_en="SF",
                  category="location", is_predefined=True, is_approved=True)
    session.add(loc_tag)
    await session.commit()
    await session.refresh(loc_tag)

    listing = await listings_svc.create_listing(
        session,
        user_id=u.id,
        kind="offer",
        text="Нужно убраться в доме",
        location_tag_ids=[loc_tag.id],
        skill_tag_ids=[skill_tag_id],
        num_people=1,
        urgency="this_week",
    )
    assert listing is not None
    assert listing.kind == "offer"
    assert listing.num_people == 1
    assert listing.status == "pending"
    assert listing.duration is None
    assert listing.helper_kind is None


# ---------------------------------------------------------------------------
# Гейтинг: Customer не может использовать /check
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_can_view_profiles_blocks_customer() -> None:
    """Customer не должен видеть профили через /check."""
    from bot.handlers.profile import _can_view_profiles
    from bot.db.models import User

    coworker = User(tg_id=300, role="coworker", full_name="A", language="ru")
    customer = User(tg_id=301, role="customer", full_name="B", language="ru")
    guest = User(tg_id=302, role="guest", full_name="C", language="ru")
    no_role = User(tg_id=303, full_name="D", language="ru")

    assert _can_view_profiles(coworker) is True
    assert _can_view_profiles(customer) is False
    assert _can_view_profiles(guest) is False
    assert _can_view_profiles(no_role) is False
    assert _can_view_profiles(None) is False


# ---------------------------------------------------------------------------
# Гейтинг: Customer может публиковать
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_can_post_allows_customer() -> None:
    from bot.handlers.post import _can_post

    assert _can_post("coworker") is True
    assert _can_post("customer") is True
    assert _can_post("guest") is False
    assert _can_post(None) is False
    assert _can_post("handyman") is True   # legacy
