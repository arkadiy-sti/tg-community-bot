"""Welcome новичкам + капча."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import ChatMemberUpdatedFilter, IS_NOT_MEMBER, JOIN_TRANSITION
from aiogram.types import (
    CallbackQuery,
    ChatMemberUpdated,
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from bot import texts
from bot.config import get_settings
from bot.db.database import get_session
from bot.i18n import normalize_lang, t
from bot.keyboards.inline import captcha_kb
from bot.services import users
from bot.services.captcha import PendingCaptcha, captcha_store

log = logging.getLogger(__name__)

router = Router(name="welcome")

# Роли, которым разрешено писать в группе
_WRITE_ROLES = {"coworker", "customer"}


def _restricted_perms() -> ChatPermissions:
    """Запрет отправки сообщений."""
    return ChatPermissions(can_send_messages=False)


def _write_perms() -> ChatPermissions:
    """Базовые права на отправку сообщений (текст, медиа, стикеры, опросы)."""
    return ChatPermissions(
        can_send_messages=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True,
        can_send_polls=True,
    )


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

    # Сохраняем пользователя в БД, проверяем статус регистрации
    async with get_session() as session:
        await users.upsert_user(
            session,
            tg_id=user_id,
            username=user.username,
            full_name=name,
        )
        u = await users.get_user(session, user_id)

    is_registered = (
        u is not None
        and u.role in _WRITE_ROLES
        and not (u.is_deleted or False)
    )

    # Незарегистрированных — сразу ограничиваем в отправке сообщений
    if not is_registered:
        try:
            await bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=_restricted_perms(),
            )
        except TelegramBadRequest as ex:
            log.warning("Не смог ограничить %s: %s", user_id, ex)

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
        u = await users.get_user(session, user_id)
    lang = normalize_lang(u.language if u else None)
    community = t(lang, "community_name")
    name = callback.from_user.full_name or callback.from_user.first_name or "друг"

    is_registered = (
        u is not None
        and u.role in _WRITE_ROLES
        and not (u.is_deleted or False)
    )

    # Кнопка «Открыть бота» — deep-link к нашему боту
    bot_url: str | None = None
    try:
        me = await bot.me()
        if me.username:
            bot_url = f"https://t.me/{me.username}?start=welcome"
    except Exception as e:
        log.info("Could not fetch bot username for welcome button: %s", e)

    if is_registered:
        # Уже зарегистрирован — снимаем ограничения
        try:
            await bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=_write_perms(),
            )
        except TelegramBadRequest as ex:
            log.info("Не смог выдать права %s: %s", user_id, ex)

        kb = None
        if bot_url:
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=t(lang, "btn_open_bot"), url=bot_url),
            ]])
        try:
            await callback.message.edit_text(
                t(lang, "captcha_passed", name=name, community=community),
                reply_markup=kb,
                disable_web_page_preview=True,
            )
        except TelegramBadRequest:
            pass
    else:
        # Не зарегистрирован — остаётся restricted, показываем инструкцию
        kb = None
        if bot_url:
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=t(lang, "btn_open_bot"), url=bot_url),
            ]])
        try:
            await callback.message.edit_text(
                t(lang, "captcha_passed_restricted", name=name, community=community),
                reply_markup=kb,
                disable_web_page_preview=True,
            )
        except TelegramBadRequest:
            pass

        # DM: дублируем инструкцию в личку (если бот уже запущен у юзера)
        if bot_url:
            try:
                await bot.send_message(
                    user_id,
                    t(lang, "captcha_passed_restricted", name=name, community=community),
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(text=t(lang, "btn_open_bot"), url=bot_url),
                    ]]),
                    disable_web_page_preview=True,
                )
            except Exception as ex:
                log.info("Не смог отправить DM %s: %s", user_id, ex)

    await callback.answer("Добро пожаловать!" if is_registered else "Зарегистрируйся через бота!")
