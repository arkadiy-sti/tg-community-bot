"""Админ-команды: /ban /unban /warn /mute /stats."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.types import ChatPermissions, Message

from bot import texts
from bot.config import get_settings
from bot.db.database import get_session
from bot.services import users

log = logging.getLogger(__name__)

router = Router(name="admin")


def _is_admin(user_id: int | None) -> bool:
    if user_id is None:
        return False
    return user_id in get_settings().admin_ids


@router.message(Command("ban"))
async def cmd_ban(message: Message, bot: Bot) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        await message.answer(texts.MSG_ONLY_ADMIN)
        return
    target = message.reply_to_message.from_user if message.reply_to_message else None
    if target is None:
        await message.answer(texts.MSG_REPLY_REQUIRED)
        return
    try:
        await bot.ban_chat_member(message.chat.id, target.id)
    except TelegramBadRequest as ex:
        log.warning("ban_chat_member failed: %s", ex)
    async with get_session() as session:
        await users.ban_user(session, target.id)
    await message.answer(texts.MSG_BANNED.format(name=target.full_name))


@router.message(Command("unban"))
async def cmd_unban(message: Message, bot: Bot, command: CommandObject) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        await message.answer(texts.MSG_ONLY_ADMIN)
        return
    target_id: int | None = None
    if message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
    elif command.args:
        try:
            target_id = int(command.args.strip())
        except ValueError:
            await message.answer("Используй: /unban <user_id> или ответом.")
            return
    if target_id is None:
        await message.answer(texts.MSG_REPLY_REQUIRED)
        return
    try:
        await bot.unban_chat_member(message.chat.id, target_id, only_if_banned=True)
    except TelegramBadRequest as ex:
        log.warning("unban_chat_member failed: %s", ex)
    async with get_session() as session:
        await users.unban_user(session, target_id)
    await message.answer(texts.MSG_UNBANNED)


@router.message(Command("warn"))
async def cmd_warn(message: Message, bot: Bot) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        await message.answer(texts.MSG_ONLY_ADMIN)
        return
    target = message.reply_to_message.from_user if message.reply_to_message else None
    if target is None:
        await message.answer(texts.MSG_REPLY_REQUIRED)
        return

    async with get_session() as session:
        warns = await users.add_warning(session, target.id)

    max_warnings = get_settings().max_warnings
    if warns >= max_warnings:
        async with get_session() as session:
            await users.ban_user(session, target.id)
        try:
            await bot.ban_chat_member(message.chat.id, target.id)
        except TelegramBadRequest as ex:
            log.warning("auto-ban failed: %s", ex)
        await message.answer(texts.MSG_AUTO_BAN.format(name=target.full_name))
    else:
        await message.answer(
            texts.MSG_WARNED.format(
                name=target.full_name, warnings=warns, max_warnings=max_warnings
            )
        )


@router.message(Command("mute"))
async def cmd_mute(message: Message, bot: Bot, command: CommandObject) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        await message.answer(texts.MSG_ONLY_ADMIN)
        return
    target = message.reply_to_message.from_user if message.reply_to_message else None
    if target is None:
        await message.answer(texts.MSG_REPLY_REQUIRED)
        return
    try:
        minutes = int(command.args.strip()) if command.args else 60
    except ValueError:
        await message.answer("Используй: /mute <минуты> ответом.")
        return
    until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    try:
        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until,
        )
    except TelegramBadRequest as ex:
        log.warning("restrict_chat_member failed: %s", ex)
        await message.answer(f"Не смог замьютить: {ex.message}")
        return
    await message.answer(texts.MSG_MUTED.format(name=target.full_name, minutes=minutes))


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        await message.answer(texts.MSG_ONLY_ADMIN)
        return
    async with get_session() as session:
        stats = await users.get_stats(session)
    await message.answer(
        texts.STATS_TEMPLATE.format(community=texts.COMMUNITY_NAME, **stats)
    )
