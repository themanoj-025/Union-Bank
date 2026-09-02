"""Tests for application.transfer_service — deposit, withdraw, transfer with fakes."""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.fakes import (
    FakeAccountRepository,
    FakeAuditLogRepository,
    FakeTransactionRepository,
)
from unionbank.application.services import TransactionService
from unionbank.domain.entities import Account

pytestmark = pytest.mark.slow


@pytest.fixture
def account_repo() -> FakeAccountRepository:
    return FakeAccountRepository()


@pytest.fixture
def txn_repo() -> FakeTransactionRepository:
    return FakeTransactionRepository()


@pytest.fixture
def audit_log_repo() -> FakeAuditLogRepository:
    return FakeAuditLogRepository()


@pytest.fixture
def sample_account() -> Account:
    return Account(
        account_number="1000000001",
        name="Test User",
        balance=Decimal("100000"),
    )


@pytest.fixture
def service(
    account_repo: FakeAccountRepository,
    txn_repo: FakeTransactionRepository,
) -> TransactionService:
    return TransactionService(account_repo, txn_repo)


class TestDeposit:
    """Deposit use-case."""

    def test_deposit_success(self, service: TransactionService, account_repo: FakeAccountRepository, sample_account: Account) -> None:
        account_repo.create(sample_account)
        result = service.deposit("1000000001", Decimal("5000"))
        assert result.success is True
        assert "5,000" in result.message

    def test_deposit_zero_amount(self, service: TransactionService) -> None:
        result = service.deposit("1000000001", Decimal("0"))
        assert result.success is False
        assert "positive" in result.message.lower()

    def test_deposit_negative_amount(self, service: TransactionService) -> None:
        result = service.deposit("1000000001", Decimal("-100"))
        assert result.success is False

    def test_deposit_account_not_found(self, service: TransactionService) -> None:
        result = service.deposit("9999999999", Decimal("1000"))
        assert result.success is False
        assert "not found" in result.message.lower()

    def test_deposit_frozen_account(self, service: TransactionService, account_repo: FakeAccountRepository) -> None:
        frozen = Account(
            account_number="1000000001", name="Frozen", is_frozen=True,
            balance=Decimal("100000")
        )
        account_repo.create(frozen)
        result = service.deposit("1000000001", Decimal("1000"))
        assert result.success is False
        assert "frozen" in result.message.lower()

    def test_deposit_updates_balance(self, service: TransactionService, account_repo: FakeAccountRepository, sample_account: Account) -> None:
        account_repo.create(sample_account)
        service.deposit("1000000001", Decimal("5000"))
        updated = account_repo.get("1000000001")
        assert updated is not None
        assert updated.balance == Decimal("105000")

    def test_deposit_creates_transaction(self, service: TransactionService, account_repo: FakeAccountRepository, txn_repo: FakeTransactionRepository, sample_account: Account) -> None:
        account_repo.create(sample_account)
        service.deposit("1000000001", Decimal("5000"))
        txns = txn_repo.get_by_account("1000000001")
        assert len(txns) == 1
        assert txns[0].amount == Decimal("5000")


class TestWithdraw:
    """Withdraw use-case."""

    def test_withdraw_success(self, service: TransactionService, account_repo: FakeAccountRepository, sample_account: Account) -> None:
        account_repo.create(sample_account)
        result = service.withdraw("1000000001", Decimal("5000"))
        assert result.success is True
        assert "5,000" in result.message

    def test_withdraw_insufficient_balance(self, service: TransactionService, account_repo: FakeAccountRepository, sample_account: Account) -> None:
        account_repo.create(sample_account)
        result = service.withdraw("1000000001", Decimal("200000"))
        assert result.success is False
        assert "insufficient" in result.message.lower() or "balance" in result.message.lower()

    def test_withdraw_zero_amount(self, service: TransactionService) -> None:
        result = service.withdraw("1000000001", Decimal("0"))
        assert result.success is False

    def test_withdraw_updates_balance(self, service: TransactionService, account_repo: FakeAccountRepository, sample_account: Account) -> None:
        account_repo.create(sample_account)
        service.withdraw("1000000001", Decimal("10000"))
        updated = account_repo.get("1000000001")
        assert updated is not None
        assert updated.balance == Decimal("90000")


class TestTransfer:
    """Transfer use-case."""

    def test_transfer_success(
        self, service: TransactionService, account_repo: FakeAccountRepository,
    ) -> None:
        sender = Account(
            account_number="1000000001", name="Sender", balance=Decimal("100000")
        )
        receiver = Account(
            account_number="1000000002", name="Receiver", balance=Decimal("50000")
        )
        account_repo.create(sender)
        account_repo.create(receiver)
        result = service.transfer("1000000001", "1000000002", Decimal("25000"))
        assert result.success is True

    def test_transfer_insufficient_balance(
        self, service: TransactionService, account_repo: FakeAccountRepository,
    ) -> None:
        sender = Account(
            account_number="1000000001", name="Sender", balance=Decimal("1000")
        )
        receiver = Account(
            account_number="1000000002", name="Receiver", balance=Decimal("50000")
        )
        account_repo.create(sender)
        account_repo.create(receiver)
        result = service.transfer("1000000001", "1000000002", Decimal("5000"))
        assert result.success is False

    def test_transfer_self(
        self, service: TransactionService, account_repo: FakeAccountRepository,
    ) -> None:
        account = Account(
            account_number="1000000001", name="Self", balance=Decimal("100000")
        )
        account_repo.create(account)
        result = service.transfer("1000000001", "1000000001", Decimal("1000"))
        assert result.success is False

    def test_transfer_updates_balances(
        self, service: TransactionService, account_repo: FakeAccountRepository,
    ) -> None:
        sender = Account(
            account_number="1000000001", name="Sender", balance=Decimal("100000")
        )
        receiver = Account(
            account_number="1000000002", name="Receiver", balance=Decimal("50000")
        )
        account_repo.create(sender)
        account_repo.create(receiver)
        service.transfer("1000000001", "1000000002", Decimal("25000"))
        s = account_repo.get("1000000001")
        r = account_repo.get("1000000002")
        assert s is not None
        assert r is not None
        assert s.balance == Decimal("75000")
        assert r.balance == Decimal("75000")
