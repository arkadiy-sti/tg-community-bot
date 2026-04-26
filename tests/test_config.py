"""Тесты парсинга конфигурации."""
from __future__ import annotations

import os

from bot.config import Settings


def test_admin_ids_from_csv_string(monkeypatch) -> None:
    monkeypatch.setenv("BOT_TOKEN", "x:y")
    monkeypatch.setenv("ADMIN_IDS", "111, 222 ,333")
    s = Settings()  # type: ignore[call-arg]
    assert s.admin_ids == [111, 222, 333]


def test_empty_admin_ids(monkeypatch) -> None:
    monkeypatch.setenv("BOT_TOKEN", "x:y")
    monkeypatch.setenv("ADMIN_IDS", "")
    s = Settings()  # type: ignore[call-arg]
    assert s.admin_ids == []


def test_main_chat_optional(monkeypatch) -> None:
    monkeypatch.setenv("BOT_TOKEN", "x:y")
    monkeypatch.setenv("ADMIN_IDS", "1")
    monkeypatch.delenv("MAIN_CHAT_ID", raising=False)
    s = Settings()  # type: ignore[call-arg]
    assert s.main_chat_id is None


def test_admin_ids_single_number(monkeypatch) -> None:
    """ADMIN_IDS=125293998 без запятой — pydantic-settings отдаёт int, валидатор оборачивает в [int]."""
    monkeypatch.setenv("BOT_TOKEN", "x:y")
    monkeypatch.setenv("ADMIN_IDS", "125293998")
    s = Settings()  # type: ignore[call-arg]
    assert s.admin_ids == [125293998]
