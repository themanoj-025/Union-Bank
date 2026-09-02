"""Tests for domain entities and utility functions."""

from __future__ import annotations

from decimal import Decimal

import pytest
from datetime import UTC

pytestmark = pytest.mark.slow


class TestAccountEntity:
    """Test Account entity properties."""

    def test_account_status_active(self) -> None:
        from unionbank.domain.entities import Account, AccountStatus
        acc = Account(account_number="1000000001", name="Test")
        assert acc.status == AccountStatus.ACTIVE

    def test_account_status_frozen(self) -> None:
        from unionbank.domain.entities import Account, AccountStatus
        acc = Account(account_number="1000000001", name="Test", is_frozen=True)
        assert acc.status == AccountStatus.FROZEN

    def test_account_status_closed(self) -> None:
        from unionbank.domain.entities import Account, AccountStatus
        acc = Account(account_number="1000000001", name="Test", is_active=False)
        assert acc.status == AccountStatus.CLOSED

    def test_account_is_deleted(self) -> None:
        from unionbank.domain.entities import Account
        from datetime import datetime, timezone
        acc = Account(
            account_number="1000000001", name="Test",
            deleted_at=datetime.now(UTC)
        )
        assert acc.is_deleted is True

    def test_account_not_deleted(self) -> None:
        from unionbank.domain.entities import Account
        acc = Account(account_number="1000000001", name="Test")
        assert acc.is_deleted is False

    def test_account_can_transact(self) -> None:
        from unionbank.domain.entities import Account
        acc = Account(account_number="1000000001", name="Test")
        assert acc.can_transact is True

    def test_account_cannot_transact_frozen(self) -> None:
        from unionbank.domain.entities import Account
        acc = Account(account_number="1000000001", name="Test", is_frozen=True)
        assert acc.can_transact is False


class TestLoanEntity:
    """Test Loan entity properties."""

    def test_loan_progress_pct(self) -> None:
        from unionbank.domain.entities import Loan
        loan = Loan(
            loan_id="LOAN001",
            account_number="1000000001",
            loan_type="Personal",
            principal_amount=Decimal("100000"),
            interest_rate=Decimal("12.0"),
            tenure_months=24,
            emi_amount=Decimal("4707"),
            amount_paid=Decimal("50000"),
        )
        assert loan.progress_pct == 50.0

    def test_loan_progress_pct_zero_principal(self) -> None:
        from unionbank.domain.entities import Loan
        loan = Loan(
            loan_id="LOAN001",
            account_number="1000000001",
            loan_type="Personal",
            principal_amount=Decimal("0"),
            interest_rate=Decimal("12.0"),
            tenure_months=24,
            emi_amount=Decimal("0"),
        )
        assert loan.progress_pct == 0.0

    def test_loan_remaining_emis(self) -> None:
        from unionbank.domain.entities import Loan
        loan = Loan(
            loan_id="LOAN001",
            account_number="1000000001",
            loan_type="Personal",
            principal_amount=Decimal("100000"),
            interest_rate=Decimal("12.0"),
            tenure_months=24,
            emi_amount=Decimal("4707"),
            remaining_amount=Decimal("50000"),
        )
        assert loan.remaining_emis > 0

    def test_loan_is_active(self) -> None:
        from unionbank.domain.entities import Loan, LoanStatus
        loan = Loan(
            loan_id="LOAN001",
            account_number="1000000001",
            loan_type="Personal",
            principal_amount=Decimal("100000"),
            interest_rate=Decimal("12.0"),
            tenure_months=24,
            emi_amount=Decimal("4707"),
            status=LoanStatus.ACTIVE.value,
        )
        assert loan.is_active is True


class TestTransactionEntity:
    """Test Transaction entity."""

    def test_transaction_creation(self) -> None:
        from unionbank.domain.entities import Transaction, TransactionType
        txn = Transaction(
            txn_id="TXN001",
            account_number="1000000001",
            type=TransactionType.DEPOSIT,
            amount=Decimal("5000"),
            balance=Decimal("105000"),
            description="Deposit",
        )
        assert txn.txn_id == "TXN001"
        assert txn.amount == Decimal("5000")


class TestServiceResult:
    """Test ServiceResult entity."""

    def test_service_result_success(self) -> None:
        from unionbank.domain.entities import ServiceResult
        result = ServiceResult(success=True, message="OK")
        assert result.success is True
        assert result.message == "OK"

    def test_service_result_failure(self) -> None:
        from unionbank.domain.entities import ServiceResult
        result = ServiceResult(success=False, message="Failed")
        assert result.success is False

    def test_service_result_with_data(self) -> None:
        from unionbank.domain.entities import ServiceResult
        result = ServiceResult(success=True, message="OK", data={"balance": 1000})
        assert result.data == {"balance": 1000}


class TestTransferResult:
    """Test TransferResult entity."""

    def test_transfer_result_success(self) -> None:
        from unionbank.domain.entities import TransferResult
        result = TransferResult(success=True, message="Transferred")
        assert result.success is True

    def test_transfer_result_with_txn_ids(self) -> None:
        from unionbank.domain.entities import TransferResult
        result = TransferResult(
            success=True,
            message="Transferred",
            source_txn_id="TXN001",
            target_txn_id="TXN002",
        )
        assert result.source_txn_id == "TXN001"
        assert result.target_txn_id == "TXN002"


class TestEnums:
    """Test enum values."""

    def test_account_status_values(self) -> None:
        from unionbank.domain.entities import AccountStatus
        assert AccountStatus.ACTIVE.value == "active"
        assert AccountStatus.FROZEN.value == "frozen"
        assert AccountStatus.CLOSED.value == "closed"

    def test_transaction_type_values(self) -> None:
        from unionbank.domain.entities import TransactionType
        assert TransactionType.DEPOSIT.value == "DEPOSIT"
        assert TransactionType.WITHDRAW.value == "WITHDRAW"
        assert TransactionType.TRANSFER_OUT.value == "TRANSFER_OUT"

    def test_loan_type_values(self) -> None:
        from unionbank.domain.entities import LoanType
        assert LoanType.PERSONAL.value == "Personal"
        assert LoanType.HOME.value == "Home"
        assert LoanType.VEHICLE.value == "Vehicle"

    def test_loan_status_values(self) -> None:
        from unionbank.domain.entities import LoanStatus
        assert LoanStatus.PENDING.value == "PENDING"
        assert LoanStatus.APPROVED.value == "APPROVED"
        assert LoanStatus.ACTIVE.value == "ACTIVE"
        assert LoanStatus.CLOSED.value == "CLOSED"
        assert LoanStatus.REJECTED.value == "REJECTED"
