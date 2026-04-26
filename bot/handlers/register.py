"""FSM регистрации: /register — выбор языка, роли, имени, района, телефона, био.

Поддерживает /lang для смены языка отдельно от регистрации.
"""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardRemove,
)

from bot.db.database import get_session
from bot.i18n import normalize_lang, t
from bot.services import users

log = logging.getLogger(__name__)
router = Router(name="register")


# Лимиты
MAX_NAME_LEN = 128
MAX_AREA_LEN = 256
MAX_PHONE_LEN = 64
MAX_BIO_LEN = 500


# ---------------------------------------------------------------------------
# Состояния FSM
# ---------------------------------------------------------------------------


class RegStates(StatesGroup):
    """Шаги регистрации."""

    language = State()
    role = State()
    name = State()
    area = State()
    phone = State()
    bio = State()


# ---------------------------------------------------------------------------
# Клавиатуры
# ---------------------------------------------------------------------------


def _kb_language() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="reg:lang:ru"),
                InlineKeyboardButton(text="🇺🇸 English", callback_data="reg:lang:en"),
            ]
        ]
    )


def _kb_role(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "role_handyman"),
                                  callback_data="reg:role:handyman")],
            [InlineKeyboardButton(text=t(lang, "role_individual"),
                                  callback_data="reg:role:individual")],
            [InlineKeyboardButton(text=t(lang, "role_company"),
                                  callback_data="reg:role:company")],
        ]
    )


def _kb_skip(lang: str, payload: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=t(lang, "register_ask_skip"),
                callback_data=f"reg:skip:{payload}",
            )]
        ]
    )


# ---------------------------------------------------------------------------
# Хелпер: достать язык пользователя из БД (для текстов вне FSM)
# ---------------------------------------------------------------------------


async def _user_lang(tg_id: int) -> str:
    async with get_session() as session:
        u = await users.get_user(session, tg_id)
        return normalize_lang(u.language if u else None)


# ---------------------------------------------------------------------------
# /register — стартует FSM
# ---------------------------------------------------------------------------


@router.message(Command("register"))
async def cmd_register(message: Message, state: FSMContext) -> None:
    if message.chat.type != "private":
        # Регистрация — только в личке
        return
    await state.clear()
    await state.set_state(RegStates.language)
    await message.answer(
        "Выбери язык / Choose language:",
        reply_markup=_kb_language(),
    )


@router.message(Command("lang"))
async def cmd_lang(message: Message, state: FSMContext) -> None:
    """Смена языка вне FSM регистрации."""
    if message.chat.type != "private":
        return
    await state.clear()
    await state.set_state(RegStates.language)
    await state.update_data(lang_only=True)
    await message.answer(
        "Выбери язык / Choose language:",
        reply_markup=_kb_language(),
    )


# ---------------------------------------------------------------------------
# Шаг 1: выбор языка
# ---------------------------------------------------------------------------


@router.callback_query(RegStates.language, F.data.startswith("reg:lang:"))
async def cb_language(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None or callback.from_user is None:
        return
    lang = callback.data.split(":")[2]
    lang = normalize_lang(lang)

    async with get_session() as session:
        await users.set_language(session, callback.from_user.id, lang)

    data = await state.get_data()
    if data.get("lang_only"):
        # /lang — просто переключить и закрыть
        await state.clear()
        if callback.message:
            await callback.message.edit_text(
                {"ru": "✅ Язык переключён на русский.",
                 "en": "✅ Language switched to English."}[lang]
            )
        await callback.answer()
        return

    await state.update_data(lang=lang)
    await state.set_state(RegStates.role)
    if callback.message:
        await callback.message.edit_text(t(lang, "register_choose_role"),
                                         reply_markup=_kb_role(lang))
    await callback.answer()


# ---------------------------------------------------------------------------
# Шаг 2: выбор роли
# ---------------------------------------------------------------------------


@router.callback_query(RegStates.role, F.data.startswith("reg:role:"))
async def cb_role(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None:
        return
    role = callback.data.split(":")[2]
    if role not in {"handyman", "individual", "company"}:
        await callback.answer("?", show_alert=False)
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.update_data(role=role)
    await state.set_state(RegStates.name)
    if callback.message:
        await callback.message.edit_text(t(lang, "register_ask_name"))
    await callback.answer()


# ---------------------------------------------------------------------------
# Шаг 3: имя
# ---------------------------------------------------------------------------


@router.message(RegStates.name)
async def step_name(message: Message, state: FSMContext) -> None:
    if not message.text:
        return
    name = message.text.strip()
    if len(name) > MAX_NAME_LEN:
        await message.answer(
            t((await state.get_data()).get("lang", "ru"), "post_too_long",
              n=len(name), max=MAX_NAME_LEN)
        )
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.update_data(name=name)
    await state.set_state(RegStates.area)
    await message.answer(t(lang, "register_ask_area"))


# ---------------------------------------------------------------------------
# Шаг 4: район
# ---------------------------------------------------------------------------


@router.message(RegStates.area)
async def step_area(message: Message, state: FSMContext) -> None:
    if not message.text:
        return
    area = message.text.strip()
    if len(area) > MAX_AREA_LEN:
        await message.answer(
            t((await state.get_data()).get("lang", "ru"), "post_too_long",
              n=len(area), max=MAX_AREA_LEN)
        )
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.update_data(area=area)
    await state.set_state(RegStates.phone)
    await message.answer(
        t(lang, "register_ask_phone"),
        reply_markup=_kb_skip(lang, "phone"),
    )


# ---------------------------------------------------------------------------
# Шаг 5: телефон
# ---------------------------------------------------------------------------


@router.callback_query(RegStates.phone, F.data == "reg:skip:phone")
async def cb_skip_phone(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.update_data(phone=None)
    await state.set_state(RegStates.bio)
    if callback.message:
        await callback.message.edit_text(t(lang, "register_ask_bio"))
    await callback.answer()


@router.message(RegStates.phone)
async def step_phone(message: Message, state: FSMContext) -> None:
    if not message.text:
        return
    phone = message.text.strip()
    if len(phone) > MAX_PHONE_LEN:
        await message.answer(
            t((await state.get_data()).get("lang", "ru"), "post_too_long",
              n=len(phone), max=MAX_PHONE_LEN)
        )
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.update_data(phone=phone)
    await state.set_state(RegStates.bio)
    await message.answer(t(lang, "register_ask_bio"),
                         reply_markup=ReplyKeyboardRemove())


# ---------------------------------------------------------------------------
# Шаг 6: bio + сохранение
# ---------------------------------------------------------------------------


@router.message(RegStates.bio)
async def step_bio(message: Message, state: FSMContext) -> None:
    if not message.text or message.from_user is None:
        return
    bio = message.text.strip()
    data = await state.get_data()
    lang = data.get("lang", "ru")
    if len(bio) > MAX_BIO_LEN:
        await message.answer(t(lang, "post_too_long", n=len(bio), max=MAX_BIO_LEN))
        return

    async with get_session() as session:
        u = await users.save_registration(
            session,
            tg_id=message.from_user.id,
            role=data["role"],
            display_name=data["name"],
            area=data.get("area"),
            phone=data.get("phone"),
            bio=bio,
        )
    await state.clear()

    if u is None:
        log.warning("save_registration: user not found tg_id=%s", message.from_user.id)
        await message.answer(t(lang, "profile_not_registered"))
        return

    log.info("Registered user tg_id=%s role=%s", message.from_user.id, data["role"])
    await message.answer(t(lang, "register_done"))
