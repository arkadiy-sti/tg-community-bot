"""/suggest — обратная связь о боте, идеи и предложения от юзеров админам.

Юзер пишет одно сообщение → сохраняем в БД + DM всем admin_ids.
Админ читает /suggestions (последние 20) и помечает /suggest_done <id>.
"""
from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from bot.config import get_settings
from bot.db.database import get_session
from bot.db.models import Suggestion
from bot.i18n import normalize_lang, t
from bot.services import users

log = logging.getLogger(__name__)
router = Router(name="suggest")

MIN_TEXT_LEN = 5
MAX_TEXT_LEN = 2000


class SuggestStates(StatesGroup):
    waiting_text = State()


async def _user_lang(tg_id: int | None) -> str:
    if tg_id is None:
        return normalize_lang(None)
    async with get_session() as session:
        u = await users.get_user(session, tg_id)
        return normalize_lang(u.language if u else None)


# ---------------------------------------------------------------------------
# /suggest — пользовательская команда
# ---------------------------------------------------------------------------


@router.message(Command("suggest"))
async def cmd_suggest(message: Message, state: FSMContext) -> None:
    if message.chat.type != "private" or message.from_user is None:
        return
    lang = await _user_lang(message.from_user.id)
    await state.clear()
    await state.set_state(SuggestStates.waiting_text)
    await state.update_data(lang=lang)
    await message.answer(t(lang, "suggest_ask_text"))


@router.message(SuggestStates.waiting_text, Command("cancel"))
async def cmd_cancel_suggest(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.clear()
    await message.answer(t(lang, "suggest_canceled"))


@router.message(SuggestStates.waiting_text)
async def step_text(message: Message, state: FSMContext) -> None:
    if not message.text or message.from_user is None:
        return
    data = await state.get_data()
    lang = data.get("lang", "ru")
    text = message.text.strip()[:MAX_TEXT_LEN]
    if len(text) < MIN_TEXT_LEN:
        await message.answer(t(lang, "suggest_too_short", min=MIN_TEXT_LEN))
        return

    async with get_session() as session:
        user = await users.get_user(session, message.from_user.id)
        suggestion = Suggestion(
            user_id=user.id if user else None,
            text=text,
        )
        session.add(suggestion)
        await session.commit()
        await session.refresh(suggestion)
        sug_id = suggestion.id

    # Уведомляем админов
    settings = get_settings()
    user_label = (
        f"@{message.from_user.username}"
        if message.from_user.username
        else (message.from_user.full_name or f"id{message.from_user.id}")
    )
    admin_text = t(
        "ru", "suggest_admin_notif",
        id=sug_id, user=user_label, text=text,
    )
    if message.bot:
        for admin_id in settings.admin_ids:
            try:
                await message.bot.send_message(chat_id=admin_id, text=admin_text)
            except Exception as e:
                log.warning("Suggest notify admin %s failed: %s", admin_id, e)

    await state.clear()
    await message.answer(t(lang, "suggest_thanks"))
    log.info("Suggestion #%s from tg_id=%s", sug_id, message.from_user.id)


# ---------------------------------------------------------------------------
# Админские команды: /suggestions, /suggest_done
# ---------------------------------------------------------------------------


@router.message(Command("suggestions"))
async def cmd_suggestions_list(message: Message) -> None:
    """Админ: список последних 20 предложений."""
    settings = get_settings()
    if message.from_user is None or message.from_user.id not in settings.admin_ids:
        return
    async with get_session() as session:
        from sqlalchemy import select
        rs = await session.execute(
            select(Suggestion).order_by(Suggestion.created_at.desc()).limit(20)
        )
        items = list(rs.scalars().all())
    if not items:
        await message.answer("📭 Предложений пока нет.")
        return
    lines = []
    for s in items:
        status = "✅" if s.is_resolved else "🆕"
        snippet = s.text[:200] + ("…" if len(s.text) > 200 else "")
        lines.append(
            f"{status} <b>#{s.id}</b> · {s.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            f"{snippet}"
        )
    await message.answer(
        "💡 <b>Последние предложения:</b>\n\n" + "\n\n".join(lines)
        + "\n\nПометить обработанным: <code>/suggest_done &lt;id&gt;</code>"
    )


@router.message(Command("suggest_done"))
async def cmd_suggest_done(
    message: Message, command: CommandObject
) -> None:
    """Админ: пометить предложение как обработанное."""
    settings = get_settings()
    if message.from_user is None or message.from_user.id not in settings.admin_ids:
        return
    arg = (command.args or "").strip()
    try:
        sid = int(arg)
    except ValueError:
        await message.answer("Использование: <code>/suggest_done &lt;id&gt;</code>")
        return
    async with get_session() as session:
        sug = await session.get(Suggestion, sid)
        if sug is None:
            await message.answer(f"❌ Предложение #{sid} не найдено.")
            return
        sug.is_resolved = True
        await session.commit()
    await message.answer(f"✅ Предложение #{sid} помечено как обработанное.")
