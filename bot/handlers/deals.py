"""/my_deals — список сделок юзера + flow закрытия и отзыва.

Архитектура:
- Deal создаётся в post_moderation.cb_hire когда автор кликает «Нанял этого».
- Оба участника видят сделку в /my_deals.
- Кнопки на сделке зависят от статуса и наличия отзыва:
  • status=open  → «✅ Закрыть и оценить» (закрывает + сразу feedback FSM)
  • status=closed без своего отзыва → «📝 Оставить отзыв»
  • status=closed со своим отзывом → текст «✓ Отзыв оставлен»
- При закрытии сделки одной стороной — DM второй с приглашением оставить отзыв.
- Feedback + FeedbackTag сохраняются → /profile cloud начинает наполняться.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

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
from sqlalchemy import select, or_

from bot.db.database import get_session
from bot.db.models import Deal, Feedback, FeedbackTag, Tag, User
from bot.i18n import normalize_lang, t
from bot.services import users
from bot.services.tags import list_tags_by_category

log = logging.getLogger(__name__)
router = Router(name="deals")

MAX_COMMENT_LEN = 500
MAX_TAGS_PER_FEEDBACK = 8


class FeedbackStates(StatesGroup):
    rating = State()
    tags = State()
    comment = State()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _user_lang(tg_id: int | None) -> str:
    if tg_id is None:
        return normalize_lang(None)
    async with get_session() as session:
        u = await users.get_user(session, tg_id)
        return normalize_lang(u.language if u else None)


async def _has_my_feedback(
    session, deal_id: int, my_user_id: int,
) -> bool:
    rs = await session.execute(
        select(Feedback).where(
            Feedback.deal_id == deal_id,
            Feedback.from_user_id == my_user_id,
        )
    )
    return rs.scalar_one_or_none() is not None


def _partner_label(partner: User | None) -> str:
    if partner is None:
        return "—"
    if partner.username:
        return f"@{partner.username}"
    return partner.display_name or partner.full_name or f"id{partner.tg_id}"


# ---------------------------------------------------------------------------
# /my_deals
# ---------------------------------------------------------------------------


@router.message(Command("my_deals"))
async def cmd_my_deals(message: Message) -> None:
    if message.chat.type != "private" or message.from_user is None:
        return
    lang = await _user_lang(message.from_user.id)
    async with get_session() as session:
        me = await users.get_user(session, message.from_user.id)
        if me is None or me.role != "coworker":
            await message.answer(t(lang, "post_only_coworkers"))
            return
        # Все сделки где я customer ИЛИ contractor
        rs = await session.execute(
            select(Deal)
            .where(or_(Deal.customer_id == me.id, Deal.contractor_id == me.id))
            .order_by(Deal.started_at.desc())
            .limit(20)
        )
        deals = list(rs.scalars().all())
        if not deals:
            await message.answer(t(lang, "deals_list_empty"))
            return

        # Подгружаем партнёров и проверяем мои отзывы
        items: list[tuple[Deal, User | None, bool]] = []  # (deal, partner, my_review_exists)
        for d in deals:
            partner_id = d.contractor_id if d.customer_id == me.id else d.customer_id
            partner_rs = await session.execute(
                select(User).where(User.id == partner_id)
            )
            partner = partner_rs.scalar_one_or_none()
            my_review = await _has_my_feedback(session, d.id, me.id)
            items.append((d, partner, my_review))

    # Рендерим список
    blocks: list[str] = [t(lang, "deals_list_header")]
    rows: list[list[InlineKeyboardButton]] = []
    for d, partner, my_review in items:
        plabel = _partner_label(partner)
        date = d.started_at.strftime("%Y-%m-%d") if d.started_at else "—"
        if d.status == "open":
            blocks.append(t(lang, "deals_item_open",
                            id=d.id, partner=plabel, date=date))
            rows.append([InlineKeyboardButton(
                text=t(lang, "deal_btn_close_review", id=d.id),
                callback_data=f"dl:close:{d.id}",
            )])
        elif d.status == "closed":
            if my_review:
                blocks.append(t(lang, "deals_item_closed_my_review",
                                id=d.id, partner=plabel, date=date))
                # без кнопки
            else:
                blocks.append(t(lang, "deals_item_closed_no_review",
                                id=d.id, partner=plabel, date=date))
                rows.append([InlineKeyboardButton(
                    text=t(lang, "deal_btn_review", id=d.id),
                    callback_data=f"dl:review:{d.id}",
                )])

    await message.answer(
        "\n\n".join(blocks),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows) if rows else None,
    )


# ---------------------------------------------------------------------------
# Закрытие сделки + старт feedback FSM
# ---------------------------------------------------------------------------


def _kb_rating() -> InlineKeyboardMarkup:
    """Описательные кнопки по одной в ряд — без обрезки на мобильных."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐⭐⭐⭐⭐ Отлично", callback_data="dl:rate:5")],
        [InlineKeyboardButton(text="⭐⭐⭐⭐ Хорошо", callback_data="dl:rate:4")],
        [InlineKeyboardButton(text="⭐⭐⭐ Нормально", callback_data="dl:rate:3")],
        [InlineKeyboardButton(text="⭐⭐ Так себе", callback_data="dl:rate:2")],
        [InlineKeyboardButton(text="⭐ Плохо", callback_data="dl:rate:1")],
        [InlineKeyboardButton(text="✖ Отмена", callback_data="dl:cancel")],
    ])


