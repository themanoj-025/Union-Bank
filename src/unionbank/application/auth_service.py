"""
application/auth_service.py  –  Authentication and authorization use-cases.

Extracted from services.py for focused maintenance.
"""

from __future__ import annotations

from decimal import Decimal

import pybreaker

from unionbank.domain.entities import Account, ServiceResult
from unionbank.utils.formatting import generate_account_number
from unionbank.utils.hashing import hash_password, verify_password

from .interfaces import (
    AccountRepositoryProtocol,
    AdminRepositoryProtocol,
    LoginAttemptRepositoryProtocol,
    NotificationServiceProtocol,
    TokenVersionRepositoryProtocol,
)
from .services_shared import (
    MAX_LOGIN_ATTEMPTS,
    NOTIFICATION_BREAKER,
    LOGIN_LOCKOUT_MINUTES,
)


class AuthService:
    """Authentication and authorization use-cases."""

    def __init__(
        self,
        account_repo: AccountRepositoryProtocol,
        admin_repo: AdminRepositoryProtocol,
        login_attempt_repo: LoginAttemptRepositoryProtocol,
        token_version_repo: TokenVersionRepositoryProtocol | None = None,
        notif_service: NotificationServiceProtocol | None = None,
    ):
        self.account_repo = account_repo
        self.admin_repo = admin_repo
        self.login_attempt_repo = login_attempt_repo
        self.token_version_repo = token_version_repo
        self.notif_service = notif_service

    def customer_login(self, acc_no: str, password: str) -> ServiceResult:
        """Authenticate a customer login."""
        is_locked, remaining = self.login_attempt_repo.is_locked(acc_no)
        if is_locked:
            return ServiceResult(
                success=False,
                message=f"Account locked. Try again in {remaining} minute(s).",
            )

        account = self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")

        if account.is_frozen:
            return ServiceResult(
                success=False, message="Account is frozen. Please contact the bank."
            )

        if not account.is_active:
            return ServiceResult(success=False, message="Account has been closed.")

        if not verify_password(password, account.password):
            remaining = self.login_attempt_repo.record_failure(
                acc_no, MAX_LOGIN_ATTEMPTS, LOGIN_LOCKOUT_MINUTES
            )
            self.login_attempt_repo.commit()
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

        self.login_attempt_repo.reset(acc_no)
        self.login_attempt_repo.commit()
        return ServiceResult(success=True, data={"account_number": acc_no, "role": "customer"})

    def customer_register(
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
        self.account_repo.create(account)
        self.account_repo.commit()

        if self.notif_service:
            try:
                NOTIFICATION_BREAKER.call(self.notif_service.notify_welcome)(acc_no)
            except pybreaker.CircuitBreakerError:
                from unionbank.utils.logger import logger

                logger.warning("Notification circuit breaker open, skipping welcome notification")
            except (OSError, ValueError, TypeError, AttributeError):
                from unionbank.utils.logger import logger

                logger.warning("Failed to send welcome notification", exc_info=True)

        return ServiceResult(
            success=True,
            message=f"Account created successfully! Account number: {acc_no}",
            data={"account_number": acc_no},
        )

    def admin_login(self, username: str, password: str) -> ServiceResult:
        """Authenticate an admin login."""
        lock_key = f"admin_{username}"
        is_locked, remaining = self.login_attempt_repo.is_locked(lock_key)
        if is_locked:
            return ServiceResult(
                success=False,
                message=f"Admin account locked. Try again in {remaining} minute(s).",
            )

        admin = self.admin_repo.get_by_username(username)
        if admin and verify_password(password, admin.password):
            self.login_attempt_repo.reset(lock_key)
            self.login_attempt_repo.commit()
            return ServiceResult(success=True, data={"username": username, "role": "admin"})

        remaining = self.login_attempt_repo.record_failure(
            lock_key, MAX_LOGIN_ATTEMPTS, LOGIN_LOCKOUT_MINUTES
        )
        self.login_attempt_repo.commit()
        if remaining > 0:
            return ServiceResult(
                success=False,
                message=f"Invalid credentials. {remaining} attempt(s) remaining.",
            )
        return ServiceResult(
            success=False,
            message=f"Admin account locked for {LOGIN_LOCKOUT_MINUTES} minutes.",
        )
