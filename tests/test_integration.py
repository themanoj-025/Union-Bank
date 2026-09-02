"""
tests/test_integration.py  –  Integration tests with real SQLite in-memory DB.

These tests use the actual DI container and SQLite (in-memory, via temp file)
to verify that the infrastructure layer, repositories, and services work
correctly together. This catches bugs that in-memory fakes cannot detect
(e.g., SQLAlchemy model mapping errors, constraint violations).

Testcontainers are not needed — the project uses SQLite, so an in-memory
database is the most faithful test environment.
"""

from __future__ import annotations

import os
import tempfile
from decimal import Decimal

import pytest

from unionbank.domain.entities import Account, TransactionType
from unionbank.infrastructure.container import get_container, reset_container

#  Fixtures


@pytest.fixture(autouse=True)
def _fresh_db() -> None:
    """
    Set up a fresh SQLite database for each test.

    Uses a temp directory for the database file and resets the DI container
    so each test starts with a clean database.
    """
    # Create a temp directory for this test's database
    data_dir = tempfile.mkdtemp(prefix="union_bank_inttest_")
    old_data_dir = os.environ.get("UNION_BANK_DATA_DIR")
    os.environ["UNION_BANK_DATA_DIR"] = data_dir
    os.environ["UNION_BANK_TESTING"] = "1"

    reset_container()

    yield

    # Cleanup: reset container state
    reset_container()
    if old_data_dir:
        os.environ["UNION_BANK_DATA_DIR"] = old_data_dir
    else:
        os.environ.pop("UNION_BANK_DATA_DIR", None)


@pytest.fixture
def c() -> None:
    """Get a fresh DI container with a clean SQLite database."""
    return get_container()


@pytest.fixture
def sample_account() -> dict:
    """Return a dict representing a valid account for Account(...) constructor."""
    return {
        "account_number": "1000000001",
        "name": "Integration Tester",
        "age": 30,
        "gender": "Male",
        "mobile": "9876543210",
        "email": "inttest@example.com",
        "password": "$2b$12$test.int.hash.123456789012345678901234567890",
        "balance": 1000.0,
        "is_active": True,
        "is_frozen": False,
        "created_at": "2026-01-01 00:00:00",
    }


#  Integration: Account CRUD via Container


