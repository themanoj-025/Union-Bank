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
import json
from datetime import datetime
from decimal import Decimal

from unionbank.config import settings
from unionbank.domain.clock import utcnow as _utcnow
from unionbank.domain.entities import (
    Account,
    IdempotencyRecord,
    SavingsGoal,
    ServiceResult,
    Transaction,
    TransactionType,
    TransferResult,
)
from unionbank.domain.interest import calculate_monthly_interest
from unionbank.utils.formatting import (
    fmt_currency,
    generate_account_number,
    generate_goal_id,
    generate_transaction_id,
)
from unionbank.utils.hashing import hash_password, verify_password

try:
    from sqlalchemy.exc import SQLAlchemyError
except ImportError:
    SQLAlchemyError = Exception  # fallback if sqlalchemy not installed

from .interfaces import (
    KeysetPage,
)

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



class AsyncAccountService:
    """Async customer account management use-cases."""

    def __init__(
        self,
        account_repo,  # AsyncSqlAlchemyAccountRepository
        txn_repo,  # AsyncSqlAlchemyTransactionRepository
        token_version_repo=None,
    ):
        self.account_repo = account_repo
        self.txn_repo = txn_repo
        self.token_version_repo = token_version_repo

    async def get_profile(self, acc_no: str) -> Account | None:
        return await self.account_repo.get(acc_no)

    async def update_profile(self, acc_no: str, **kwargs) -> ServiceResult:
        account = await self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")

        for key, value in kwargs.items():
            if hasattr(account, key) and value is not None:
                setattr(account, key, value)

        await self.account_repo.update(account)
        await self.account_repo.commit()
        return ServiceResult(success=True, message="Profile updated successfully.")

    async def change_password(self, acc_no: str, current_pwd: str, new_pwd: str) -> ServiceResult:
        account = await self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")

        if not verify_password(current_pwd, account.password):
            return ServiceResult(success=False, message="Incorrect current password.")

        account.password = hash_password(new_pwd)
        await self.account_repo.update(account)

        # Increment token version to invalidate all existing JWTs
        if self.token_version_repo:
            await self.token_version_repo.increment(acc_no)

        await self.account_repo.commit()
        return ServiceResult(success=True, message="Password changed successfully.")

    async def close_account(self, acc_no: str, password: str) -> ServiceResult:
        account = await self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")

        if not verify_password(password, account.password):
            return ServiceResult(success=False, message="Incorrect password.")

        account.is_active = False
        await self.account_repo.update(account)
        await self.account_repo.commit()
        return ServiceResult(success=True, message="Account closed successfully.")

    async def get_balance(self, acc_no: str) -> Decimal | None:
        account = await self.account_repo.get(acc_no)
        return account.balance if account else None


#  Async Auth Service


