"""
Tests for UNION-BANK- domain entities.

Tests entity creation, enum values, and dataclass behavior.
"""

from datetime import datetime
from decimal import Decimal

from unionbank.domain.entities import (
    Account,
    AccountStatus,
    LoginAttempt,
    Notification,
    SavingsGoal,
    Transaction,
    TransactionType,
)


class TestAccountStatus:
    """Test AccountStatus enum."""

    def test_values(self) -> None:
        assert AccountStatus.ACTIVE.value == "active"
        assert AccountStatus.FROZEN.value == "frozen"
        assert AccountStatus.CLOSED.value == "closed"

    def test_members(self) -> None:
        assert len(AccountStatus) == 3


class TestTransactionType:
    """Test TransactionType enum."""

    def test_values(self) -> None:
        assert TransactionType.DEPOSIT.value == "DEPOSIT"
        assert TransactionType.WITHDRAW.value == "WITHDRAW"
        assert TransactionType.TRANSFER_OUT.value == "TRANSFER_OUT"
        assert TransactionType.TRANSFER_IN.value == "TRANSFER_IN"
        assert TransactionType.INTEREST.value == "INTEREST"

    def test_members(self) -> None:
        assert len(TransactionType) == 7


class TestAccount:
    """Test Account dataclass."""

    def test_create_account(self) -> None:
        account = Account(
            account_number="1234567890",
            holder_name="Test User",
            balance=Decimal("10000.00"),
            status=AccountStatus.ACTIVE,
            pin_hash="hashed_pin",
        )
        assert account.account_number == "1234567890"
        assert account.balance == Decimal("10000.00")

    def test_account_status_active(self) -> None:
        account = Account(
            account_number="1234567890",
            holder_name="Test",
            balance=Decimal("0"),
            status=AccountStatus.ACTIVE,
            pin_hash="h",
        )
        assert account.status == AccountStatus.ACTIVE


class TestTransaction:
    """Test Transaction dataclass."""

    def test_create_transaction(self) -> None:
        tx = Transaction(
            tx_id="TXN001",
            account_number="1234567890",
            tx_type=TransactionType.DEPOSIT,
            amount=Decimal("5000.00"),
            timestamp=datetime.now(),
            description="Test deposit",
        )
        assert tx.tx_type == TransactionType.DEPOSIT
        assert tx.amount == Decimal("5000.00")


class TestSavingsGoal:
    """Test SavingsGoal dataclass."""

    def test_create_goal(self) -> None:
        goal = SavingsGoal(
            goal_id="GOAL001",
            account_number="1234567890",
            name="Emergency Fund",
            target_amount=Decimal("100000.00"),
            current_amount=Decimal("25000.00"),
        )
        assert goal.target_amount == Decimal("100000.00")
        assert goal.current_amount == Decimal("25000.00")


class TestNotification:
    """Test Notification dataclass."""

    def test_create_notification(self) -> None:
        notif = Notification(
            notification_id="NOTIF001",
            account_number="1234567890",
            message="Your transfer was successful",
            read=False,
        )
        assert notif.read is False


class TestLoginAttempt:
    """Test LoginAttempt dataclass."""

    def test_create_attempt(self) -> None:
        attempt = LoginAttempt(
            attempt_id="ATT001",
            account_number="1234567890",
            success=True,
            timestamp=datetime.now(),
        )
        assert attempt.success is True
