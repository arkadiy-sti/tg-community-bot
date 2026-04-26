"""Конфигурация бота — читается из .env через pydantic-settings.

Один процесс — один токен. Для dev/prod держим два .env файла
(.env.prod и .env.dev) и указываем нужный через переменную ENV_FILE
в systemd-юните.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Telegram ---
    bot_token: str = Field(..., alias="BOT_TOKEN")
    # Сырая строка: "1,2,3" или "1" — pydantic-settings не пытается JSON-парсить.
    # Список int отдаётся через property admin_ids ниже.
    admin_ids_raw: str = Field(default="", alias="ADMIN_IDS")
    main_chat_id: int | None = Field(default=None, alias="MAIN_CHAT_ID")
    channel_id: int | None = Field(default=None, alias="CHANNEL_ID")

    # --- Профиль запуска: "prod" или "dev". Меняет, например, куда писать
    # одобренные объявления (в канал или в личку админу). Лежит в .env.dev = "dev".
    profile: str = Field(default="prod", alias="BOT_PROFILE")

    # --- Локализация ---
    default_lang: str = Field(default="ru", alias="DEFAULT_LANG")

    # --- БД ---
    db_url: str = Field(
        default="sqlite+aiosqlite:///data/bot.db", alias="DB_URL"
    )

    # --- Параметры антиспама / капчи ---
    captcha_timeout_sec: int = Field(default=60, alias="CAPTCHA_TIMEOUT_SEC")
    rate_limit_msgs: int = Field(default=5, alias="RATE_LIMIT_MSGS")
    rate_limit_window_sec: int = Field(default=10, alias="RATE_LIMIT_WINDOW_SEC")
    new_user_hours: int = Field(default=24, alias="NEW_USER_HOURS")
    max_warnings: int = Field(default=3, alias="MAX_WARNINGS")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @field_validator("main_chat_id", "channel_id", mode="before")
    @classmethod
    def _parse_chat(cls, v):
        if v is None or v == "":
            return None
        return int(v)

    @property
    def admin_ids(self) -> List[int]:
        """ID админов из ENV (CSV или одно число). Возвращает [] если пусто."""
        raw = (self.admin_ids_raw or "").strip()
        if not raw:
            return []
        result: List[int] = []
        for chunk in raw.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            try:
                result.append(int(chunk))
            except ValueError:
                continue
        return result

    @property
    def is_dev(self) -> bool:
        return self.profile.lower() == "dev"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
