"""Тесты сервиса listings."""
from __future__ import annotations

import pytest

from bot.db.models import Tag
from bot.services import listings as listings_svc
from bot.services import users


@pytest.mark.asyncio
async def test_create_listing_offer_full(session) -> None:
    u = await users.upsert_user(session, tg_id=1, username="ark", full_name="Ark")
    await users.save_registration_v2(
        session,
        tg_id=1,
        role="coworker",
        display_name="Ark",
        contact_phone="+12125551234",
        consent_data=True,
    )
    u = await users.get_user(session, 1)

    loc = Tag(slug="loc_test", category="location", label_ru="SF", label_en="SF")
    skill_a = Tag(slug="sk_a", category="skill", label_ru="A", label_en="A")
    skill_b = Tag(slug="sk_b", category="skill", label_ru="B", label_en="B")
    session.add_all([loc, skill_a, skill_b])
    await session.flush()

    listing = await listings_svc.create_listing(
        session,
        user_id=u.id,
        kind="offer",
        text="Need 2 hands for drywall",
        location_tag_ids=[loc.id],
        skill_tag_ids=[skill_a.id, skill_b.id],
        num_people=2,
        helper_kind="pro",
        language_req="any",
        duration="day",
        urgency="this_week",
        budget="500_2k",
    )
    assert listing.id is not None
    assert listing.status == "pending"
    assert listing.num_people == 2
    assert listing.helper_kind == "pro"


@pytest.mark.asyncio
async def test_create_listing_seek_minimal(session) -> None:
    u = await users.upsert_user(session, tg_id=2, username=None, full_name="X")
    await users.save_registration_v2(
        session, tg_id=2, role="coworker", display_name="X", consent_data=True
    )
    u = await users.get_user(session, 2)

    loc = Tag(slug="loc_b", category="location", label_ru="L", label_en="L")
    skill = Tag(slug="sk_c", category="skill", label_ru="S", label_en="S")
    session.add_all([loc, skill])
    await session.flush()

    listing = await listings_svc.create_listing(
        session,
        user_id=u.id,
        kind="seek",
        text="Looking for side gigs",
        location_tag_ids=[loc.id],
        skill_tag_ids=[skill.id],
        engagement_kind="part_time",
        language_req="ru_en",
        duration="few_days",
        urgency="flexible",
    )
    assert listing.kind == "seek"
    assert listing.engagement_kind == "part_time"
    assert listing.budget is None  # для seek не задаётся


@pytest.mark.asyncio
async def test_render_listing_offer(session) -> None:
    u = await users.upsert_user(session, tg_id=3, username="ark2", full_name="Ark")
    await users.save_registration_v2(
        session,
        tg_id=3,
        role="coworker",
        display_name="Ark",
        contact_phone="+12125551234",
        consent_data=True,
    )
    u = await users.get_user(session, 3)
    loc = Tag(slug="loc_sf2", category="location", label_ru="SF", label_en="SF")
    skill = Tag(slug="sk_drywall", category="skill",
                label_ru="Гипсокартон", label_en="Drywall")
    session.add_all([loc, skill])
    await session.flush()

    listing = await listings_svc.create_listing(
        session,
        user_id=u.id,
        kind="offer",
        text="Quick fix needed",
        location_tag_ids=[loc.id],
        skill_tag_ids=[skill.id],
        num_people=1,
        helper_kind="pro",
        language_req="ru",
        duration="hours",
        urgency="urgent",
        budget="under_500",
    )
    listing.author = u  # подгружаем для рендера
    text = await listings_svc.render_listing(session, listing, lang="ru")
    assert "Предлагаю работу" in text
    assert "SF" in text
    assert "Гипсокартон" in text
    assert "Срочно" in text
    assert "+12125551234" in text


