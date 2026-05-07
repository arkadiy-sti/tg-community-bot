"""FSM создания объявления /post.

Шаги: kind → locations → skills → (num_people|engagement) → helper_kind →
language → duration → urgency → budget → description → photos → contact → preview.

После Submit объявление сохраняется со status='pending'.
Модерация и публикация — в bot/handlers/post_moderation.py (часть 2).
"""
from __future__ import annotations

import html
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
from bot.db.models import Tag
from bot.i18n import normalize_lang, t
from bot.services import listings as listings_svc
from bot.services import users
from bot.services.tags import list_tags_by_category

log = logging.getLogger(__name__)
router = Router(name="post")


# ---------------------------------------------------------------------------
# Состояния FSM
# ---------------------------------------------------------------------------


class PostStates(StatesGroup):
    kind = State()
    locations = State()
    location_custom_input = State()
    skills = State()
    skill_custom_input = State()
    num_people = State()        # offer
    engagement = State()        # seek
    helper_kind = State()       # offer
    language = State()
    duration = State()
    urgency = State()
    budget = State()            # offer (опц.)
    description = State()
    photos = State()
    contact = State()
    contact_other = State()
    preview = State()


# ---------------------------------------------------------------------------
# Клавиатуры
# ---------------------------------------------------------------------------


def _kb_kind(lang: str) -> InlineKeyboardMarkup:
    # «Ищу работу» (seek) временно скрыто — раскомментируем когда наберём
    # аудиторию исполнителей (~> 100 Coworker-ов).
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "post_kind_offer_btn"),
                                  callback_data="p:k:offer")],
            # [InlineKeyboardButton(text=t(lang, "post_kind_seek_btn"),
            #                       callback_data="p:k:seek")],
            [InlineKeyboardButton(text=t(lang, "post_cancel"),
                                  callback_data="p:cancel")],
        ]
    )


def _kb_tag_grid(
    tags: list[Tag],
    lang: str,
    *,
    selected: set[int],
    show_done: bool = True,
    show_custom: bool = False,
    cb_prefix: str = "p:t",
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    line: list[InlineKeyboardButton] = []
    for tag in tags:
        label = tag.label_ru if lang == "ru" else tag.label_en
        prefix = "☑ " if tag.id in selected else ""
        line.append(InlineKeyboardButton(
            text=f"{prefix}{label}",
            callback_data=f"{cb_prefix}:{tag.id}",
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
            callback_data=f"{cb_prefix}:custom",
        ))
    if show_done:
        bottom.append(InlineKeyboardButton(
            text=t(lang, "post_done") + f" ({len(selected)})",
            callback_data=f"{cb_prefix}:done",
        ))
    bottom.append(InlineKeyboardButton(
        text=t(lang, "post_cancel"), callback_data="p:cancel"
    ))
    rows.append(bottom)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _kb_simple_choices(
    items: list[tuple[str, str]],
    lang: str,
    *,
    show_skip: bool = False,
    show_cancel: bool = True,
) -> InlineKeyboardMarkup:
    """items = [(callback_value, label_text), …]"""
    rows = [
        [InlineKeyboardButton(text=lbl, callback_data=cb)]
        for cb, lbl in items
    ]
    bottom: list[InlineKeyboardButton] = []
    if show_skip:
        bottom.append(InlineKeyboardButton(
            text=t(lang, "post_skip"), callback_data="p:skip"
        ))
    if show_cancel:
        bottom.append(InlineKeyboardButton(
            text=t(lang, "post_cancel"), callback_data="p:cancel"
        ))
    if bottom:
        rows.append(bottom)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _kb_num_people(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1", callback_data="p:n:1"),
            InlineKeyboardButton(text="2", callback_data="p:n:2"),
            InlineKeyboardButton(text="3", callback_data="p:n:3"),
            InlineKeyboardButton(text="4", callback_data="p:n:4"),
            InlineKeyboardButton(
                text=t(lang, "post_num_5_plus"), callback_data="p:n:5"
            ),
        ],
        [InlineKeyboardButton(text=t(lang, "post_cancel"), callback_data="p:cancel")],
    ])


def _kb_engagement(lang: str) -> InlineKeyboardMarkup:
    return _kb_simple_choices([
        ("p:e:one_time", t(lang, "post_engagement_one_time")),
        ("p:e:part_time", t(lang, "post_engagement_part_time")),
    ], lang)


def _kb_helper(lang: str) -> InlineKeyboardMarkup:
    return _kb_simple_choices([
        ("p:hk:pro", t(lang, "post_helper_pro")),
        ("p:hk:helper", t(lang, "post_helper_helper")),
        ("p:hk:any", t(lang, "post_helper_any")),
    ], lang)


def _kb_language_offer(lang: str) -> InlineKeyboardMarkup:
    return _kb_simple_choices([
        ("p:lo:none", t(lang, "post_lang_offer_none")),
        ("p:lo:ru", t(lang, "post_lang_offer_ru")),
        ("p:lo:en", t(lang, "post_lang_offer_en")),
    ], lang)


