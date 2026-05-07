"""Тесты save_registration_v2 / update_profile_field / delete_user."""
from __future__ import annotations

import pytest

from bot.services import users


@pytest.mark.asyncio
async def test_v2_requires_consent_for_coworker(session) -> None:
    await users.upsert_user(session, tg_id=1, username="u", full_name="U")
    out = await users.save_registration_v2(
        session,
        tg_id=1,
        role="coworker",
        display_name="Ark",
        consent_data=False,
    )
    assert out is None  # без consent не сохраняем


@pytest.mark.asyncio
async def test_v2_saves_with_consent(session) -> None:
    await users.upsert_user(session, tg_id=2, username="u", full_name="U")
    u = await users.save_registration_v2(
        session,
        tg_id=2,
        role="coworker",
        display_name="Ark",
        area="SF",
        bio="hi",
        contact_phone="+12125551234",
        consent_data=True,
        consent_notifications=True,
    )
    assert u is not None
    assert u.role == "coworker"
    assert u.contact_phone == "+12125551234"
    assert u.consent_data is True
    assert u.consent_at is not None


@pytest.mark.asyncio
async def test_v2_guest_no_consent_required(session) -> None:
    await users.upsert_user(session, tg_id=3, username=None, full_name="X")
    u = await users.save_registration_v2(
        session,
        tg_id=3,
        role="guest",
        consent_data=False,
    )
    assert u is not None
    assert u.role == "guest"


@pytest.mark.asyncio
async def test_update_profile_field_whitelist(session) -> None:
    await users.upsert_user(session, tg_id=4, username=None, full_name="X")
    # Whitelisted поле
    ok = await users.update_profile_field(session, 4, "display_name", "New Name")
    assert ok is True
    u = await users.get_user(session, 4)
    assert u and u.display_name == "New Name"


@pytest.mark.asyncio
async def test_update_profile_field_blocks_non_whitelisted(session) -> None:
    await users.upsert_user(session, tg_id=5, username=None, full_name="X")
    # is_banned не в whitelist — не должно меняться через update_profile_field
    ok = await users.update_profile_field(session, 5, "is_banned", True)
    assert ok is False
    u = await users.get_user(session, 5)
    assert u and u.is_banned is False


@pytest.mark.asyncio
async def test_update_profile_field_partial_no_clobber(session) -> None:
    await users.upsert_user(session, tg_id=6, username=None, full_name="X")
    await users.save_registration_v2(
        session,
        tg_id=6,
        role="coworker",
        display_name="Old",
        area="SF",
        bio="bio",
        consent_data=True,
    )
    # Меняем только bio
    await users.update_profile_field(session, 6, "bio", "new bio")
    u = await users.get_user(session, 6)
    assert u and u.bio == "new bio"
    assert u.display_name == "Old"
    assert u.area == "SF"


@pytest.mark.asyncio
async def test_delete_user_soft(session) -> None:
    """v3: /delete_me делает soft-delete — row остаётся, личные поля стёрты."""
    await users.upsert_user(session, tg_id=7, username="ark", full_name="Ark")
    await users.save_registration_v2(
        session, tg_id=7, role="coworker", display_name="Ark",
        contact_phone="+12125551234", consent_data=True,
    )
    ok = await users.delete_user(session, 7)
    assert ok is True
    # Row остался, но помечен и личное стёрто
    u = await users.get_user(session, 7)
    assert u is not None
    assert u.is_deleted is True
    assert u.deleted_at is not None
    assert u.delete_count == 1
    assert u.display_name is None
    assert u.contact_phone is None
    assert u.role is None
    # Сохранилось
    assert u.tg_id == 7
    assert u.joined_at is not None


@pytest.mark.asyncio
async def test_delete_then_reregister(session) -> None:
    """После soft-delete юзер может снова /register — реюз row, delete_count++."""
    await users.upsert_user(session, tg_id=8, username=None, full_name="X")
    await users.save_registration_v2(
        session, tg_id=8, role="coworker", display_name="Old",
        consent_data=True,
    )
    await users.delete_user(session, 8)
    # Re-register
    u = await users.save_registration_v2(
        session, tg_id=8, role="coworker", display_name="New",
        consent_data=True,
    )
    assert u is not None
    assert u.display_name == "New"
    assert u.is_deleted is False
    assert u.delete_count == 1  # счётчик удалений сохраняется


@pytest.mark.asyncio
async def test_delete_user_unknown(session) -> None:
    ok = await users.delete_user(session, 999999)
    assert ok is False


# ---------------------------------------------------------------------------
# Ban-list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ban_unban_tg_id(session) -> None:
    assert await users.is_tg_id_banned(session, 1234) is False
    entry = await users.ban_tg_id(session, 1234, by_admin=999, reason="spam")
    assert entry is not None
    assert entry.tg_id == 1234
    assert entry.reason == "spam"
    assert await users.is_tg_id_banned(session, 1234) is True

    # Двойной ban — None
    again = await users.ban_tg_id(session, 1234, by_admin=999)
    assert again is None

    # Unban
    ok = await users.unban_tg_id(session, 1234)
    assert ok is True
    assert await users.is_tg_id_banned(session, 1234) is False

    # Unban повторно — False
    assert await users.unban_tg_id(session, 1234) is False


@pytest.mark.asyncio
async def test_ban_marks_user_is_banned(session) -> None:
    """Если у tg_id уже есть User row — ban_tg_id ставит is_banned=True."""
    await users.upsert_user(session, tg_id=42, username=None, full_name="X")
    await users.ban_tg_id(session, 42, by_admin=1)
    u = await users.get_user(session, 42)
    assert u is not None and u.is_banned is True
    await users.unban_tg_id(session, 42)
    u = await users.get_user(session, 42)
    assert u is not None and u.is_banned is False


