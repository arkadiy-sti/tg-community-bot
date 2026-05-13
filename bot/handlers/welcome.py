"""Welcome новичкам.

Капча отключена — слишком пугает новых пользователей.
Код капчи (таймаут + кик) удалён. Чтобы вернуть —
восстановить captcha_store/PendingCaptcha и таск в on_user_joined.

Остаётся: write restriction для незарегистрированных.
Права на запись выдаются в register.py (_finalize_registration).
"""
from __future__ import annotations

import logging

from aiogram import Bot, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import ChatMemberUpdatedFilter, JOIN_TRANSITION
from aiogram.types import (
    ChatMemberUpdated,
    ChatPermissions,
)

from bot.db.database import get_session
from bot.services import users

log = logging.getLogger(__name__)

router = Router(name="welcome")

# Роли, которым разрешено писать в группе
_WRITE_ROLES = {"coworker", "customer"}


def _restricted_perms() -> ChatPermissions:
    """Запрет отправки сообщений (до завершения регистрации)."""
    return ChatPermissions(can_send_messages=False)


def _write_perms() -> ChatPermissions:
    """Базовые права на отправку (выдаются после регистрации)."""
    return ChatPermissions(
        can_send_messages=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True,
        can_send_polls=True,
    )


@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def on_user_joined(event: ChatMemberUpdated, bot: Bot) -> None:
    """При вступлении в чат — сохраняем юзера, ограничиваем незарегистрированных."""
    user = event.new_chat_member.user
    if user.is_bot:
        return

    chat_id = event.chat.id
    user_id = user.id

    async with get_session() as session:
        await users.upsert_user(
            session,
            tg_id=user_id,
            username=user.username,
            full_name=user.full_name,
        )
        u = await users.get_user(session, user_id)

    is_registered = (
        u is not None
        and u.role in _WRITE_ROLES
        and not (u.is_deleted or False)
    )

    if not is_registered:
        try:
            await bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=_restricted_perms(),
            )
        except TelegramBadRequest as ex:
            log.warning("Не смог ограничить %s: %s", user_id, ex)
