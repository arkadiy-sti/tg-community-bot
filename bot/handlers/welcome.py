"""Welcome новичкам + капча."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import ChatMemberUpdatedFilter, IS_NOT_MEMBER, JOIN_TRANSITION
from aiogram.types import CallbackQuery, ChatMemberUpdated

from bot import texts
from bot.config import get_settings
from bot.db.database import get_session
from bot.keyboards.inline import captcha_kb
from bot.services import users
from bot.services.captcha import PendingCaptcha, captcha_store

log = logging.getLogger(__name__)

router = Router(name="welcome")


@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def on_user_joined(event: ChatMemberUpdated, bot: Bot) -> None:
    """При вступлении в чат — отправить капчу, кикнуть при таймауте."""
    user = event.new_chat_member.user
    if user.is_bot:
        return

    settings = get_settings()
    chat_id = event.chat.id
    user_id = user.id
    name = user.full_name

    # Сохраняем пользователя в БД
    async with get_session() as session:
        await users.upsert_user(
            session,
            tg_id=user_id,
            username=user.username,
            full_name=name,
        )

    # Отправляем капчу
    try:
        msg = await bot.send_message(
            chat_id=chat_id,
            text=texts.WELCOME_CAPTCHA.format(
                name=name,
                community=texts.COMMUNITY_NAME,
                seconds=settings.captcha_timeout_sec,
            ),
            reply_markup=captcha_kb(user_id),
        )
    except TelegramBadRequest as ex:
        log.warning("Не удалось отправить капчу в %s: %s", chat_id, ex)
        return

    # Таск на кик по таймауту
    async def _kick_on_timeout() -> None:
        try:
            await asyncio.sleep(settings.captcha_timeout_sec)
            pending = await captcha_store.pop(chat_id, user_id)
            if pending is None:
                return
            try:
                await bot.delete_message(chat_id, pending.message_id)
            except TelegramBadRequest:
                pass
            try:
                await bot.ban_chat_member(chat_id, user_id)
                await bot.unban_chat_member(chat_id, user_id, only_if_banned=True)
            except TelegramBadRequest as ex:
                log.warning("Не смог кикнуть %s: %s", user_id, ex)
            try:
                await bot.send_message(chat_id, texts.CAPTCHA_FAILED)
            except TelegramBadRequest:
                pass
        except asyncio.CancelledError:
            pass

    task = asyncio.create_task(_kick_on_timeout())
    await captcha_store.add(
        chat_id,
        user_id,
        PendingCaptcha(
            user_id=user_id, chat_id=chat_id, message_id=msg.message_id, task=task
        ),
    )


@router.callback_query(F.data.startswith("captcha:"))
async def on_captcha_click(callback: CallbackQuery, bot: Bot) -> None:
    """Проверка капчи. Только сам пользователь может нажать свою кнопку."""
    if callback.data is None or not callback.from_user:
        return
    try:
        target_id = int(callback.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("Некорректная капча.", show_alert=True)
        return

    if callback.from_user.id != target_id:
        await callback.answer("Эта кнопка не для тебя.", show_alert=True)
        return

    if callback.message is None:
        await callback.answer()
        return

    chat_id = callback.message.chat.id
    user_id = callback.from_user.id

    pending = await captcha_store.pop(chat_id, user_id)
    if pending is None:
        await callback.answer("Капча уже пройдена или истекла.", show_alert=True)
        return

    if pending.task is not None:
        pending.task.cancel()

    async with get_session() as session:
        await users.mark_captcha_passed(session, user_id)

    try:
        await callback.message.edit_text(
            texts.CAPTCHA_PASSED.format(name=callback.from_user.full_name)
        )
    except TelegramBadRequest:
        pass

    await callback.answer("Добро пожаловать!")
