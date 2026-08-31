"""Tests for UNION-BANK- input validation helpers."""

import pytest

from unionbank.utils.validation import (
    validate_email,
    validate_name,
    validate_password,
    validate_phone,
)


class TestValidateEmail:
    """Tests for email validation."""

    def test_valid_email(self) -> None:
        assert validate_email("user@example.com") is True

    def test_valid_with_dots(self) -> None:
        assert validate_email("first.last@example.com") is True

    def test_valid_with_plus(self) -> None:
        assert validate_email("user+tag@example.com") is True

    def test_valid_with_subdomain(self) -> None:
        assert validate_email("user@mail.example.co.uk") is True

    def test_invalid_no_at(self) -> None:
        assert validate_email("userexample.com") is False

    def test_invalid_no_domain(self) -> None:
        assert validate_email("user@") is False

    def test_invalid_no_tld(self) -> None:
        assert validate_email("user@example") is False

    def test_empty_string(self) -> None:
        assert validate_email("") is False

    def test_whitespace_stripped(self) -> None:
        assert validate_email("  user@example.com  ") is True


class TestValidatePhone:
    """Tests for Indian phone number validation."""

    def test_valid_6_prefix(self) -> None:
        assert validate_phone("6123456789") is True

    def test_valid_9_prefix(self) -> None:
        assert validate_phone("9876543210") is True

    def test_invalid_short(self) -> None:
        assert validate_phone("987654321") is False

    def test_invalid_long(self) -> None:
        assert validate_phone("98765432101") is False

    def test_invalid_starts_with_5(self) -> None:
        assert validate_phone("5123456789") is False

    def test_invalid_letters(self) -> None:
        assert validate_phone("abcdefghij") is False

    def test_empty(self) -> None:
        assert validate_phone("") is False


class TestValidatePassword:
    """Tests for password strength validation."""

    def test_valid_strong_password(self) -> None:
        valid, msg = validate_password("MyStr0ng!")
        assert valid is True
        assert msg == ""

    def test_valid_minimal(self) -> None:
        valid, _ = validate_password("Abcdef1g")
        assert valid is True

    def test_too_short(self) -> None:
        valid, msg = validate_password("Ab1")
        assert valid is False
        assert "8 characters" in msg

    def test_no_uppercase(self) -> None:
        valid, msg = validate_password("abcdefg1")
        assert valid is False
        assert "uppercase" in msg

    def test_no_lowercase(self) -> None:
        valid, msg = validate_password("ABCDEFG1")
        assert valid is False
        assert "lowercase" in msg

    def test_no_digit(self) -> None:
        valid, msg = validate_password("Abcdefgh")
        assert valid is False
        assert "digit" in msg


class TestValidateName:
    """Tests for name validation."""

    def test_valid_name(self) -> None:
        assert validate_name("John Doe") is True

    def test_valid_single_name(self) -> None:
        assert validate_name("Raj") is True

    def test_valid_with_dot(self) -> None:
        assert validate_name("Dr. Smith") is True

    def test_empty_name(self) -> None:
        assert validate_name("") is False

    def test_whitespace_only(self) -> None:
        assert validate_name("   ") is False

    def test_too_short(self) -> None:
        assert validate_name("A") is False

    def test_invalid_characters(self) -> None:
        assert validate_name("John123") is False

    def test_too_long(self) -> None:
        assert validate_name("A" * 51) is False
