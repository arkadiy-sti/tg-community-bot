"""Тесты сервиса пользователей."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from bot.services import users


@pytest.mark.asyncio
async def test_upsert_creates_then_updates(session) -> None:
    u1 = await users.upsert_user(session, tg_id=42, username="foo", full_name="Foo Bar")
    assert u1.id is not None
    assert u1.username == "foo"

    # Повторный upsert обновляет, а не дублирует
    u2 = await users.upsert_user(session, tg_id=42, username="foo2", full_name="Foo Bar")
    assert u2.id == u1.id
    assert u2.username == "foo2"


@pytest.mark.asyncio
async def test_ban_unban(session) -> None:
    await users.upsert_user(session, tg_id=7, username=None, full_name="U")
    await users.ban_user(session, 7)
    u = await users.get_user(session, 7)
    assert u and u.is_banned is True

    await users.unban_user(session, 7)
    u = await users.get_user(session, 7)
    assert u and u.is_banned is False
    assert u.warnings == 0


@pytest.mark.asyncio
async def test_warnings_accumulate(session) -> None:
    await users.upsert_user(session, tg_id=9, username=None, full_name="U")
    assert await users.add_warning(session, 9) == 1
    assert await users.add_warning(session, 9) == 2
    assert await users.add_warning(session, 9) == 3


@pytest.mark.asyncio
async def test_captcha_flag(session) -> None:
    await users.upsert_user(session, tg_id=1, username=None, full_name="U")
    u = await users.get_user(session, 1)
    assert u and u.captcha_passed is False

    await users.mark_captcha_passed(session, 1)
    u = await users.get_user(session, 1)
    assert u and u.captcha_passed is True


@pytest.mark.asyncio
async def test_is_new_user(session) -> None:
    u = await users.upsert_user(session, tg_id=100, username=None, full_name="X")
    # Свежий пользователь — новый
    assert await users.is_new_user(session, 100, hours=24) is True

    # Имитируем что вступил давно
    u.joined_at = datetime.now(timezone.utc) - timedelta(days=3)
    await session.commit()
    assert await users.is_new_user(session, 100, hours=24) is False


@pytest.mark.asyncio
async def test_stats(session) -> None:
    for i in range(5):
        await users.upsert_user(session, tg_id=i, username=None, full_name=f"u{i}")
    await users.ban_user(session, 0)

    stats = await users.get_stats(session)
    assert stats["total"] == 5
    assert stats["banned"] == 1
    assert stats["active_7d"] == 5
    assert stats["new_24h"] == 5


@pytest.mark.asyncio
async def test_list_users_for_broadcast_excludes_banned(session) -> None:
    for i in range(3):
        await users.upsert_user(session, tg_id=i, username=None, full_name=f"u{i}")
    await users.ban_user(session, 1)

    ids = await users.list_users_for_broadcast(session, segment="all")
    assert set(ids) == {0, 2}
