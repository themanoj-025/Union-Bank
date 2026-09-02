"""Tests for application.loan_service — loan use-cases with fakes."""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.fakes import (
    FakeAccountRepository,
    FakeAuditLogRepository,
    FakeSavingsGoalRepository,
    FakeTokenVersionRepository,
    FakeTransactionRepository,
)
from tests.fakes_repositories_ext import (
    FakeLoanRepository,
)
from unionbank.application.loan_service import LOAN_PRODUCTS, LOAN_TYPES, LoanService
from unionbank.domain.entities import Account, LoanStatus, LoanType

pytestmark = pytest.mark.slow


@pytest.fixture
def account_repo() -> FakeAccountRepository:
    return FakeAccountRepository()


@pytest.fixture
def txn_repo() -> FakeTransactionRepository:
    return FakeTransactionRepository()


@pytest.fixture
def loan_repo() -> FakeLoanRepository:
    return FakeLoanRepository()


@pytest.fixture
def audit_log_repo() -> FakeAuditLogRepository:
    return FakeAuditLogRepository()


@pytest.fixture
def sample_account() -> Account:
    return Account(
        account_number="1000000001",
        name="Test User",
        balance=Decimal("500000"),
    )


@pytest.fixture
def service(
    loan_repo: FakeLoanRepository,
    account_repo: FakeAccountRepository,
    txn_repo: FakeTransactionRepository,
    audit_log_repo: FakeAuditLogRepository,
) -> LoanService:
    return LoanService(loan_repo, account_repo, txn_repo, audit_log_repo)


class TestLoanConstants:
    """Verify loan product configuration."""

    def test_loan_types_match_enum(self) -> None:
        for lt in LoanType:
            assert lt.value in LOAN_TYPES

    def test_all_loan_types_have_products(self) -> None:
        for lt in LoanType:
            assert lt.value in LOAN_PRODUCTS

    def test_personal_loan_product(self) -> None:
        p = LOAN_PRODUCTS[LoanType.PERSONAL.value]
        assert p["min_rate"] == 10.0
        assert p["max_rate"] == 15.0
        assert p["max_tenure"] == 60

    def test_home_loan_product(self) -> None:
        p = LOAN_PRODUCTS[LoanType.HOME.value]
        assert p["min_rate"] == 7.0
        assert p["max_rate"] == 10.0
        assert p["max_tenure"] == 360


class TestLoanServiceApply:
    """Loan application use-case."""

    def test_apply_loan_success(self, service: LoanService, account_repo: FakeAccountRepository, sample_account: Account) -> None:
        account_repo.create(sample_account)
        result = service.apply_loan(
            "1000000001", "Personal", Decimal("100000"), Decimal("12.0"), 24, "Home renovation"
        )
        assert result.success is True
        assert "loan_id" in result.data

    def test_apply_loan_account_not_found(self, service: LoanService) -> None:
        result = service.apply_loan(
            "9999999999", "Personal", Decimal("100000"), Decimal("12.0"), 24
        )
        assert result.success is False
        assert "not found" in result.message.lower()

    def test_apply_loan_invalid_type(self, service: LoanService, account_repo: FakeAccountRepository, sample_account: Account) -> None:
        account_repo.create(sample_account)
        result = service.apply_loan(
            "1000000001", "InvalidType", Decimal("100000"), Decimal("12.0"), 24
        )
        assert result.success is False
        assert "Invalid loan type" in result.message

    def test_apply_loan_below_minimum(self, service: LoanService, account_repo: FakeAccountRepository, sample_account: Account) -> None:
        account_repo.create(sample_account)
        result = service.apply_loan(
            "1000000001", "Personal", Decimal("500"), Decimal("12.0"), 24
        )
        assert result.success is False
        assert "Minimum" in result.message

    def test_apply_loan_above_maximum(self, service: LoanService, account_repo: FakeAccountRepository, sample_account: Account) -> None:
        account_repo.create(sample_account)
        result = service.apply_loan(
            "1000000001", "Personal", Decimal("50000000"), Decimal("12.0"), 24
        )
        assert result.success is False
        assert "Maximum" in result.message

    def test_apply_loan_invalid_tenure(self, service: LoanService, account_repo: FakeAccountRepository, sample_account: Account) -> None:
        account_repo.create(sample_account)
        result = service.apply_loan(
            "1000000001", "Personal", Decimal("100000"), Decimal("12.0"), 200
        )
        assert result.success is False
        assert "Tenure" in result.message

    def test_apply_loan_invalid_rate(self, service: LoanService, account_repo: FakeAccountRepository, sample_account: Account) -> None:
        account_repo.create(sample_account)
        result = service.apply_loan(
            "1000000001", "Personal", Decimal("100000"), Decimal("25.0"), 24
        )
        assert result.success is False
        assert "Interest rate" in result.message

    def test_apply_loan_frozen_account(self, service: LoanService, account_repo: FakeAccountRepository) -> None:
        frozen = Account(
            account_number="1000000001", name="Frozen", is_frozen=True, balance=Decimal("500000")
        )
        account_repo.create(frozen)
        result = service.apply_loan(
            "1000000001", "Personal", Decimal("100000"), Decimal("12.0"), 24
        )
        assert result.success is False
        assert "frozen" in result.message.lower()


class TestLoanServiceListAndGet:
    """Loan listing and retrieval."""

    def test_list_loans_empty(self, service: LoanService) -> None:
        loans = service.list_loans("1000000001")
        assert loans == []

    def test_list_pending(self, service: LoanService) -> None:
        pending = service.list_pending()
        assert isinstance(pending, list)

    def test_list_active(self, service: LoanService) -> None:
        active = service.list_active()
        assert isinstance(active, list)

    def test_list_all(self, service: LoanService) -> None:
        all_loans = service.list_all()
        assert isinstance(all_loans, list)

    def test_get_loan_none(self, service: LoanService) -> None:
        assert service.get_loan("NONEXISTENT") is None

    def test_get_loan_statistics(self, service: LoanService) -> None:
        stats = service.get_loan_statistics()
        assert "total_pending" in stats
        assert "total_active" in stats
        assert "total_disbursed" in stats
        assert "total_outstanding" in stats