@pytest.mark.asyncio
async def test_list_banned(session) -> None:
    for tg in (101, 102, 103):
        await users.ban_tg_id(session, tg, by_admin=1)
    items = await users.list_banned(session)
    assert len(items) == 3
    assert {x.tg_id for x in items} == {101, 102, 103}


# ---------------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_grant_revoke_subscription(session) -> None:
    await users.upsert_user(session, tg_id=300, username=None, full_name="X")
    # Изначально нет
    me = await users.get_user(session, 300)
    assert await users.get_active_subscription(session, me.id) is None

    sub = await users.grant_subscription(
        session, tg_id=300, kind="pro", days=30, granted_by_tg_id=1,
    )
    assert sub is not None
    assert sub.kind == "pro"
    assert sub.is_active is True

    active = await users.get_active_subscription(session, me.id)
    assert active is not None
    assert active.kind == "pro"

    ok = await users.revoke_subscription(session, 300)
    assert ok is True
    assert await users.get_active_subscription(session, me.id) is None

    # Повторный revoke — False
    assert await users.revoke_subscription(session, 300) is False


@pytest.mark.asyncio
async def test_grant_subscription_extends_existing(session) -> None:
    await users.upsert_user(session, tg_id=301, username=None, full_name="X")
    s1 = await users.grant_subscription(
        session, tg_id=301, kind="pro", days=30, granted_by_tg_id=1,
    )
    first_until = s1.expires_at
    # Продлеваем на 15 дней
    s2 = await users.grant_subscription(
        session, tg_id=301, kind="pro", days=15, granted_by_tg_id=1,
    )
    # Это та же подписка — продлена
    assert s2.id == s1.id
    delta = (s2.expires_at - first_until).days
    assert delta == 15


@pytest.mark.asyncio
async def test_grant_subscription_unknown_user(session) -> None:
    sub = await users.grant_subscription(
        session, tg_id=99999, kind="pro", days=30, granted_by_tg_id=1,
    )
    assert sub is None


# ---------------------------------------------------------------------------
# Community badges
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_user_badge_grant_revoke(session) -> None:
    await users.upsert_user(session, tg_id=400, username=None, full_name="X")
    # Grant
    ok, changed = await users.set_user_badge(
        session, tg_id=400, badge="trusted", value=True,
    )
    assert ok and changed
    u = await users.get_user(session, 400)
    assert u.badge_trusted is True
    assert u.badge_verified is False

    # Re-grant — no-op
    ok, changed = await users.set_user_badge(
        session, tg_id=400, badge="trusted", value=True,
    )
    assert ok and not changed

    # Revoke
    ok, changed = await users.set_user_badge(
        session, tg_id=400, badge="trusted", value=False,
    )
    assert ok and changed
    u = await users.get_user(session, 400)
    assert u.badge_trusted is False


@pytest.mark.asyncio
async def test_set_user_badge_unknown(session) -> None:
    await users.upsert_user(session, tg_id=401, username=None, full_name="X")
    ok, changed = await users.set_user_badge(
        session, tg_id=401, badge="unknown_badge", value=True,
    )
    assert not ok and not changed


@pytest.mark.asyncio
async def test_set_user_badge_unknown_user(session) -> None:
    ok, changed = await users.set_user_badge(
        session, tg_id=99999, badge="verified", value=True,
    )
    assert not ok and not changed


def test_known_badges() -> None:
    assert "verified" in users.KNOWN_BADGES
    assert "trusted" in users.KNOWN_BADGES
    assert "top" in users.KNOWN_BADGES


# ---------------------------------------------------------------------------
# /check gate — только coworker может смотреть профили
# ---------------------------------------------------------------------------


def test_can_view_profiles_unregistered() -> None:
    from bot.handlers.profile import _can_view_profiles
    assert _can_view_profiles(None) is False


@pytest.mark.asyncio
async def test_can_view_profiles_guest_blocked(session) -> None:
    from bot.handlers.profile import _can_view_profiles

    await users.upsert_user(session, tg_id=100, username=None, full_name="G")
    await users.save_registration_v2(
        session, tg_id=100, role="guest", consent_data=False
    )
    u = await users.get_user(session, 100)
    assert u is not None
    assert _can_view_profiles(u) is False


@pytest.mark.asyncio
async def test_can_view_profiles_coworker_allowed(session) -> None:
    from bot.handlers.profile import _can_view_profiles

    await users.upsert_user(session, tg_id=101, username=None, full_name="C")
    await users.save_registration_v2(
        session,
        tg_id=101,
        role="coworker",
        display_name="C",
        consent_data=True,
    )
    u = await users.get_user(session, 101)
    assert u is not None
    assert _can_view_profiles(u) is True


@pytest.mark.asyncio
async def test_can_view_profiles_legacy_roles(session) -> None:
    """Legacy-роли (handyman/individual/company) тоже допускаются — обратная совместимость."""
    from bot.handlers.profile import _can_view_profiles

    for tg_id, role in [(200, "handyman"), (201, "individual"), (202, "company")]:
        await users.upsert_user(session, tg_id=tg_id, username=None, full_name="X")
        await users.save_registration(
            session,
            tg_id=tg_id,
            role=role,
            display_name="X",
            area=None,
            phone=None,
            bio=None,
        )
        u = await users.get_user(session, tg_id)
        assert _can_view_profiles(u) is True, f"legacy role {role} should be allowed"
