"""Команды /start /help /rules — работают в личке и группе."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot import texts
from bot.config import get_settings
from bot.db.database import get_session
from bot.i18n import COMMUNITY_INVITE_URL, normalize_lang, t
from bot.services import users

router = Router(name="common")


async def _user_lang(tg_id: int | None) -> str:
    """Прочитать язык юзера из БД, fallback на DEFAULT_LANG."""
    if tg_id is None:
        return normalize_lang(None)
    async with get_session() as session:
        u = await users.get_user(session, tg_id)
        return normalize_lang(u.language if u else None)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    if message.chat.type != "private" or message.from_user is None:
        return
    lang = await _user_lang(message.from_user.id)
    name = message.from_user.first_name or ("друг" if lang == "ru" else "friend")
    community = t(lang, "community_name")
    await message.answer(
        t(lang, "start_private", name=name, community=community,
          invite=COMMUNITY_INVITE_URL),
        disable_web_page_preview=True,
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    settings = get_settings()
    lang = await _user_lang(message.from_user.id if message.from_user else None)
    base = t(lang, "help")
    if message.from_user and message.from_user.id in settings.admin_ids:
        await message.answer(base + "\n" + texts.ADMIN_HELP)
    else:
        await message.answer(base)


@router.message(Command("rules"))
async def cmd_rules(message: Message) -> None:
    lang = await _user_lang(message.from_user.id if message.from_user else None)
    await message.answer(
        t(lang, "rules", community=t(lang, "community_name"))
    )