class TestAccountCRUD:
    def test_create_and_get_account(self, c) -> None:
        """Create an account via the container and verify it persists."""
        account = Account(
            account_number="1000000001",
            name="Test User",
            balance=Decimal("500.00"),
            password="$2b$12$testhash",
        )
        repo = c.account_repo()
        repo.create(account)
        repo.commit()

        fetched = repo.get("1000000001")
        assert fetched is not None
        assert fetched.account_number == "1000000001"
        assert fetched.name == "Test User"
        assert fetched.balance == Decimal("500.00")

    def test_create_and_list_accounts(self, c) -> None:
        """List all accounts after creating multiple."""
        repo = c.account_repo()
        repo.create(Account(account_number="1000000001", name="User 1", password="pw"))
        repo.create(Account(account_number="2000000002", name="User 2", password="pw"))
        repo.commit()

        accounts = repo.get_all()
        assert len(accounts) == 2

    def test_idempotency_repo_create_and_get(self, c) -> None:
        """Verify the idempotency repository can create and retrieve records."""
        from unionbank.domain.entities import IdempotencyRecord

        repo = c.idempotency_repo()

        record = IdempotencyRecord(
            idempotency_key="test-key-001",
            account_number="1000000001",
            operation="deposit",
            result_json='{"success": true}',
            amount=Decimal("100.00"),
        )
        repo.create(record)
        repo.commit()

        fetched = repo.get("test-key-001")
        assert fetched is not None
        assert fetched.idempotency_key == "test-key-001"
        assert fetched.operation == "deposit"

    def test_idempotency_deposit_prevents_double_spend(self, c) -> None:
        """
        ⭐ IDEMPOTENCY: Depositing twice with the same idempotency_key
        should only move the money once. The second call returns the
        cached result without modifying the balance.
        """
        account = Account(
            account_number="1000000001",
            name="Idempotency Tester",
            balance=Decimal("500.00"),
            password="pw",
        )
        c.account_repo().create(account)
        c.account_repo().commit()

        svc = c.transaction_service()

        # First call: should succeed and credit balance
        result1 = svc.deposit(
            acc_no="1000000001",
            amount=Decimal("100.00"),
            idempotency_key="dep-dup-001",
        )
        assert result1.success
        assert result1.data["balance"] == 600.0  # 500 + 100

        # Second call with the SAME key: should return cached result
        result2 = svc.deposit(
            acc_no="1000000001",
            amount=Decimal("100.00"),
            idempotency_key="dep-dup-001",
        )
        assert result2.success

        # Balance should still be 600, NOT 700
        account = c.account_repo().get("1000000001")
        assert account.balance == Decimal("600.00"), (
            f"Double-spend detected! Balance is {account.balance}, expected 600.00"
        )

    def test_idempotency_withdraw_prevents_double_spend(self, c) -> None:
        """
        Withdrawing twice with the same idempotency_key should only
        debit the account once.
        """
        account = Account(
            account_number="1000000001",
            name="Idempotency Tester",
            balance=Decimal("500.00"),
            password="pw",
        )
        c.account_repo().create(account)
        c.account_repo().commit()

        svc = c.transaction_service()

        # First withdraw
        result1 = svc.withdraw(
            acc_no="1000000001",
            amount=Decimal("100.00"),
            idempotency_key="wd-dup-001",
        )
        assert result1.success
        assert result1.data["balance"] == 400.0  # 500 - 100

        # Second withdraw with same key
        result2 = svc.withdraw(
            acc_no="1000000001",
            amount=Decimal("100.00"),
            idempotency_key="wd-dup-001",
        )
        assert result2.success

        account = c.account_repo().get("1000000001")
        assert account.balance == Decimal("400.00"), (
            f"Double-spend detected! Balance is {account.balance}, expected 400.00"
        )

    def test_idempotency_different_keys_both_succeed(self, c) -> None:
        """Different idempotency keys should each execute independently."""
        account = Account(
            account_number="1000000001",
            name="Idempotency Tester",
            balance=Decimal("500.00"),
            password="pw",
        )
        c.account_repo().create(account)
        c.account_repo().commit()

        svc = c.transaction_service()

        r1 = svc.deposit("1000000001", Decimal("50"), idempotency_key="key-a")
        r2 = svc.deposit("1000000001", Decimal("75"), idempotency_key="key-b")
        assert r1.success and r2.success

        account = c.account_repo().get("1000000001")
        assert account.balance == Decimal("625.00"), f"Expected 625, got {account.balance}"

    def test_idempotency_without_key_still_works(self, c) -> None:
        """
        Backward compatibility: not sending an idempotency_key should
        behave exactly as before (no dedup, no errors).
        """
        account = Account(
            account_number="1000000001",
            name="Back Compat",
            balance=Decimal("100.00"),
            password="pw",
        )
        c.account_repo().create(account)
        c.account_repo().commit()

        svc = c.transaction_service()

        # Without idempotency_key — should work
        r1 = svc.deposit("1000000001", Decimal("50"))
        assert r1.success
        assert r1.data["balance"] == 150.0

        # Same operation again (no key) — should execute again (no dedup)
        r2 = svc.deposit("1000000001", Decimal("50"))
        assert r2.success
        assert r2.data["balance"] == 200.0

    def test_soft_delete_preserves_transactions(self, c) -> None:
        """
        ⭐ COMPLIANCE: Soft-deleting an account must preserve transaction history.

        In a banking domain, destroying transaction records on account deletion
        is a compliance violation (record-retention requirements).
        Soft-delete sets deleted_at and hides the account from default queries,
        but transaction history survives for audit and regulatory purposes.
        """
        repo = c.account_repo()
        txn_repo = c.transaction_repo()

        account = Account(
            account_number="1000000001",
            name="To Delete",
            balance=Decimal("100.00"),
            password="pw",
        )
        repo.create(account)
        repo.commit()

        # Create a transaction for this account
        from unionbank.domain.entities import Transaction

        txn = Transaction(
            txn_id="TXN-DELETETEST",
            account_number="1000000001",
            type=TransactionType.DEPOSIT,
            amount=Decimal("50.00"),
            balance=Decimal("150.00"),
        )
        txn_repo.create(txn)
        txn_repo.commit()

        # Soft-delete the account
        repo.delete("1000000001")
        repo.commit()

        # Account should NOT be returned by normal get() (hidden from default queries)
        assert repo.get("1000000001") is None

        # Account SHOULD be recoverable via get_deleted()
        deleted = repo.get_deleted("1000000001")
        assert deleted is not None
        assert deleted.deleted_at is not None
        assert deleted.account_number == "1000000001"

        # ═══ CRITICAL: Transaction history MUST survive ═══
        assert txn_repo.count_by_account("1000000001") == 1, (
            "Transaction history was destroyed! Soft-delete must preserve "
            "transaction records for audit and compliance."
        )

        # Verify we can still read the transaction
        txns = txn_repo.get_by_account("1000000001")
        assert len(txns) == 1
        assert txns[0].txn_id == "TXN-DELETETEST"
        assert txns[0].amount == Decimal("50.00")


#  Integration: Transaction flow via Services


