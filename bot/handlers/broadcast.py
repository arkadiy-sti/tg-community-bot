"""Команда /broadcast — рассылка подписчикам бота."""
from __future__ import annotations

import logging

from aiogram import Bot, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from bot import texts
from bot.config import get_settings
from bot.db.database import get_session
from bot.db.models import Broadcast
from bot.services import users
from bot.services.broadcast import broadcast as do_broadcast

log = logging.getLogger(__name__)

router = Router(name="broadcast")

SEGMENTS = {"all", "active_7d", "new_users"}


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, bot: Bot, command: CommandObject) -> None:
    settings = get_settings()
    if not message.from_user or message.from_user.id not in settings.admin_ids:
        await message.answer(texts.MSG_ONLY_ADMIN)
        return
    if message.reply_to_message is None:
        await message.answer(texts.BROADCAST_USAGE)
        return

    segment = (command.args or "all").strip().split()[0] if command.args else "all"
    if segment not in SEGMENTS:
        await message.answer(
            f"Неизвестный сегмент: {segment}. Доступно: {', '.join(SEGMENTS)}"
        )
        return

    async with get_session() as session:
        ids = await users.list_users_for_broadcast(session, segment=segment)

    await message.answer(texts.BROADCAST_START.format(count=len(ids)))

    result = await do_broadcast(
        bot=bot,
        user_ids=ids,
        from_chat_id=message.reply_to_message.chat.id,
        message_id=message.reply_to_message.message_id,
    )

    async with get_session() as session:
        session.add(
            Broadcast(
                text=(message.reply_to_message.text or message.reply_to_message.caption or "")[:4096],
                segment=segment,
                sent_count=result.sent,
                blocked_count=result.blocked,
                error_count=result.errors,
                initiated_by=message.from_user.id,
            )
        )
        await session.commit()

    await message.answer(
        texts.BROADCAST_DONE.format(
            sent=result.sent, blocked=result.blocked, errors=result.errors
        )
    )
