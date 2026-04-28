"""Тесты сервиса тегов: normalize, custom, user_tags, cloud."""
from __future__ import annotations

import pytest

from bot.db.models import Deal, Feedback, FeedbackTag, Tag, User
from bot.services import tags as tags_svc
from bot.services import users


class TestNormalizeCustomTag:
    def test_simple(self) -> None:
        assert tags_svc.normalize_custom_tag("Hardwood") == "hardwood"

    def test_collapse_spaces(self) -> None:
        assert tags_svc.normalize_custom_tag("  hard   wood  ") == "hard wood"

    def test_cyrillic(self) -> None:
        assert tags_svc.normalize_custom_tag("Гипсокартон") == "гипсокартон"

    def test_with_hyphen(self) -> None:
        assert tags_svc.normalize_custom_tag("smart-home") == "smart-home"

    def test_too_short(self) -> None:
        assert tags_svc.normalize_custom_tag("a") is None

    def test_too_long(self) -> None:
        assert tags_svc.normalize_custom_tag("a" * 31) is None

    def test_emoji_rejected(self) -> None:
        assert tags_svc.normalize_custom_tag("hardwood 🔨") is None

    def test_zero_width_rejected(self) -> None:
        assert tags_svc.normalize_custom_tag("hard​wood") is None

    def test_punctuation_rejected(self) -> None:
        assert tags_svc.normalize_custom_tag("hello!") is None
        assert tags_svc.normalize_custom_tag("a;DROP TABLE") is None

    def test_empty(self) -> None:
        assert tags_svc.normalize_custom_tag("") is None
        assert tags_svc.normalize_custom_tag(None) is None


@pytest.mark.asyncio
async def test_create_custom_tag_creates_then_reuses(session) -> None:
    u = await users.upsert_user(session, tg_id=1, username="u", full_name="U")
    t1 = await tags_svc.create_custom_tag(
        session, raw_label="my skill", category="skill", created_by_user_id=u.id
    )
    assert t1 is not None
    assert t1.is_predefined is False
    assert t1.is_approved is False
    assert t1.created_by_user_id == u.id

    # Повторное создание с тем же label — реюзает существующий
    t2 = await tags_svc.create_custom_tag(
        session, raw_label="MY SKILL", category="skill", created_by_user_id=u.id
    )
    assert t2 is not None
    assert t2.id == t1.id


@pytest.mark.asyncio
async def test_custom_tag_rate_limit(session) -> None:
    u = await users.upsert_user(session, tg_id=2, username=None, full_name="U")
    for i in range(tags_svc.CUSTOM_TAG_LIMIT_PER_USER):
        t = await tags_svc.create_custom_tag(
            session,
            raw_label=f"skill {i}",
            category="skill",
            created_by_user_id=u.id,
        )
        assert t is not None
    # Сверх лимита — None
    over = await tags_svc.create_custom_tag(
        session, raw_label="extra", category="skill", created_by_user_id=u.id
    )
    assert over is None


@pytest.mark.asyncio
async def test_custom_tag_invalid_returns_none(session) -> None:
    u = await users.upsert_user(session, tg_id=3, username=None, full_name="U")
    assert (
        await tags_svc.create_custom_tag(
            session,
            raw_label="hello 🔨",
            category="skill",
            created_by_user_id=u.id,
        )
        is None
    )


@pytest.mark.asyncio
async def test_replace_user_tags_atomic(session) -> None:
    u = await users.upsert_user(session, tg_id=10, username=None, full_name="U")
    # Заводим несколько тегов
    t_primary = Tag(slug="t_primary", label_ru="A", label_en="A", category="skill")
    t_a = Tag(slug="t_a", label_ru="A2", label_en="A2", category="skill")
    t_b = Tag(slug="t_b", label_ru="B", label_en="B", category="skill")
    session.add_all([t_primary, t_a, t_b])
    await session.flush()

    await tags_svc.replace_user_tags(
        session,
        user_id=u.id,
        primary_tag_id=t_primary.id,
        secondary_tag_ids=[t_a.id, t_b.id],
    )

    user_tags = await tags_svc.get_user_tags(session, u.id)
    assert len(user_tags) == 3
    primaries = [ut for ut in user_tags if ut.is_primary]
    assert len(primaries) == 1
    assert primaries[0].tag_id == t_primary.id

    # User.primary_tag_id обновлён
    refreshed = await users.get_user(session, 10)
    assert refreshed is not None
    assert refreshed.primary_tag_id == t_primary.id


