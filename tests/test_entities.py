"""
Tests for UNION-BANK- domain entities.

Tests entity creation, enum values, defaults, and dataclass behavior
against the real dataclass field definitions in unionbank.domain.entities.
"""

from datetime import datetime
from decimal import Decimal

from unionbank.domain.entities import (
    Account,
    AccountStatus,
    AdminUser,
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
        assert TransactionType.LOAN_DISBURSEMENT.value == "LOAN_DISBURSEMENT"
        assert TransactionType.LOAN_REPAYMENT.value == "LOAN_REPAYMENT"

    def test_members(self) -> None:
        assert len(TransactionType) == 7


class TestAccount:
    """Test Account dataclass."""

    def test_create_account(self) -> None:
        account = Account(
            account_number="1234567890",
            name="Test User",
            age=30,
            gender="Male",
            mobile="9876543210",
            email="test@example.com",
            password="hashed",
            balance=Decimal("10000.00"),
        )
        assert account.account_number == "1234567890"
        assert account.name == "Test User"
        assert account.balance == Decimal("10000.00")

    def test_defaults(self) -> None:
        account = Account(account_number="1234567890", name="Test")
        assert account.balance == Decimal("0.00")
        assert account.is_active is True
        assert account.is_frozen is False
        assert account.deleted_at is None
        assert isinstance(account.created_at, datetime)
        assert isinstance(account.updated_at, datetime)

    def test_not_frozen_by_default(self) -> None:
        account = Account(account_number="1234567890", name="Test")
        assert account.is_frozen is False


class TestTransaction:
    """Test Transaction dataclass."""

    def test_create_transaction(self) -> None:
        tx = Transaction(
            txn_id="TXN001",
            account_number="1234567890",
            type=TransactionType.DEPOSIT,
            amount=Decimal("5000.00"),
            balance=Decimal("5000.00"),
            description="Test deposit",
        )
        assert tx.txn_id == "TXN001"
        assert tx.type == TransactionType.DEPOSIT
        assert tx.amount == Decimal("5000.00")

    def test_defaults(self) -> None:
        tx = Transaction(
            txn_id="TXN002",
            account_number="1234567890",
            type=TransactionType.WITHDRAW,
            amount=Decimal("100.00"),
            balance=Decimal("900.00"),
        )
        assert tx.description == ""
        assert tx.category == "General"
        assert tx.target_account is None
        assert isinstance(tx.timestamp, datetime)


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

    def test_progress_pct(self) -> None:
        goal = SavingsGoal(
            goal_id="GOAL002",
            account_number="1234567890",
            name="Car",
            target_amount=Decimal("1000.00"),
            current_amount=Decimal("250.00"),
        )
        assert goal.progress_pct == 25.0

    def test_progress_pct_zero_target(self) -> None:
        goal = SavingsGoal(
            goal_id="GOAL003",
            account_number="1234567890",
            name="Empty",
            target_amount=Decimal("0"),
            current_amount=Decimal("0"),
        )
        assert goal.progress_pct == 0.0

    def test_remaining(self) -> None:
        goal = SavingsGoal(
            goal_id="GOAL004",
            account_number="1234567890",
            name="Trip",
            target_amount=Decimal("500.00"),
            current_amount=Decimal("200.00"),
        )
        assert goal.remaining == Decimal("300.00")

    def test_remaining_never_negative(self) -> None:
        goal = SavingsGoal(
            goal_id="GOAL005",
            account_number="1234567890",
            name="Overshoot",
            target_amount=Decimal("100.00"),
            current_amount=Decimal("250.00"),
        )
        assert goal.remaining == Decimal("0.00")


class TestAdminUser:
    """Test AdminUser dataclass."""

    def test_create_admin(self) -> None:
        admin = AdminUser(username="admin", password="hashed", role="admin")
        assert admin.username == "admin"
        assert admin.role == "admin"
        assert admin.totp_enabled is False

    def test_repr(self) -> None:
        admin = AdminUser(username="boss")
        assert "boss" in repr(admin)


class TestNotification:
    """Test Notification dataclass."""

    def test_create_notification(self) -> None:
        notif = Notification(
            notif_id="NTF001",
            account_number="1234567890",
            type="deposit",
            title="Deposit received",
            message="Your transfer was successful",
        )
        assert notif.notif_id == "NTF001"
        assert notif.is_read is False
        assert notif.message == "Your transfer was successful"

    def test_defaults(self) -> None:
        notif = Notification(
            notif_id="NTF002",
            account_number="1234567890",
            type="withdraw",
            title="Withdrawal",
            message="Money out",
        )
        assert notif.is_read is False
        assert notif.related_txn_id is None
        assert isinstance(notif.created_at, datetime)


class TestLoginAttempt:
    """Test LoginAttempt dataclass."""

    def test_create_attempt(self) -> None:
        attempt = LoginAttempt(key="1000000001", count=1)
        assert attempt.key == "1000000001"
        assert attempt.count == 1
        assert attempt.lockout_until is None

    def test_defaults(self) -> None:
        attempt = LoginAttempt(key="1000000002")
        assert attempt.count == 0
        assert attempt.first_failed is None
        assert isinstance(attempt.updated_at, datetime)
