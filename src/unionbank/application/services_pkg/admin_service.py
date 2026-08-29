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

from unionbank.config import settings
from unionbank.domain.entities import (
    Account,
    ServiceResult,
)
from unionbank.utils.formatting import (
    fmt_currency,
)
from unionbank.utils.hashing import hash_password, verify_password

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



class AsyncAdminService:
    """Async admin use-cases for account oversight."""

    def __init__(
        self,
        account_repo,  # AsyncSqlAlchemyAccountRepository
        txn_repo,  # AsyncSqlAlchemyTransactionRepository
        admin_repo,  # AsyncSqlAlchemyAdminRepository
        audit_log_repo=None,
        notif_service=None,
    ):
        self.account_repo = account_repo
        self.txn_repo = txn_repo
        self.admin_repo = admin_repo
        self.audit_log_repo = audit_log_repo
        self.notif_service = notif_service

    async def _audit_log(
        self,
        actor: str,
        action: str,
        target: str | None = None,
        details: str | None = None,
        ip_address: str | None = None,
        reason: str | None = None,
    ) -> None:
        """Write an immutable audit log entry."""
        if self.audit_log_repo:
            await self.audit_log_repo.log(
                actor=actor,
                action=action,
                target=target,
                details=details,
                ip_address=ip_address,
                reason=reason,
            )
            await self.audit_log_repo.commit()

    async def list_accounts(self) -> list[Account]:
        return await self.account_repo.get_all()

    async def search_accounts(self, query: str) -> list[Account]:
        return await self.account_repo.search(query)

    async def freeze_account(
        self, acc_no: str, actor: str = "admin", reason: str | None = None
    ) -> ServiceResult:
        account = await self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")
        if not account.is_active and not account.is_frozen:
            return ServiceResult(success=False, message="Account is permanently closed.")
        if account.is_frozen:
            return ServiceResult(success=False, message=f"Account {acc_no} is already frozen.")

        await self.account_repo.set_frozen(acc_no, True)
        await self.account_repo.set_active(acc_no, False)
        await self.account_repo.commit()

        await self._audit_log(
            actor=actor,
            action="freeze",
            target=acc_no,
            details=f"Frozen account for {account.name}",
            reason=reason,
        )

        if self.notif_service:
            try:
                await self.notif_service.notify_account_frozen(acc_no, reason=reason or "")
            except (OSError, TimeoutError):
                from unionbank.utils.logger import logger

                logger.warning("Failed to send freeze notification", exc_info=True)

        return ServiceResult(
            success=True, message=f"Account {acc_no} ({account.name}) has been frozen."
        )

    async def unfreeze_account(
        self, acc_no: str, actor: str = "admin", reason: str | None = None
    ) -> ServiceResult:
        account = await self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")
        if not account.is_frozen:
            return ServiceResult(success=False, message=f"Account {acc_no} is not frozen.")

        await self.account_repo.set_frozen(acc_no, False)
        await self.account_repo.commit()

        await self._audit_log(
            actor=actor,
            action="unfreeze",
            target=acc_no,
            details=f"Unfrozen account for {account.name}",
            reason=reason,
        )

        if self.notif_service:
            try:
                await self.notif_service.notify_account_unfrozen(acc_no)
            except (OSError, TimeoutError):
                from unionbank.utils.logger import logger

                logger.warning("Failed to send unfreeze notification", exc_info=True)

        return ServiceResult(
            success=True, message=f"Account {acc_no} ({account.name}) has been unfrozen."
        )

    async def delete_account(
        self, acc_no: str, actor: str = "admin", reason: str | None = None
    ) -> ServiceResult:
        account = await self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")

        acc_name = account.name
        await self.account_repo.delete(acc_no)
        await self.account_repo.commit()

        await self._audit_log(
            actor=actor,
            action="delete",
            target=acc_no,
            details=f"Deleted account for {acc_name}",
            reason=reason,
        )
        return ServiceResult(
            success=True, message=f"Account {acc_no} ({acc_name}) has been deleted."
        )

    async def list_accounts_paginated(
        self, page: int = 1, per_page: int = 20
    ) -> tuple[list[Account], int]:
        """Get accounts with pagination."""
        return await self.account_repo.get_all_paginated(page=page, per_page=per_page)

    async def get_statistics(self) -> dict:
        """Compute bank-wide statistics."""
        stats = await self.account_repo.get_statistics()

        total_txns = await self.txn_repo.count()
        total_dep = float(await self.txn_repo.total_by_type("DEPOSIT"))
        total_with = float(await self.txn_repo.total_by_type("WITHDRAW"))
        total_trans = float(await self.txn_repo.total_by_type("TRANSFER_OUT"))
        category_totals = await self.txn_repo.get_category_totals()
        sorted_cats = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)

        return {
            **stats,
            "total_balance_formatted": fmt_currency(stats["total_balance"]),
            "total_dep": total_dep,
            "total_with": total_with,
            "total_trans": total_trans,
            "total_txns": total_txns,
            "sorted_categories": [{"name": c[0], "total": float(c[1])} for c in sorted_cats[:8]],
        }

    async def change_admin_password(
        self, username: str, current_pwd: str, new_pwd: str, actor: str = "admin"
    ) -> ServiceResult:
        admin = await self.admin_repo.get_by_username(username)
        if admin is None:
            return ServiceResult(success=False, message="Admin not found.")
        if not verify_password(current_pwd, admin.password):
            return ServiceResult(success=False, message="Incorrect current password.")

        await self.admin_repo.update_password(username, hash_password(new_pwd))
        await self.admin_repo.commit()

        await self._audit_log(
            actor=actor,
            action="password_reset",
            target=username,
            details="Admin password changed",
        )
        return ServiceResult(success=True, message="Admin password changed successfully.")


#  Async Savings Goal Service


