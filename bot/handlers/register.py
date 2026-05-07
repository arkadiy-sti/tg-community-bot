"""FSM регистрации v2: language → role → name → area → primary_tag →
secondary_tags → contact_type → contact_value → bio → licensed → consent.

Поддерживает /lang отдельно от регистрации.
Гость пропускает всё после выбора роли.
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
from bot.i18n import COMMUNITY_INVITE_URL, normalize_lang, t
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
router = Router(name="register")


# Лимиты ввода
MAX_NAME_LEN = 128
MAX_AREA_LEN = 256
MAX_BIO_LEN = 500
MAX_LICENSE_LEN = 64


# ---------------------------------------------------------------------------
# Состояния FSM
# ---------------------------------------------------------------------------


class RegStates(StatesGroup):
    language = State()
    role = State()
    name = State()
    area = State()
    primary_tag = State()
    secondary_tags = State()
    custom_tag_input = State()
    contact_type = State()
    contact_value = State()
    bio = State()
    licensed = State()
    license_number = State()
    consent = State()


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
            [InlineKeyboardButton(text=t(lang, "role_coworker"),
                                  callback_data="reg:role:coworker")],
            [InlineKeyboardButton(text=t(lang, "role_customer"),
                                  callback_data="reg:role:customer")],
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


def _kb_tag_grid(
    tag_list,
    lang: str,
    *,
    selected: set[int] | None = None,
    show_done: bool = False,
    show_custom: bool = False,
) -> InlineKeyboardMarkup:
    """Сетка тегов (3 колонки), с опциональными кнопками снизу."""
    selected = selected or set()
    rows: list[list[InlineKeyboardButton]] = []
    line: list[InlineKeyboardButton] = []
    for tag in tag_list:
        label = tag.label_ru if lang == "ru" else tag.label_en
        prefix = "☑ " if tag.id in selected else ""
        line.append(InlineKeyboardButton(
            text=f"{prefix}{label}",
            callback_data=f"reg:tag:{tag.id}",
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
            callback_data="reg:tag:custom",
        ))
    if show_done:
        done_label = (
            f"✅ Готово ({len(selected)})"
            if lang == "ru" else f"✅ Done ({len(selected)})"
        )
        bottom.append(InlineKeyboardButton(
            text=done_label, callback_data="reg:tag:done"
        ))
    if bottom:
        rows.append(bottom)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _kb_contact_type(lang: str, *, required: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура выбора типа контакта.
    required=True — нет кнопки «Пропустить» (для Customer, где контакт обязателен).
    """
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text=t(lang, "contact_type_phone"),
                              callback_data="reg:contact:phone")],
        [InlineKeyboardButton(text=t(lang, "contact_type_whatsapp"),
                              callback_data="reg:contact:whatsapp")],
        [InlineKeyboardButton(text=t(lang, "contact_type_email"),
                              callback_data="reg:contact:email")],
    ]
    if not required:
        rows.append([InlineKeyboardButton(text=t(lang, "register_ask_skip"),
                                          callback_data="reg:contact:skip")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _kb_licensed(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "licensed_yes"),
                                  callback_data="reg:lic:yes")],
            [InlineKeyboardButton(text=t(lang, "licensed_no"),
                                  callback_data="reg:lic:no")],
            [InlineKeyboardButton(text=t(lang, "licensed_skip"),
                                  callback_data="reg:lic:skip")],
        ]
    )


def _kb_consent(lang: str, *, data_ok: bool, notif_ok: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=t(lang, "consent_data" if data_ok else "consent_data_off"),
                callback_data="reg:consent:toggle_data",
            )],
            [InlineKeyboardButton(
                text=t(lang, "consent_notif" if notif_ok else "consent_notif_off"),
                callback_data="reg:consent:toggle_notif",
            )],
            [InlineKeyboardButton(
                text=t(lang, "consent_finish"),
                callback_data="reg:consent:finish",
            )],
        ]
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _user_lang(tg_id: int) -> str:
    async with get_session() as session:
        u = await users.get_user(session, tg_id)
        return normalize_lang(u.language if u else None)


