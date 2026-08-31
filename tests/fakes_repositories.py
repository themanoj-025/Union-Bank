"""In-memory repository fakes for unit testing — repository implementations."""

from __future__ import annotations

import random
import time
from datetime import datetime, timedelta, UTC
from decimal import Decimal
from typing import Any

from unionbank.application.interfaces import KeysetPage
from unionbank.domain.entities import (
    Account,
    AdminUser,
    AuditLog,
    LoginAttempt,
    Notification,
    NotificationPreference,
    RefreshToken,
    SavingsGoal,
    TokenVersion,
    Transaction,
)

from tests.fakes import (
    SimulatedDuplicateKeyError,
    SimulatedForeignKeyViolation,
    SimulatedRaceConditionError,
    SimulatedDatabaseTimeout,
    _FakeSession,
    _utcnow,
)


class FakeAccountRepository:
    """
    In-memory account repository — stores accounts in a dict keyed by account_number.

    Provides a `.session` attribute (a no-op _FakeSession) so that
    savepoint-based transactions like begin_nested() work transparently
    without a real SQLAlchemy session.

    Simulation flags (opt-in):
        simulate_duplicate_key (bool): Raises SimulatedDuplicateKeyError on create()
                                       if account_number already exists.
        simulate_fk_violation (bool):  Raises SimulatedForeignKeyViolation on create()
                                       if no matching parent exists.
        simulate_race_condition (bool): Makes atomic_decrement/increment fail randomly.
        simulate_timeout (bool):        Raises SimulatedDatabaseTimeout on commit().
    """

    def __init__(self):
        self.session = _FakeSession()  # Supports begin_nested() for atomic transactions
        self._accounts: dict[str, Account] = {}
        self.simulate_duplicate_key = False
        self.simulate_fk_violation = False
        self.simulate_race_condition = False
        self.simulate_timeout = False

    def get(self, acc_no: str) -> Account | None:
        return self._accounts.get(acc_no)

    def get_all(self) -> list[Account]:
        return list(self._accounts.values())

    def exists(self, acc_no: str) -> bool:
        return acc_no in self._accounts

    def create(self, account: Account) -> Account:
        if self.simulate_duplicate_key and account.account_number in self._accounts:
            raise SimulatedDuplicateKeyError(
                f"Duplicate key: account {account.account_number} already exists"
            )
        self._accounts[account.account_number] = account
        return account

    def update(self, account: Account) -> Account:
        self._accounts[account.account_number] = account
        return account

    def update_balance(self, acc_no: str, new_balance: Decimal) -> bool:
        if acc_no not in self._accounts:
            return False
        self._accounts[acc_no].balance = new_balance
        return True

    def atomic_decrement(self, acc_no: str, amount: Decimal) -> bool:
        """Atomic decrement — fake version with in-memory balance check."""
        if acc_no not in self._accounts:
            return False
        if self._accounts[acc_no].balance < amount:
            return False
        self._accounts[acc_no].balance -= amount
        return True

    def atomic_increment(self, acc_no: str, amount: Decimal) -> bool:
        """Atomic increment — fake version."""
        if acc_no not in self._accounts:
            return False
        self._accounts[acc_no].balance += amount
        return True

    def set_active(self, acc_no: str, active: bool) -> bool:
        if acc_no not in self._accounts:
            return False
        self._accounts[acc_no].is_active = active
        return True

    def set_frozen(self, acc_no: str, frozen: bool) -> bool:
        """
        Set the frozen status of an account.

        NOTE: This does NOT change is_active. Freezing does not imply
        closing, and unfreezing does not imply reactivating.
        """
        if acc_no not in self._accounts:
            return False
        self._accounts[acc_no].is_frozen = frozen
        return True

    def delete(self, acc_no: str) -> bool:
        if acc_no not in self._accounts:
            return False
        del self._accounts[acc_no]
        return True

    def search(self, query: str) -> list[Account]:
        q = query.lower()
        return [
            a
            for a in self._accounts.values()
            if q in a.account_number.lower() or q in a.name.lower()
        ]

    def count(self) -> int:
        return len(self._accounts)

    def total_balance(self) -> Decimal:
        return sum(
            (a.balance for a in self._accounts.values()),
            Decimal("0.00"),
        )

    def active_count(self) -> int:
        return sum(1 for a in self._accounts.values() if a.is_active and not a.is_frozen)

    def frozen_count(self) -> int:
        return sum(1 for a in self._accounts.values() if a.is_frozen)

    def closed_count(self) -> int:
        return sum(1 for a in self._accounts.values() if not a.is_active and not a.is_frozen)

    def get_statistics(self) -> dict:
        """Compute bank-wide statistics from in-memory data."""
        accounts = list(self._accounts.values())
        return {
            "total_customers": len(accounts),
            "active": sum(1 for a in accounts if a.is_active and not a.is_frozen),
            "frozen": sum(1 for a in accounts if a.is_frozen),
            "closed": sum(1 for a in accounts if not a.is_active and not a.is_frozen),
            "total_balance": float(sum(a.balance for a in accounts) if accounts else 0),
        }

    def get_all_paginated(self, page: int = 1, per_page: int = 20) -> tuple[list[Account], int]:
        """Get accounts with offset-based pagination from in-memory data."""
        accounts = list(self._accounts.values())
        total = len(accounts)
        start = (page - 1) * per_page
        return accounts[start : start + per_page], total

    def get_by_email(self, email: str) -> Account | None:
        for a in self._accounts.values():
            if a.email == email:
                return a
        return None

    def commit(self) -> None:
        pass  # No-op for in-memory

    def rollback(self) -> None:
        pass  # No-op for in-memory


