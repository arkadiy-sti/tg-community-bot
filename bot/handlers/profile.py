"""/profile — моя карточка; /check @username — карточка контрагента."""
from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy import func, select

from bot.db.database import get_session
from bot.db.models import Deal, Feedback, Subscription, User
from bot.i18n import normalize_lang, t
from bot.services import users

log = logging.getLogger(__name__)
router = Router(name="profile")


_ROLE_LABELS = {
    "ru": {
        "handyman": "🔧 Исполнитель",
        "individual": "🏠 Заказчик (физлицо)",
        "company": "🏢 Компания-заказчик",
    },
    "en": {
        "handyman": "🔧 Contractor",
        "individual": "🏠 Individual client",
        "company": "🏢 Company client",
    },
}


async def _build_card(session, user: User, lang: str) -> str:
    role_label = _ROLE_LABELS.get(lang, _ROLE_LABELS["ru"]).get(
        user.role or "", user.role or "—"
    )

    # Рейтинг и кол-во сделок
    rating_avg = await session.scalar(
        select(func.avg(Feedback.rating)).where(Feedback.to_user_id == user.id)
    )
    deals_count = await session.scalar(
        select(func.count(Deal.id)).where(
            (Deal.contractor_id == user.id) | (Deal.customer_id == user.id),
            Deal.status == "closed",
        )
    )
    rating_str = f"{rating_avg:.1f}" if rating_avg else "—"

    # Подписка
    sub = await session.scalar(
        select(Subscription)
        .where(Subscription.user_id == user.id, Subscription.is_active.is_(True))
        .order_by(Subscription.expires_at.desc())
        .limit(1)
    )
    if sub and sub.expires_at:
        sub_str = t(lang, "profile_subscription_active",
                    until=sub.expires_at.strftime("%Y-%m-%d"))
    else:
        sub_str = t(lang, "profile_no_subscription")

    return t(
        lang,
        "profile_card",
        name=user.display_name or user.full_name or "—",
        role=role_label,
        area=user.area or "—",
        bio=(user.bio or ""),
        rating=rating_str,
        deals=deals_count or 0,
        subscription=sub_str,
    )


@router.message(Command("profile"))
async def cmd_profile(message: Message) -> None:
    if message.chat.type != "private" or message.from_user is None:
        return
    async with get_session() as session:
        user = await users.get_user(session, message.from_user.id)
        if user is None or not user.role:
            lang = normalize_lang(user.language if user else None)
            await message.answer(t(lang, "profile_not_registered"))
            return
        lang = normalize_lang(user.language)
        text = await _build_card(session, user, lang)
    await message.answer(text)


@router.message(Command("check"))
async def cmd_check(message: Message, command: CommandObject) -> None:
    """/check @username — карточка пользователя по username."""
    if message.chat.type != "private" or message.from_user is None:
        return

    async with get_session() as session:
        me = await users.get_user(session, message.from_user.id)
        my_lang = normalize_lang(me.language if me else None)

        arg = (command.args or "").strip().lstrip("@").lower()
        if not arg:
            await message.answer(
                {"ru": "Использование: /check @username",
                 "en": "Usage: /check @username"}[my_lang]
            )
            return

        rs = await session.execute(
            select(User).where(func.lower(User.username) == arg)
        )
        target = rs.scalar_one_or_none()
        if target is None or not target.role:
            await message.answer(
                {"ru": "Пользователь не найден или не зарегистрирован.",
                 "en": "User not found or not registered."}[my_lang]
            )
            return
        text = await _build_card(session, target, my_lang)

    await message.answer(text)
