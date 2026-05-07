"""Декоратор @subscription_required для гейтинга платных функций.

Использование:
    from bot.services.subscriptions import subscription_required

    @router.message(Command("featured_post"))
    @subscription_required(plan="pro")  # или "any"
    async def cmd_featured(message: Message) -> None:
        ...

Если у юзера нет активной подписки нужного плана — бот показывает
сообщение «функция для подписчиков» и хэндлер не вызывается.

Пока что (MVP) ни один хэндлер не обёрнут — лимиты и Pro-фичи запустим
после набора аудитории. Декоратор готов к использованию.
"""
from __future__ import annotations

import logging
from functools import wraps
from typing import Awaitable, Callable

from aiogram.types import CallbackQuery, Message

from bot.db.database import get_session
from bot.i18n import normalize_lang, t
from bot.services import users

log = logging.getLogger(__name__)

EventT = Message | CallbackQuery
HandlerT = Callable[..., Awaitable]


async def _deny(event: EventT, lang: str) -> None:
    """Показать «функция для подписчиков»."""
    msg = t(lang, "subscription_required_msg")
    if isinstance(event, CallbackQuery):
        await event.answer(msg[:200], show_alert=True)
    else:
        await event.answer(msg, disable_web_page_preview=True)


def subscription_required(plan: str = "any") -> Callable[[HandlerT], HandlerT]:
    """Гейт по подписке. plan='any' — любая активная; конкретный план
    (pro/business) — проверяется через Subscription.kind."""

    def decorator(func: HandlerT) -> HandlerT:
        @wraps(func)
        async def wrapper(event: EventT, *args, **kwargs):
            user_id = event.from_user.id if event.from_user else None
            if user_id is None:
                return
            async with get_session() as session:
                me = await users.get_user(session, user_id)
                if me is None:
                    lang = normalize_lang(None)
                    await _deny(event, lang)
                    return
                lang = normalize_lang(me.language)
                sub = await users.get_active_subscription(session, me.id)
            if sub is None:
                await _deny(event, lang)
                return
            if plan != "any" and sub.kind != plan:
                await _deny(event, lang)
                return
            return await func(event, *args, **kwargs)

        return wrapper

    return decorator