def _kb_feedback_tags(
    fb_tags: list[Tag], lang: str, *, selected: set[int],
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    line: list[InlineKeyboardButton] = []
    for tag in fb_tags:
        label = tag.label_ru if lang == "ru" else tag.label_en
        prefix = "☑ " if tag.id in selected else ""
        line.append(InlineKeyboardButton(
            text=f"{prefix}{label}",
            callback_data=f"dl:tag:{tag.id}",
        ))
        if len(line) == 2:
            rows.append(line)
            line = []
    if line:
        rows.append(line)
    rows.append([
        InlineKeyboardButton(
            text=t(lang, "feedback_btn_done", n=len(selected)),
            callback_data="dl:tag:done",
        ),
        InlineKeyboardButton(
            text=t(lang, "feedback_btn_cancel"),
            callback_data="dl:cancel",
        ),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _kb_comment_skip(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=t(lang, "feedback_btn_skip"),
            callback_data="dl:comment_skip",
        ),
        InlineKeyboardButton(
            text=t(lang, "feedback_btn_cancel"),
            callback_data="dl:cancel",
        ),
    ]])


async def _start_feedback_fsm(
    target_message: Message, state: FSMContext, *,
    deal_id: int, partner_id: int, partner_label: str, lang: str,
    closed_by_me: bool,
) -> None:
    """Запустить FSM ⭐→теги→коммент. closed_by_me=True если только что
    закрыли сделку (нужно DM партнёру после submit)."""
    await state.clear()
    await state.update_data(
        lang=lang,
        fb_deal_id=deal_id,
        fb_partner_id=partner_id,
        fb_partner_label=partner_label,
        fb_tags=[],
        fb_closed_by_me=closed_by_me,
    )
    await state.set_state(FeedbackStates.rating)
    await target_message.answer(
        t(lang, "feedback_ask_rating", partner=partner_label),
        reply_markup=_kb_rating(),
    )


