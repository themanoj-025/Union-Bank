"""Extended tests for UNION-BANK- domain entities and utils."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.integration



class TestAccountEntity:
    """Tests for domain Account entity."""

    def test_account_creation(self) -> None:
        from unionbank.domain.entities import Account

        acc = Account(
            account_number="1234567890",
            name="John Doe",
            email="john@test.com",
            balance=1000.0,
        )
        assert acc.account_number == "1234567890"
        assert acc.balance == 1000.0

    def test_account_debit(self) -> None:
        from unionbank.domain.entities import Account

        acc = Account(account_number="123", name="Test", email="t@t.com", balance=1000.0)
        acc.debit(200.0)
        assert acc.balance == 800.0

    def test_account_credit(self) -> None:
        from unionbank.domain.entities import Account

        acc = Account(account_number="123", name="Test", email="t@t.com", balance=1000.0)
        acc.credit(500.0)
        assert acc.balance == 1500.0

    def test_account_insufficient_funds(self) -> None:
        from unionbank.domain.entities import Account

        acc = Account(account_number="123", name="Test", email="t@t.com", balance=100.0)
        with pytest.raises((ValueError, RuntimeError)):
            acc.debit(200.0)


class TestValidation:
    """Tests for UNION-BANK- validation utils."""

    def test_validate_email_valid(self) -> None:
        from unionbank.utils.validation import validate_email

        assert validate_email("test@example.com") is True

    def test_validate_email_invalid(self) -> None:
        from unionbank.utils.validation import validate_email

        assert validate_email("not-an-email") is False

    def test_validate_account_number(self) -> None:
        from unionbank.utils.validation import validate_account_number

        assert validate_account_number("1234567890") is True

    def test_validate_amount_positive(self) -> None:
        from unionbank.utils.validation import validate_amount

        assert validate_amount("100.50") is True

    def test_validate_amount_negative(self) -> None:
        from unionbank.utils.validation import validate_amount

        assert validate_amount("-50") is False


class TestHashing:
    """Tests for UNION-BANK- hashing utils."""

    def test_hash_password(self) -> None:
        from unionbank.utils.hashing import hash_password

        h = hash_password("test123")
        assert h != "test123"
        assert len(h) > 0

    def test_verify_password_correct(self) -> None:
        from unionbank.utils.hashing import hash_password, verify_password

        h = hash_password("mypassword")
        assert verify_password("mypassword", h) is True

    def test_verify_password_wrong(self) -> None:
        from unionbank.utils.hashing import hash_password, verify_password

        h = hash_password("mypassword")
        assert verify_password("wrong", h) is False


class TestRateLimit:
    """Tests for rate limiting utils."""

    def test_rate_limiter_basic(self) -> None:
        from unionbank.utils.rate_limit import RateLimiter

        rl = RateLimiter(max_requests=5, window_seconds=60)
        for _ in range(5):
            assert rl.allow("user1") is True
        assert rl.allow("user1") is False

    def test_rate_limiter_different_users(self) -> None:
        from unionbank.utils.rate_limit import RateLimiter

        rl = RateLimiter(max_requests=1, window_seconds=60)
        assert rl.allow("user1") is True
        assert rl.allow("user2") is True
        assert rl.allow("user1") is False


class TestFormatting:
    """Tests for formatting utils."""

    def test_format_currency(self) -> None:
        from unionbank.utils.formatting import format_currency

        result = format_currency(1234.56)
        assert "1" in result or "1234" in result

    def test_format_date(self) -> None:
        from unionbank.utils.formatting import format_date

        result = format_date("2024-01-15T10:30:00")
        assert result is not None
