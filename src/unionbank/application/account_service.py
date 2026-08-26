"""
application/account_service.py  –  Account management and admin use-cases.

Contains AccountService (customer profile, balance, password) and
AdminService (freeze, unfreeze, delete, statistics, audit).
Extracted from services.py for focused maintenance.
"""

from __future__ import annotations

from decimal import Decimal

import pybreaker

from unionbank.domain.entities import Account, ServiceResult
from unionbank.utils.formatting import fmt_currency
from unionbank.utils.hashing import hash_password, verify_password

from .interfaces import (
    AccountRepositoryProtocol,
    AdminRepositoryProtocol,
    AuditLogRepositoryProtocol,
    NotificationServiceProtocol,
    TokenVersionRepositoryProtocol,
    TransactionRepositoryProtocol,
)
from .services_shared import NOTIFICATION_BREAKER


# ── Account Service ──


class AccountService:
    """Customer account management use-cases."""

    def __init__(
        self,
        account_repo: AccountRepositoryProtocol,
        txn_repo: TransactionRepositoryProtocol,
        token_version_repo: TokenVersionRepositoryProtocol | None = None,
    ):
        self.account_repo = account_repo
        self.txn_repo = txn_repo
        self.token_version_repo = token_version_repo

    def get_profile(self, acc_no: str) -> Account | None:
        return self.account_repo.get(acc_no)

    def update_profile(self, acc_no: str, **kwargs) -> ServiceResult:
        account = self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")

        for key, value in kwargs.items():
            if hasattr(account, key) and value is not None:
                setattr(account, key, value)

        self.account_repo.update(account)
        self.account_repo.commit()
        return ServiceResult(success=True, message="Profile updated successfully.")

    def change_password(self, acc_no: str, current_pwd: str, new_pwd: str) -> ServiceResult:
        account = self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")

        if not verify_password(current_pwd, account.password):
            return ServiceResult(success=False, message="Incorrect current password.")

        account.password = hash_password(new_pwd)
        self.account_repo.update(account)

        if self.token_version_repo:
            self.token_version_repo.increment(acc_no)

        self.account_repo.commit()
        return ServiceResult(success=True, message="Password changed successfully.")

    def close_account(self, acc_no: str, password: str) -> ServiceResult:
        account = self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")

        if not verify_password(password, account.password):
            return ServiceResult(success=False, message="Incorrect password.")

        account.is_active = False
        self.account_repo.update(account)
        self.account_repo.commit()
        return ServiceResult(success=True, message="Account closed successfully.")

    def get_balance(self, acc_no: str) -> Decimal | None:
        account = self.account_repo.get(acc_no)
        return account.balance if account else None


# ── Admin Service ──