@pytest.mark.asyncio
async def test_replace_user_tags_respects_limit(session) -> None:
    u = await users.upsert_user(session, tg_id=11, username=None, full_name="U")
    # Создаём 10 тегов, попробуем все назначить — должно отсечься на 6
    tag_ids: list[int] = []
    for i in range(10):
        t = Tag(slug=f"tt_{i}", label_ru=f"T{i}", label_en=f"T{i}", category="skill")
        session.add(t)
        await session.flush()
        tag_ids.append(t.id)

    await tags_svc.replace_user_tags(
        session,
        user_id=u.id,
        primary_tag_id=tag_ids[0],
        secondary_tag_ids=tag_ids[1:],
    )
    user_tags = await tags_svc.get_user_tags(session, u.id)
    assert len(user_tags) == tags_svc.USER_TAGS_LIMIT


@pytest.mark.asyncio
async def test_feedback_tag_cloud_aggregation(session) -> None:
    u_to = await users.upsert_user(session, tg_id=20, username=None, full_name="To")
    u_a = await users.upsert_user(session, tg_id=21, username=None, full_name="A")
    u_b = await users.upsert_user(session, tg_id=22, username=None, full_name="B")
    u_c = await users.upsert_user(session, tg_id=23, username=None, full_name="C")

    # 3 разных сделки, 3 разных автора отзыва — UNIQUE (deal_id, from_user_id)
    deal_a = Deal(customer_id=u_a.id, contractor_id=u_to.id, status="closed")
    deal_b = Deal(customer_id=u_b.id, contractor_id=u_to.id, status="closed")
    deal_c = Deal(customer_id=u_c.id, contractor_id=u_to.id, status="closed")
    session.add_all([deal_a, deal_b, deal_c])
    await session.flush()

    t1 = Tag(slug="fb_pun", label_ru="Пунктуальный", label_en="Punctual",
             category="feedback_pos")
    t2 = Tag(slug="fb_qual", label_ru="Качественно", label_en="Quality",
             category="feedback_pos")
    session.add_all([t1, t2])
    await session.flush()

    # 2 отзыва с тегом "Пунктуальный", 1 — с "Качественно"
    fb_a = Feedback(deal_id=deal_a.id, from_user_id=u_a.id, to_user_id=u_to.id, rating=5)
    fb_b = Feedback(deal_id=deal_b.id, from_user_id=u_b.id, to_user_id=u_to.id, rating=5)
    fb_c = Feedback(deal_id=deal_c.id, from_user_id=u_c.id, to_user_id=u_to.id, rating=4)
    session.add_all([fb_a, fb_b, fb_c])
    await session.flush()
    session.add_all([
        FeedbackTag(feedback_id=fb_a.id, tag_id=t1.id),
        FeedbackTag(feedback_id=fb_b.id, tag_id=t1.id),
        FeedbackTag(feedback_id=fb_c.id, tag_id=t2.id),
    ])
    await session.commit()

    cloud = await tags_svc.get_feedback_tag_cloud(session, to_user_id=u_to.id)
    assert cloud[0] == ("Пунктуальный", 2)
    labels = [c[0] for c in cloud]
    assert "Качественно" in labels


def test_render_tag_cloud_empty() -> None:
    assert tags_svc.render_tag_cloud([]) == "—"


def test_render_tag_cloud_size_hints() -> None:
    out = tags_svc.render_tag_cloud([
        ("Пунктуальный", 9),
        ("Качественно", 5),
        ("Чисто", 1),
    ])
    # самый частый — UPPERCASE
    assert "ПУНКТУАЛЬНЫЙ" in out
    # средний — bold но не upper
    assert "<b>Качественно</b>" in out
    # редкий — без bold
    assert "Чисто ×1" in out
