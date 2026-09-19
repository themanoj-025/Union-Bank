"""Extended tests for UNION-BANK- domain entities and utils."""

from __future__ import annotations

from decimal import Decimal

import pytest

from unionbank.domain.entities import Account
from datetime import UTC

pytestmark = pytest.mark.integration


class TestAccountEntity:
    """Tests for domain Account entity."""

    def test_account_creation(self) -> None:
        acc = Account(
            account_number="1234567890",
            name="John Doe",
            email="john@test.com",
            balance=Decimal("1000.00"),
        )
        assert acc.account_number == "1234567890"
        assert acc.balance == Decimal("1000.00")

    def test_account_defaults(self) -> None:
        acc = Account(account_number="123", name="Test")
        assert acc.balance == Decimal("0.00")
        assert acc.is_active is True
        assert acc.is_frozen is False
        assert acc.deleted_at is None

    def test_account_status_active(self) -> None:
        acc = Account(account_number="123", name="Test")
        assert acc.status.value == "active"
        assert acc.can_transact is True

    def test_account_status_frozen(self) -> None:
        acc = Account(account_number="123", name="Test", is_frozen=True)
        assert acc.status.value == "frozen"
        assert acc.can_transact is False

    def test_account_status_closed(self) -> None:
        acc = Account(account_number="123", name="Test", is_active=False)
        assert acc.status.value == "closed"
        assert acc.can_transact is False

    def test_account_is_deleted(self) -> None:
        from datetime import datetime

        acc = Account(account_number="123", name="Test")
        assert acc.is_deleted is False
        acc.deleted_at = datetime.now(UTC)
        assert acc.is_deleted is True

    def test_account_repr(self) -> None:
        acc = Account(account_number="1234567890", name="Jane")
        assert "1234567890" in repr(acc)
        assert "Jane" in repr(acc)


class TestValidation:
    """Tests for UNION-BANK- validation utils."""

    def test_validate_email_valid(self) -> None:
        from unionbank.utils.validation import validate_email

        assert validate_email("test@example.com") is True

    def test_validate_email_invalid(self) -> None:
        from unionbank.utils.validation import validate_email

        assert validate_email("not-an-email") is False

    def test_validate_name_valid(self) -> None:
        from unionbank.utils.validation import validate_name

        assert validate_name("John Doe") is True

    def test_validate_name_invalid(self) -> None:
        from unionbank.utils.validation import validate_name

        assert validate_name("") is False


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
    """Tests for the function-based session rate-limiting utils."""

    def test_session_active_recently(self) -> None:
        import time

        from unionbank.utils.rate_limit import check_session_timeout

        assert check_session_timeout(time.time()) is True

    def test_session_expired(self) -> None:
        import time

        from unionbank.utils.rate_limit import (
            SESSION_TIMEOUT_SECONDS,
            check_session_timeout,
        )

        past_time = time.time() - SESSION_TIMEOUT_SECONDS - 10
        assert check_session_timeout(past_time) is False

    def test_session_timeout_constant(self) -> None:
        from unionbank.utils.rate_limit import (
            SESSION_TIMEOUT_SECONDS,
            get_session_timeout_seconds,
        )

        assert get_session_timeout_seconds() == SESSION_TIMEOUT_SECONDS
        assert isinstance(SESSION_TIMEOUT_SECONDS, int)
        assert SESSION_TIMEOUT_SECONDS > 0


class TestFormatting:
    """Tests for formatting utils."""

    def test_fmt_currency(self) -> None:
        from unionbank.utils.formatting import fmt_currency

        result = fmt_currency(1234.56)
        assert "₹" in result
        assert "1,234.56" in result

    def test_now_str(self) -> None:
        from unionbank.utils.formatting import now_str

        result = now_str()
        assert result is not None
        assert isinstance(result, str)
        assert "-" in result

    def test_mask_account_number(self) -> None:
        from unionbank.utils.formatting import mask_account_number

        masked = mask_account_number("1234567890")
        assert masked != "1234567890"
        assert "1234567890" not in masked
