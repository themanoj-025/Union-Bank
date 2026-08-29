"""
application/async_services.py  â€“  Async use-case service classes.

These mirror the synchronous services in services.py but use async/await for
all database operations. They are used when the application is configured
with a PostgreSQL DATABASE_URL (async via asyncpg).

For SQLite (which doesn't support async), the synchronous services in
services.py are used instead.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal

from unionbank.config import settings
from unionbank.domain.entities import (
    SavingsGoal,
    ServiceResult,
    Transaction,
    TransactionType,
)
from unionbank.utils.formatting import (
    fmt_currency,
    generate_goal_id,
    generate_transaction_id,
)

try:
    from sqlalchemy.exc import SQLAlchemyError
except ImportError:
    SQLAlchemyError = Exception  # fallback if sqlalchemy not installed


TRANSACTION_CATEGORIES = settings.TRANSACTION_CATEGORIES
MAX_LOGIN_ATTEMPTS = settings.MAX_LOGIN_ATTEMPTS
LOGIN_LOCKOUT_MINUTES = settings.LOGIN_LOCKOUT_MINUTES


#  Async per-account concurrency lock

_account_locks: dict[str, asyncio.Lock] = {}


def _get_account_lock(*acc_nos: str) -> asyncio.Lock:
    """
    Get an asyncio.Lock for the given accounts, creating if needed.

    For single-account operations, returns the lock for that account.
    For multi-account operations (transfer), returns a lock based on the
    sorted account numbers to prevent deadlocks.
    """
    # Use a combined key for multi-account operations
    sorted_nos = sorted(acc_nos)
    key = ":".join(sorted_nos)
    if key not in _account_locks:
        _account_locks[key] = asyncio.Lock()
    return _account_locks[key]


#  Async Transaction Service



class AsyncSavingsGoalService:
    """Async savings goal use-cases."""

    def __init__(
        self,
        goal_repo,  # AsyncSqlAlchemySavingsGoalRepository
        account_repo,  # AsyncSqlAlchemyAccountRepository
        txn_repo,  # AsyncSqlAlchemyTransactionRepository
    ):
        self.goal_repo = goal_repo
        self.account_repo = account_repo
        self.txn_repo = txn_repo

    async def list_goals(self, acc_no: str) -> list[SavingsGoal]:
        return await self.goal_repo.get_by_account(acc_no)

    async def create_goal(
        self, acc_no: str, name: str, target_amount: Decimal, target_date: str | None = None
    ) -> ServiceResult:
        if not name or len(name) < 2:
            return ServiceResult(success=False, message="Goal name must be at least 2 characters.")
        if target_amount <= 0:
            return ServiceResult(success=False, message="Target amount must be positive.")

        goal = SavingsGoal(
            goal_id=generate_goal_id(),
            account_number=acc_no,
            name=name,
            target_amount=target_amount,
            target_date=target_date,
        )
        await self.goal_repo.create(goal)
        await self.goal_repo.commit()
        return ServiceResult(success=True, message=f"Goal '{name}' created!")

    async def contribute(self, acc_no: str, goal_id: str, amount: Decimal) -> ServiceResult:
        if amount <= 0:
            return ServiceResult(success=False, message="Amount must be positive.")

        account = await self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")
        if amount > account.balance:
            return ServiceResult(success=False, message="Insufficient balance.")

        goal = await self.goal_repo.get(goal_id)
        if goal is None:
            return ServiceResult(success=False, message="Goal not found.")

        # Deduct from account
        account.balance -= amount
        await self.account_repo.update(account)

        # Log transfer-out transaction
        txn = Transaction(
            txn_id=generate_transaction_id(),
            account_number=acc_no,
            type=TransactionType.TRANSFER_OUT,
            amount=amount,
            balance=account.balance,
            description=f"Savings goal: {goal.name}",
            category="Savings",
        )
        await self.txn_repo.create(txn)

        # Contribute to goal
        await self.goal_repo.contribute(goal_id, amount)
        await self.account_repo.commit()

        return ServiceResult(
            success=True,
            message=f"{fmt_currency(float(amount))} contributed to '{goal.name}'!",
        )

    async def delete_goal(self, acc_no: str, goal_id: str) -> ServiceResult:
        goal = await self.goal_repo.get(goal_id)
        if goal is None:
            return ServiceResult(success=False, message="Goal not found.")

        refund = goal.current_amount
        name = goal.name
        await self.goal_repo.delete(goal_id)

        # Refund to balance
        if refund > 0:
            account = await self.account_repo.get(acc_no)
            if account:
                account.balance += refund
                await self.account_repo.update(account)

        await self.goal_repo.commit()
        return ServiceResult(success=True, message=f"Goal '{name}' deleted. Amount refunded.")