async def _send_primary_tag_step(
    target_message: Message, state: FSMContext, lang: str
) -> None:
    async with get_session() as session:
        skill_tags = await list_tags_by_category(session, "skill")
    await state.set_state(RegStates.primary_tag)
    await target_message.answer(
        t(lang, "register_ask_primary_tag"),
        reply_markup=_kb_tag_grid(skill_tags, lang, show_done=False, show_custom=False),
    )


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
    # Скрыть primary из сетки — он уже выбран
    visible = [tg for tg in skill_tags if tg.id != primary_id]
    text = t(
        lang,
        "register_ask_more_tags",
        limit=USER_TAGS_LIMIT,
        selected=len(selected),
        max=USER_TAGS_LIMIT - 1,  # primary уже в счёте
    )
    kb = _kb_tag_grid(
        visible, lang, selected=selected, show_done=True, show_custom=True
    )
    await state.set_state(RegStates.secondary_tags)
    if edit and target_message:
        try:
            await target_message.edit_text(text, reply_markup=kb)
            return
        except Exception:
            pass
    await target_message.answer(text, reply_markup=kb)


# ---------------------------------------------------------------------------
# /register — старт FSM
# ---------------------------------------------------------------------------


@router.message(Command("register"))
async def cmd_register(message: Message, state: FSMContext) -> None:
    if message.chat.type != "private" or message.from_user is None:
        return
    # Ban-check (защита от reroll) — но админов всегда пропускаем
    from bot.config import get_settings
    settings = get_settings()
    async with get_session() as session:
        if (
            message.from_user.id not in settings.admin_ids
            and await users.is_tg_id_banned(session, message.from_user.id)
        ):
            lang = await _user_lang(message.from_user.id)
            await message.answer(t(lang, "banned_user_blocked"))
            return
        existing = await users.get_user(session, message.from_user.id)
    await state.clear()
    await state.set_state(RegStates.language)
    # Если возвращающийся юзер (был soft-deleted) — мягкое приветствие
    if existing is not None and (existing.delete_count or 0) > 0:
        lang = normalize_lang(existing.language)
        await message.answer(t(lang, "register_returning"))
    await message.answer(
        "Выбери язык / Choose language:",
        reply_markup=_kb_language(),
    )


@router.message(Command("lang"))
async def cmd_lang(message: Message, state: FSMContext) -> None:
    if message.chat.type != "private":
        return
    await state.clear()
    await state.set_state(RegStates.language)
    await state.update_data(lang_only=True)
    await message.answer(
        "Выбери язык / Choose language:",
        reply_markup=_kb_language(),
    )


@router.message(Command("cancel"), RegStates())
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.clear()
    await message.answer(t(lang, "register_canceled"))


# ---------------------------------------------------------------------------
# Шаг 1: язык
# ---------------------------------------------------------------------------


