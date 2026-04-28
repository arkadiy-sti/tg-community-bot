"""Тесты нормализации телефонов и email."""
from __future__ import annotations

import pytest

from bot.services import phones


class TestNormalizePhone:
    def test_us_10_digits(self) -> None:
        assert phones.normalize_phone("2125551234") == "+12125551234"

    def test_us_with_country_code(self) -> None:
        assert phones.normalize_phone("+12125551234") == "+12125551234"

    def test_us_with_formatting(self) -> None:
        assert phones.normalize_phone("(212) 555-1234") == "+12125551234"

    def test_us_with_dashes(self) -> None:
        assert phones.normalize_phone("212-555-1234") == "+12125551234"

    def test_empty(self) -> None:
        assert phones.normalize_phone("") is None
        assert phones.normalize_phone(None) is None

    def test_too_short(self) -> None:
        assert phones.normalize_phone("12345") is None

    def test_only_letters(self) -> None:
        assert phones.normalize_phone("hello world") is None

    def test_invalid_us_area(self) -> None:
        # area code 0xx невалиден
        assert phones.normalize_phone("0125551234") is None


class TestFormatPhoneForDisplay:
    def test_dash(self) -> None:
        assert phones.format_phone_for_display(None) == "—"

    def test_e164_to_intl(self) -> None:
        out = phones.format_phone_for_display("+12125551234")
        assert "212" in out and "555" in out


class TestValidateEmail:
    def test_valid(self) -> None:
        assert phones.validate_email("Test@Example.COM") == "test@example.com"

    def test_invalid_no_at(self) -> None:
        assert phones.validate_email("notanemail") is None

    def test_invalid_double_at(self) -> None:
        assert phones.validate_email("a@@b.com") is None

    def test_empty(self) -> None:
        assert phones.validate_email("") is None
        assert phones.validate_email(None) is None

    def test_too_long(self) -> None:
        long = ("a" * 250) + "@example.com"
        assert phones.validate_email(long) is None
