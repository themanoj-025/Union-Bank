"""Tests for utility functions — formatting, hashing, categories, rate limiting."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow


class TestFormatting:
    """Test formatting utility functions."""

    def test_fmt_currency(self) -> None:
        from unionbank.utils.formatting import fmt_currency
        result = fmt_currency(100000.0)
        assert "100,000" in result or "100000" in result

    def test_fmt_currency_zero(self) -> None:
        from unionbank.utils.formatting import fmt_currency
        result = fmt_currency(0.0)
        assert "0" in result

    def test_generate_transaction_id(self) -> None:
        from unionbank.utils.formatting import generate_transaction_id
        txn_id = generate_transaction_id()
        assert txn_id.startswith("TXN")

    def test_generate_loan_id(self) -> None:
        from unionbank.utils.formatting import generate_loan_id
        loan_id = generate_loan_id()
        assert loan_id.startswith("LOAN")

    def test_generate_goal_id(self) -> None:
        from unionbank.utils.formatting import generate_goal_id
        goal_id = generate_goal_id()
        assert goal_id.startswith("GOAL")

    def test_generate_notification_id(self) -> None:
        from unionbank.utils.formatting import generate_notification_id
        notif_id = generate_notification_id()
        assert notif_id.startswith("NOTIF")

    def test_calculate_emi(self) -> None:
        from unionbank.utils.formatting import calculate_emi
        emi = calculate_emi(100000, 12.0, 24)
        assert emi > 0
        assert isinstance(emi, float)


class TestHashing:
    """Test hashing utility functions."""

    def test_hash_password(self) -> None:
        from unionbank.utils.hashing import hash_password
        hashed = hash_password("Secure1Pass")
        assert hashed != "Secure1Pass"
        assert len(hashed) > 0

    def test_verify_password_correct(self) -> None:
        from unionbank.utils.hashing import hash_password, verify_password
        hashed = hash_password("Secure1Pass")
        assert verify_password("Secure1Pass", hashed) is True

    def test_verify_password_wrong(self) -> None:
        from unionbank.utils.hashing import hash_password, verify_password
        hashed = hash_password("Secure1Pass")
        assert verify_password("Wrong1Pass", hashed) is False


class TestCategories:
    """Test transaction categories."""

    def test_categories_defined(self) -> None:
        from unionbank.utils.categories import TRANSACTION_CATEGORIES
        assert len(TRANSACTION_CATEGORIES) > 0
        assert "General" in TRANSACTION_CATEGORIES


class TestValidation:
    """Test input validation functions."""

    def test_validate_email_valid(self) -> None:
        from unionbank.utils.validation import validate_email
        assert validate_email("user@example.com") is True

    def test_validate_email_invalid(self) -> None:
        from unionbank.utils.validation import validate_email
        assert validate_email("invalid") is False

    def test_validate_phone_valid(self) -> None:
        from unionbank.utils.validation import validate_phone
        assert validate_phone("9876543210") is True

    def test_validate_phone_invalid(self) -> None:
        from unionbank.utils.validation import validate_phone
        assert validate_phone("12345") is False

    def test_validate_password_valid(self) -> None:
        from unionbank.utils.validation import validate_password
        is_valid, msg = validate_password("Secure1Pass")
        assert is_valid is True
        assert msg == ""

    def test_validate_password_too_short(self) -> None:
        from unionbank.utils.validation import validate_password
        is_valid, msg = validate_password("Short1")
        assert is_valid is False
        assert "8 characters" in msg

    def test_validate_name_valid(self) -> None:
        from unionbank.utils.validation import validate_name
        assert validate_name("John Doe") is True

    def test_validate_name_invalid(self) -> None:
        from unionbank.utils.validation import validate_name
        assert validate_name("") is False
        assert validate_name("J") is False


class TestRateLimiting:
    """Test rate limiting utilities."""

    def test_rate_limit_module_importable(self) -> None:
        import unionbank.utils.rate_limit as mod
        assert hasattr(mod, "__file__")

    def test_account_rate_limit_module_importable(self) -> None:
        import unionbank.utils.account_rate_limit as mod
        assert hasattr(mod, "__file__")


class TestTokenSecurity:
    """Test token security utilities."""

    def test_token_security_module_importable(self) -> None:
        import unionbank.utils.token_security as mod
        assert hasattr(mod, "__file__")


class TestCookieAuth:
    """Test cookie authentication utilities."""

    def test_cookie_auth_module_importable(self) -> None:
        import unionbank.utils.cookie_auth as mod
        assert hasattr(mod, "__file__")
