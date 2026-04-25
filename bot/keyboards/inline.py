"""Inline-клавиатуры."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot import texts


def captcha_kb(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура капчи — user_id зашит в callback_data для проверки."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts.CAPTCHA_BUTTON,
                    callback_data=f"captcha:{user_id}",
                )
            ]
        ]
    )
