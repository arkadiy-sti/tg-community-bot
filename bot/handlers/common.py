"""Команды /start /help /rules — работают в личке и группе."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot import texts
from bot.config import get_settings

router = Router(name="common")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    if message.chat.type == "private":
        name = (
            message.from_user.first_name
            if message.from_user and message.from_user.first_name
            else "друг"
        )
        await message.answer(
            texts.START_PRIVATE.format(
                community=texts.COMMUNITY_NAME,
                name=name,
            )
        )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    settings = get_settings()
    if message.from_user and message.from_user.id in settings.admin_ids:
        await message.answer(texts.HELP_TEXT + "\n" + texts.ADMIN_HELP)
    else:
        await message.answer(texts.HELP_TEXT)


@router.message(Command("rules"))
async def cmd_rules(message: Message) -> None:
    await message.answer(texts.RULES.format(community=texts.COMMUNITY_NAME))
