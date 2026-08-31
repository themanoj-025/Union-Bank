"""Tests for unionbank.domain.entities — all domain dataclasses."""

from datetime import datetime, timedelta, UTC
from decimal import Decimal

from unionbank.domain.entities import (
    Account,
    AccountStatus,
    AdminUser,
    IdempotencyRecord,
    Loan,
    LoanStatus,
    LoginAttempt,
    Notification,
    NotificationPreference,
    RefreshToken,
    SavingsGoal,
    ServiceResult,
    TokenVersion,
    Transaction,
    TransactionType,
    TransferResult,
)


class TestAccountStatus:
    def test_values(self) -> None:
        assert AccountStatus.ACTIVE.value == "active"
        assert AccountStatus.FROZEN.value == "frozen"
        assert AccountStatus.CLOSED.value == "closed"


class TestTransactionType:
    def test_values(self) -> None:
        assert TransactionType.DEPOSIT.value == "DEPOSIT"
        assert TransactionType.TRANSFER_OUT.value == "TRANSFER_OUT"
        assert len(TransactionType) == 7


class TestLoanStatus:
    def test_values(self) -> None:
        assert LoanStatus.PENDING.value == "PENDING"
        assert LoanStatus.ACTIVE.value == "ACTIVE"
        assert len(LoanStatus) == 5


class TestAccount:
    def test_default_account(self) -> None:
        a = Account(account_number="1234567890", name="John")
        assert a.balance == Decimal("0.00")
        assert a.is_active is True
        assert a.is_frozen is False
        assert a.is_deleted is False
        assert a.status == AccountStatus.ACTIVE
        assert a.can_transact is True

    def test_frozen_account(self) -> None:
        a = Account(account_number="123", name="J", is_frozen=True)
        assert a.status == AccountStatus.FROZEN
        assert a.can_transact is False

    def test_closed_account(self) -> None:
        a = Account(account_number="123", name="J", is_active=False)
        assert a.status == AccountStatus.CLOSED
        assert a.can_transact is False

    def test_deleted_account(self) -> None:
        a = Account(account_number="123", name="J", deleted_at=datetime.now(UTC))
        assert a.is_deleted is True

    def test_repr(self) -> None:
        a = Account(account_number="123", name="John")
        assert "123" in repr(a)
        assert "John" in repr(a)


class TestTransaction:
    def test_create_transaction(self) -> None:
        t = Transaction(
            txn_id="TXN001", account_number="123",
            type=TransactionType.DEPOSIT,
            amount=Decimal("1000"), balance=Decimal("5000"),
        )
        assert t.amount == Decimal("1000")
        assert t.category == "General"

    def test_repr(self) -> None:
        t = Transaction(
            txn_id="TXN001", account_number="123",
            type=TransactionType.WITHDRAW,
            amount=Decimal("500"), balance=Decimal("4500"),
        )
        assert "TXN001" in repr(t)


class TestSavingsGoal:
    def test_progress_pct(self) -> None:
        g = SavingsGoal(
            goal_id="G001", account_number="123",
            name="Emergency", target_amount=Decimal("10000"),
            current_amount=Decimal("5000"),
        )
        assert g.progress_pct == 50.0

    def test_progress_zero_target(self) -> None:
        g = SavingsGoal(
            goal_id="G001", account_number="123",
            name="X", target_amount=Decimal("0"),
        )
        assert g.progress_pct == 0.0

    def test_remaining(self) -> None:
        g = SavingsGoal(
            goal_id="G001", account_number="123",
            name="X", target_amount=Decimal("10000"),
            current_amount=Decimal("3000"),
        )
        assert g.remaining == Decimal("7000")

    def test_remaining_overfunded(self) -> None:
        g = SavingsGoal(
            goal_id="G001", account_number="123",
            name="X", target_amount=Decimal("10000"),
            current_amount=Decimal("15000"),
        )
        assert g.remaining == Decimal("0.00")


class TestLoan:
    def test_progress_pct(self) -> None:
        loan = Loan(
            loan_id="L001", account_number="123",
            loan_type="Personal", principal_amount=Decimal("100000"),
            interest_rate=Decimal("10"), tenure_months=12,
            emi_amount=Decimal("8792"), amount_paid=Decimal("50000"),
            remaining_amount=Decimal("50000"),
        )
        assert loan.progress_pct == 50.0

    def test_remaining_emis(self) -> None:
        loan = Loan(
            loan_id="L001", account_number="123",
            loan_type="Personal", principal_amount=Decimal("100000"),
            interest_rate=Decimal("10"), tenure_months=12,
            emi_amount=Decimal("8792"), remaining_amount=Decimal("17584"),
        )
        assert loan.remaining_emis == 2

    def test_is_active(self) -> None:
        loan = Loan(
            loan_id="L001", account_number="123",
            loan_type="Personal", principal_amount=Decimal("100000"),
            interest_rate=Decimal("10"), tenure_months=12,
            emi_amount=Decimal("8792"), status=LoanStatus.ACTIVE.value,
        )
        assert loan.is_active is True

    def test_is_not_active_pending(self) -> None:
        loan = Loan(
            loan_id="L001", account_number="123",
            loan_type="Personal", principal_amount=Decimal("100000"),
            interest_rate=Decimal("10"), tenure_months=12,
            emi_amount=Decimal("8792"), status=LoanStatus.PENDING.value,
        )
        assert loan.is_active is False


class TestRefreshToken:
    def test_valid_token(self) -> None:
        rt = RefreshToken(
            token_id="T001", account_number="123",
            role="customer",
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        assert rt.is_valid is True
        assert rt.is_expired is False

    def test_expired_token(self) -> None:
        rt = RefreshToken(
            token_id="T001", account_number="123",
            role="customer",
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
        assert rt.is_expired is True
        assert rt.is_valid is False

    def test_revoked_token(self) -> None:
        rt = RefreshToken(
            token_id="T001", account_number="123",
            role="customer",
            expires_at=datetime.now(UTC) + timedelta(days=7),
            revoked_at=datetime.now(UTC),
        )
        assert rt.is_valid is False


class TestLoginAttempt:
    def test_not_locked(self) -> None:
        la = LoginAttempt(key="123")
        assert la.is_locked is False
        assert la.remaining_minutes == 0

    def test_locked(self) -> None:
        la = LoginAttempt(
            key="123", count=5,
            lockout_until=datetime.now(UTC) + timedelta(minutes=15),
        )
        assert la.is_locked is True
        assert la.remaining_minutes >= 1


class TestNotificationPreference:
    def test_defaults(self) -> None:
        np = NotificationPreference(account_number="123")
        assert np.in_app_enabled is True
        assert np.email_enabled is True
        assert np.sms_enabled is False
        assert np.deposit_alerts is True


class TestResultTypes:
    def test_transfer_result(self) -> None:
        tr = TransferResult(success=True, sender_balance=Decimal("5000"))
        assert tr.success is True
        assert tr.error_message == ""

    def test_service_result(self) -> None:
        sr = ServiceResult(success=True, message="OK", data={"key": "val"})
        assert sr.success is True
        assert sr.data == {"key": "val"}
