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
from bot.services import tags as tags_svc
from bot.services import users
from bot.services.tags import (
    CUSTOM_TAG_LIMIT_PER_USER,
    USER_TAGS_LIMIT,
    list_tags_by_category,
    normalize_custom_tag,
)

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
    tags_primary = State()
    tags_secondary = State()
    tags_custom_input = State()


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
                InlineKeyboardButton(text=t(lang, "edit_field_tags"),
                                     callback_data="edit:f:tags"),
                InlineKeyboardButton(text=t(lang, "edit_field_license"),
                                     callback_data="edit:f:license"),
            ],
            [
                InlineKeyboardButton(text=t(lang, "edit_field_lang"),
                                     callback_data="edit:f:lang"),
                InlineKeyboardButton(text=t(lang, "edit_cancel"),
                                     callback_data="edit:cancel"),
            ],
        ]
    )


def _kb_tag_grid(
    tag_list,
    lang: str,
    *,
    selected: set[int] | None = None,
    show_done: bool = False,
    show_custom: bool = False,
) -> InlineKeyboardMarkup:
    """Сетка тегов 3 в ряд для /edit (зеркалит register._kb_tag_grid)."""
    selected = selected or set()
    rows: list[list[InlineKeyboardButton]] = []
    line: list[InlineKeyboardButton] = []
    for tag in tag_list:
        label = tag.label_ru if lang == "ru" else tag.label_en
        prefix = "☑ " if tag.id in selected else ""
        line.append(InlineKeyboardButton(
            text=f"{prefix}{label}",
            callback_data=f"edit:t:{tag.id}",
        ))
        if len(line) == 3:
            rows.append(line)
            line = []
    if line:
        rows.append(line)
    bottom: list[InlineKeyboardButton] = []
    if show_custom:
        bottom.append(InlineKeyboardButton(
            text="✏️ Свой вариант" if lang == "ru" else "✏️ Custom",
            callback_data="edit:t:custom",
        ))
    if show_done:
        done_label = (
            f"✅ Готово ({len(selected)})"
            if lang == "ru" else f"✅ Done ({len(selected)})"
        )
        bottom.append(InlineKeyboardButton(
            text=done_label, callback_data="edit:t:done"
        ))
    if bottom:
        rows.append(bottom)
    return InlineKeyboardMarkup(inline_keyboard=rows)


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
    elif field == "tags":
        if callback.from_user:
            async with get_session() as session:
                me = await users.get_user(session, callback.from_user.id)
                if me is None:
                    await callback.answer()
                    return
                # Текущие теги — pre-select
                cur = await tags_svc.get_user_tags(session, me.id)
                primary_id = next(
                    (ut.tag_id for ut in cur if ut.is_primary), None
                )
                secondary_ids = [
                    ut.tag_id for ut in cur if not ut.is_primary
                ]
                skill_tags = await list_tags_by_category(session, "skill")
            await state.update_data(
                primary_tag_id=primary_id,
                secondary_tag_ids=secondary_ids,
            )
            await state.set_state(EditStates.tags_primary)
            if callback.message:
                await callback.message.edit_text(
                    t(lang, "register_ask_primary_tag"),
                    reply_markup=_kb_tag_grid(
                        skill_tags, lang,
                        selected={primary_id} if primary_id else set(),
                        show_done=False, show_custom=False,
                    ),
                )
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
# /edit → теги (multi-select c pre-select текущих)
# ---------------------------------------------------------------------------


async def _send_secondary_tags_step(
    target_message: Message,
    state: FSMContext,
    lang: str,
    *,
    edit: bool = False,
) -> None:
    data = await state.get_data()
    primary_id: int | None = data.get("primary_tag_id")
    selected: set[int] = set(data.get("secondary_tag_ids", []))
    async with get_session() as session:
        skill_tags = await list_tags_by_category(session, "skill")
    visible = [tg for tg in skill_tags if tg.id != primary_id]
    text = t(
        lang,
        "register_ask_more_tags",
        limit=USER_TAGS_LIMIT,
        selected=len(selected),
        max=USER_TAGS_LIMIT - 1,
    )
    kb = _kb_tag_grid(
        visible, lang, selected=selected, show_done=True, show_custom=True
    )
    await state.set_state(EditStates.tags_secondary)
    if edit and target_message:
        try:
            await target_message.edit_text(text, reply_markup=kb)
            return
        except Exception:
            pass
    await target_message.answer(text, reply_markup=kb)


