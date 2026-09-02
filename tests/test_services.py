"""
tests/test_services.py  –  Unit tests for application services using in-memory fakes.

These tests run entirely in memory — no SQLite, no I/O.
The services depend only on repository protocols, which we satisfy with Fakes.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.fakes import (
    FakeAccountRepository,
    FakeAdminRepository,
    FakeAuditLogRepository,
    FakeLoginAttemptRepository,
    FakeSavingsGoalRepository,
    FakeTokenVersionRepository,
    FakeTransactionRepository,
)
from unionbank.application.services import (
    AccountService,
    AdminService,
    AuthService,
    SavingsGoalService,
    TransactionService,
)
from unionbank.domain.entities import Account, AdminUser, SavingsGoal
from unionbank.utils.hashing import hash_password

#  Fixtures


@pytest.fixture
def account_repo() -> None:
    return FakeAccountRepository()


@pytest.fixture
def txn_repo() -> None:
    return FakeTransactionRepository()


@pytest.fixture
def admin_repo() -> None:
    return FakeAdminRepository()


@pytest.fixture
def login_attempt_repo() -> None:
    return FakeLoginAttemptRepository()


@pytest.fixture
def token_version_repo() -> None:
    return FakeTokenVersionRepository()


@pytest.fixture
def audit_log_repo() -> None:
    return FakeAuditLogRepository()


@pytest.fixture
def savings_goal_repo() -> None:
    return FakeSavingsGoalRepository()


@pytest.fixture
def sample_account() -> Account:
    return Account(
        account_number="1000000001",
        name="Test User",
        age=30,
        gender="Male",
        mobile="9876543210",
        email="test@example.com",
        password=hash_password("Secure1Pass"),
        balance=Decimal("1000.00"),
        is_active=True,
        is_frozen=False,
    )


@pytest.fixture
def sample_admin() -> AdminUser:
    return AdminUser(
        username="admin",
        password=hash_password("AdminPass1"),
        role="admin",
    )


@pytest.fixture
def auth_service(account_repo, admin_repo, login_attempt_repo, token_version_repo) -> None:
    return AuthService(
        account_repo=account_repo,
        admin_repo=admin_repo,
        login_attempt_repo=login_attempt_repo,
        token_version_repo=token_version_repo,
    )


@pytest.fixture
def account_service(account_repo, txn_repo, token_version_repo) -> None:
    return AccountService(
        account_repo=account_repo,
        txn_repo=txn_repo,
        token_version_repo=token_version_repo,
    )


@pytest.fixture
def transaction_service(account_repo, txn_repo) -> None:
    return TransactionService(
        account_repo=account_repo,
        txn_repo=txn_repo,
    )


@pytest.fixture
def admin_service(account_repo, txn_repo, admin_repo, audit_log_repo) -> None:
    return AdminService(
        account_repo=account_repo,
        txn_repo=txn_repo,
        admin_repo=admin_repo,
        audit_log_repo=audit_log_repo,
    )


@pytest.fixture
def savings_goal_service(account_repo, txn_repo, savings_goal_repo) -> None:
    return SavingsGoalService(
        goal_repo=savings_goal_repo,
        account_repo=account_repo,
        txn_repo=txn_repo,
    )


#  AuthService Tests


class TestAuthService:
    def test_customer_login_success(self, auth_service, account_repo, sample_account) -> None:
        account_repo.create(sample_account)
        result = auth_service.customer_login("1000000001", "Secure1Pass")
        assert result.success is True
        assert result.data["role"] == "customer"

    def test_customer_login_wrong_password(self, auth_service, account_repo, sample_account) -> None:
        account_repo.create(sample_account)
        result = auth_service.customer_login("1000000001", "WrongPass1")
        assert result.success is False
        assert "attempt" in result.message.lower()

    def test_customer_login_account_not_found(self, auth_service) -> None:
        result = auth_service.customer_login("9999999999", "SomePass1")
        assert result.success is False
        assert "not found" in result.message.lower()

    def test_customer_login_frozen_account(self, auth_service, account_repo, sample_account) -> None:
        sample_account.is_frozen = True
        account_repo.create(sample_account)
        result = auth_service.customer_login("1000000001", "Secure1Pass")
        assert result.success is False
        assert "frozen" in result.message.lower()

    def test_customer_login_closed_account(self, auth_service, account_repo, sample_account) -> None:
        sample_account.is_active = False
        account_repo.create(sample_account)
        result = auth_service.customer_login("1000000001", "Secure1Pass")
        assert result.success is False
        assert "closed" in result.message.lower()

    def test_customer_login_rate_limit_exceeded(
        self, auth_service, account_repo, sample_account, login_attempt_repo
    ) -> None:
        account_repo.create(sample_account)
        # Exhaust login attempts
        for _ in range(6):
            auth_service.customer_login("1000000001", "WrongPass1")

        now_locked = auth_service.customer_login("1000000001", "Secure1Pass")
        assert now_locked.success is False
        assert "locked" in now_locked.message.lower()

    def test_customer_register_success(self, auth_service, account_repo) -> None:
        result = auth_service.customer_register(
            name="New User",
            age=25,
            gender="Female",
            mobile="9123456789",
            email="new@example.com",
            password="NewPass1Secure",
        )
        assert result.success is True
        assert "created" in result.message.lower()
        assert account_repo.exists(result.data["account_number"])

    def test_admin_login_success(self, auth_service, admin_repo, sample_admin) -> None:
        admin_repo.create(sample_admin)
        result = auth_service.admin_login("admin", "AdminPass1")
        assert result.success is True
        assert result.data["role"] == "admin"

    def test_admin_login_wrong_password(self, auth_service, admin_repo, sample_admin) -> None:
        admin_repo.create(sample_admin)
        result = auth_service.admin_login("admin", "Wrong1")
        assert result.success is False

    def test_admin_login_locked(self, auth_service, admin_repo, sample_admin, login_attempt_repo) -> None:
        admin_repo.create(sample_admin)
        for _ in range(6):
            auth_service.admin_login("admin", "Wrong1")

        result = auth_service.admin_login("admin", "AdminPass1")
        assert result.success is False
        assert "locked" in result.message.lower()


#  AccountService Tests


class TestAccountService:
    def test_get_profile(self, account_service, account_repo, sample_account) -> None:
        account_repo.create(sample_account)
        profile = account_service.get_profile("1000000001")
        assert profile is not None
        assert profile.name == "Test User"
        assert profile.balance == Decimal("1000.00")

    def test_get_profile_not_found(self, account_service) -> None:
        profile = account_service.get_profile("9999999999")
        assert profile is None

    def test_update_profile(self, account_service, account_repo, sample_account) -> None:
        account_repo.create(sample_account)
        result = account_service.update_profile("1000000001", name="Updated Name", age=35)
        assert result.success is True
        updated = account_repo.get("1000000001")
        assert updated.name == "Updated Name"
        assert updated.age == 35

    def test_update_profile_not_found(self, account_service) -> None:
        result = account_service.update_profile("9999999999", name="Nobody")
        assert result.success is False
        assert "not found" in result.message.lower()

    def test_change_password_success(self, account_service, account_repo, sample_account) -> None:
        account_repo.create(sample_account)
        result = account_service.change_password("1000000001", "Secure1Pass", "NewSecure1Pass")
        assert result.success is True
        # Verify new password works
        from unionbank.utils.hashing import verify_password

        updated = account_repo.get("1000000001")
        assert verify_password("NewSecure1Pass", updated.password)

    def test_change_password_wrong_current(self, account_service, account_repo, sample_account) -> None:
        account_repo.create(sample_account)
        result = account_service.change_password("1000000001", "Wrong1", "NewSecure1Pass")
        assert result.success is False
        assert "incorrect" in result.message.lower()

    def test_close_account_success(self, account_service, account_repo, sample_account) -> None:
        account_repo.create(sample_account)
        result = account_service.close_account("1000000001", "Secure1Pass")
        assert result.success is True
        updated = account_repo.get("1000000001")
        assert updated.is_active is False

    def test_close_account_wrong_password(self, account_service, account_repo, sample_account) -> None:
        account_repo.create(sample_account)
        result = account_service.close_account("1000000001", "Wrong1")
        assert result.success is False

    def test_get_balance(self, account_service, account_repo, sample_account) -> None:
        account_repo.create(sample_account)
        balance = account_service.get_balance("1000000001")
        assert balance == Decimal("1000.00")

    def test_get_balance_not_found(self, account_service) -> None:
        assert account_service.get_balance("9999999999") is None


#  TransactionService Tests


class TestTransactionService:
    def test_deposit_success(self, transaction_service, account_repo, sample_account) -> None:
        account_repo.create(sample_account)
        result = transaction_service.deposit("1000000001", Decimal("500.00"), "Salary")
        assert result.success is True
        updated = account_repo.get("1000000001")
        assert updated.balance == Decimal("1500.00")

    def test_deposit_zero_amount(self, transaction_service, account_repo, sample_account) -> None:
        account_repo.create(sample_account)
        result = transaction_service.deposit("1000000001", Decimal("0"))
        assert result.success is False
        assert "positive" in result.message.lower()

    def test_deposit_account_not_found(self, transaction_service) -> None:
        result = transaction_service.deposit("9999999999", Decimal("100.00"))
        assert result.success is False
        assert "not found" in result.message.lower()

    def test_deposit_frozen_account(self, transaction_service, account_repo, sample_account) -> None:
        sample_account.is_frozen = True
        account_repo.create(sample_account)
        result = transaction_service.deposit("1000000001", Decimal("100.00"))
        assert result.success is False
        assert "frozen" in result.message.lower() or "closed" in result.message.lower()

    def test_withdraw_success(self, transaction_service, account_repo, sample_account) -> None:
        account_repo.create(sample_account)
        result = transaction_service.withdraw("1000000001", Decimal("300.00"), "Food & Dining")
        assert result.success is True
        updated = account_repo.get("1000000001")
        assert updated.balance == Decimal("700.00")

    def test_withdraw_insufficient_balance(self, transaction_service, account_repo, sample_account) -> None:
        account_repo.create(sample_account)
        result = transaction_service.withdraw("1000000001", Decimal("99999.00"))
        assert result.success is False
        assert "insufficient" in result.message.lower()

    def test_withdraw_frozen_account(self, transaction_service, account_repo, sample_account) -> None:
        sample_account.is_frozen = True
        account_repo.create(sample_account)
        result = transaction_service.withdraw("1000000001", Decimal("100.00"))
        assert result.success is False

    def test_transfer_success(self, transaction_service, account_repo, sample_account) -> None:
        sender = sample_account
        receiver = Account(
            account_number="2000000002",
            name="Receiver",
            balance=Decimal("500.00"),
            password=hash_password("pass"),
        )
        account_repo.create(sender)
        account_repo.create(receiver)

        result = transaction_service.transfer(
            sender_acc_no="1000000001",
            receiver_acc_no="2000000002",
            amount=Decimal("400.00"),
            category="General",
        )
        assert result.success is True
        assert account_repo.get("1000000001").balance == Decimal("600.00")  # 1000 - 400
        assert account_repo.get("2000000002").balance == Decimal("900.00")  # 500 + 400

    def test_transfer_self(self, transaction_service, account_repo, sample_account) -> None:
        account_repo.create(sample_account)
        result = transaction_service.transfer(
            sender_acc_no="1000000001",
            receiver_acc_no="1000000001",
            amount=Decimal("100.00"),
        )
        assert result.success is False
        assert "own account" in result.error_message.lower()

    def test_transfer_sender_not_found(self, transaction_service, account_repo, sample_account) -> None:
        account_repo.create(sample_account)
        result = transaction_service.transfer(
            sender_acc_no="9999999999",
            receiver_acc_no="1000000001",
            amount=Decimal("100.00"),
        )
        assert result.success is False

    def test_transfer_insufficient_balance(self, transaction_service, account_repo, sample_account) -> None:
        receiver = Account(
            account_number="2000000002", name="Receiver", password=hash_password("p")
        )
        account_repo.create(sample_account)
        account_repo.create(receiver)

        result = transaction_service.transfer(
            sender_acc_no="1000000001",
            receiver_acc_no="2000000002",
            amount=Decimal("99999.00"),
        )
        assert result.success is False
        assert "insufficient" in result.error_message.lower()

    def test_get_statement(self, transaction_service, account_repo, sample_account) -> None:
        account_repo.create(sample_account)
        transaction_service.deposit("1000000001", Decimal("200.00"))
        transaction_service.withdraw("1000000001", Decimal("100.00"))
        txns = transaction_service.get_statement("1000000001")
        assert len(txns) == 2

    def test_get_mini_statement(self, transaction_service, account_repo, sample_account) -> None:
        account_repo.create(sample_account)
        for _ in range(10):
            transaction_service.deposit("1000000001", Decimal("100.00"))
        mini = transaction_service.get_mini_statement("1000000001", limit=5)
        assert len(mini) == 5

    def test_apply_interest_success(self, transaction_service, account_repo, sample_account) -> None:
        account_repo.create(sample_account)
        result = transaction_service.apply_interest("1000000001")
        assert result.success is True
        assert result.data["interest"] > 0
        updated = account_repo.get("1000000001")
        assert updated.balance > Decimal("1000.00")

    def test_apply_interest_zero_balance(self, transaction_service, account_repo) -> None:
        account = Account(
            account_number="1000000001",
            name="Zero Bal",
            balance=Decimal("0.00"),
            password=hash_password("pass"),
        )
        account_repo.create(account)
        result = transaction_service.apply_interest("1000000001")
        assert result.success is False
        assert "no interest" in result.message.lower()

    def test_get_category_totals(self, transaction_service, account_repo, sample_account) -> None:
        account_repo.create(sample_account)
        transaction_service.deposit("1000000001", Decimal("500"), "Salary")
        transaction_service.withdraw("1000000001", Decimal("100"), "Food & Dining")
        totals = transaction_service.get_category_totals()
        assert totals.get("Salary", Decimal("0")) >= Decimal("500")
        assert totals.get("Food & Dining", Decimal("0")) >= Decimal("100")


#  AdminService Tests


