"""Хранилище активных капч в памяти."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class PendingCaptcha:
    user_id: int
    chat_id: int
    message_id: int
    task: asyncio.Task | None = field(default=None)


class CaptchaStore:
    """Потокобезопасное хранилище pending-капч."""

    def __init__(self) -> None:
        self._store: Dict[tuple[int, int], PendingCaptcha] = {}
        self._lock = asyncio.Lock()

    async def add(self, chat_id: int, user_id: int, captcha: PendingCaptcha) -> None:
        async with self._lock:
            self._store[(chat_id, user_id)] = captcha

    async def pop(self, chat_id: int, user_id: int) -> PendingCaptcha | None:
        async with self._lock:
            return self._store.pop((chat_id, user_id), None)

    async def has(self, chat_id: int, user_id: int) -> bool:
        async with self._lock:
            return (chat_id, user_id) in self._store


captcha_store = CaptchaStore()