@router.callback_query(RegStates.language, F.data.startswith("reg:lang:"))
async def cb_language(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None or callback.from_user is None:
        return
    lang = normalize_lang(callback.data.split(":")[2])

    async with get_session() as session:
        await users.set_language(session, callback.from_user.id, lang)

    data = await state.get_data()
    if data.get("lang_only"):
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
        await callback.message.edit_text(
            t(lang, "register_choose_role"),
            reply_markup=_kb_role(lang),
        )
    await callback.answer()


# ---------------------------------------------------------------------------
# Шаг 2: роль (coworker / guest)
# ---------------------------------------------------------------------------


@router.callback_query(RegStates.role, F.data.startswith("reg:role:"))
async def cb_role(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None or callback.from_user is None:
        return
    role = callback.data.split(":")[2]
    if role not in {"coworker", "customer"}:
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
    data = await state.get_data()
    lang = data.get("lang", "ru")
    name = message.text.strip()
    if not name or len(name) > MAX_NAME_LEN:
        await message.answer(
            t(lang, "post_too_long", n=len(name), max=MAX_NAME_LEN)
        )
        return
    await state.update_data(name=name)

    # Customer — пропускаем area/теги/bio/лицензию, сразу к контакту
    if data.get("role") == "customer":
        await state.set_state(RegStates.contact_type)
        await message.answer(
            t(lang, "register_ask_contact_type"),
            reply_markup=_kb_contact_type(lang, required=True),
        )
    else:
        await state.set_state(RegStates.area)
        await message.answer(t(lang, "register_ask_area"))


# ---------------------------------------------------------------------------
# Шаг 4: район
# ---------------------------------------------------------------------------


@router.message(RegStates.area)
async def step_area(message: Message, state: FSMContext) -> None:
    if not message.text:
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    area = message.text.strip()
    if not area or len(area) > MAX_AREA_LEN:
        await message.answer(
            t(lang, "post_too_long", n=len(area), max=MAX_AREA_LEN)
        )
        return
    await state.update_data(area=area)
    await _send_primary_tag_step(message, state, lang)


# ---------------------------------------------------------------------------
# Шаг 5: primary tag
# ---------------------------------------------------------------------------


@router.callback_query(RegStates.primary_tag, F.data.startswith("reg:tag:"))
async def cb_primary_tag(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None or callback.from_user is None:
        return
    payload = callback.data.split(":", 2)[2]
    data = await state.get_data()
    lang = data.get("lang", "ru")

    if payload in ("done", "custom"):
        # На primary нет custom/done — игнорируем
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

    await state.update_data(primary_tag_id=tag_id, secondary_tag_ids=[])
    if callback.message:
        await _send_secondary_tags_step(
            callback.message, state, lang, edit=True
        )
    await callback.answer()


# ---------------------------------------------------------------------------
# Шаг 6: secondary tags (multi-select)
# ---------------------------------------------------------------------------


@router.callback_query(RegStates.secondary_tags, F.data.startswith("reg:tag:"))
async def cb_secondary_tag(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None or callback.from_user is None:
        return
    payload = callback.data.split(":", 2)[2]
    data = await state.get_data()
    lang = data.get("lang", "ru")
    selected: list[int] = list(data.get("secondary_tag_ids", []))

    if payload == "done":
        await state.set_state(RegStates.contact_type)
        if callback.message:
            await callback.message.edit_text(
                t(lang, "register_ask_contact_type"),
                reply_markup=_kb_contact_type(lang),
            )
        await callback.answer()
        return

    if payload == "custom":
        async with get_session() as session:
            user = await users.get_user(session, callback.from_user.id)
            if user:
                used = await tags_svc.count_custom_tags_by_user(session, user.id)
            else:
                used = 0
        if used >= CUSTOM_TAG_LIMIT_PER_USER:
            await callback.answer(
                t(lang, "register_custom_tag_limit", limit=CUSTOM_TAG_LIMIT_PER_USER),
                show_alert=True,
            )
            return
        await state.set_state(RegStates.custom_tag_input)
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
        # Лимит: USER_TAGS_LIMIT всего, primary уже занимает 1 слот
        if len(selected_set) + 1 >= USER_TAGS_LIMIT:
            await callback.answer(
                t(lang, "register_tag_limit_reached", limit=USER_TAGS_LIMIT),
                show_alert=False,
            )
            return
        selected_set.add(tag_id)

    await state.update_data(secondary_tag_ids=list(selected_set))
    if callback.message:
        await _send_secondary_tags_step(
            callback.message, state, lang, edit=True
        )
    await callback.answer()


# Custom-tag ввод
@router.message(RegStates.custom_tag_input)
async def step_custom_tag(message: Message, state: FSMContext) -> None:
    if not message.text or message.from_user is None:
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    label = normalize_custom_tag(message.text)
    if label is None:
        await message.answer(t(lang, "register_custom_tag_invalid"))
        return

    async with get_session() as session:
        user = await users.get_user(session, message.from_user.id)
        if user is None:
            await message.answer(t(lang, "profile_not_registered"))
            await state.clear()
            return
        tag = await tags_svc.create_custom_tag(
            session,
            raw_label=label,
            category="skill",
            created_by_user_id=user.id,
        )
    if tag is None:
        await message.answer(
            t(lang, "register_custom_tag_limit", limit=CUSTOM_TAG_LIMIT_PER_USER)
        )
        # Возвращаемся к выбору
        await _send_secondary_tags_step(message, state, lang)
        return

    selected = list(data.get("secondary_tag_ids", []))
    if tag.id not in selected and len(selected) + 1 < USER_TAGS_LIMIT:
        selected.append(tag.id)
    await state.update_data(secondary_tag_ids=selected)
    await _send_secondary_tags_step(message, state, lang)


# ---------------------------------------------------------------------------
# Шаг 7: contact type → contact value
# ---------------------------------------------------------------------------


@router.callback_query(RegStates.contact_type, F.data.startswith("reg:contact:"))
async def cb_contact_type(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None:
        return
    kind = callback.data.split(":")[2]
    data = await state.get_data()
    lang = data.get("lang", "ru")

    if kind == "skip":
        # Для customer контакт обязателен — показываем алерт
        if data.get("role") == "customer":
            await callback.answer(
                t(lang, "register_contact_required"), show_alert=True
            )
            return
        await state.update_data(contact_kind=None)
        await state.set_state(RegStates.bio)
        if callback.message:
            await callback.message.edit_text(t(lang, "register_ask_bio"))
        await callback.answer()
        return

    if kind not in ("phone", "whatsapp", "email"):
        await callback.answer()
        return

    await state.update_data(contact_kind=kind)
    await state.set_state(RegStates.contact_value)
    prompt_key = {
        "phone": "register_ask_phone",
        "whatsapp": "register_ask_whatsapp",
        "email": "register_ask_email",
    }[kind]
    if callback.message:
        await callback.message.edit_text(t(lang, prompt_key))
    await callback.answer()


@router.message(RegStates.contact_value)
async def step_contact_value(message: Message, state: FSMContext) -> None:
    if not message.text:
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
        await state.update_data(contact_value=normalized)
    elif kind == "email":
        normalized = phones_svc.validate_email(raw)
        if normalized is None:
            await message.answer(t(lang, "register_email_invalid"))
            return
        await state.update_data(contact_value=normalized)
    else:
        await state.update_data(contact_value=None)

    # Customer — пропускаем bio/лицензию, сразу к consent
    if data.get("role") == "customer":
        await _go_to_consent_msg(message, state, lang)
    else:
        await state.set_state(RegStates.bio)
        await message.answer(t(lang, "register_ask_bio"))


# ---------------------------------------------------------------------------
# Шаг 8: bio
# ---------------------------------------------------------------------------


@router.message(RegStates.bio)
async def step_bio(message: Message, state: FSMContext) -> None:
    if not message.text:
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    bio = message.text.strip()
    if len(bio) > MAX_BIO_LEN:
        await message.answer(t(lang, "post_too_long", n=len(bio), max=MAX_BIO_LEN))
        return
    await state.update_data(bio=bio)
    await state.set_state(RegStates.licensed)
    await message.answer(
        t(lang, "register_ask_licensed"),
        reply_markup=_kb_licensed(lang),
    )


# ---------------------------------------------------------------------------
# Шаг 9: licensed?
# ---------------------------------------------------------------------------


@router.callback_query(RegStates.licensed, F.data.startswith("reg:lic:"))
async def cb_licensed(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None:
        return
    choice = callback.data.split(":")[2]
    data = await state.get_data()
    lang = data.get("lang", "ru")

    if choice == "yes":
        await state.update_data(is_licensed=True)
        await state.set_state(RegStates.license_number)
        if callback.message:
            await callback.message.edit_text(
                t(lang, "register_ask_license_number"),
                reply_markup=_kb_skip(lang, "license"),
            )
        await callback.answer()
        return

    # no / skip — пропускаем номер, идём к consent
    await state.update_data(is_licensed=(choice == "yes"), license_number=None)
    await _go_to_consent(callback, state, lang)


@router.callback_query(RegStates.license_number, F.data == "reg:skip:license")
async def cb_skip_license(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.update_data(license_number=None)
    await _go_to_consent(callback, state, lang)


@router.message(RegStates.license_number)
async def step_license_number(message: Message, state: FSMContext) -> None:
    if not message.text:
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    num = message.text.strip()
    if len(num) > MAX_LICENSE_LEN:
        await message.answer(
            t(lang, "post_too_long", n=len(num), max=MAX_LICENSE_LEN)
        )
        return
    await state.update_data(license_number=num)
    await _go_to_consent_msg(message, state, lang)


# ---------------------------------------------------------------------------
# Шаг 10: consent
# ---------------------------------------------------------------------------


async def _go_to_consent(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.update_data(consent_data=False, consent_notif=True)
    await state.set_state(RegStates.consent)
    if callback.message:
        await callback.message.edit_text(
            t(lang, "register_consent_intro"),
            reply_markup=_kb_consent(lang, data_ok=False, notif_ok=True),
        )
    await callback.answer()


async def _go_to_consent_msg(message: Message, state: FSMContext, lang: str) -> None:
    await state.update_data(consent_data=False, consent_notif=True)
    await state.set_state(RegStates.consent)
    await message.answer(
        t(lang, "register_consent_intro"),
        reply_markup=_kb_consent(lang, data_ok=False, notif_ok=True),
    )


@router.callback_query(RegStates.consent, F.data.startswith("reg:consent:"))
async def cb_consent(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None or callback.from_user is None:
        return
    action = callback.data.split(":")[2]
    data = await state.get_data()
    lang = data.get("lang", "ru")
    data_ok = bool(data.get("consent_data", False))
    notif_ok = bool(data.get("consent_notif", True))

    if action == "toggle_data":
        data_ok = not data_ok
        await state.update_data(consent_data=data_ok)
        if callback.message:
            await callback.message.edit_reply_markup(
                reply_markup=_kb_consent(lang, data_ok=data_ok, notif_ok=notif_ok)
            )
        await callback.answer()
        return

    if action == "toggle_notif":
        notif_ok = not notif_ok
        await state.update_data(consent_notif=notif_ok)
        if callback.message:
            await callback.message.edit_reply_markup(
                reply_markup=_kb_consent(lang, data_ok=data_ok, notif_ok=notif_ok)
            )
        await callback.answer()
        return

    if action == "finish":
        if not data_ok:
            await callback.answer(
                t(lang, "consent_data_required"),
                show_alert=True,
            )
            return
        await _finalize_registration(callback, state, lang)
        return

    await callback.answer()


async def _finalize_registration(
    callback: CallbackQuery, state: FSMContext, lang: str
) -> None:
    if callback.from_user is None:
        return
    data = await state.get_data()
    role = data.get("role", "coworker")

    contact_kind = data.get("contact_kind")
    contact_value = data.get("contact_value")
    contact_phone = contact_value if contact_kind == "phone" else None
    contact_whatsapp = contact_value if contact_kind == "whatsapp" else None
    contact_email = contact_value if contact_kind == "email" else None

    async with get_session() as session:
        u = await users.save_registration_v2(
            session,
            tg_id=callback.from_user.id,
            role=role,
            display_name=data.get("name"),
            area=data.get("area"),
            bio=data.get("bio"),
            contact_phone=contact_phone,
            contact_whatsapp=contact_whatsapp,
            contact_email=contact_email,
            is_licensed_contractor=bool(data.get("is_licensed", False)),
            license_number=data.get("license_number"),
            consent_data=bool(data.get("consent_data", False)),
            consent_notifications=bool(data.get("consent_notif", False)),
        )
        if u is not None and role == "coworker":
            primary_id = data.get("primary_tag_id")
            secondary_ids = data.get("secondary_tag_ids", [])
            await tags_svc.replace_user_tags(
                session,
                user_id=u.id,
                primary_tag_id=primary_id,
                secondary_tag_ids=secondary_ids,
            )

    await state.clear()
    if u is None:
        log.warning("save_registration_v2 failed for tg_id=%s", callback.from_user.id)
        if callback.message:
            await callback.message.edit_text(t(lang, "profile_not_registered"))
        await callback.answer()
        return

    log.info(
        "Registered v2 tg_id=%s role=%s licensed=%s",
        callback.from_user.id, u.role, u.is_licensed_contractor,
    )
    if callback.message:
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text=t(lang, "btn_join_group"),
                url=COMMUNITY_INVITE_URL,
            )
        ]])
        # Customer — отдельное welcome-сообщение
        done_key = "register_customer_done" if role == "customer" else "register_done"
        await callback.message.edit_text(
            t(lang, done_key, invite=COMMUNITY_INVITE_URL),
            reply_markup=kb,
            disable_web_page_preview=True,
        )
    await callback.answer()
