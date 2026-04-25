"""Middleware для обновления last_active пользователя при любом сообщении."""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message

from bot.db.database import get_session
from bot.db.models import Message as MessageRow
from bot.services import users


class ActivityMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.from_user:
            async with get_session() as session:
                user = await users.upsert_user(
                    session,
                    tg_id=event.from_user.id,
                    username=event.from_user.username,
                    full_name=event.from_user.full_name,
                )
                if event.chat.type in {"group", "supergroup"} and event.text:
                    session.add(
                        MessageRow(
                            user_id=user.id,
                            chat_id=event.chat.id,
                            text=event.text[:4096],
                        )
                    )
                    await session.commit()
        return await handler(event, data)
