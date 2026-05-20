"""Модерация объявлений: DM админам → approve/reject → публикация в группу.

Архитектура:
- После Submit в /post вызывается notify_moderators_for_listing(bot, listing_id):
  всем ADMIN_IDS уходит DM с inline-кнопками Approve/Reject.
- Кнопки имеют callback_data "mp:apr:<id>" / "mp:rej:<id>".
- Кто из админов первым кликнет — тот и обрабатывает; остальным сообщения
  обновляются в "уже обработано".
- Approve: публикуем в group_chat_id (если задан) с inline-кнопкой
  "📩 Откликнуться" → Response в БД + DM автору.
- Reject: спрашиваем причину одним сообщением, сохраняем, DM автору.
"""
from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
)

from datetime import datetime, timezone

from bot.config import get_settings
from bot.db.database import get_session
from bot.db.models import Deal, Listing, ListingPhoto, Response, User
from bot.i18n import normalize_lang, t
from bot.services import listings as listings_svc
from bot.services import users

log = logging.getLogger(__name__)
router = Router(name="post_moderation")


# ---------------------------------------------------------------------------
# Состояния FSM (для модератора при reject — ввод причины)
# ---------------------------------------------------------------------------


class ModerationStates(StatesGroup):
    rejecting = State()  # ожидание текста причины


# ---------------------------------------------------------------------------
# Клавиатуры
# ---------------------------------------------------------------------------


def _kb_moderation(lang: str, listing_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=t(lang, "mod_btn_approve"),
            callback_data=f"mp:apr:{listing_id}",
        ),
        InlineKeyboardButton(
            text=t(lang, "mod_btn_reject"),
            callback_data=f"mp:rej:{listing_id}",
        ),
    ]])


def _kb_respond(listing_id: int, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=t(lang, "post_respond_btn"),
            callback_data=f"mp:resp:{listing_id}",
        ),
    ]])


# ---------------------------------------------------------------------------
# Helpers: карточка пользователя + кнопки контактов
# ---------------------------------------------------------------------------


async def _render_user_card(session, user: User, lang: str) -> str:
    """Рендер /check-style карточки. Reuse profile._build_card."""
    from bot.handlers.profile import _build_card
    try:
        return await _build_card(session, user, lang)
    except Exception as e:
        log.warning("Не удалось отрендерить карточку user_id=%s: %s",
                    user.id, e)
        name_line = f"<b>{user.display_name or user.full_name or '—'}</b>"
        username_line = f"\n@{user.username}" if user.username else ""
        return name_line + username_line


def _contact_url_buttons(user: User) -> list[list[InlineKeyboardButton]]:
    """Кнопки прямой связи: Telegram / WhatsApp / Phone / Email.

    Telegram-кнопка добавляется ВСЕГДА — даже если у юзера нет @username,
    мы используем tg://user?id={tg_id} (работает в любых Telegram-клиентах).
    Это гарантирует что у автора есть хотя бы один способ связаться с
    откликнувшимся.
    """
    rows: list[list[InlineKeyboardButton]] = []
    if user.username:
        rows.append([InlineKeyboardButton(
            text=f"💬 Telegram: @{user.username}",
            url=f"https://t.me/{user.username}",
        )])
    elif user.tg_id:
        rows.append([InlineKeyboardButton(
            text="💬 Написать в Telegram",
            url=f"tg://user?id={user.tg_id}",
        )])
    if user.contact_whatsapp:
        digits = user.contact_whatsapp.lstrip("+")
        rows.append([InlineKeyboardButton(
            text=f"💬 WhatsApp: {user.contact_whatsapp}",
            url=f"https://wa.me/{digits}",
        )])
    if user.contact_phone:
        rows.append([InlineKeyboardButton(
            text=f"📞 Позвонить: {user.contact_phone}",
            url=f"tel:{user.contact_phone}",
        )])
    if user.contact_email:
        rows.append([InlineKeyboardButton(
            text=f"✉️ Email: {user.contact_email}",
            url=f"mailto:{user.contact_email}",
        )])
    return rows


