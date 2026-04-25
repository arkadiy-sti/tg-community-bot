"""Middleware антиспама для групповых сообщений."""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message

from bot import texts
from bot.config import get_settings
from bot.db.database import get_session
from bot.services import antispam, users

log = logging.getLogger(__name__)


class AntispamMiddleware(BaseMiddleware):
    """Проверяет сообщения в группах: ссылки у новичков, стоп-слова, rate limit."""

    def __init__(self) -> None:
        settings = get_settings()
        self.rate = antispam.RateLimiter(
            max_msgs=settings.rate_limit_msgs,
            window_sec=settings.rate_limit_window_sec,
        )
        self.new_user_hours = settings.new_user_hours
        self.max_warnings = settings.max_warnings

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)
        if event.chat.type not in {"group", "supergroup"}:
            return await handler(event, data)
        if not event.from_user:
            return await handler(event, data)

        settings = get_settings()
        if event.from_user.id in settings.admin_ids:
            return await handler(event, data)

        text = event.text or event.caption or ""
        user_id = event.from_user.id
        name = event.from_user.full_name

        # 1. Rate limit
        if self.rate.hit(user_id):
            await self._delete_safe(event)
            await event.answer(texts.MSG_ANTISPAM_RATE.format(name=name))
            return None

        # 2. Стоп-слова
        if antispam.contains_stopword(text):
            await self._delete_safe(event)
            await self._warn(event, user_id, name, reason="stopword")
            return None

        # 3. Ссылки у новичков
        if antispam.contains_link(text):
            async with get_session() as session:
                is_new = await users.is_new_user(session, user_id, self.new_user_hours)
            if is_new:
                await self._delete_safe(event)
                await event.answer(texts.MSG_ANTISPAM_LINK.format(name=name))
                return None

        return await handler(event, data)

    async def _delete_safe(self, event: Message) -> None:
        try:
            await event.delete()
        except TelegramBadRequest as ex:
            log.debug("Не смог удалить сообщение: %s", ex)

    async def _warn(self, event: Message, user_id: int, name: str, reason: str) -> None:
        async with get_session() as session:
            warns = await users.add_warning(session, user_id)
        if warns >= self.max_warnings:
            async with get_session() as session:
                await users.ban_user(session, user_id)
            try:
                if event.chat and event.bot:
                    await event.bot.ban_chat_member(event.chat.id, user_id)
            except TelegramBadRequest as ex:
                log.warning("Не удалось забанить %s: %s", user_id, ex)
            await event.answer(texts.MSG_AUTO_BAN.format(name=name))
        else:
            await event.answer(
                texts.MSG_WARNED.format(
                    name=name, warnings=warns, max_warnings=self.max_warnings
                )
            )
