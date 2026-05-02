"""Модели БД для tg-community-bot.

Включает:
- User (расширен ролью, языком, профилем для маркетплейса)
- Message, Broadcast (как было)
- Tag, Listing, ListingTag — объявления
- Response — отклики на объявления
- Deal — сделки
- Feedback, FeedbackTag — отзывы и облако тегов
- Subscription — платные подписки
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.db.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Базовые: пользователь, сообщение, рассылка
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    warnings: Mapped[int] = mapped_column(Integer, default=0)
    captcha_passed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Маркетплейс-поля (заполняются через /register)
    language: Mapped[str] = mapped_column(String(8), default="ru")
    role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # roles: coworker | guest | None (legacy: handyman/individual/company)
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    area: Mapped[str | None] = mapped_column(String(256), nullable=True)
    # legacy phone (оставляем для обратной совместимости)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    registered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # v2: контакты (раздельно)
    contact_phone: Mapped[str | None] = mapped_column(String(16), nullable=True)
    contact_whatsapp: Mapped[str | None] = mapped_column(String(16), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(254), nullable=True)

    # v2: согласия (GDPR/CCPA)
    consent_data: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_notifications: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # v2: лицензия contractor
    is_licensed_contractor: Mapped[bool] = mapped_column(Boolean, default=False)
    license_number: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # v2: основной (primary) тег — ключевая компетенция
    primary_tag_id: Mapped[int | None] = mapped_column(
        ForeignKey("tags.id", ondelete="SET NULL"), nullable=True
    )

    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="user", cascade="all, delete-orphan"
    )
    listings: Mapped[list["Listing"]] = relationship(
        "Listing",
        back_populates="author",
        cascade="all, delete-orphan",
        foreign_keys="Listing.user_id",
    )
    subscriptions: Mapped[list["Subscription"]] = relationship(
        "Subscription", back_populates="user", cascade="all, delete-orphan"
    )
    user_tags: Mapped[list["UserTag"]] = relationship(
        "UserTag", back_populates="user", cascade="all, delete-orphan"
    )
    primary_tag: Mapped["Tag | None"] = relationship(
        "Tag", foreign_keys=[primary_tag_id]
    )


class Suggestion(Base):
    """Идея/обратная связь от юзера админам.

    Юзер пишет через /suggest. Админ читает список через /suggestions
    и помечает обработанные через /suggest_done <id>.
    """

    __tablename__ = "suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    chat_id: Mapped[int] = mapped_column(BigInteger)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )

    user: Mapped["User"] = relationship("User", back_populates="messages")


class Broadcast(Base):
    __tablename__ = "broadcasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(Text)
    segment: Mapped[str] = mapped_column(String(32), default="all")
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    blocked_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    initiated_by: Mapped[int] = mapped_column(BigInteger)


# ---------------------------------------------------------------------------
# Маркетплейс: теги, объявления, отклики
# ---------------------------------------------------------------------------


class Tag(Base):
    """Справочник тегов (skill/location/other)."""

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    label_ru: Mapped[str] = mapped_column(String(128))
    label_en: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(32), default="skill")
    # category: skill | location | feedback_pos | feedback_neg

    # v2: пользовательские теги — модерация
    is_predefined: Mapped[bool] = mapped_column(Boolean, default=True)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    usages_count: Mapped[int] = mapped_column(Integer, default=0)


class UserTag(Base):
    """M2M User↔Tag — навыки/виды работ пользователя (до 6, включая primary)."""

    __tablename__ = "user_tags"
    __table_args__ = (
        UniqueConstraint("user_id", "tag_id", name="uix_user_tag"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), index=True
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    user: Mapped["User"] = relationship("User", back_populates="user_tags")
    tag: Mapped["Tag"] = relationship("Tag")


class Listing(Base):
    """Объявление: 'Предлагаю работу' (offer) или 'Ищу работу' (seek)."""

    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(16))  # offer | seek
    text: Mapped[str] = mapped_column(Text)  # описание (до 1000 символов)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    # status: pending | approved | rejected | expired
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )
    moderated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    moderator_tg_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # v2: структурированные поля от FSM /post
    num_people: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 1..5 (5 значит "5+"), для offer
    engagement_kind: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # 'one_time' | 'part_time' (для seek)
    helper_kind: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # 'pro' | 'helper' | 'any' (для offer)
    language_req: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # offer: 'none' | 'ru' | 'en' | 'any'
    # seek: 'ru' | 'en' | 'ru_en'
    duration: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # 'hours' | 'day' | 'few_days' | 'week_plus' | 'longterm'
    urgency: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # 'urgent' | 'this_week' | 'this_month' | 'flexible'
    budget: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # 'under_500' | '500_2k' | '2k_10k' | 'over_10k' | 'discuss' | None
    contact_override: Mapped[str | None] = mapped_column(String(254), nullable=True)
    # если автор для этого объявления указал другой контакт
    location_freetext: Mapped[str | None] = mapped_column(String(256), nullable=True)
    # пользовательский ввод (город/ZIP/адрес) если предустановленных регионов мало

    author: Mapped["User"] = relationship(
        "User", back_populates="listings", foreign_keys=[user_id]
    )
    tags: Mapped[list["ListingTag"]] = relationship(
        "ListingTag", back_populates="listing", cascade="all, delete-orphan"
    )
    responses: Mapped[list["Response"]] = relationship(
        "Response", back_populates="listing", cascade="all, delete-orphan"
    )
    photos: Mapped[list["ListingPhoto"]] = relationship(
        "ListingPhoto", back_populates="listing", cascade="all, delete-orphan"
    )


class ListingPhoto(Base):
    """Фото к объявлению — храним Telegram file_id, не сами байты."""

    __tablename__ = "listing_photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    listing_id: Mapped[int] = mapped_column(
        ForeignKey("listings.id", ondelete="CASCADE"), index=True
    )
    file_id: Mapped[str] = mapped_column(String(256))
    caption: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    listing: Mapped["Listing"] = relationship("Listing", back_populates="photos")


class ListingTag(Base):
    """M2M Listing↔Tag."""

    __tablename__ = "listing_tags"
    __table_args__ = (
        UniqueConstraint("listing_id", "tag_id", name="uix_listing_tag"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    listing_id: Mapped[int] = mapped_column(
        ForeignKey("listings.id", ondelete="CASCADE"), index=True
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), index=True
    )

    listing: Mapped["Listing"] = relationship("Listing", back_populates="tags")
    tag: Mapped["Tag"] = relationship("Tag")


class Response(Base):
    """Отклик пользователя на объявление."""

    __tablename__ = "responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    listing_id: Mapped[int] = mapped_column(
        ForeignKey("listings.id", ondelete="CASCADE"), index=True
    )
    responder_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    # v2: автор отметил отклик как «нанял» → создаётся Deal
    is_hired: Mapped[bool] = mapped_column(Boolean, default=False)
    hired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    listing: Mapped["Listing"] = relationship("Listing", back_populates="responses")
    responder: Mapped["User"] = relationship("User", foreign_keys=[responder_id])


# ---------------------------------------------------------------------------
# Сделки и фидбэк
# ---------------------------------------------------------------------------


class Deal(Base):
    """Сделка между заказчиком и исполнителем."""

    __tablename__ = "deals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    contractor_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    listing_id: Mapped[int | None] = mapped_column(
        ForeignKey("listings.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), default="open", index=True)
    # status: open | closed | cancelled
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    customer: Mapped["User"] = relationship("User", foreign_keys=[customer_id])
    contractor: Mapped["User"] = relationship("User", foreign_keys=[contractor_id])
    listing: Mapped["Listing | None"] = relationship("Listing")


class Feedback(Base):
    """Отзыв от одной стороны сделки на другую."""

    __tablename__ = "feedbacks"
    __table_args__ = (
        UniqueConstraint("deal_id", "from_user_id", name="uix_feedback_deal_from"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    deal_id: Mapped[int] = mapped_column(
        ForeignKey("deals.id", ondelete="CASCADE"), index=True
    )
    from_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    to_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    rating: Mapped[int] = mapped_column(Integer)  # 1..5
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    tags: Mapped[list["FeedbackTag"]] = relationship(
        "FeedbackTag", back_populates="feedback", cascade="all, delete-orphan"
    )
    from_user: Mapped["User"] = relationship("User", foreign_keys=[from_user_id])
    to_user: Mapped["User"] = relationship("User", foreign_keys=[to_user_id])
    deal: Mapped["Deal"] = relationship("Deal")


class FeedbackTag(Base):
    """Тег отзыва — для облака слов на профиле."""

    __tablename__ = "feedback_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    feedback_id: Mapped[int] = mapped_column(
        ForeignKey("feedbacks.id", ondelete="CASCADE"), index=True
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), index=True
    )

    feedback: Mapped["Feedback"] = relationship("Feedback", back_populates="tags")
    tag: Mapped["Tag"] = relationship("Tag")


# ---------------------------------------------------------------------------
# Подписки
# ---------------------------------------------------------------------------


class Subscription(Base):
    """Платная подписка (выдаётся вручную админом)."""

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(32), default="individual")
    # kind: individual | company
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    granted_by_tg_id: Mapped[int] = mapped_column(BigInteger)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User"] = relationship("User", back_populates="subscriptions")
