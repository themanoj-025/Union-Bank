"""
tests/test_services.py  –  Unit tests for application services using in-memory fakes.

These tests run entirely in memory — no SQLite, no I/O.
The services depend only on repository protocols, which we satisfy with Fakes. — Part 2.
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

class TestAdminService:
    def test_list_accounts(self, admin_service, account_repo, sample_account) -> None:
        account_repo.create(sample_account)
        account_repo.create(
            Account(
                account_number="2000000002",
                name="User 2",
                password=hash_password("p"),
            )
        )
        accounts = admin_service.list_accounts()
        assert len(accounts) == 2

    def test_search_accounts(self, admin_service, account_repo, sample_account) -> None:
        account_repo.create(sample_account)
        account_repo.create(
            Account(
                account_number="2000000002",
                name="Another User",
                password=hash_password("p"),
            )
        )

        results = admin_service.search_accounts("Test")
        assert len(results) == 1
        assert results[0].account_number == "1000000001"

        results2 = admin_service.search_accounts("1000000001")
        assert len(results2) == 1

    def test_freeze_account(self, admin_service, account_repo, sample_account) -> None:
        account_repo.create(sample_account)
        result = admin_service.freeze_account("1000000001", actor="admin")
        assert result.success is True
        updated = account_repo.get("1000000001")
        assert updated.is_frozen is True

    def test_freeze_already_frozen(self, admin_service, account_repo, sample_account) -> None:
        sample_account.is_frozen = True
        account_repo.create(sample_account)
        result = admin_service.freeze_account("1000000001")
        assert result.success is False
        assert "already frozen" in result.message.lower()

    def test_unfreeze_account(self, admin_service, account_repo, sample_account) -> None:
        sample_account.is_frozen = True
        account_repo.create(sample_account)
        result = admin_service.unfreeze_account("1000000001", actor="admin")
        assert result.success is True
        updated = account_repo.get("1000000001")
        assert updated.is_frozen is False
        assert updated.is_active is True

    def test_unfreeze_not_frozen(self, admin_service, account_repo, sample_account) -> None:
        account_repo.create(sample_account)
        result = admin_service.unfreeze_account("1000000001")
        assert result.success is False
        assert "not frozen" in result.message.lower()

    def test_delete_account(self, admin_service, account_repo, sample_account) -> None:
        account_repo.create(sample_account)
        result = admin_service.delete_account("1000000001", actor="admin")
        assert result.success is True
        assert account_repo.get("1000000001") is None

    def test_delete_account_not_found(self, admin_service) -> None:
        result = admin_service.delete_account("9999999999")
        assert result.success is False
        assert "not found" in result.message.lower()

    def test_get_statistics(self, admin_service, account_repo, txn_repo, sample_account) -> None:
        account_repo.create(sample_account)
        account_repo.create(
            Account(
                account_number="2000000002",
                name="User 2",
                password=hash_password("p"),
                balance=Decimal("500.00"),
                is_frozen=True,
            )
        )

        stats = admin_service.get_statistics()
        assert stats["total_customers"] == 2
        assert stats["active"] == 1
        assert stats["frozen"] == 1
        assert float(stats["total_balance"]) >= 1000.0

    def test_audit_log_on_freeze(self, admin_service, account_repo, sample_account, audit_log_repo) -> None:
        account_repo.create(sample_account)
        admin_service.freeze_account("1000000001", actor="admin_test", reason="Fraud suspicion")
        entries = audit_log_repo.get_by_action("freeze")
        assert len(entries) >= 1
        assert entries[0]["actor"] == "admin_test"
        assert entries[0]["reason"] == "Fraud suspicion"

    def test_audit_log_on_delete(self, admin_service, account_repo, sample_account, audit_log_repo) -> None:
        account_repo.create(sample_account)
        admin_service.delete_account("1000000001", actor="admin_test")
        entries = audit_log_repo.get_by_action("delete")
        assert len(entries) >= 1
        assert entries[0]["target"] == "1000000001"

    def test_change_admin_password(self, admin_service, admin_repo, sample_admin) -> None:
        admin_repo.create(sample_admin)
        result = admin_service.change_admin_password("admin", "AdminPass1", "NewAdmin1Pass")
        assert result.success is True
        from unionbank.utils.hashing import verify_password

        assert verify_password("NewAdmin1Pass", admin_repo.get_by_username("admin").password)


#  SavingsGoalService Tests


class TestSavingsGoalService:
    def test_create_goal(self, savings_goal_service, savings_goal_repo) -> None:
        result = savings_goal_service.create_goal(
            acc_no="1000000001",
            name="New Laptop",
            target_amount=Decimal("1500.00"),
            target_date="2026-12-31",
        )
        assert result.success is True
        goals = savings_goal_repo.get_by_account("1000000001")
        assert len(goals) == 1
        assert goals[0].name == "New Laptop"

    def test_create_goal_short_name(self, savings_goal_service) -> None:
        result = savings_goal_service.create_goal(
            acc_no="1000000001", name="X", target_amount=Decimal("100.00")
        )
        assert result.success is False
        assert "2 characters" in result.message.lower()

    def test_create_goal_zero_target(self, savings_goal_service) -> None:
        result = savings_goal_service.create_goal(
            acc_no="1000000001", name="Goal", target_amount=Decimal("0")
        )
        assert result.success is False
        assert "positive" in result.message.lower()

    def test_list_goals(self, savings_goal_service, savings_goal_repo) -> None:
        savings_goal_repo.create(
            SavingsGoal(
                goal_id="GOAL-001",
                account_number="1000000001",
                name="Goal 1",
                target_amount=Decimal("1000.00"),
            )
        )
        savings_goal_repo.create(
            SavingsGoal(
                goal_id="GOAL-002",
                account_number="1000000001",
                name="Goal 2",
                target_amount=Decimal("2000.00"),
            )
        )
        goals = savings_goal_service.list_goals("1000000001")
        assert len(goals) == 2

    def test_contribute_success(
        self, savings_goal_service, account_repo, savings_goal_repo, sample_account
    ) -> None:
        account_repo.create(sample_account)
        goal = SavingsGoal(
            goal_id="GOAL-001",
            account_number="1000000001",
            name="Vacation",
            target_amount=Decimal("2000.00"),
        )
        savings_goal_repo.create(goal)

        result = savings_goal_service.contribute("1000000001", "GOAL-001", Decimal("500.00"))
        assert result.success is True

        updated_goal = savings_goal_repo.get("GOAL-001")
        assert updated_goal.current_amount == Decimal("500.00")

        updated_acc = account_repo.get("1000000001")
        assert updated_acc.balance == Decimal("500.00")  # 1000 - 500

    def test_contribute_exceeds_balance(
        self, savings_goal_service, account_repo, savings_goal_repo, sample_account
    ) -> None:
        account_repo.create(sample_account)
        goal = SavingsGoal(
            goal_id="GOAL-001",
            account_number="1000000001",
            name="Dream Car",
            target_amount=Decimal("99999.00"),
        )
        savings_goal_repo.create(goal)

        result = savings_goal_service.contribute("1000000001", "GOAL-001", Decimal("99999.00"))
        assert result.success is False
        assert "insufficient" in result.message.lower()

    def test_contribute_completes_goal(
        self, savings_goal_service, account_repo, savings_goal_repo, sample_account
    ) -> None:
        sample_account.balance = Decimal("5000.00")
        account_repo.create(sample_account)
        goal = SavingsGoal(
            goal_id="GOAL-001",
            account_number="1000000001",
            name="Small Goal",
            target_amount=Decimal("100.00"),
        )
        savings_goal_repo.create(goal)

        savings_goal_service.contribute("1000000001", "GOAL-001", Decimal("100.00"))
        updated_goal = savings_goal_repo.get("GOAL-001")
        assert updated_goal.is_completed is True

    def test_delete_goal_with_refund(
        self, savings_goal_service, account_repo, savings_goal_repo, sample_account
    ) -> None:
        sample_account.balance = Decimal("1000.00")
        account_repo.create(sample_account)
        goal = SavingsGoal(
            goal_id="GOAL-001",
            account_number="1000000001",
            name="Refund Test",
            target_amount=Decimal("500.00"),
            current_amount=Decimal("200.00"),
        )
        savings_goal_repo.create(goal)

        result = savings_goal_service.delete_goal("1000000001", "GOAL-001")
        assert result.success is True

        # Verify refund
        updated_acc = account_repo.get("1000000001")
        assert updated_acc.balance == Decimal("1200.00")  # 1000 + 200 refund

        # Verify goal deleted
        assert savings_goal_repo.get("GOAL-001") is None

    def test_delete_goal_not_found(self, savings_goal_service) -> None:
        result = savings_goal_service.delete_goal("1000000001", "GOAL-NONEXIST")
        assert result.success is False
        assert "not found" in result.message.lower()