def _kb_language_seek(lang: str, selected: set[str]) -> InlineKeyboardMarkup:
    rows = []
    for code, key in [("ru", "post_lang_seek_ru"), ("en", "post_lang_seek_en")]:
        prefix = "☑ " if code in selected else ""
        rows.append([InlineKeyboardButton(
            text=f"{prefix}{t(lang, key)}",
            callback_data=f"p:ls:{code}",
        )])
    rows.append([
        InlineKeyboardButton(
            text=t(lang, "post_done") + f" ({len(selected)})",
            callback_data="p:ls:done",
        ),
        InlineKeyboardButton(text=t(lang, "post_cancel"), callback_data="p:cancel"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _kb_duration(lang: str) -> InlineKeyboardMarkup:
    return _kb_simple_choices([
        ("p:dur:hours", t(lang, "post_duration_hours")),
        ("p:dur:day", t(lang, "post_duration_day")),
        ("p:dur:few_days", t(lang, "post_duration_few_days")),
        ("p:dur:week_plus", t(lang, "post_duration_week_plus")),
        ("p:dur:longterm", t(lang, "post_duration_longterm")),
    ], lang)


def _kb_urgency(lang: str) -> InlineKeyboardMarkup:
    return _kb_simple_choices([
        ("p:u:urgent", t(lang, "post_urgency_urgent")),
        ("p:u:this_week", t(lang, "post_urgency_this_week")),
        ("p:u:this_month", t(lang, "post_urgency_this_month")),
        ("p:u:flexible", t(lang, "post_urgency_flexible")),
    ], lang)


def _kb_budget(lang: str) -> InlineKeyboardMarkup:
    return _kb_simple_choices([
        ("p:b:under_500", t(lang, "post_budget_under_500")),
        ("p:b:500_2k", t(lang, "post_budget_500_2k")),
        ("p:b:2k_10k", t(lang, "post_budget_2k_10k")),
        ("p:b:over_10k", t(lang, "post_budget_over_10k")),
        ("p:b:discuss", t(lang, "post_budget_discuss")),
    ], lang, show_skip=True)


def _kb_photos(lang: str, n: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if n > 0:
        rows.append([
            InlineKeyboardButton(
                text=t(lang, "post_photos_done").format(n=n),
                callback_data="p:ph:done",
            ),
            InlineKeyboardButton(
                text=t(lang, "post_photos_undo"),
                callback_data="p:ph:undo",
            ),
        ])
        rows.append([
            InlineKeyboardButton(text=t(lang, "post_skip"),
                                 callback_data="p:ph:skip"),
            InlineKeyboardButton(text=t(lang, "post_cancel"),
                                 callback_data="p:cancel"),
        ])
    else:
        rows.append([
            InlineKeyboardButton(
                text=t(lang, "post_photos_done").format(n=n),
                callback_data="p:ph:done",
            ),
            InlineKeyboardButton(text=t(lang, "post_skip"),
                                 callback_data="p:ph:skip"),
            InlineKeyboardButton(text=t(lang, "post_cancel"),
                                 callback_data="p:cancel"),
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _kb_contact_choice(lang: str) -> InlineKeyboardMarkup:
    return _kb_simple_choices([
        ("p:c:keep", t(lang, "post_contact_keep")),
        ("p:c:other", t(lang, "post_contact_other")),
    ], lang)


def _kb_preview(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "post_send"), callback_data="p:submit"),
        InlineKeyboardButton(text=t(lang, "post_cancel"), callback_data="p:cancel"),
    ]])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _default_contact_label(user) -> str:
    if user.contact_phone:
        return f"📱 {user.contact_phone}"
    if user.contact_whatsapp:
        return f"💬 WhatsApp {user.contact_whatsapp}"
    if user.contact_email:
        return f"✉️ {user.contact_email}"
    return "Telegram DM"


async def _send_locations_step(message: Message, state: FSMContext, lang: str) -> None:
    data = await state.get_data()
    selected = set(data.get("location_ids", []))
    custom_loc = data.get("location_freetext")
    async with get_session() as session:
        loc_tags = await list_tags_by_category(session, "location")
    text = t(
        lang, "post_ask_locations",
        limit=listings_svc.MAX_LOCATIONS, selected=len(selected),
    )
    if custom_loc:
        text += f"\n\n📍 Свой адрес: <b>{custom_loc}</b>"
    kb = _kb_tag_grid(
        loc_tags, lang, selected=selected,
        show_done=True, show_custom=True, cb_prefix="p:l",
    )
    await state.set_state(PostStates.locations)
    await message.answer(text, reply_markup=kb)


async def _send_skills_step(message: Message, state: FSMContext, lang: str) -> None:
    data = await state.get_data()
    selected = set(data.get("skill_ids", []))
    async with get_session() as session:
        skill_tags = await list_tags_by_category(session, "skill")
    text = t(
        lang, "post_ask_skills",
        limit=listings_svc.MAX_SKILL_TAGS, selected=len(selected),
    )
    kb = _kb_tag_grid(
        skill_tags, lang, selected=selected,
        show_done=True, show_custom=True, cb_prefix="p:s",
    )
    await state.set_state(PostStates.skills)
    await message.answer(text, reply_markup=kb)


async def _go_after_skills(message: Message, state: FSMContext, lang: str) -> None:
    data = await state.get_data()
    # Customer — пропускает num_people/helper_kind/language/duration → сразу к описанию
    if data.get("post_role") == "customer":
        await _go_to_description(message, state, lang)
    elif data.get("kind") == "offer":
        await state.set_state(PostStates.num_people)
        await message.answer(t(lang, "post_ask_num_people"),
                             reply_markup=_kb_num_people(lang))
    else:
        await state.set_state(PostStates.engagement)
        await message.answer(t(lang, "post_ask_engagement"),
                             reply_markup=_kb_engagement(lang))


async def _go_to_language(message: Message, state: FSMContext, lang: str) -> None:
    data = await state.get_data()
    if data.get("kind") == "offer":
        await state.set_state(PostStates.language)
        await message.answer(t(lang, "post_ask_language_offer"),
                             reply_markup=_kb_language_offer(lang))
    else:
        await state.update_data(seek_languages=set())
        await state.set_state(PostStates.language)
        await message.answer(
            t(lang, "post_ask_language_seek"),
            reply_markup=_kb_language_seek(lang, set()),
        )


async def _go_to_duration(message: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(PostStates.duration)
    await message.answer(t(lang, "post_ask_duration"),
                         reply_markup=_kb_duration(lang))


async def _go_to_urgency(message: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(PostStates.urgency)
    await message.answer(t(lang, "post_ask_urgency"),
                         reply_markup=_kb_urgency(lang))


async def _go_to_budget_or_description(
    message: Message, state: FSMContext, lang: str
) -> None:
    """Бюджет — только для offer. Для seek сразу к описанию."""
    data = await state.get_data()
    if data.get("kind") == "offer":
        await state.set_state(PostStates.budget)
        await message.answer(t(lang, "post_ask_budget"),
                             reply_markup=_kb_budget(lang))
    else:
        await _go_to_description(message, state, lang)


async def _go_to_description(
    message: Message, state: FSMContext, lang: str
) -> None:
    await state.set_state(PostStates.description)
    await message.answer(t(lang, "post_ask_description"))


async def _go_to_photos(message: Message, state: FSMContext, lang: str) -> None:
    await state.update_data(photo_ids=[])
    await state.set_state(PostStates.photos)
    await message.answer(
        t(lang, "post_ask_photos", limit=listings_svc.MAX_PHOTOS),
        reply_markup=_kb_photos(lang, 0),
    )


async def _go_to_contact(
    target_message: Message, state: FSMContext, lang: str, *, tg_id: int
) -> None:
    """Перейти к шагу выбора контакта.

    tg_id передаётся явно, потому что target_message.from_user может быть
    ботом (когда вызвано из callback_query).
    """
    async with get_session() as session:
        u = await users.get_user(session, tg_id)
    if u is None:
        await state.clear()
        return
    contact_label = _default_contact_label(u)
    await state.set_state(PostStates.contact)
    await target_message.answer(
        t(lang, "post_ask_contact", contact=contact_label),
        reply_markup=_kb_contact_choice(lang),
    )


async def _go_to_preview(
    target_message: Message, state: FSMContext, lang: str, *, tg_id: int
) -> None:
    """Показать preview. tg_id явно — см. комментарий выше."""
    log.info("_go_to_preview ENTER tg_id=%s", tg_id)
    try:
        data = await state.get_data()
        log.info("_go_to_preview state=%s", {k: v for k, v in data.items() if k != "photo_ids"})
        async with get_session() as session:
            u = await users.get_user(session, tg_id)
            if u is None:
                log.warning("_go_to_preview: user not found tg_id=%s", tg_id)
                await state.clear()
                await target_message.answer(
                    "⚠️ Не нашёл твой профиль. Запусти /start и попробуй снова."
                )
                return
            # Подгружаем теги для preview-рендера
            from sqlalchemy import select
            ids = (list(data.get("location_ids", []))
                   + list(data.get("skill_ids", [])))
            if ids:
                rs = await session.execute(select(Tag).where(Tag.id.in_(ids)))
                loaded_tags = list(rs.scalars().all())
            else:
                loaded_tags = []
            # Эксплицитно «вытащим» поля юзера, пока сессия открыта,
            # чтобы DetachedInstanceError не возник при render-е.
            user_snapshot = {
                "id": u.id,
                "display_name": u.display_name,
                "full_name": u.full_name,
                "username": u.username,
                "contact_phone": u.contact_phone,
                "contact_whatsapp": u.contact_whatsapp,
                "contact_email": u.contact_email,
            }
        log.info("_go_to_preview tags_loaded=%d", len(loaded_tags))
        text_body = await _render_preview_safe(
            data, user_snapshot, loaded_tags, lang
        )
        await state.set_state(PostStates.preview)
        await target_message.answer(
            t(lang, "post_preview_title") + "\n\n" + text_body,
            reply_markup=_kb_preview(lang),
        )
        log.info("_go_to_preview OK tg_id=%s", tg_id)
    except Exception as e:
        log.exception("_go_to_preview FAILED tg_id=%s: %s", tg_id, e)
        try:
            await target_message.answer(
                "⚠️ Что-то пошло не так при подготовке предпросмотра. "
                "Попробуй /post снова. Логи у админа."
            )
        except Exception:
            pass
        await state.clear()


def _default_contact_from_snapshot(snap: dict) -> str:
    if snap.get("contact_phone"):
        return f"📱 {snap['contact_phone']}"
    if snap.get("contact_whatsapp"):
        return f"💬 WhatsApp {snap['contact_whatsapp']}"
    if snap.get("contact_email"):
        return f"✉️ {snap['contact_email']}"
    return "Telegram DM"


async def _render_preview_safe(
    data: dict, user_snapshot: dict, tags: list[Tag], lang: str
) -> str:
    """Превью без зависимости от ORM-объекта (чтобы не было DetachedInstanceError).

    user_snapshot — словарь полей User, собранный пока сессия была открыта.
    """
    locs = [tg for tg in tags if tg.category == "location"
            and tg.id in data.get("location_ids", [])]
    skills = [tg for tg in tags if tg.category != "location"
              and tg.id in data.get("skill_ids", [])]
    loc_parts = [tg.label_ru if lang == "ru" else tg.label_en for tg in locs]
    custom_loc = data.get("location_freetext")
    if custom_loc:
        loc_parts.append(html.escape(custom_loc))
    loc_str = ", ".join(loc_parts) or "—"
    skill_str = ", ".join(
        tg.label_ru if lang == "ru" else tg.label_en for tg in skills
    ) or "—"

    kind = data.get("kind")
    parts = [
        f"<b>{listings_svc.label(listings_svc.KIND_LABELS, lang, kind)}</b>",
        "",
        f"📍 Район: <b>{loc_str}</b>",
        f"🏷 Виды работ: <b>{skill_str}</b>",
    ]
    if kind == "offer":
        n = data.get("num_people")
        if n:
            parts.append(
                "👥 Нужно человек: "
                f"<b>{listings_svc.NUM_PEOPLE_LABELS.get(n, n)}</b>"
            )
        hk = data.get("helper_kind")
        if hk:
            parts.append(
                "👷 Кто нужен: "
                f"<b>{listings_svc.label(listings_svc.HELPER_LABELS, lang, hk)}</b>"
            )
        lr = data.get("language_req")
        if lr:
            parts.append(
                "🗣 Язык общения: "
                f"<b>{listings_svc.label(listings_svc.LANGUAGE_OFFER_LABELS, lang, lr)}</b>"
            )
        b = data.get("budget")
        if b:
            parts.append(
                "💵 Бюджет: "
                f"<b>{listings_svc.label(listings_svc.BUDGET_LABELS, lang, b)}</b>"
            )
    else:
        ek = data.get("engagement_kind")
        if ek:
            parts.append(
                "📋 Занятость: "
                f"<b>{listings_svc.label(listings_svc.ENGAGEMENT_LABELS, lang, ek)}</b>"
            )
        lr = data.get("language_req")
        if lr:
            parts.append(
                "🗣 Языки: "
                f"<b>{listings_svc.label(listings_svc.LANGUAGE_SEEK_LABELS, lang, lr)}</b>"
            )

    if data.get("duration"):
        parts.append(
            "⏱ Длительность: "
            f"<b>{listings_svc.label(listings_svc.DURATION_LABELS, lang, data.get('duration'))}</b>"
        )
    if data.get("urgency"):
        parts.append(
            "⚡ Срочность: "
            f"<b>{listings_svc.label(listings_svc.URGENCY_LABELS, lang, data.get('urgency'))}</b>"
        )
    parts.append("")
    parts.append(html.escape(data.get("description") or "—"))

    contact_raw = (
        data.get("contact_override")
        or _default_contact_from_snapshot(user_snapshot)
    )
    parts.append("")
    parts.append(f"📞 Контакт: {html.escape(contact_raw)}")

    photos = data.get("photo_ids", [])
    if photos:
        parts.append(f"\n📷 Фото: {len(photos)}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# /post — старт
# ---------------------------------------------------------------------------


def _can_post(role: str | None) -> bool:
    """True если роль позволяет публиковать объявления."""
    return role in ("coworker", "customer", "handyman", "individual", "company")


@router.message(Command("my_posts"))
async def cmd_my_posts(message: Message) -> None:
    """Список своих объявлений с быстрым «Закрыть»."""
    if message.chat.type != "private" or message.from_user is None:
        return
    async with get_session() as session:
        me = await users.get_user(session, message.from_user.id)
        if me is None or not _can_post(me.role):
            lang = normalize_lang(me.language if me else None)
            await message.answer(t(lang, "post_only_coworkers"))
            return
        lang = normalize_lang(me.language)
        from sqlalchemy import select
        from bot.db.models import Listing
        rs = await session.execute(
            select(Listing)
            .where(Listing.user_id == me.id)
            .order_by(Listing.created_at.desc())
            .limit(20)
        )
        listings = list(rs.scalars().all())

    if not listings:
        await message.answer(t(lang, "my_posts_empty"))
        return

    blocks: list[str] = [t(lang, "my_posts_header")]
    rows: list[list[InlineKeyboardButton]] = []
    for lst in listings:
        date = lst.created_at.strftime("%Y-%m-%d") if lst.created_at else "—"
        kind_emoji = "💼" if lst.kind == "offer" else "🔎"
        status_label = t(lang, f"my_posts_status_{lst.status}")
        snippet = (lst.text or "")[:80]
        if len(lst.text or "") > 80:
            snippet += "…"
        blocks.append(
            f"{kind_emoji} <b>#LST-{lst.id}</b> · {date} · {status_label}\n"
            f"{snippet}"
        )
        # Кнопка «Закрыть» только для активных и pending
        if lst.status in ("pending", "approved", "expired"):
            rows.append([InlineKeyboardButton(
                text=t(lang, "my_posts_btn_close", id=lst.id),
                callback_data=f"mp:close:{lst.id}",  # reuse существующего хендлера
            )])

    await message.answer(
        "\n\n".join(blocks),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows) if rows else None,
        disable_web_page_preview=True,
    )


@router.message(Command("post"))
async def cmd_post(message: Message, state: FSMContext) -> None:
    if message.chat.type != "private" or message.from_user is None:
        return
    async with get_session() as session:
        u = await users.get_user(session, message.from_user.id)
    if u is None or not _can_post(u.role):
        lang = normalize_lang(u.language if u else None)
        await message.answer(t(lang, "post_only_coworkers"))
        return
    lang = normalize_lang(u.language)
    # Soft-лимит — пока только warning, не блокируем
    async with get_session() as session:
        recent = await listings_svc.count_recent_listings(session, u.id)
    log.info("/post by tg_id=%s role=%s recent_30d=%s",
             message.from_user.id, u.role, recent)

    await state.clear()
    await state.update_data(lang=lang)

    # Customer — упрощённый flow: kind/num_people/helper/language/duration пропускаем
    if u.role == "customer":
        await state.update_data(
            post_role="customer",
            kind="offer",
            num_people=1,
            location_ids=[],
            skill_ids=[],
        )
        await _send_locations_step(message, state, lang)
    else:
        await state.set_state(PostStates.kind)
        await message.answer(t(lang, "post_kind_choose"), reply_markup=_kb_kind(lang))


# ---------------------------------------------------------------------------
# Cancel — глобальный для всех состояний /post
# ---------------------------------------------------------------------------


@router.callback_query(F.data == "p:cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.clear()
    if callback.message:
        try:
            await callback.message.edit_text(t(lang, "post_canceled"))
        except Exception:
            pass
    await callback.answer()


# ---------------------------------------------------------------------------
# Шаг 1: kind
# ---------------------------------------------------------------------------


@router.callback_query(PostStates.kind, F.data.startswith("p:k:"))
async def cb_kind(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None:
        return
    kind = callback.data.split(":")[2]
    if kind not in ("offer", "seek"):
        await callback.answer()
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.update_data(kind=kind, location_ids=[], skill_ids=[])
    if callback.message:
        try:
            await callback.message.edit_reply_markup()
        except Exception:
            pass
        await _send_locations_step(callback.message, state, lang)
    await callback.answer()


# ---------------------------------------------------------------------------
# Шаг 2: locations (multi-select)
# ---------------------------------------------------------------------------


@router.callback_query(PostStates.locations, F.data.startswith("p:l:"))
async def cb_locations(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None:
        return
    payload = callback.data.split(":", 2)[2]
    data = await state.get_data()
    lang = data.get("lang", "ru")
    selected: list[int] = list(data.get("location_ids", []))
    custom_loc = data.get("location_freetext")

    if payload == "done":
        if not selected and not custom_loc:
            await callback.answer(t(lang, "post_need_locations"), show_alert=True)
            return
        if callback.message:
            try:
                await callback.message.edit_reply_markup()
            except Exception:
                pass
            await _send_skills_step(callback.message, state, lang)
        await callback.answer()
        return

    if payload == "custom":
        await state.set_state(PostStates.location_custom_input)
        if callback.message:
            await callback.message.answer(t(lang, "post_ask_custom_location"))
        await callback.answer()
        return

    try:
        tag_id = int(payload)
    except ValueError:
        await callback.answer()
        return

    s = set(selected)
    if tag_id in s:
        s.remove(tag_id)
    else:
        if len(s) >= listings_svc.MAX_LOCATIONS:
            await callback.answer(
                t(lang, "post_need_locations"), show_alert=False,
            )
            return
        s.add(tag_id)
    await state.update_data(location_ids=list(s))

    # Перерисовать клавиатуру
    async with get_session() as session:
        loc_tags = await list_tags_by_category(session, "location")
    new_text = t(
        lang, "post_ask_locations",
        limit=listings_svc.MAX_LOCATIONS, selected=len(s),
    )
    if custom_loc:
        new_text += f"\n\n📍 Свой адрес: <b>{custom_loc}</b>"
    if callback.message:
        try:
            await callback.message.edit_text(
                new_text,
                reply_markup=_kb_tag_grid(loc_tags, lang, selected=s,
                                           show_done=True, show_custom=True,
                                           cb_prefix="p:l"),
            )
        except Exception:
            pass
    await callback.answer()


@router.message(PostStates.location_custom_input)
async def step_location_custom(message: Message, state: FSMContext) -> None:
    if not message.text:
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    custom = message.text.strip()[:256]
    if not custom:
        return
    await state.update_data(location_freetext=custom)
    await _send_locations_step(message, state, lang)


# ---------------------------------------------------------------------------
# Шаг 3: skills (multi-select)
# ---------------------------------------------------------------------------


@router.callback_query(PostStates.skills, F.data.startswith("p:s:"))
async def cb_skills(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None or callback.from_user is None:
        return
    payload = callback.data.split(":", 2)[2]
    data = await state.get_data()
    lang = data.get("lang", "ru")
    selected = list(data.get("skill_ids", []))

    if payload == "done":
        if not selected:
            await callback.answer(t(lang, "post_need_skills"), show_alert=True)
            return
        if callback.message:
            try:
                await callback.message.edit_reply_markup()
            except Exception:
                pass
            await _go_after_skills(callback.message, state, lang)
        await callback.answer()
        return

    if payload == "custom":
        # Свой вариант — спрашиваем ввод
        from bot.services import tags as tags_svc
        async with get_session() as session:
            u = await users.get_user(session, callback.from_user.id)
            used = (
                await tags_svc.count_custom_tags_by_user(session, u.id)
                if u else 0
            )
        if used >= tags_svc.CUSTOM_TAG_LIMIT_PER_USER:
            await callback.answer(
                t(lang, "register_custom_tag_limit",
                  limit=tags_svc.CUSTOM_TAG_LIMIT_PER_USER),
                show_alert=True,
            )
            return
        await state.set_state(PostStates.skill_custom_input)
        if callback.message:
            await callback.message.answer(t(lang, "register_ask_custom_tag"))
        await callback.answer()
        return

    try:
        tag_id = int(payload)
    except ValueError:
        await callback.answer()
        return

    s = set(selected)
    if tag_id in s:
        s.remove(tag_id)
    else:
        if len(s) >= listings_svc.MAX_SKILL_TAGS:
            await callback.answer()
            return
        s.add(tag_id)
    await state.update_data(skill_ids=list(s))

    async with get_session() as session:
        skill_tags = await list_tags_by_category(session, "skill")
    if callback.message:
        try:
            await callback.message.edit_text(
                t(lang, "post_ask_skills",
                  limit=listings_svc.MAX_SKILL_TAGS, selected=len(s)),
                reply_markup=_kb_tag_grid(skill_tags, lang, selected=s,
                                           show_done=True, show_custom=True,
                                           cb_prefix="p:s"),
            )
        except Exception:
            pass
    await callback.answer()


@router.message(PostStates.skill_custom_input)
async def step_skill_custom(message: Message, state: FSMContext) -> None:
    if not message.text or message.from_user is None:
        return
    from bot.services import tags as tags_svc
    data = await state.get_data()
    lang = data.get("lang", "ru")
    label = tags_svc.normalize_custom_tag(message.text)
    if label is None:
        await message.answer(t(lang, "register_custom_tag_invalid"))
        return
    async with get_session() as session:
        u = await users.get_user(session, message.from_user.id)
        if u is None:
            await state.clear()
            return
        tag = await tags_svc.create_custom_tag(
            session, raw_label=label, category="skill",
            created_by_user_id=u.id,
        )
    if tag is None:
        await message.answer(
            t(lang, "register_custom_tag_limit",
              limit=tags_svc.CUSTOM_TAG_LIMIT_PER_USER)
        )
        await _send_skills_step(message, state, lang)
        return
    selected = list(data.get("skill_ids", []))
    if tag.id not in selected and len(selected) < listings_svc.MAX_SKILL_TAGS:
        selected.append(tag.id)
    await state.update_data(skill_ids=selected)
    await _send_skills_step(message, state, lang)


# ---------------------------------------------------------------------------
# Шаг 4a: num_people (offer)
# ---------------------------------------------------------------------------


@router.callback_query(PostStates.num_people, F.data.startswith("p:n:"))
async def cb_num_people(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None:
        return
    n = int(callback.data.split(":")[2])
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.update_data(num_people=n)
    await state.set_state(PostStates.helper_kind)
    if callback.message:
        await callback.message.edit_text(
            t(lang, "post_ask_helper_kind"), reply_markup=_kb_helper(lang)
        )
    await callback.answer()


# ---------------------------------------------------------------------------
# Шаг 4b: engagement (seek)
# ---------------------------------------------------------------------------


@router.callback_query(PostStates.engagement, F.data.startswith("p:e:"))
async def cb_engagement(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None:
        return
    e = callback.data.split(":")[2]
    if e not in ("one_time", "part_time"):
        await callback.answer()
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.update_data(engagement_kind=e)
    if callback.message:
        try:
            await callback.message.edit_reply_markup()
        except Exception:
            pass
        await _go_to_language(callback.message, state, lang)
    await callback.answer()


# ---------------------------------------------------------------------------
# Шаг 5: helper_kind (offer)
# ---------------------------------------------------------------------------


@router.callback_query(PostStates.helper_kind, F.data.startswith("p:hk:"))
async def cb_helper(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None:
        return
    hk = callback.data.split(":")[2]
    if hk not in ("pro", "helper", "any"):
        await callback.answer()
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.update_data(helper_kind=hk)
    if callback.message:
        try:
            await callback.message.edit_reply_markup()
        except Exception:
            pass
        await _go_to_language(callback.message, state, lang)
    await callback.answer()


# ---------------------------------------------------------------------------
# Шаг 6: language
# ---------------------------------------------------------------------------


@router.callback_query(PostStates.language, F.data.startswith("p:lo:"))
async def cb_language_offer(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None:
        return
    code = callback.data.split(":")[2]
    if code not in ("none", "ru", "en"):
        await callback.answer()
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.update_data(language_req=code)
    if callback.message:
        try:
            await callback.message.edit_reply_markup()
        except Exception:
            pass
        await _go_to_duration(callback.message, state, lang)
    await callback.answer()


@router.callback_query(PostStates.language, F.data.startswith("p:ls:"))
async def cb_language_seek(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None:
        return
    payload = callback.data.split(":")[2]
    data = await state.get_data()
    lang = data.get("lang", "ru")
    selected: set[str] = set(data.get("seek_languages", []))

    if payload == "done":
        if not selected:
            await callback.answer(t(lang, "post_need_languages"), show_alert=True)
            return
        # Кодируем: ru / en / ru_en
        if "ru" in selected and "en" in selected:
            code = "ru_en"
        elif "ru" in selected:
            code = "ru"
        else:
            code = "en"
        await state.update_data(language_req=code)
        if callback.message:
            try:
                await callback.message.edit_reply_markup()
            except Exception:
                pass
            await _go_to_duration(callback.message, state, lang)
        await callback.answer()
        return

    if payload not in ("ru", "en"):
        await callback.answer()
        return

    if payload in selected:
        selected.remove(payload)
    else:
        selected.add(payload)
    await state.update_data(seek_languages=list(selected))
    if callback.message:
        try:
            await callback.message.edit_reply_markup(
                reply_markup=_kb_language_seek(lang, selected)
            )
        except Exception:
            pass
    await callback.answer()


# ---------------------------------------------------------------------------
# Шаг 7: duration
# ---------------------------------------------------------------------------


@router.callback_query(PostStates.duration, F.data.startswith("p:dur:"))
async def cb_duration(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None:
        return
    code = callback.data.split(":")[2]
    valid = {"hours", "day", "few_days", "week_plus", "longterm"}
    if code not in valid:
        await callback.answer()
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.update_data(duration=code)
    if callback.message:
        try:
            await callback.message.edit_reply_markup()
        except Exception:
            pass
        await _go_to_urgency(callback.message, state, lang)
    await callback.answer()


# ---------------------------------------------------------------------------
# Шаг 8: urgency
# ---------------------------------------------------------------------------


@router.callback_query(PostStates.urgency, F.data.startswith("p:u:"))
async def cb_urgency(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None:
        return
    code = callback.data.split(":")[2]
    valid = {"urgent", "this_week", "this_month", "flexible"}
    if code not in valid:
        await callback.answer()
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.update_data(urgency=code)
    if callback.message:
        try:
            await callback.message.edit_reply_markup()
        except Exception:
            pass
        # Customer: urgency → budget (optional) → photos
        # Coworker: urgency → budget (optional) → description
        if data.get("post_role") == "customer":
            await state.set_state(PostStates.budget)
            await callback.message.answer(t(lang, "post_ask_budget"),
                                          reply_markup=_kb_budget(lang))
        else:
            await _go_to_budget_or_description(callback.message, state, lang)
    await callback.answer()


# ---------------------------------------------------------------------------
# Шаг 9: budget (offer only, опц.)
# ---------------------------------------------------------------------------


@router.callback_query(PostStates.budget, F.data.startswith("p:b:"))
async def cb_budget(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None:
        return
    code = callback.data.split(":")[2]
    valid = {"under_500", "500_2k", "2k_10k", "over_10k", "discuss"}
    if code not in valid:
        await callback.answer()
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.update_data(budget=code)
    if callback.message:
        try:
            await callback.message.edit_reply_markup()
        except Exception:
            pass
        # Customer: budget → photos; Coworker: budget → description
        if data.get("post_role") == "customer":
            await _go_to_photos(callback.message, state, lang)
        else:
            await _go_to_description(callback.message, state, lang)
    await callback.answer()


@router.callback_query(PostStates.budget, F.data == "p:skip")
async def cb_budget_skip(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.update_data(budget=None)
    if callback.message:
        try:
            await callback.message.edit_reply_markup()
        except Exception:
            pass
        # Customer: budget → photos; Coworker: budget → description
        if data.get("post_role") == "customer":
            await _go_to_photos(callback.message, state, lang)
        else:
            await _go_to_description(callback.message, state, lang)
    await callback.answer()


# ---------------------------------------------------------------------------
# Шаг 10: description
# ---------------------------------------------------------------------------


@router.message(PostStates.description)
async def step_description(message: Message, state: FSMContext) -> None:
    if not message.text:
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    desc = message.text.strip()
    if len(desc) > listings_svc.MAX_DESCRIPTION_LEN:
        await message.answer(
            t(lang, "post_too_long",
              n=len(desc), max=listings_svc.MAX_DESCRIPTION_LEN)
        )
        return
    await state.update_data(description=desc)
    # Customer: description → urgency → budget → photos
    # Coworker: description → photos (urgency/budget уже позади)
    if data.get("post_role") == "customer":
        await _go_to_urgency(message, state, lang)
    else:
        await _go_to_photos(message, state, lang)


# ---------------------------------------------------------------------------
# Шаг 11: photos (опц.)
# ---------------------------------------------------------------------------


@router.message(PostStates.photos, F.photo)
async def step_photo(message: Message, state: FSMContext) -> None:
    if not message.photo:
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    photo_ids = list(data.get("photo_ids", []))
    if len(photo_ids) >= listings_svc.MAX_PHOTOS:
        await message.answer(
            t(lang, "post_photo_limit", limit=listings_svc.MAX_PHOTOS)
        )
        return
    # Берём наибольший вариант (последний в списке photo)
    photo_ids.append(message.photo[-1].file_id)
    await state.update_data(photo_ids=photo_ids)
    n = len(photo_ids)
    await message.answer(
        t(lang, "post_photo_added", n=n, limit=listings_svc.MAX_PHOTOS),
        reply_markup=_kb_photos(lang, n),
    )


@router.callback_query(PostStates.photos, F.data == "p:ph:undo")
async def cb_photos_undo(callback: CallbackQuery, state: FSMContext) -> None:
    """Удалить последнее загруженное фото из черновика."""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    photo_ids = list(data.get("photo_ids", []))
    if not photo_ids:
        await callback.answer()
        return
    photo_ids.pop()
    await state.update_data(photo_ids=photo_ids)
    n = len(photo_ids)
    if callback.message:
        try:
            await callback.message.answer(
                t(lang, "post_photo_removed",
                  n=n, limit=listings_svc.MAX_PHOTOS),
                reply_markup=_kb_photos(lang, n),
            )
        except Exception:
            pass
    await callback.answer(
        t(lang, "post_photo_removed", n=n, limit=listings_svc.MAX_PHOTOS),
        show_alert=False,
    )


@router.callback_query(PostStates.photos, F.data == "p:ph:done")
async def cb_photos_done(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user is None:
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    if callback.message:
        try:
            await callback.message.edit_reply_markup()
        except Exception:
            pass
        await _go_to_contact(
            callback.message, state, lang, tg_id=callback.from_user.id
        )
    await callback.answer()


@router.callback_query(PostStates.photos, F.data == "p:ph:skip")
async def cb_photos_skip(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user is None:
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.update_data(photo_ids=[])
    if callback.message:
        try:
            await callback.message.edit_reply_markup()
        except Exception:
            pass
        await _go_to_contact(
            callback.message, state, lang, tg_id=callback.from_user.id
        )
    await callback.answer()


# ---------------------------------------------------------------------------
# Шаг 12: contact
# ---------------------------------------------------------------------------


@router.callback_query(PostStates.contact, F.data == "p:c:keep")
async def cb_contact_keep(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user is None:
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.update_data(contact_override=None)
    if callback.message:
        try:
            await callback.message.edit_reply_markup()
        except Exception:
            pass
        await _go_to_preview(
            callback.message, state, lang, tg_id=callback.from_user.id
        )
    await callback.answer()


@router.callback_query(PostStates.contact, F.data == "p:c:other")
async def cb_contact_other(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.set_state(PostStates.contact_other)
    if callback.message:
        await callback.message.answer(t(lang, "post_ask_contact_other"))
    await callback.answer()


@router.message(PostStates.contact_other)
async def step_contact_other(message: Message, state: FSMContext) -> None:
    if not message.text or message.from_user is None:
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    contact = message.text.strip()[:254]
    await state.update_data(contact_override=contact)
    await _go_to_preview(message, state, lang, tg_id=message.from_user.id)


# ---------------------------------------------------------------------------
# Шаг 13: preview & submit
# ---------------------------------------------------------------------------


@router.callback_query(PostStates.preview, F.data == "p:submit")
async def cb_submit(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user is None:
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    async with get_session() as session:
        u = await users.get_user(session, callback.from_user.id)
        if u is None:
            await state.clear()
            await callback.answer()
            return
        listing = await listings_svc.create_listing(
            session,
            user_id=u.id,
            kind=data.get("kind", "offer"),
            text=data.get("description", ""),
            location_tag_ids=data.get("location_ids", []),
            skill_tag_ids=data.get("skill_ids", []),
            num_people=data.get("num_people"),
            engagement_kind=data.get("engagement_kind"),
            helper_kind=data.get("helper_kind"),
            language_req=data.get("language_req"),
            duration=data.get("duration"),
            urgency=data.get("urgency"),
            budget=data.get("budget"),
            contact_override=data.get("contact_override"),
            location_freetext=data.get("location_freetext"),
            photo_file_ids=data.get("photo_ids", []),
        )
    await state.clear()
    log.info(
        "Listing created: id=%s kind=%s by tg_id=%s",
        listing.id, listing.kind, callback.from_user.id,
    )
    if callback.message:
        try:
            await callback.message.edit_text(t(lang, "post_sent"))
        except Exception:
            await callback.message.answer(t(lang, "post_sent"))
    await callback.answer()

    # Уведомляем модераторов в DM. Делаем это после ответа автору,
    # чтобы UI не подвисал на ошибке отправки.
    if callback.bot:
        try:
            from bot.handlers.post_moderation import (
                notify_moderators_for_listing,
            )
            await notify_moderators_for_listing(callback.bot, listing.id)
        except Exception as e:
            log.exception(
                "notify_moderators_for_listing failed for id=%s: %s",
                listing.id, e,
            )