@router.callback_query(EditStates.tags_primary, F.data.startswith("edit:t:"))
async def cb_edit_primary_tag(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None:
        return
    payload = callback.data.split(":", 2)[2]
    data = await state.get_data()
    lang = data.get("lang", "ru")
    if payload in ("done", "custom"):
        await callback.answer()
        return
    try:
        tag_id = int(payload)
    except ValueError:
        await callback.answer()
        return
    async with get_session() as session:
        tag = await tags_svc.get_tag(session, tag_id)
    if tag is None:
        await callback.answer("?")
        return
    # При смене primary очищаем secondary (как в register)
    await state.update_data(primary_tag_id=tag_id, secondary_tag_ids=[])
    if callback.message:
        await _send_secondary_tags_step(callback.message, state, lang, edit=True)
    await callback.answer()


@router.callback_query(EditStates.tags_secondary, F.data.startswith("edit:t:"))
async def cb_edit_secondary_tag(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None or callback.from_user is None:
        return
    payload = callback.data.split(":", 2)[2]
    data = await state.get_data()
    lang = data.get("lang", "ru")
    selected: list[int] = list(data.get("secondary_tag_ids", []))

    if payload == "done":
        # Сохраняем
        primary_id = data.get("primary_tag_id")
        async with get_session() as session:
            me = await users.get_user(session, callback.from_user.id)
            if me is None:
                await state.clear()
                await callback.answer()
                return
            await tags_svc.replace_user_tags(
                session,
                user_id=me.id,
                primary_tag_id=primary_id,
                secondary_tag_ids=selected,
            )
        await state.clear()
        if callback.message:
            await callback.message.edit_text(t(lang, "edit_done"))
        log.info("Edited tags for tg_id=%s", callback.from_user.id)
        await callback.answer()
        return

    if payload == "custom":
        async with get_session() as session:
            me = await users.get_user(session, callback.from_user.id)
            used = (
                await tags_svc.count_custom_tags_by_user(session, me.id)
                if me else 0
            )
        if used >= CUSTOM_TAG_LIMIT_PER_USER:
            await callback.answer(
                t(lang, "register_custom_tag_limit", limit=CUSTOM_TAG_LIMIT_PER_USER),
                show_alert=True,
            )
            return
        await state.set_state(EditStates.tags_custom_input)
        if callback.message:
            await callback.message.answer(t(lang, "register_ask_custom_tag"))
        await callback.answer()
        return

    try:
        tag_id = int(payload)
    except ValueError:
        await callback.answer()
        return

    selected_set = set(selected)
    if tag_id in selected_set:
        selected_set.remove(tag_id)
    else:
        if len(selected_set) + 1 >= USER_TAGS_LIMIT:
            await callback.answer(
                t(lang, "register_tag_limit_reached", limit=USER_TAGS_LIMIT),
                show_alert=False,
            )
            return
        selected_set.add(tag_id)
    await state.update_data(secondary_tag_ids=list(selected_set))
    if callback.message:
        await _send_secondary_tags_step(callback.message, state, lang, edit=True)
    await callback.answer()


@router.message(EditStates.tags_custom_input)
async def edit_custom_tag(message: Message, state: FSMContext) -> None:
    if not message.text or message.from_user is None:
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    label = normalize_custom_tag(message.text)
    if label is None:
        await message.answer(t(lang, "register_custom_tag_invalid"))
        return
    async with get_session() as session:
        me = await users.get_user(session, message.from_user.id)
        if me is None:
            await message.answer(t(lang, "edit_not_registered"))
            await state.clear()
            return
        tag = await tags_svc.create_custom_tag(
            session,
            raw_label=label,
            category="skill",
            created_by_user_id=me.id,
        )
    if tag is None:
        await message.answer(
            t(lang, "register_custom_tag_limit", limit=CUSTOM_TAG_LIMIT_PER_USER)
        )
        await _send_secondary_tags_step(message, state, lang)
        return
    selected = list(data.get("secondary_tag_ids", []))
    if tag.id not in selected and len(selected) + 1 < USER_TAGS_LIMIT:
        selected.append(tag.id)
    await state.update_data(secondary_tag_ids=selected)
    await _send_secondary_tags_step(message, state, lang)


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
