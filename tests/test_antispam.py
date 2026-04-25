"""Тесты антиспам-детекторов."""
from __future__ import annotations

import pytest

from bot.services import antispam


class TestContainsLink:
    @pytest.mark.parametrize(
        "text",
        [
            "Заходи https://example.com",
            "Смотри http://t.me/foo",
            "www.site.ru — огонь",
            "пиши t.me/chan",
            "tg://resolve?domain=foo",
        ],
    )
    def test_detects_links(self, text: str) -> None:
        assert antispam.contains_link(text) is True

    @pytest.mark.parametrize(
        "text",
        ["", "просто текст", "никаких ссылок тут", "com. не ссылка."],
    )
    def test_no_false_positives(self, text: str) -> None:
        assert antispam.contains_link(text) is False


class TestContainsStopword:
    def test_detects_default(self) -> None:
        assert antispam.contains_stopword("Переходи на КАЗИНО ОНЛАЙН сейчас") is True

    def test_empty(self) -> None:
        assert antispam.contains_stopword("") is False

    def test_clean(self) -> None:
        assert antispam.contains_stopword("Привет, как дела") is False

    def test_custom_stopwords(self) -> None:
        assert antispam.contains_stopword("срочно деньги", {"деньги"}) is True


class TestRateLimiter:
    def test_below_limit(self) -> None:
        rl = antispam.RateLimiter(max_msgs=3, window_sec=10)
        assert rl.hit(1, now=0) is False
        assert rl.hit(1, now=1) is False
        assert rl.hit(1, now=2) is False  # 3-е, ещё не превышено

    def test_triggers(self) -> None:
        rl = antispam.RateLimiter(max_msgs=3, window_sec=10)
        rl.hit(1, now=0)
        rl.hit(1, now=1)
        rl.hit(1, now=2)
        assert rl.hit(1, now=3) is True  # 4-е в окне

    def test_window_slides(self) -> None:
        rl = antispam.RateLimiter(max_msgs=2, window_sec=10)
        rl.hit(1, now=0)
        rl.hit(1, now=1)
        # через 20 сек окно чистое
        assert rl.hit(1, now=20) is False

    def test_per_user_isolation(self) -> None:
        rl = antispam.RateLimiter(max_msgs=1, window_sec=10)
        assert rl.hit(1, now=0) is False
        assert rl.hit(2, now=0) is False  # другой пользователь — не влияет
        assert rl.hit(1, now=1) is True
