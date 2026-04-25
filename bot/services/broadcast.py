"""Массовая рассылка с rate-limit и retry."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Sequence

from aiogram import Bot
from aiogram.exceptions import (
    TelegramForbiddenError,
    TelegramRetryAfter,
)

log = logging.getLogger(__name__)


@dataclass
class BroadcastResult:
    sent: int = 0
    blocked: int = 0
    errors: int = 0


async def send_copy_to_user(
    bot: Bot,
    user_id: int,
    from_chat_id: int,
    message_id: int,
) -> str:
    """Копирует сообщение пользователю. Возвращает статус."""
    try:
        await bot.copy_message(
            chat_id=user_id,
            from_chat_id=from_chat_id,
            message_id=message_id,
        )
        return "sent"
    except TelegramForbiddenError:
        return "blocked"
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after + 1)
        try:
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=from_chat_id,
                message_id=message_id,
            )
            return "sent"
        except Exception as ex:  # noqa: BLE001
            log.warning("Broadcast retry failed for %s: %s", user_id, ex)
            return "error"
    except Exception as ex:  # noqa: BLE001
        log.warning("Broadcast error for %s: %s", user_id, ex)
        return "error"


async def broadcast(
    bot: Bot,
    user_ids: Sequence[int],
    from_chat_id: int,
    message_id: int,
    rate_per_sec: int = 25,
) -> BroadcastResult:
    """Рассылка с лимитом rate_per_sec сообщений в секунду."""
    result = BroadcastResult()
    delay = 1.0 / max(rate_per_sec, 1)
    for uid in user_ids:
        status = await send_copy_to_user(bot, uid, from_chat_id, message_id)
        if status == "sent":
            result.sent += 1
        elif status == "blocked":
            result.blocked += 1
        else:
            result.errors += 1
        await asyncio.sleep(delay)
    return result