@pytest.mark.asyncio
async def test_count_recent_listings(session) -> None:
    u = await users.upsert_user(session, tg_id=4, username=None, full_name="X")
    await users.save_registration_v2(
        session, tg_id=4, role="coworker", display_name="X", consent_data=True
    )
    u = await users.get_user(session, 4)

    loc = Tag(slug="loc_x", category="location", label_ru="X", label_en="X")
    skill = Tag(slug="sk_x", category="skill", label_ru="S", label_en="S")
    session.add_all([loc, skill])
    await session.flush()

    n0 = await listings_svc.count_recent_listings(session, u.id)
    assert n0 == 0

    for i in range(3):
        await listings_svc.create_listing(
            session,
            user_id=u.id,
            kind="offer",
            text=f"job {i}",
            location_tag_ids=[loc.id],
            skill_tag_ids=[skill.id],
            duration="day",
            urgency="flexible",
        )
    n1 = await listings_svc.count_recent_listings(session, u.id)
    assert n1 == 3


@pytest.mark.asyncio
async def test_auto_expire_old_listings(session) -> None:
    """Approved-объявления старше N дней должны помечаться expired."""
    from datetime import datetime, timedelta, timezone
    u = await users.upsert_user(session, tg_id=99, username=None, full_name="X")
    await users.save_registration_v2(
        session, tg_id=99, role="coworker", display_name="X", consent_data=True,
    )
    u = await users.get_user(session, 99)

    loc = Tag(slug="loc_x99", category="location", label_ru="Y", label_en="Y")
    skill = Tag(slug="sk_x99", category="skill", label_ru="Y", label_en="Y")
    session.add_all([loc, skill])
    await session.flush()

    # Старое объявление — approved, 20 дней назад
    old = await listings_svc.create_listing(
        session, user_id=u.id, kind="offer", text="старое",
        location_tag_ids=[loc.id], skill_tag_ids=[skill.id],
        duration="day", urgency="flexible",
    )
    old.status = "approved"
    old.created_at = datetime.now(timezone.utc) - timedelta(days=20)
    await session.commit()

    # Свежее approved — 1 день
    fresh = await listings_svc.create_listing(
        session, user_id=u.id, kind="offer", text="свежее",
        location_tag_ids=[loc.id], skill_tag_ids=[skill.id],
        duration="day", urgency="flexible",
    )
    fresh.status = "approved"
    fresh.created_at = datetime.now(timezone.utc) - timedelta(days=1)
    await session.commit()

    n = await listings_svc.auto_expire_old_listings(session, days=14)
    assert n == 1

    await session.refresh(old)
    await session.refresh(fresh)
    assert old.status == "expired"
    assert fresh.status == "approved"


@pytest.mark.asyncio
async def test_approve_reject(session) -> None:
    u = await users.upsert_user(session, tg_id=5, username=None, full_name="X")
    await users.save_registration_v2(
        session, tg_id=5, role="coworker", display_name="X", consent_data=True
    )
    u = await users.get_user(session, 5)
    loc = Tag(slug="loc_y", category="location", label_ru="Y", label_en="Y")
    skill = Tag(slug="sk_y", category="skill", label_ru="Y", label_en="Y")
    session.add_all([loc, skill])
    await session.flush()

    listing = await listings_svc.create_listing(
        session,
        user_id=u.id,
        kind="offer",
        text="t",
        location_tag_ids=[loc.id],
        skill_tag_ids=[skill.id],
        duration="day",
        urgency="flexible",
    )
    out = await listings_svc.approve_listing(
        session, listing.id, moderator_tg_id=999, channel_message_id=42
    )
    assert out and out.status == "approved"
    assert out.channel_message_id == 42

    # Reject
    listing2 = await listings_svc.create_listing(
        session,
        user_id=u.id,
        kind="offer",
        text="t2",
        location_tag_ids=[loc.id],
        skill_tag_ids=[skill.id],
        duration="day",
        urgency="flexible",
    )
    rj = await listings_svc.reject_listing(
        session, listing2.id, moderator_tg_id=999, reason="spam"
    )
    assert rj and rj.status == "rejected"
    assert rj.reject_reason == "spam"
