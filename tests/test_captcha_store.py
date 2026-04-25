"""Тесты хранилища капч."""
from __future__ import annotations

import pytest

from bot.services.captcha import CaptchaStore, PendingCaptcha


@pytest.mark.asyncio
async def test_add_has_pop() -> None:
    store = CaptchaStore()
    p = PendingCaptcha(user_id=1, chat_id=10, message_id=100)
    await store.add(10, 1, p)
    assert await store.has(10, 1) is True
    popped = await store.pop(10, 1)
    assert popped is p
    assert await store.has(10, 1) is False


@pytest.mark.asyncio
async def test_pop_missing_returns_none() -> None:
    store = CaptchaStore()
    assert await store.pop(1, 1) is None
