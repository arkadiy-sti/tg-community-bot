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

from bot.config import get_settings
from bot.db.database import get_session
from bot.db.models import Listing, ListingPhoto, Response
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


async def _publish_to_group(
    bot: Bot, listing_id: int, *, group_chat_id: int
) -> int | None:
    """Опубликовать listing в группу. Возвращает channel_message_id или None."""
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
            session, listing, lang="ru", include_contact=True,
        )
        photos_rs = await session.execute(
            select(ListingPhoto).where(ListingPhoto.listing_id == listing.id)
        )
        photo_files = [p.file_id for p in photos_rs.scalars().all()]

    kb = _kb_respond(listing_id, "ru")

    if photo_files:
        msg = await bot.send_photo(
            chat_id=group_chat_id,
            photo=photo_files[0],
            caption=body[:1024],
            reply_markup=kb,
        )
        if len(photo_files) > 1:
            media = [InputMediaPhoto(media=fid) for fid in photo_files[1:]]
            await bot.send_media_group(chat_id=group_chat_id, media=media)
    else:
        msg = await bot.send_message(
            chat_id=group_chat_id, text=body, reply_markup=kb,
        )
    return msg.message_id


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
            await callback.answer("Объявление недоступно.", show_alert=True)
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
                "Нельзя откликнуться на свое объявление.", show_alert=True,
            )
            return
        if responder is None:
            await callback.answer(
                "Сначала зарегистрируйся в боте: /start", show_alert=True,
            )
            return

        # Создаём Response
        session.add(Response(
            listing_id=listing_id,
            responder_id=responder.id,
            text=None,
        ))
        await session.commit()

    # DM автору
    if callback.bot and author:
        responder_label = (
            f"@{responder.username}" if responder.username
            else (responder.display_name or responder.full_name or f"id{responder.tg_id}")
        )
        # Контакт responder (его приоритетный)
        if responder.contact_phone:
            contact = f"📱 {responder.contact_phone}"
        elif responder.contact_whatsapp:
            contact = f"💬 WhatsApp {responder.contact_whatsapp}"
        elif responder.contact_email:
            contact = f"✉️ {responder.contact_email}"
        elif responder.username:
            contact = f"@{responder.username}"
        else:
            contact = "Telegram DM"
        try:
            lang = normalize_lang(author.language)
            await callback.bot.send_message(
                chat_id=author.tg_id,
                text=t(lang, "post_response_to_author",
                       responder=responder_label, contact=contact),
            )
        except Exception as e:
            log.warning("Не удалось уведомить автора tg_id=%s: %s",
                        author.tg_id, e)

    # Подтверждение responder-у
    await callback.answer(
        t("ru", "post_response_acked"), show_alert=True,
    )
    log.info(
        "Response: listing=%s responder=%s author=%s",
        listing_id, callback.from_user.id, author.tg_id if author else None,
    )