#  Fake Transaction Repository


class FakeTransactionRepository:
    """In-memory transaction repository — stores transactions in a list."""

    def __init__(self):
        self._transactions: list[Transaction] = []

    def get_by_account(self, acc_no: str) -> list[Transaction]:
        return sorted(
            [t for t in self._transactions if t.account_number == acc_no],
            key=lambda t: t.timestamp or _utcnow(),
            reverse=True,
        )

    def get_mini(self, acc_no: str, limit: int = 5) -> list[Transaction]:
        txns = self.get_by_account(acc_no)
        return txns[:limit]

    def create(self, transaction: Transaction) -> Transaction:
        self._transactions.append(transaction)
        return transaction

    def get_all(self) -> list[Transaction]:
        return list(self._transactions)

    def total_by_type(self, txn_type: str) -> Decimal:
        return sum(
            (t.amount for t in self._transactions if t.type.value == txn_type),
            Decimal("0.00"),
        )

    def count(self) -> int:
        return len(self._transactions)

    def count_by_account(self, acc_no: str) -> int:
        return sum(1 for t in self._transactions if t.account_number == acc_no)

    def get_category_totals(self) -> dict[str, Decimal]:
        totals: dict[str, Decimal] = {}
        for t in self._transactions:
            cat = t.category or "General"
            totals[cat] = totals.get(cat, Decimal("0.00")) + t.amount
        return totals

    def get_paginated(
        self,
        acc_no: str | None = None,
        page: int = 1,
        per_page: int = 20,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        txn_type: str | None = None,
    ) -> tuple[list[Transaction], int]:
        filtered = self._filter_txns(acc_no, from_date, to_date, txn_type)
        filtered.sort(key=lambda t: t.timestamp or _utcnow(), reverse=True)
        total = len(filtered)
        start = (page - 1) * per_page
        return filtered[start : start + per_page], total

    def get_paginated_keyset(
        self,
        acc_no: str | None = None,
        limit: int = 20,
        cursor: datetime | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        txn_type: str | None = None,
    ) -> KeysetPage[Transaction]:
        filtered = self._filter_txns(acc_no, from_date, to_date, txn_type)
        filtered.sort(key=lambda t: t.timestamp or _utcnow(), reverse=True)

        if cursor is not None:
            filtered = [t for t in filtered if t.timestamp and t.timestamp < cursor]

        has_more = len(filtered) > limit
        items = filtered[:limit]
        next_cursor = items[-1].timestamp if items else None

        return KeysetPage(
            items=items,
            cursor=next_cursor,
            has_more=has_more,
            cursor_key="timestamp",
        )

    def _filter_txns(
        self,
        acc_no: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        txn_type: str | None = None,
    ) -> list[Transaction]:
        """Filter transactions by optional criteria."""
        filtered = list(self._transactions)
        if acc_no:
            filtered = [t for t in filtered if t.account_number == acc_no]
        if from_date:
            filtered = [t for t in filtered if (t.timestamp or _utcnow()) >= from_date]
        if to_date:
            filtered = [t for t in filtered if (t.timestamp or _utcnow()) <= to_date]
        if txn_type:
            filtered = [t for t in filtered if t.type.value == txn_type]
        return filtered

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


