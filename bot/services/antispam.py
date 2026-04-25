"""Антиспам-детекторы: ссылки, rate limit, стоп-слова."""
from __future__ import annotations

import re
import time
from collections import defaultdict, deque
from typing import Deque, Dict

LINK_RE = re.compile(
    r"(https?://|www\.|t\.me/|telegram\.me/|tg://)",
    re.IGNORECASE,
)

# Базовый словарь — расширяется через admin-команды или конфиг
DEFAULT_STOPWORDS: set[str] = {
    "crypto scam",
    "казино онлайн",
    "заработок в интернете",
    "инвестиции гарантия",
}


def contains_link(text: str) -> bool:
    if not text:
        return False
    return bool(LINK_RE.search(text))


def contains_stopword(text: str, stopwords: set[str] | None = None) -> bool:
    if not text:
        return False
    words = (stopwords or DEFAULT_STOPWORDS)
    low = text.lower()
    return any(sw in low for sw in words)


class RateLimiter:
    """Скользящее окно: макс N сообщений за W секунд."""

    def __init__(self, max_msgs: int, window_sec: int) -> None:
        self.max_msgs = max_msgs
        self.window_sec = window_sec
        self._history: Dict[int, Deque[float]] = defaultdict(deque)

    def hit(self, user_id: int, now: float | None = None) -> bool:
        """Регистрирует сообщение. Возвращает True, если лимит превышен."""
        now = now if now is not None else time.monotonic()
        dq = self._history[user_id]
        cutoff = now - self.window_sec
        while dq and dq[0] < cutoff:
            dq.popleft()
        dq.append(now)
        return len(dq) > self.max_msgs

    def reset(self, user_id: int) -> None:
        self._history.pop(user_id, None)