class TestTransactionFlow:
    def test_deposit_creates_transaction_record(self, c) -> None:
        """Deposit updates account balance AND creates a transaction record."""
        repo = c.account_repo()
        account = Account(
            account_number="1000000001",
            name="Flow Test",
            balance=Decimal("0.00"),
            password="pw",
        )
        repo.create(account)
        repo.commit()

        svc = c.transaction_service()
        result = svc.deposit("1000000001", Decimal("250.00"), "Salary")
        assert result.success is True

        # Verify balance updated
        updated = repo.get("1000000001")
        assert updated.balance == Decimal("250.00")

        # Verify transaction record exists
        txns = c.transaction_repo().get_by_account("1000000001")
        assert len(txns) == 1
        assert txns[0].type == TransactionType.DEPOSIT
        assert txns[0].amount == Decimal("250.00")
        assert txns[0].balance == Decimal("250.00")

    def test_full_deposit_withdraw_transfer_flow(self, c) -> None:
        """Complete banking flow: deposit → withdraw → transfer → verify all persisted."""
        repo = c.account_repo()
        svc = c.transaction_service()

        # Create accounts
        sender = Account(
            account_number="1000000001",
            name="Sender",
            balance=Decimal("500.00"),
            password="pw",
        )
        receiver = Account(
            account_number="2000000002",
            name="Receiver",
            balance=Decimal("100.00"),
            password="pw",
        )
        repo.create(sender)
        repo.create(receiver)
        repo.commit()

        # Deposit
        svc.deposit("1000000001", Decimal("300.00"))
        assert repo.get("1000000001").balance == Decimal("800.00")

        # Withdraw
        svc.withdraw("1000000001", Decimal("100.00"))
        assert repo.get("1000000001").balance == Decimal("700.00")

        # Transfer
        svc.transfer("1000000001", "2000000002", Decimal("200.00"))
        assert repo.get("1000000001").balance == Decimal("500.00")
        assert repo.get("2000000002").balance == Decimal("300.00")

        # Verify all transactions recorded
        txns = c.transaction_repo().get_all()
        assert len(txns) == 4  # 1 deposit + 1 withdraw + 2 transfer

    def test_transfer_rollback_on_failure(self, c) -> None:
        """
        If a transfer fails mid-way, NO changes persist.

        The atomic transfer should roll back both the debit and the credit
        if any part of the operation fails.
        """
        repo = c.account_repo()
        svc = c.transaction_service()

        sender = Account(
            account_number="1000000001",
            name="Sender",
            balance=Decimal("100.00"),
            password="pw",
        )
        receiver = Account(
            account_number="2000000002",
            name="Receiver",
            balance=Decimal("50.00"),
            password="pw",
        )
        repo.create(sender)
        repo.create(receiver)
        repo.commit()

        # Try to transfer more than sender has
        result = svc.transfer("1000000001", "2000000002", Decimal("99999.00"))
        assert result.success is False

        # Both accounts must be unchanged
        assert repo.get("1000000001").balance == Decimal("100.00")
        assert repo.get("2000000002").balance == Decimal("50.00")


#  Integration: Admin operations via Container


class TestAdminOperations:
    def test_freeze_account_via_service(self, c) -> None:
        """
        Freezing an account via AdminService should persist in SQLite.

        Freeze now explicitly also deactivates the account (via AdminService),
        but unfreezing does NOT reactivate it.
        """
        repo = c.account_repo()
        account = Account(
            account_number="1000000001",
            name="Freeze Target",
            balance=Decimal("1000.00"),
            password="pw",
            is_active=True,
            is_frozen=False,
        )
        repo.create(account)
        repo.commit()

        admin_svc = c.admin_service()
        result = admin_svc.freeze_account("1000000001", actor="test_admin")
        assert result.success is True

        updated = repo.get("1000000001")
        assert updated.is_frozen is True
        # AdminService.freeze_account() explicitly deactivates when freezing
        assert updated.is_active is False

    def test_audit_log_persisted(self, c) -> None:
        """Admin audit log entries should be persisted in SQLite."""
        repo = c.account_repo()
        account = Account(
            account_number="1000000001",
            name="Audit Target",
            balance=Decimal("500.00"),
            password="pw",
        )
        repo.create(account)
        repo.commit()

        admin_svc = c.admin_service()
        admin_svc.freeze_account("1000000001", actor="test_admin", reason="Testing audit log")

        # Check audit log via the audit_log_repo
        audit_repo = c.audit_log_repo()
        entries = audit_repo.get_by_action("freeze")
        assert len(entries) >= 1
        assert entries[0]["actor"] == "test_admin"
        assert entries[0]["reason"] == "Testing audit log"


#  Integration: Savings Goals via Container

