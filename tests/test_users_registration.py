"""Тесты save_registration / set_language."""
from __future__ import annotations

import pytest

from bot.services import users


@pytest.mark.asyncio
async def test_set_language(session) -> None:
    await users.upsert_user(session, tg_id=1, username="u", full_name="U")
    await users.set_language(session, tg_id=1, lang="en")
    u = await users.get_user(session, 1)
    assert u is not None
    assert u.language == "en"


@pytest.mark.asyncio
async def test_save_registration_creates_profile(session) -> None:
    await users.upsert_user(session, tg_id=42, username="ark", full_name="Ark")
    u = await users.save_registration(
        session,
        tg_id=42,
        role="handyman",
        display_name="Ark Master",
        area="SF, Oakland",
        phone="555-0100",
        bio="10 yr pro",
    )
    assert u is not None
    assert u.role == "handyman"
    assert u.display_name == "Ark Master"
    assert u.phone == "555-0100"
    assert u.bio == "10 yr pro"
    assert u.registered_at is not None


@pytest.mark.asyncio
async def test_save_registration_unknown_user_returns_none(session) -> None:
    u = await users.save_registration(
        session,
        tg_id=999999,
        role="individual",
        display_name="X",
        area=None,
        phone=None,
        bio=None,
    )
    assert u is None


@pytest.mark.asyncio
async def test_save_registration_preserves_other_fields(session) -> None:
    """save_registration не должен ломать full_name / username."""
    await users.upsert_user(session, tg_id=7, username="seven", full_name="Seven")
    await users.save_registration(
        session,
        tg_id=7,
        role="company",
        display_name="Co Inc",
        area="SF",
        phone=None,
        bio=None,
    )
    u = await users.get_user(session, 7)
    assert u is not None
    assert u.username == "seven"
    assert u.full_name == "Seven"
    assert u.role == "company"


@pytest.mark.asyncio
async def test_default_language_is_ru(session) -> None:
    await users.upsert_user(session, tg_id=200, username=None, full_name="X")
    u = await users.get_user(session, 200)
    assert u is not None
    assert u.language == "ru"
