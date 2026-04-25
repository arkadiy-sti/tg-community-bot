"""Тесты рассылки с моком Telegram API."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter

from bot.services.broadcast import broadcast, send_copy_to_user


def _make_bot(copy_message_mock: AsyncMock) -> object:
    bot = type("B", (), {})()
    bot.copy_message = copy_message_mock
    return bot


@pytest.mark.asyncio
async def test_send_copy_success() -> None:
    cm = AsyncMock()
    bot = _make_bot(cm)
    status = await send_copy_to_user(bot, 1, 10, 100)  # type: ignore[arg-type]
    assert status == "sent"
    cm.assert_awaited_once()


@pytest.mark.asyncio
async def test_send_copy_forbidden() -> None:
    cm = AsyncMock(side_effect=TelegramForbiddenError(method=object(), message="blocked"))
    bot = _make_bot(cm)
    status = await send_copy_to_user(bot, 1, 10, 100)  # type: ignore[arg-type]
    assert status == "blocked"


@pytest.mark.asyncio
async def test_send_copy_retry_after_then_success() -> None:
    # Первый вызов — TelegramRetryAfter, второй — ок
    err = TelegramRetryAfter(method=object(), message="flood", retry_after=0)
    cm = AsyncMock(side_effect=[err, None])
    bot = _make_bot(cm)
    status = await send_copy_to_user(bot, 1, 10, 100)  # type: ignore[arg-type]
    assert status == "sent"
    assert cm.await_count == 2


@pytest.mark.asyncio
async def test_broadcast_counts() -> None:
    err = TelegramForbiddenError(method=object(), message="blocked")

    async def copy_side_effect(**kwargs):
        uid = kwargs["chat_id"]
        if uid == 2:
            raise err
        if uid == 3:
            raise RuntimeError("boom")

    cm = AsyncMock(side_effect=copy_side_effect)
    bot = _make_bot(cm)
    # rate_per_sec большой чтобы не тормозить тест
    result = await broadcast(bot, [1, 2, 3, 4], 10, 100, rate_per_sec=10000)  # type: ignore[arg-type]
    assert result.sent == 2
    assert result.blocked == 1
    assert result.errors == 1