@router.callback_query(F.data.startswith("dl:close:"))
async def cb_close_deal(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user is None or callback.data is None:
        return
    try:
        deal_id = int(callback.data.split(":")[2])
    except (ValueError, IndexError):
        await callback.answer()
        return
    lang = await _user_lang(callback.from_user.id)

    async with get_session() as session:
        me = await users.get_user(session, callback.from_user.id)
        deal = await session.get(Deal, deal_id)
        if me is None or deal is None:
            await callback.answer()
            return
        # Проверяем что я участник
        if me.id not in (deal.customer_id, deal.contractor_id):
            await callback.answer("Это не твоя сделка.", show_alert=True)
            return
        if deal.status not in ("open", "closed"):
            await callback.answer(
                f"Сделка в статусе {deal.status}.", show_alert=True,
            )
            return
        partner_id = (
            deal.contractor_id if deal.customer_id == me.id
            else deal.customer_id
        )
        partner_rs = await session.execute(
            select(User).where(User.id == partner_id)
        )
        partner = partner_rs.scalar_one_or_none()
        partner_label = _partner_label(partner)

        # Закрываем если ещё open
        was_open = deal.status == "open"
        if was_open:
            deal.status = "closed"
            deal.closed_at = datetime.now(timezone.utc)
            await session.commit()

    if callback.message:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await _start_feedback_fsm(
            callback.message, state,
            deal_id=deal_id, partner_id=partner_id,
            partner_label=partner_label, lang=lang,
            closed_by_me=was_open,
        )
    await callback.answer()


@router.callback_query(F.data.startswith("dl:review:"))
async def cb_review_deal(callback: CallbackQuery, state: FSMContext) -> None:
    """Закрытая сделка — оставить отзыв (без изменения status)."""
    if callback.from_user is None or callback.data is None:
        return
    try:
        deal_id = int(callback.data.split(":")[2])
    except (ValueError, IndexError):
        await callback.answer()
        return
    lang = await _user_lang(callback.from_user.id)

    async with get_session() as session:
        me = await users.get_user(session, callback.from_user.id)
        deal = await session.get(Deal, deal_id)
        if me is None or deal is None:
            await callback.answer()
            return
        if me.id not in (deal.customer_id, deal.contractor_id):
            await callback.answer("Это не твоя сделка.", show_alert=True)
            return
        # Проверяем что отзыва ещё нет
        if await _has_my_feedback(session, deal_id, me.id):
            await callback.answer(
                t(lang, "feedback_already_left"), show_alert=True,
            )
            return
        partner_id = (
            deal.contractor_id if deal.customer_id == me.id
            else deal.customer_id
        )
        partner_rs = await session.execute(
            select(User).where(User.id == partner_id)
        )
        partner = partner_rs.scalar_one_or_none()
        partner_label = _partner_label(partner)

    if callback.message:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await _start_feedback_fsm(
            callback.message, state,
            deal_id=deal_id, partner_id=partner_id,
            partner_label=partner_label, lang=lang,
            closed_by_me=False,
        )
    await callback.answer()


# ---------------------------------------------------------------------------
# FSM: rating → tags → comment → save
# ---------------------------------------------------------------------------


@router.callback_query(FeedbackStates.rating, F.data.startswith("dl:rate:"))
async def cb_rate(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None:
        return
    try:
        rating = int(callback.data.split(":")[2])
    except (ValueError, IndexError):
        await callback.answer()
        return
    if rating not in range(1, 6):
        await callback.answer()
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.update_data(fb_rating=rating)

    # Грузим feedback-теги (positive + negative)
    async with get_session() as session:
        pos = await list_tags_by_category(session, "feedback_pos")
        neg = await list_tags_by_category(session, "feedback_neg")
    fb_tags = pos + neg
    await state.update_data(_fb_tag_ids=[tg.id for tg in fb_tags])

    await state.set_state(FeedbackStates.tags)
    if callback.message:
        try:
            await callback.message.edit_text(
                t(lang, "feedback_ask_tags"),
                reply_markup=_kb_feedback_tags(fb_tags, lang, selected=set()),
            )
        except Exception:
            pass
    await callback.answer()


@router.callback_query(FeedbackStates.tags, F.data.startswith("dl:tag:"))
async def cb_tag(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None:
        return
    payload = callback.data.split(":")[2]
    data = await state.get_data()
    lang = data.get("lang", "ru")
    selected: list[int] = list(data.get("fb_tags", []))

    if payload == "done":
        await state.set_state(FeedbackStates.comment)
        if callback.message:
            try:
                await callback.message.edit_text(
                    t(lang, "feedback_ask_comment"),
                    reply_markup=_kb_comment_skip(lang),
                )
            except Exception:
                pass
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
        if len(s) >= MAX_TAGS_PER_FEEDBACK:
            await callback.answer()
            return
        s.add(tag_id)
    await state.update_data(fb_tags=list(s))

    # Перерисовать клавиатуру
    async with get_session() as session:
        pos = await list_tags_by_category(session, "feedback_pos")
        neg = await list_tags_by_category(session, "feedback_neg")
    fb_tags = pos + neg
    if callback.message:
        try:
            await callback.message.edit_reply_markup(
                reply_markup=_kb_feedback_tags(fb_tags, lang, selected=s),
            )
        except Exception:
            pass
    await callback.answer()


@router.callback_query(FeedbackStates.comment, F.data == "dl:comment_skip")
async def cb_comment_skip(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user is None:
        return
    await _save_feedback(callback, state, comment=None)


@router.message(FeedbackStates.comment)
async def step_comment(message: Message, state: FSMContext) -> None:
    if not message.text or message.from_user is None:
        return
    text = message.text.strip()[:MAX_COMMENT_LEN]
    await _save_feedback(message, state, comment=text)


@router.callback_query(F.data == "dl:cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.clear()
    if callback.message:
        try:
            await callback.message.edit_text(t(lang, "feedback_canceled"))
        except Exception:
            pass
    await callback.answer()


async def _save_feedback(
    event: Message | CallbackQuery, state: FSMContext, *,
    comment: str | None,
) -> None:
    """Финальное сохранение Feedback + FeedbackTag + DM партнёру."""
    user_obj = (
        event.from_user if isinstance(event, (Message, CallbackQuery)) else None
    )
    if user_obj is None:
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    deal_id = data.get("fb_deal_id")
    partner_id = data.get("fb_partner_id")
    partner_label = data.get("fb_partner_label", "—")
    rating = data.get("fb_rating")
    fb_tags: list[int] = list(data.get("fb_tags", []))
    closed_by_me = bool(data.get("fb_closed_by_me", False))
    if not deal_id or not rating:
        await state.clear()
        return

    async with get_session() as session:
        me = await users.get_user(session, user_obj.id)
        if me is None:
            await state.clear()
            return
        # Защита от дубля (UNIQUE на (deal_id, from_user_id), но ловим и в коде)
        if await _has_my_feedback(session, deal_id, me.id):
            await state.clear()
            target = (
                event.message if isinstance(event, CallbackQuery) else event
            )
            if target:
                await target.answer(t(lang, "feedback_already_left"))
            return

        fb = Feedback(
            deal_id=deal_id,
            from_user_id=me.id,
            to_user_id=partner_id,
            rating=rating,
            comment=comment,
        )
        session.add(fb)
        await session.flush()
        for tid in fb_tags:
            session.add(FeedbackTag(feedback_id=fb.id, tag_id=tid))
        await session.commit()

        # Подгружаем партнёра для уведомления
        partner_rs = await session.execute(
            select(User).where(User.id == partner_id)
        )
        partner = partner_rs.scalar_one_or_none()
        my_label = (
            f"@{me.username}" if me.username
            else (me.display_name or me.full_name or f"id{me.tg_id}")
        )

    log.info(
        "Feedback: deal=%s from=%s to=%s rating=%s tags=%s",
        deal_id, me.id, partner_id, rating, len(fb_tags),
    )
    await state.clear()

    # Подтверждение и DM партнёру
    bot = (
        event.bot if isinstance(event, Message)
        else (event.bot if isinstance(event, CallbackQuery) else None)
    )
    target = event.message if isinstance(event, CallbackQuery) else event
    if target:
        await target.answer(t(lang, "feedback_thanks"))

    if closed_by_me and partner is not None and bot:
        try:
            partner_lang = normalize_lang(partner.language)
            await bot.send_message(
                chat_id=partner.tg_id,
                text=t(partner_lang, "feedback_partner_notified",
                       partner=my_label, id=deal_id),
            )
        except Exception as e:
            log.warning("Не удалось уведомить партнёра tg_id=%s: %s",
                        partner.tg_id, e)
