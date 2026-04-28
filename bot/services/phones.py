"""Нормализация и валидация контактов: phone, whatsapp, email.

Все номера хранятся в БД в формате E.164 (`+12125551234`).
Пользователь вводит 10 цифр — мы дополняем регионом (US по умолчанию).
"""
from __future__ import annotations

import logging
import re

import phonenumbers
from email_validator import EmailNotValidError, validate_email as _validate_email

log = logging.getLogger(__name__)

DEFAULT_REGION = "US"
PHONE_MAX_LEN = 16  # E.164 верхний предел (+ и до 15 цифр)
EMAIL_MAX_LEN = 254


def normalize_phone(raw: str | None, region: str = DEFAULT_REGION) -> str | None:
    """Привести введённый телефон к E.164. None если невалидно/пусто.

    Принимает любой ввод: '2125551234', '+1 212 555 1234', '(212) 555-1234'.
    Возвращает '+12125551234' или None.
    """
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None
    # Если есть знак + в исходнике — парсим как international
    candidate = ("+" + digits) if raw.lstrip().startswith("+") else digits
    try:
        parsed = phonenumbers.parse(candidate, region)
    except phonenumbers.NumberParseException as e:
        log.debug("phone parse failed: %s (raw=%r)", e, raw)
        return None
    if not phonenumbers.is_valid_number(parsed):
        return None
    e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    if len(e164) > PHONE_MAX_LEN:
        return None
    return e164


def format_phone_for_display(e164: str | None) -> str:
    """Из '+12125551234' вернуть '+1 (212) 555-1234' для UI."""
    if not e164:
        return "—"
    try:
        parsed = phonenumbers.parse(e164, None)
    except phonenumbers.NumberParseException:
        return e164
    return phonenumbers.format_number(
        parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL
    )


def validate_email(raw: str | None) -> str | None:
    """Вернуть нормализованный email (lowercase) или None."""
    if not raw:
        return None
    raw = raw.strip()
    if len(raw) > EMAIL_MAX_LEN:
        return None
    try:
        # check_deliverability=False — без MX-чека (медленно для UX FSM)
        result = _validate_email(raw, check_deliverability=False)
    except EmailNotValidError as e:
        log.debug("email invalid: %s (raw=%r)", e, raw)
        return None
    return result.normalized.lower()
