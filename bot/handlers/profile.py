"""/profile — моя карточка; /check @username — карточка контрагента."""
from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy import func, select

from bot.db.database import get_session
from bot.db.models import Deal, Feedback, Subscription, Tag, User, UserTag
from bot.i18n import normalize_lang, t
from bot.services import tags as tags_svc
from bot.services import users

log = logging.getLogger(__name__)
router = Router(name="profile")


_ROLE_LABELS = {
    "ru": {
        "coworker": "🛠 Coworker",
        "customer": "🏠 Заказчик",
        "guest": "👀 Гость",
        "handyman": "🔧 Исполнитель",          # legacy
        "individual": "🏠 Заказчик (физлицо)",  # legacy
        "company": "🏢 Компания-заказчик",      # legacy
    },
    "en": {
        "coworker": "🛠 Coworker",
        "customer": "🏠 Customer",
        "guest": "👀 Guest",
        "handyman": "🔧 Contractor",
        "individual": "🏠 Individual client",
        "company": "🏢 Company client",
    },
}


def _label_field(tag: Tag, lang: str) -> str:
    return tag.label_ru if lang == "ru" else tag.label_en


async def _build_card(
    session, user: User, lang: str,
    *, viewer_is_admin: bool = False,
) -> str:
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

    # Теги пользователя
    rs = await session.execute(
        select(UserTag, Tag)
        .join(Tag, Tag.id == UserTag.tag_id)
        .where(UserTag.user_id == user.id)
        .order_by(UserTag.is_primary.desc())
    )
    rows = list(rs.all())
    primary_label = "—"
    secondary_labels: list[str] = []
    for ut, tag in rows:
        label = _label_field(tag, lang)
        if ut.is_primary:
            primary_label = label
        else:
            secondary_labels.append(label)
    secondary_str = ", ".join(secondary_labels) if secondary_labels else "—"

    # Облако фидбэк-тегов
    cloud_pairs = await tags_svc.get_feedback_tag_cloud(
        session, to_user_id=user.id, lang=lang
    )
    cloud_str = tags_svc.render_tag_cloud(cloud_pairs)

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

    # Бейджи: Verified contractor (auto, по lic) + community badges (admin)
    licensed_badge = (
        t(lang, "profile_licensed_badge") if user.is_licensed_contractor else ""
    )
    if user.badge_verified:
        licensed_badge += t(lang, "badge_verified")
    if user.badge_trusted:
        licensed_badge += t(lang, "badge_trusted")
    if user.badge_top:
        licensed_badge += t(lang, "badge_top")
    if user.badge_svoyak:
        licensed_badge += t(lang, "badge_svoyak")
    if user.badge_znatok:
        licensed_badge += t(lang, "badge_znatok")
    # Re-registered бейдж — ТОЛЬКО для админа.
    if viewer_is_admin and (user.delete_count or 0) > 0:
        licensed_badge += t(lang, "delete_count_badge", n=user.delete_count)

    # Приоритетный способ связи — только тип, не значение (приватность)
    if user.contact_phone:
        contact_pref = t(lang, "profile_contact_phone")
    elif user.contact_whatsapp:
        contact_pref = t(lang, "profile_contact_whatsapp")
    elif user.contact_email:
        contact_pref = t(lang, "profile_contact_email")
    else:
        contact_pref = t(lang, "profile_contact_none")

    return t(
        lang,
        "profile_card",
        name=user.display_name or user.full_name or "—",
        licensed_badge=licensed_badge,
        role=role_label,
        area=user.area or "—",
        primary_tag=primary_label,
        tags=secondary_str,
        contact_pref=contact_pref,
        bio=(user.bio or ""),
        rating=rating_str,
        deals=deals_count or 0,
        cloud=cloud_str,
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
        if user.role == "customer":
            text = await _build_customer_card(session, user, lang)
        else:
            text = await _build_card(session, user, lang)
    await message.answer(text)


@router.message(Command("my_subscription"))
async def cmd_my_subscription(message: Message) -> None:
    """Показать статус активной подписки или предложение оформить."""
    if message.chat.type != "private" or message.from_user is None:
        return
    from datetime import datetime, timezone
    async with get_session() as session:
        u = await users.get_user(session, message.from_user.id)
        lang = normalize_lang(u.language if u else None)
        if u is None:
            await message.answer(t(lang, "my_subscription_inactive"))
            return
        sub = await users.get_active_subscription(session, u.id)
    if sub is None:
        await message.answer(t(lang, "my_subscription_inactive"))
        return
    days_left = max(0, (sub.expires_at - datetime.now(timezone.utc)).days)
    until = sub.expires_at.strftime("%Y-%m-%d")
    await message.answer(t(
        lang, "my_subscription_active",
        kind=sub.kind, until=until, days_left=days_left,
    ))


async def _build_customer_card(session, user: User, lang: str) -> str:
    """Упрощённая карточка для Customer: имя, контакт, кол-во объявлений."""
    from sqlalchemy import func as sa_func
    from bot.db.models import Listing

    listings_count = await session.scalar(
        select(sa_func.count(Listing.id)).where(
            Listing.user_id == user.id,
            Listing.status.in_(("approved", "closed")),
        )
    ) or 0

    if user.contact_phone:
        contact_pref = t(lang, "profile_contact_phone")
    elif user.contact_whatsapp:
        contact_pref = t(lang, "profile_contact_whatsapp")
    elif user.contact_email:
        contact_pref = t(lang, "profile_contact_email")
    else:
        contact_pref = t(lang, "profile_contact_none")

    return t(
        lang,
        "profile_card_customer",
        name=user.display_name or user.full_name or "—",
        contact_pref=contact_pref,
        listings_count=listings_count,
    )


def _can_view_profiles(user: User | None) -> bool:
    """True если user имеет полный профиль Coworker (или legacy роли)."""
    if user is None or not user.role:
        return False
    # Coworker и legacy роли — да; guest и customer — нет
    return user.role in ("coworker", "handyman", "individual", "company")


@router.message(Command("check"))
async def cmd_check(message: Message, command: CommandObject) -> None:
    """/check @username — карточка пользователя по username.

    Доступ: только зарегистрированным Coworker-ам (и legacy ролям).
    Гости и нерегистрированные видят сообщение с предложением /register.
    """
    if message.chat.type != "private" or message.from_user is None:
        return

    async with get_session() as session:
        me = await users.get_user(session, message.from_user.id)
        my_lang = normalize_lang(me.language if me else None)

        # Gate: только Coworker-ы могут смотреть карточки других
        if not _can_view_profiles(me):
            await message.answer(t(my_lang, "check_only_coworkers"))
            return

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
        from bot.config import get_settings
        viewer_is_admin = (
            message.from_user.id in get_settings().admin_ids
        )
        if target is None or not target.role:
            await message.answer(
                {"ru": "Пользователь не найден или не зарегистрирован.",
                 "en": "User not found or not registered."}[my_lang]
            )
            return
        # Customer — упрощённая карточка без рейтинга и тегов
        if target.role == "customer":
            text = await _build_customer_card(session, target, my_lang)
        else:
            text = await _build_card(
                session, target, my_lang, viewer_is_admin=viewer_is_admin,
            )

    await message.answer(text)