def _kb_author_actions(
    response_id: int, listing_id: int, lang: str,
    contact_buttons: list[list[InlineKeyboardButton]],
) -> InlineKeyboardMarkup:
    """Под DM автору: кнопки контактов + Нанял / Ещё ищу / Закрыть."""
    rows = list(contact_buttons)
    rows.append([
        InlineKeyboardButton(
            text=t(lang, "btn_hire_this"),
            callback_data=f"mp:hire:{response_id}",
        ),
        InlineKeyboardButton(
            text=t(lang, "btn_still_looking"),
            callback_data=f"mp:still:{listing_id}",
        ),
    ])
    rows.append([InlineKeyboardButton(
        text=t(lang, "btn_close_listing"),
        callback_data=f"mp:close:{listing_id}",
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ---------------------------------------------------------------------------
# Шаг 0: pинг админам сразу после Submit
# ---------------------------------------------------------------------------


async def notify_moderators_for_listing(bot: Bot, listing_id: int) -> None:
    """Отправить DM каждому админу с превью объявления и кнопками."""
    settings = get_settings()
    admin_ids = settings.admin_ids
    if not admin_ids:
        log.warning("ADMIN_IDS пуст — модерация не уведомлена для listing_id=%s",
                    listing_id)
        return

    async with get_session() as session:
        listing = await session.get(Listing, listing_id)
        if listing is None:
            log.warning("Listing %s исчез до уведомления", listing_id)
            return
        from sqlalchemy import select
        from bot.db.models import User
        rs = await session.execute(select(User).where(User.id == listing.user_id))
        author = rs.scalar_one_or_none()
        listing.author = author  # render_listing использует listing.author
        body = await listings_svc.render_listing(
            session, listing, lang="ru", include_contact=True,
        )
        photos_rs = await session.execute(
            select(ListingPhoto).where(ListingPhoto.listing_id == listing.id)
        )
        photo_files = [p.file_id for p in photos_rs.scalars().all()]

    author_label = (
        f"@{author.username}" if author and author.username
        else (author.display_name or author.full_name or "—" if author else "—")
    )
    text = t(
        "ru", "mod_new_listing",
        id=listing_id, author=author_label, body=body,
    )
    kb = _kb_moderation("ru", listing_id)

    for admin_id in admin_ids:
        try:
            if photo_files:
                # Если есть фото — шлём первое как media с caption
                await bot.send_photo(
                    chat_id=admin_id,
                    photo=photo_files[0],
                    caption=text[:1024],  # caption limit
                    reply_markup=kb,
                )
                # Остальные фото — отдельной media-группой без кнопок
                if len(photo_files) > 1:
                    media = [InputMediaPhoto(media=fid)
                             for fid in photo_files[1:]]
                    await bot.send_media_group(chat_id=admin_id, media=media)
            else:
                await bot.send_message(
                    chat_id=admin_id, text=text, reply_markup=kb,
                )
            log.info(
                "Модерация: отправлено админу tg_id=%s listing_id=%s",
                admin_id, listing_id,
            )
        except Exception as e:
            log.exception(
                "Не удалось уведомить админа tg_id=%s: %s", admin_id, e
            )


# ---------------------------------------------------------------------------
# Approve → публикация в группу
# ---------------------------------------------------------------------------


async def _close_group_message(bot: Bot | None, listing: Listing) -> None:
    """Когда listing достиг cap — убрать кнопку «Откликнуться» в группе и
    дописать "🔒 Набор закрыт" в текст. Best-effort: если сообщение уже
    нельзя редактировать (≥48 часов в Telegram), молча игнорируем.
    """
    if bot is None:
        return
    settings = get_settings()
    chat_id = settings.main_chat_id
    if not chat_id or not listing.channel_message_id:
        return
    try:
        await bot.edit_message_reply_markup(
            chat_id=chat_id,
            message_id=listing.channel_message_id,
            reply_markup=None,
        )
    except Exception as e:
        log.info("edit_message_reply_markup failed (likely too old): %s", e)
    # Постим reply «закрыто» под сообщением
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=t("ru", "post_listing_closed_in_group"),
            reply_to_message_id=listing.channel_message_id,
        )
    except Exception as e:
        log.info("close-reply send failed: %s", e)


async def _publish_to_group(
    bot: Bot, listing_id: int, *, group_chat_id: int
) -> int | None:
    """Опубликовать listing в группу. Возвращает channel_message_id или None.

    Контакт автора маскируется (только тип, без номера) — приватность.
    Реальный контакт автор получает в DM когда кто-то откликается.
    """
    async with get_session() as session:
        listing = await session.get(Listing, listing_id)
        if listing is None:
            return None
        from sqlalchemy import select
        from bot.db.models import User
        rs = await session.execute(select(User).where(User.id == listing.user_id))
        author = rs.scalar_one_or_none()
        listing.author = author
        body = await listings_svc.render_listing(
            session, listing, lang="ru",
            include_contact=True, mask_contact=True,  # ← скрываем номер
        )
        photos_rs = await session.execute(
            select(ListingPhoto).where(ListingPhoto.listing_id == listing.id)
        )
        photo_files = [p.file_id for p in photos_rs.scalars().all()]

    kb = _kb_respond(listing_id, "ru")

    if not photo_files:
        msg = await bot.send_message(
            chat_id=group_chat_id, text=body, reply_markup=kb,
        )
        return msg.message_id

    if len(photo_files) == 1:
        # Один фото — caption + кнопка в одном сообщении
        msg = await bot.send_photo(
            chat_id=group_chat_id,
            photo=photo_files[0],
            caption=body[:1024],
            reply_markup=kb,
        )
        return msg.message_id

    # Несколько фото — альбом всех фото, потом текст с кнопкой как reply.
    # Telegram не поддерживает inline_keyboard на media_group, поэтому два сообщения.
    # Визуально это смотрится как album + следующее под ним сообщение.
    media = [InputMediaPhoto(media=fid) for fid in photo_files[:10]]
    album_msgs = await bot.send_media_group(
        chat_id=group_chat_id, media=media,
    )
    first_album_msg_id = album_msgs[0].message_id if album_msgs else None
    text_msg = await bot.send_message(
        chat_id=group_chat_id,
        text=body,
        reply_markup=kb,
        reply_to_message_id=first_album_msg_id,
    )
    # channel_message_id — это сообщение с кнопкой (текстовое), его потом
    # будем редактировать при close.
    return text_msg.message_id


@router.callback_query(F.data.startswith("mp:apr:"))
async def cb_moderate_approve(callback: CallbackQuery) -> None:
    if callback.from_user is None or callback.data is None:
        return
    settings = get_settings()
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("Только для модераторов.", show_alert=True)
        return

    try:
        listing_id = int(callback.data.split(":")[2])
    except (ValueError, IndexError):
        await callback.answer()
        return

    # Race-protection: проверяем что pending
    async with get_session() as session:
        listing = await session.get(Listing, listing_id)
        if listing is None:
            await callback.answer("Listing не найден.", show_alert=True)
            return
        if listing.status != "pending":
            await callback.answer(
                t("ru", "mod_already_handled",
                  status=listing.status, who=listing.moderator_tg_id or "—"),
                show_alert=True,
            )
            return

    # Публикуем в группу (если задан chat_id)
    group_chat_id = settings.main_chat_id
    channel_message_id: int | None = None
    if group_chat_id and callback.bot:
        try:
            channel_message_id = await _publish_to_group(
                callback.bot, listing_id, group_chat_id=group_chat_id,
            )
        except Exception as e:
            log.exception("Публикация в группу упала listing_id=%s: %s",
                          listing_id, e)
            await callback.answer(
                f"Ошибка публикации: {e}. Listing помечен approved, но в группе не появился.",
                show_alert=True,
            )

    # Помечаем approved
    async with get_session() as session:
        await listings_svc.approve_listing(
            session, listing_id,
            moderator_tg_id=callback.from_user.id,
            channel_message_id=channel_message_id,
        )
        # Подгружаем автора для DM
        listing = await session.get(Listing, listing_id)
        if listing is None:
            await callback.answer()
            return
        from sqlalchemy import select
        from bot.db.models import User
        rs = await session.execute(select(User).where(User.id == listing.user_id))
        author = rs.scalar_one_or_none()

    # DM автору что одобрено
    if author and callback.bot:
        try:
            lang = normalize_lang(author.language)
            await callback.bot.send_message(
                chat_id=author.tg_id,
                text=t(lang, "post_approved_user"),
            )
        except Exception as e:
            log.warning("Не удалось уведомить автора tg_id=%s: %s",
                        author.tg_id, e)

    # Обновляем сообщение модератора
    if callback.message:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
            extra = ""
            if not group_chat_id:
                extra = "\n\n" + t("ru", "mod_no_group_chat")
            await callback.message.reply(
                t("ru", "mod_done_approved") + extra
            )
        except Exception:
            pass
    log.info("Approved listing_id=%s by mod=%s", listing_id, callback.from_user.id)
    await callback.answer()


# ---------------------------------------------------------------------------
# Reject → ввод причины → DM автору
# ---------------------------------------------------------------------------


@router.callback_query(F.data.startswith("mp:rej:"))
async def cb_moderate_reject(
    callback: CallbackQuery, state: FSMContext
) -> None:
    if callback.from_user is None or callback.data is None:
        return
    settings = get_settings()
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("Только для модераторов.", show_alert=True)
        return

    try:
        listing_id = int(callback.data.split(":")[2])
    except (ValueError, IndexError):
        await callback.answer()
        return

    async with get_session() as session:
        listing = await session.get(Listing, listing_id)
        if listing is None:
            await callback.answer("Listing не найден.", show_alert=True)
            return
        if listing.status != "pending":
            await callback.answer(
                t("ru", "mod_already_handled",
                  status=listing.status, who=listing.moderator_tg_id or "—"),
                show_alert=True,
            )
            return

    # Просим причину одним сообщением
    await state.set_state(ModerationStates.rejecting)
    await state.update_data(rejecting_listing_id=listing_id)
    if callback.message:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await callback.message.reply(t("ru", "mod_ask_reject_reason"))
    await callback.answer()


@router.message(ModerationStates.rejecting)
async def step_reject_reason(message: Message, state: FSMContext) -> None:
    if not message.text or message.from_user is None:
        return
    data = await state.get_data()
    listing_id = data.get("rejecting_listing_id")
    if listing_id is None:
        await state.clear()
        return
    reason = message.text.strip()[:200]

    async with get_session() as session:
        listing = await session.get(Listing, listing_id)
        if listing is None or listing.status != "pending":
            await state.clear()
            await message.answer(
                t("ru", "mod_already_handled",
                  status=listing.status if listing else "—", who="—")
            )
            return
        await listings_svc.reject_listing(
            session, listing_id,
            moderator_tg_id=message.from_user.id,
            reason=reason,
        )
        from sqlalchemy import select
        from bot.db.models import User
        rs = await session.execute(select(User).where(User.id == listing.user_id))
        author = rs.scalar_one_or_none()

    # DM автору
    if author and message.bot:
        try:
            lang = normalize_lang(author.language)
            await message.bot.send_message(
                chat_id=author.tg_id,
                text=t(lang, "post_rejected_user_with_reason", reason=reason),
            )
        except Exception as e:
            log.warning("Не удалось уведомить автора tg_id=%s: %s",
                        author.tg_id, e)

    await state.clear()
    await message.answer(t("ru", "mod_done_rejected"))
    log.info("Rejected listing_id=%s by mod=%s reason=%r",
             listing_id, message.from_user.id, reason)


# ---------------------------------------------------------------------------
# Отклик: клик «📩 Откликнуться» в группе → Response + DM автору
# ---------------------------------------------------------------------------


@router.callback_query(F.data.startswith("mp:resp:"))
async def cb_respond(callback: CallbackQuery) -> None:
    if callback.from_user is None or callback.data is None:
        return
    try:
        listing_id = int(callback.data.split(":")[2])
    except (ValueError, IndexError):
        await callback.answer()
        return

    async with get_session() as session:
        listing = await session.get(Listing, listing_id)
        if listing is None:
            await callback.answer("Объявление не найдено.", show_alert=True)
            return
        if listing.status != "approved":
            await callback.answer(
                t("ru", "post_response_cap_reached"), show_alert=True,
            )
            return

        # Собираем responder и author
        from sqlalchemy import select
        from bot.db.models import User
        rs = await session.execute(
            select(User).where(User.id == listing.user_id)
        )
        author = rs.scalar_one_or_none()
        responder = await users.get_user(session, callback.from_user.id)

        if author is None or author.tg_id == callback.from_user.id:
            await callback.answer(
                t("ru", "post_response_self"), show_alert=True,
            )
            return
        if responder is None or responder.role != "coworker":
            # Гость / нерег — даём явный путь к регистрации
            try:
                me = await callback.bot.me() if callback.bot else None
                bot_username = me.username if me else "C0w0rker1_bot"
            except Exception:
                bot_username = "C0w0rker1_bot"
            await callback.answer(
                t("ru", "post_response_register_first",
                  bot_username=bot_username),
                show_alert=True,
            )
            return

        # Защита от повторных кликов
        rs_existing = await session.execute(
            select(Response).where(
                Response.listing_id == listing_id,
                Response.responder_id == responder.id,
            )
        )
        if rs_existing.scalar_one_or_none() is not None:
            await callback.answer(
                "Ты уже откликался на это объявление.", show_alert=True,
            )
            return

        # Cap = num_people + RESPONSE_CAP_BONUS
        from sqlalchemy import func as sa_func
        current_count = await session.scalar(
            select(sa_func.count()).select_from(Response).where(
                Response.listing_id == listing_id
            )
        ) or 0
        needed = listing.num_people or 1
        cap = needed + listings_svc.RESPONSE_CAP_BONUS

        if current_count >= cap:
            # Уже достигнут cap — не создаём response
            await callback.answer(
                t("ru", "post_response_cap_reached"), show_alert=True,
            )
            # На всякий случай: если status ещё approved — закроем
            if listing.status == "approved":
                listing.status = "expired"
                await session.commit()
                await _close_group_message(callback.bot, listing)
            return

        # Создаём Response
        new_response = Response(
            listing_id=listing_id,
            responder_id=responder.id,
            text=None,
        )
        session.add(new_response)
        await session.commit()
        await session.refresh(new_response)
        response_id = new_response.id
        responses_count = current_count + 1

        # Если этот отклик дотянул до cap — закрываем объявление
        if responses_count >= cap:
            listing.status = "expired"
            await session.commit()
            await _close_group_message(callback.bot, listing)

        # Рендерим карточки обоих и собираем контакт-кнопки
        # (важно — пока сессия открыта, иначе lazy-load упадёт)
        author_card = await _render_user_card(session, author, "ru")
        responder_card = await _render_user_card(session, responder, "ru")
        author_contact_btns = _contact_url_buttons(author)
        responder_contact_btns = _contact_url_buttons(responder)
        author_tg_id = author.tg_id
        author_lang = normalize_lang(author.language)
        responder_lang = normalize_lang(responder.language)
        responder_tg_id = responder.tg_id

    # DM автору — карточка responder-а + контакт-кнопки + действия
    if callback.bot:
        try:
            kb_for_author = _kb_author_actions(
                response_id, listing_id, author_lang,
                contact_buttons=responder_contact_btns,
            )
            await callback.bot.send_message(
                chat_id=author_tg_id,
                text=t(author_lang, "post_response_to_author",
                       listing_id=listing_id, card=responder_card,
                       count=responses_count, needed=needed),
                reply_markup=kb_for_author,
                disable_web_page_preview=True,
            )
            log.info(
                "Notify author OK: listing=%s author_tg_id=%s responder_tg_id=%s "
                "response_id=%s count=%s/%s",
                listing_id, author_tg_id, responder_tg_id,
                response_id, responses_count, needed,
            )
        except Exception as e:
            log.warning(
                "Notify author FAILED: listing=%s author_tg_id=%s err=%s",
                listing_id, author_tg_id, e,
            )

    # DM responder-у — карточка автора + контакт-кнопки
    if callback.bot:
        try:
            kb_for_responder = (
                InlineKeyboardMarkup(inline_keyboard=author_contact_btns)
                if author_contact_btns else None
            )
            await callback.bot.send_message(
                chat_id=responder_tg_id,
                text=t(responder_lang, "post_response_to_responder",
                       listing_id=listing_id, card=author_card),
                reply_markup=kb_for_responder,
                disable_web_page_preview=True,
            )
        except Exception as e:
            log.warning("Не удалось отправить ack responder-у tg_id=%s: %s",
                        responder_tg_id, e)

    # Короткое подтверждение в popup
    await callback.answer(
        t(responder_lang, "post_response_acked"), show_alert=True,
    )
    log.info(
        "Response created: listing=%s responder=%s author=%s response_id=%s",
        listing_id, callback.from_user.id, author_tg_id, response_id,
    )


# ---------------------------------------------------------------------------
# Author actions: Hire / Still looking / Close
# ---------------------------------------------------------------------------


@router.callback_query(F.data.startswith("mp:hire:"))
async def cb_hire(callback: CallbackQuery) -> None:
    """Автор отметил отклик как «нанял этого». Создаёт Deal, может закрыть listing."""
    if callback.from_user is None or callback.data is None:
        return
    try:
        response_id = int(callback.data.split(":")[2])
    except (ValueError, IndexError):
        await callback.answer()
        return

    async with get_session() as session:
        from sqlalchemy import select, func as sa_func
        response = await session.get(Response, response_id)
        if response is None:
            await callback.answer("Отклик не найден.", show_alert=True)
            return

        listing = await session.get(Listing, response.listing_id)
        if listing is None:
            await callback.answer("Объявление исчезло.", show_alert=True)
            return

        # Проверяем что это автор
        rs = await session.execute(
            select(User).where(User.id == listing.user_id)
        )
        author = rs.scalar_one_or_none()
        if author is None or author.tg_id != callback.from_user.id:
            await callback.answer("Доступно только автору объявления.",
                                  show_alert=True)
            return

        if response.is_hired:
            await callback.answer("Уже отмечен как нанятый.", show_alert=True)
            return

        # Помечаем
        response.is_hired = True
        response.hired_at = datetime.now(timezone.utc)

        # Создаём Deal (если ещё нет на эту пару)
        existing_deal = await session.execute(
            select(Deal).where(
                Deal.listing_id == listing.id,
                Deal.contractor_id == response.responder_id,
                Deal.customer_id == author.id,
            )
        )
        if existing_deal.scalar_one_or_none() is None:
            session.add(Deal(
                customer_id=author.id,
                contractor_id=response.responder_id,
                listing_id=listing.id,
                status="open",
            ))

        await session.commit()

        # Считаем сколько уже нанято
        hired_count = await session.scalar(
            select(sa_func.count())
            .select_from(Response)
            .where(
                Response.listing_id == listing.id,
                Response.is_hired.is_(True),
            )
        ) or 0
        needed = listing.num_people or 1

        listing_was_closed = False
        if hired_count >= needed and listing.status == "approved":
            listing.status = "closed"
            await session.commit()
            await _close_group_message(callback.bot, listing)
            listing_was_closed = True

    log.info(
        "Hire: response_id=%s listing=%s by=%s closed=%s",
        response_id, listing.id, callback.from_user.id, listing_was_closed,
    )

    # Убираем кнопки действий из этого DM (контакт-кнопки оставляем)
    if callback.message and callback.message.reply_markup:
        try:
            new_rows = [
                row for row in callback.message.reply_markup.inline_keyboard
                if not any(
                    btn.callback_data and btn.callback_data.startswith(("mp:hire", "mp:still", "mp:close"))
                    for btn in row
                )
            ]
            if new_rows:
                await callback.message.edit_reply_markup(
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=new_rows)
                )
            else:
                await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass

    await callback.answer(
        t("ru", "hire_acked_closed" if listing_was_closed else "hire_acked"),
        show_alert=True,
    )


@router.callback_query(F.data.startswith("mp:still:"))
async def cb_still_looking(callback: CallbackQuery) -> None:
    """Автор: «ещё ищу» — просто ack, ничего не меняем."""
    if callback.from_user is None or callback.data is None:
        return
    await callback.answer(t("ru", "still_looking_acked"), show_alert=False)


@router.callback_query(F.data.startswith("mp:close:"))
async def cb_close_listing(callback: CallbackQuery) -> None:
    """Автор закрывает объявление вручную."""
    if callback.from_user is None or callback.data is None:
        return
    try:
        listing_id = int(callback.data.split(":")[2])
    except (ValueError, IndexError):
        await callback.answer()
        return

    async with get_session() as session:
        from sqlalchemy import select
        listing = await session.get(Listing, listing_id)
        if listing is None:
            await callback.answer("Объявление не найдено.", show_alert=True)
            return
        rs = await session.execute(
            select(User).where(User.id == listing.user_id)
        )
        author = rs.scalar_one_or_none()
        if author is None or author.tg_id != callback.from_user.id:
            await callback.answer("Доступно только автору объявления.",
                                  show_alert=True)
            return
        if listing.status not in ("approved", "expired", "pending"):
            await callback.answer(
                f"Объявление уже в статусе {listing.status}.", show_alert=True,
            )
            return
        was_published = listing.status in ("approved", "expired")
        listing.status = "closed"
        await session.commit()
        # Группу-сообщение редактируем только если оно было опубликовано
        if was_published:
            await _close_group_message(callback.bot, listing)

    if callback.message and callback.message.reply_markup:
        try:
            new_rows = [
                row for row in callback.message.reply_markup.inline_keyboard
                if not any(
                    btn.callback_data and btn.callback_data.startswith(("mp:hire", "mp:still", "mp:close"))
                    for btn in row
                )
            ]
            if new_rows:
                await callback.message.edit_reply_markup(
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=new_rows)
                )
            else:
                await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass

    log.info("Close: listing=%s by=%s", listing_id, callback.from_user.id)
    await callback.answer(t("ru", "close_acked"), show_alert=True)
