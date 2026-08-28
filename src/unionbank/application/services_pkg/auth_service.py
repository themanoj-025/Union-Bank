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



class AsyncAuthService:
    """Async authentication and authorization use-cases."""

    def __init__(
        self,
        account_repo,  # AsyncSqlAlchemyAccountRepository
        admin_repo,  # AsyncSqlAlchemyAdminRepository
        login_attempt_repo,  # AsyncSqlAlchemyLoginAttemptRepository
        token_version_repo=None,
        notif_service=None,
    ):
        self.account_repo = account_repo
        self.admin_repo = admin_repo
        self.login_attempt_repo = login_attempt_repo
        self.token_version_repo = token_version_repo
        self.notif_service = notif_service

    async def customer_login(self, acc_no: str, password: str) -> ServiceResult:
        """Authenticate a customer login."""
        # Rate limiting check
        is_locked, remaining = await self.login_attempt_repo.is_locked(acc_no)
        if is_locked:
            return ServiceResult(
                success=False,
                message=f"Account locked. Try again in {remaining} minute(s).",
            )

        account = await self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")

        if account.is_frozen:
            return ServiceResult(
                success=False, message="Account is frozen. Please contact the bank."
            )

        if not account.is_active:
            return ServiceResult(success=False, message="Account has been closed.")

        if not verify_password(password, account.password):
            remaining = await self.login_attempt_repo.record_failure(
                acc_no, MAX_LOGIN_ATTEMPTS, LOGIN_LOCKOUT_MINUTES
            )
            await self.login_attempt_repo.commit()
            if remaining > 0:
                return ServiceResult(
                    success=False,
                    message=f"Incorrect password. {remaining} attempt(s) remaining.",
                )
            else:
                return ServiceResult(
                    success=False,
                    message=f"Incorrect password. Account locked for {LOGIN_LOCKOUT_MINUTES} minutes.",
                )

        await self.login_attempt_repo.reset(acc_no)
        await self.login_attempt_repo.commit()
        return ServiceResult(success=True, data={"account_number": acc_no, "role": "customer"})

    async def customer_register(
        self,
        name: str,
        age: int,
        gender: str,
        mobile: str,
        email: str,
        password: str,
    ) -> ServiceResult:
        """Register a new customer account."""
        acc_no = generate_account_number()
        account = Account(
            account_number=acc_no,
            name=name,
            age=age,
            gender=gender,
            mobile=mobile,
            email=email,
            password=hash_password(password),
            balance=Decimal("0.00"),
            is_active=True,
            is_frozen=False,
        )
        await self.account_repo.create(account)
        await self.account_repo.commit()

        # Send welcome notification (non-fatal if fails)
        if self.notif_service:
            try:
                await self.notif_service.notify_welcome(acc_no)
            except (OSError, TimeoutError):
                from unionbank.utils.logger import logger

                logger.warning("Failed to send welcome notification", exc_info=True)

        return ServiceResult(
            success=True,
            message=f"Account created successfully! Account number: {acc_no}",
            data={"account_number": acc_no},
        )

    async def admin_login(self, username: str, password: str) -> ServiceResult:
        """Authenticate an admin login."""
        lock_key = f"admin_{username}"
        is_locked, remaining = await self.login_attempt_repo.is_locked(lock_key)
        if is_locked:
            return ServiceResult(
                success=False,
                message=f"Admin account locked. Try again in {remaining} minute(s).",
            )

        admin = await self.admin_repo.get_by_username(username)
        if admin and verify_password(password, admin.password):
            await self.login_attempt_repo.reset(lock_key)
            await self.login_attempt_repo.commit()
            return ServiceResult(success=True, data={"username": username, "role": "admin"})

        remaining = await self.login_attempt_repo.record_failure(
            lock_key, MAX_LOGIN_ATTEMPTS, LOGIN_LOCKOUT_MINUTES
        )
        await self.login_attempt_repo.commit()
        if remaining > 0:
            return ServiceResult(
                success=False,
                message=f"Invalid credentials. {remaining} attempt(s) remaining.",
            )
        return ServiceResult(
            success=False,
            message=f"Admin account locked for {LOGIN_LOCKOUT_MINUTES} minutes.",
        )


#  Async Admin Service