class AdminService:
    """Admin use-cases for account oversight."""

    def __init__(
        self,
        account_repo: AccountRepositoryProtocol,
        txn_repo: TransactionRepositoryProtocol,
        admin_repo: AdminRepositoryProtocol,
        audit_log_repo: AuditLogRepositoryProtocol | None = None,
        notif_service: NotificationServiceProtocol | None = None,
    ):
        self.account_repo = account_repo
        self.txn_repo = txn_repo
        self.admin_repo = admin_repo
        self.audit_log_repo = audit_log_repo
        self.notif_service = notif_service

    def _audit_log(
        self,
        actor: str,
        action: str,
        target: str | None = None,
        details: str | None = None,
        ip_address: str | None = None,
        reason: str | None = None,
    ) -> None:
        """Write an immutable audit log entry (silently skip if no repo configured)."""
        if self.audit_log_repo:
            self.audit_log_repo.log(
                actor=actor,
                action=action,
                target=target,
                details=details,
                ip_address=ip_address,
                reason=reason,
            )
            self.audit_log_repo.commit()

    def list_accounts(self) -> list[Account]:
        return self.account_repo.get_all()

    def search_accounts(self, query: str) -> list[Account]:
        return self.account_repo.search(query)

    def freeze_account(
        self, acc_no: str, actor: str = "admin", reason: str | None = None
    ) -> ServiceResult:
        account = self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")
        if not account.is_active and not account.is_frozen:
            return ServiceResult(success=False, message="Account is permanently closed.")
        if account.is_frozen:
            return ServiceResult(success=False, message=f"Account {acc_no} is already frozen.")

        self.account_repo.set_frozen(acc_no, True)
        self.account_repo.set_active(acc_no, False)
        self.account_repo.commit()

        self._audit_log(
            actor=actor,
            action="freeze",
            target=acc_no,
            details=f"Frozen account for {account.name}",
            reason=reason,
        )

        if self.notif_service:
            try:
                NOTIFICATION_BREAKER.call(self.notif_service.notify_account_frozen)(
                    acc_no, reason=reason or ""
                )
            except pybreaker.CircuitBreakerError:
                from unionbank.utils.logger import logger

                logger.warning("Notification circuit breaker open, skipping freeze notification")
            except (OSError, ValueError, TypeError, AttributeError):
                from unionbank.utils.logger import logger

                logger.warning("Failed to send freeze notification", exc_info=True)

        return ServiceResult(
            success=True, message=f"Account {acc_no} ({account.name}) has been frozen."
        )

    def unfreeze_account(
        self, acc_no: str, actor: str = "admin", reason: str | None = None
    ) -> ServiceResult:
        account = self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")
        if not account.is_frozen:
            return ServiceResult(success=False, message=f"Account {acc_no} is not frozen.")

        self.account_repo.set_frozen(acc_no, False)
        self.account_repo.commit()

        self._audit_log(
            actor=actor,
            action="unfreeze",
            target=acc_no,
            details=f"Unfrozen account for {account.name}",
            reason=reason,
        )

        if self.notif_service:
            try:
                NOTIFICATION_BREAKER.call(self.notif_service.notify_account_unfrozen)(acc_no)
            except pybreaker.CircuitBreakerError:
                from unionbank.utils.logger import logger

                logger.warning("Notification circuit breaker open, skipping unfreeze notification")
            except (OSError, ValueError, TypeError, AttributeError):
                from unionbank.utils.logger import logger

                logger.warning("Failed to send unfreeze notification", exc_info=True)

        return ServiceResult(
            success=True, message=f"Account {acc_no} ({account.name}) has been unfrozen."
        )

    def delete_account(
        self, acc_no: str, actor: str = "admin", reason: str | None = None
    ) -> ServiceResult:
        account = self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")

        acc_name = account.name
        self.account_repo.delete(acc_no)
        self.account_repo.commit()

        self._audit_log(
            actor=actor,
            action="delete",
            target=acc_no,
            details=f"Deleted account for {acc_name}",
            reason=reason,
        )
        return ServiceResult(
            success=True, message=f"Account {acc_no} ({acc_name}) has been deleted."
        )

    def list_accounts_paginated(
        self, page: int = 1, per_page: int = 20
    ) -> tuple[list[Account], int]:
        """Get accounts with pagination (delegates to the repository)."""
        return self.account_repo.get_all_paginated(page=page, per_page=per_page)

    def get_statistics(self) -> dict:
        """
        Compute bank-wide statistics using consolidated aggregate queries.
        """
        stats = self.account_repo.get_statistics()

        total_txns = self.txn_repo.count()
        total_dep = float(self.txn_repo.total_by_type("DEPOSIT"))
        total_with = float(self.txn_repo.total_by_type("WITHDRAW"))
        total_trans = float(self.txn_repo.total_by_type("TRANSFER_OUT"))
        category_totals = self.txn_repo.get_category_totals()
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

    def change_admin_password(
        self, username: str, current_pwd: str, new_pwd: str, actor: str = "admin"
    ) -> ServiceResult:
        admin = self.admin_repo.get_by_username(username)
        if admin is None:
            return ServiceResult(success=False, message="Admin not found.")
        if not verify_password(current_pwd, admin.password):
            return ServiceResult(success=False, message="Incorrect current password.")

        self.admin_repo.update_password(username, hash_password(new_pwd))
        self.admin_repo.commit()

        self._audit_log(
            actor=actor,
            action="password_reset",
            target=username,
            details="Admin password changed",
        )
        return ServiceResult(success=True, message="Admin password changed successfully.")