#  Fake Admin Repository


class FakeAdminRepository:
    """In-memory admin repository."""

    def __init__(self):
        self._admins: dict[str, AdminUser] = {}

    def get_by_username(self, username: str) -> AdminUser | None:
        return self._admins.get(username)

    def create(self, admin: AdminUser) -> AdminUser:
        self._admins[admin.username] = admin
        return admin

    def update_password(self, username: str, new_hashed: str) -> bool:
        if username not in self._admins:
            return False
        self._admins[username].password = new_hashed
        return True

    def update_totp(self, username: str, totp_secret: str | None, totp_enabled: bool) -> bool:
        if username not in self._admins:
            return False
        self._admins[username].totp_secret = totp_secret
        self._admins[username].totp_enabled = totp_enabled
        return True

    def admin_count(self) -> int:
        return len(self._admins)

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


#  Fake Savings Goal Repository


class FakeSavingsGoalRepository:
    """In-memory savings goal repository."""

    def __init__(self):
        self._goals: dict[str, SavingsGoal] = {}

    def get_by_account(self, acc_no: str) -> list[SavingsGoal]:
        return [g for g in self._goals.values() if g.account_number == acc_no]

    def get(self, goal_id: str) -> SavingsGoal | None:
        return self._goals.get(goal_id)

    def create(self, goal: SavingsGoal) -> SavingsGoal:
        self._goals[goal.goal_id] = goal
        return goal

    def update(self, goal: SavingsGoal) -> SavingsGoal:
        self._goals[goal.goal_id] = goal
        return goal

    def contribute(self, goal_id: str, amount: Decimal) -> SavingsGoal | None:
        goal = self._goals.get(goal_id)
        if goal is None:
            return None
        goal.current_amount += amount
        if goal.current_amount >= goal.target_amount:
            goal.is_completed = True
        return goal

    def delete(self, goal_id: str) -> SavingsGoal | None:
        return self._goals.pop(goal_id, None)

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


#  Fake Login Attempt Repository


class FakeLoginAttemptRepository:
    """In-memory login attempt repository for rate limiting tests."""

    def __init__(self):
        self._records: dict[str, LoginAttempt] = {}

    def get(self, key: str) -> LoginAttempt | None:
        return self._records.get(key)

    def record_failure(self, key: str, max_attempts: int = 5, lockout_minutes: int = 15) -> int:
        now = _utcnow()
        record = self._records.get(key)

        if record is None:
            record = LoginAttempt(key=key, count=1, first_failed=now)
            self._records[key] = record
        else:
            if record.lockout_until and now >= record.lockout_until:
                record.count = 1
                record.first_failed = now
                record.lockout_until = None
            else:
                record.count += 1

            if record.count >= max_attempts:
                record.lockout_until = now + timedelta(minutes=lockout_minutes)

        return max(0, max_attempts - record.count)

    def is_locked(self, key: str, max_attempts: int = 5) -> tuple[bool, int]:
        record = self._records.get(key)
        if record is None or record.count < max_attempts:
            return False, 0
        if record.lockout_until and _utcnow() < record.lockout_until:
            remaining = int((record.lockout_until - _utcnow()).total_seconds() // 60)
            return True, max(1, remaining)
        if record and record.lockout_until and _utcnow() >= record.lockout_until:
            del self._records[key]
        return False, 0

    def reset(self, key: str) -> None:
        self._records.pop(key, None)

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


