"""/edit — точечное редактирование профиля.
/delete_me — удаление профиля с подтверждением.
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
)

from bot.db.database import get_session
from bot.i18n import normalize_lang, t
from bot.services import phones as phones_svc
from bot.services import users

log = logging.getLogger(__name__)
router = Router(name="edit")


MAX_NAME_LEN = 128
MAX_AREA_LEN = 256
MAX_BIO_LEN = 500
MAX_LICENSE_LEN = 64


class EditStates(StatesGroup):
    menu = State()
    name = State()
    area = State()
    bio = State()
    contact_type = State()
    contact_value = State()
    license = State()


class DeleteStates(StatesGroup):
    confirm = State()


# ---------------------------------------------------------------------------
# /edit
# ---------------------------------------------------------------------------


def _kb_edit_menu(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(lang, "edit_field_name"),
                                     callback_data="edit:f:name"),
                InlineKeyboardButton(text=t(lang, "edit_field_area"),
                                     callback_data="edit:f:area"),
            ],
            [
                InlineKeyboardButton(text=t(lang, "edit_field_bio"),
                                     callback_data="edit:f:bio"),
                InlineKeyboardButton(text=t(lang, "edit_field_contact"),
                                     callback_data="edit:f:contact"),
            ],
            [
                InlineKeyboardButton(text=t(lang, "edit_field_license"),
                                     callback_data="edit:f:license"),
                InlineKeyboardButton(text=t(lang, "edit_field_lang"),
                                     callback_data="edit:f:lang"),
            ],
            [InlineKeyboardButton(text=t(lang, "edit_cancel"),
                                  callback_data="edit:cancel")],
        ]
    )


def _kb_contact_type(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "contact_type_phone"),
                                  callback_data="edit:contact:phone")],
            [InlineKeyboardButton(text=t(lang, "contact_type_whatsapp"),
                                  callback_data="edit:contact:whatsapp")],
            [InlineKeyboardButton(text=t(lang, "contact_type_email"),
                                  callback_data="edit:contact:email")],
            [InlineKeyboardButton(text=t(lang, "edit_cancel"),
                                  callback_data="edit:cancel")],
        ]
    )


@router.message(Command("edit"))
async def cmd_edit(message: Message, state: FSMContext) -> None:
    if message.chat.type != "private" or message.from_user is None:
        return
    async with get_session() as session:
        u = await users.get_user(session, message.from_user.id)
    if u is None or not u.role or u.role == "guest":
        lang = normalize_lang(u.language if u else None)
        await message.answer(t(lang, "edit_not_registered"))
        return
    lang = normalize_lang(u.language)
    await state.clear()
    await state.set_state(EditStates.menu)
    await state.update_data(lang=lang)
    await message.answer(t(lang, "edit_menu"), reply_markup=_kb_edit_menu(lang))


@router.callback_query(EditStates.menu, F.data == "edit:cancel")
@router.callback_query(F.data == "edit:cancel")
async def cb_edit_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if callback.message:
        try:
            await callback.message.edit_text("✖")
        except Exception:
            pass
    await callback.answer()


@router.callback_query(EditStates.menu, F.data.startswith("edit:f:"))
async def cb_edit_field(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None:
        return
    field = callback.data.split(":")[2]
    data = await state.get_data()
    lang = data.get("lang", "ru")

    if field == "name":
        await state.set_state(EditStates.name)
        if callback.message:
            await callback.message.edit_text(t(lang, "register_ask_name"))
    elif field == "area":
        await state.set_state(EditStates.area)
        if callback.message:
            await callback.message.edit_text(t(lang, "register_ask_area"))
    elif field == "bio":
        await state.set_state(EditStates.bio)
        if callback.message:
            await callback.message.edit_text(t(lang, "register_ask_bio"))
    elif field == "contact":
        await state.set_state(EditStates.contact_type)
        if callback.message:
            await callback.message.edit_text(
                t(lang, "register_ask_contact_type"),
                reply_markup=_kb_contact_type(lang),
            )
    elif field == "license":
        await state.set_state(EditStates.license)
        if callback.message:
            await callback.message.edit_text(t(lang, "register_ask_license_number"))
    elif field == "lang":
        # Просто переключаем
        new_lang = "en" if lang == "ru" else "ru"
        if callback.from_user:
            async with get_session() as session:
                await users.set_language(session, callback.from_user.id, new_lang)
        await state.clear()
        if callback.message:
            await callback.message.edit_text(
                {"ru": "✅ Язык переключён на русский.",
                 "en": "✅ Language switched to English."}[new_lang]
            )
    await callback.answer()


@router.message(EditStates.name)
async def edit_name(message: Message, state: FSMContext) -> None:
    if not message.text or message.from_user is None:
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    name = message.text.strip()
    if not name or len(name) > MAX_NAME_LEN:
        await message.answer(t(lang, "post_too_long", n=len(name), max=MAX_NAME_LEN))
        return
    async with get_session() as session:
        await users.update_profile_field(session, message.from_user.id, "display_name", name)
    await state.clear()
    await message.answer(t(lang, "edit_done"))


@router.message(EditStates.area)
async def edit_area(message: Message, state: FSMContext) -> None:
    if not message.text or message.from_user is None:
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    area = message.text.strip()
    if not area or len(area) > MAX_AREA_LEN:
        await message.answer(t(lang, "post_too_long", n=len(area), max=MAX_AREA_LEN))
        return
    async with get_session() as session:
        await users.update_profile_field(session, message.from_user.id, "area", area)
    await state.clear()
    await message.answer(t(lang, "edit_done"))


@router.message(EditStates.bio)
async def edit_bio(message: Message, state: FSMContext) -> None:
    if not message.text or message.from_user is None:
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    bio = message.text.strip()
    if len(bio) > MAX_BIO_LEN:
        await message.answer(t(lang, "post_too_long", n=len(bio), max=MAX_BIO_LEN))
        return
    async with get_session() as session:
        await users.update_profile_field(session, message.from_user.id, "bio", bio)
    await state.clear()
    await message.answer(t(lang, "edit_done"))


@router.callback_query(EditStates.contact_type, F.data.startswith("edit:contact:"))
async def cb_edit_contact_type(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None:
        return
    kind = callback.data.split(":")[2]
    data = await state.get_data()
    lang = data.get("lang", "ru")
    if kind not in ("phone", "whatsapp", "email"):
        await callback.answer()
        return
    await state.update_data(contact_kind=kind)
    await state.set_state(EditStates.contact_value)
    prompt_key = {
        "phone": "register_ask_phone",
        "whatsapp": "register_ask_whatsapp",
        "email": "register_ask_email",
    }[kind]
    if callback.message:
        await callback.message.edit_text(t(lang, prompt_key))
    await callback.answer()


@router.message(EditStates.contact_value)
async def edit_contact_value(message: Message, state: FSMContext) -> None:
    if not message.text or message.from_user is None:
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    kind = data.get("contact_kind")
    raw = message.text.strip()

    if kind in ("phone", "whatsapp"):
        normalized = phones_svc.normalize_phone(raw)
        if normalized is None:
            await message.answer(t(lang, "register_phone_invalid"))
            return
        field = "contact_phone" if kind == "phone" else "contact_whatsapp"
        async with get_session() as session:
            await users.update_profile_field(
                session, message.from_user.id, field, normalized
            )
    elif kind == "email":
        normalized = phones_svc.validate_email(raw)
        if normalized is None:
            await message.answer(t(lang, "register_email_invalid"))
            return
        async with get_session() as session:
            await users.update_profile_field(
                session, message.from_user.id, "contact_email", normalized
            )
    await state.clear()
    await message.answer(t(lang, "edit_done"))


@router.message(EditStates.license)
async def edit_license(message: Message, state: FSMContext) -> None:
    if not message.text or message.from_user is None:
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    num = message.text.strip()
    if len(num) > MAX_LICENSE_LEN:
        await message.answer(
            t(lang, "post_too_long", n=len(num), max=MAX_LICENSE_LEN)
        )
        return
    async with get_session() as session:
        await users.update_profile_field(
            session, message.from_user.id, "license_number", num
        )
        await users.update_profile_field(
            session, message.from_user.id, "is_licensed_contractor", True
        )
    await state.clear()
    await message.answer(t(lang, "edit_done"))


# ---------------------------------------------------------------------------
# /delete_me
# ---------------------------------------------------------------------------


def _kb_delete_confirm(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "delete_me_yes"),
                                  callback_data="delete:yes")],
            [InlineKeyboardButton(text=t(lang, "delete_me_no"),
                                  callback_data="delete:no")],
        ]
    )


@router.message(Command("delete_me"))
async def cmd_delete_me(message: Message, state: FSMContext) -> None:
    if message.chat.type != "private" or message.from_user is None:
        return
    async with get_session() as session:
        u = await users.get_user(session, message.from_user.id)
    lang = normalize_lang(u.language if u else None)
    await state.clear()
    await state.set_state(DeleteStates.confirm)
    await state.update_data(lang=lang)
    await message.answer(
        t(lang, "delete_me_confirm"),
        reply_markup=_kb_delete_confirm(lang),
    )


@router.callback_query(DeleteStates.confirm, F.data == "delete:yes")
async def cb_delete_yes(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user is None:
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    async with get_session() as session:
        ok = await users.delete_user(session, callback.from_user.id)
    await state.clear()
    if callback.message:
        await callback.message.edit_text(
            t(lang, "delete_me_done") if ok else t(lang, "delete_me_canceled")
        )
    log.info("Deleted profile tg_id=%s ok=%s", callback.from_user.id, ok)
    await callback.answer()


@router.callback_query(DeleteStates.confirm, F.data == "delete:no")
async def cb_delete_no(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.clear()
    if callback.message:
        await callback.message.edit_text(t(lang, "delete_me_canceled"))
    await callback.answer()
