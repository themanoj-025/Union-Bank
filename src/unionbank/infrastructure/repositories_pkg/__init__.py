"""
repositories_pkg — Focused SQLAlchemy repository implementations.

Each module contains 1-3 closely-related repository classes, split from the
monolithic repositories.py for maintainability.  The original ``repositories.py``
re-exports everything here so existing ``from ...repositories import X`` still works.
"""

from unionbank.infrastructure.repositories_pkg.account_repository import (
    SqlAlchemyAccountRepository,
)
from unionbank.infrastructure.repositories_pkg.transaction_repository import (
    SqlAlchemyTransactionRepository,
)
from unionbank.infrastructure.repositories_pkg.admin_repository import (
    SqlAlchemyAdminRepository,
    SqlAlchemyTokenVersionRepository,
)
from unionbank.infrastructure.repositories_pkg.auth_repository import (
    SqlAlchemyLoginAttemptRepository,
)
from unionbank.infrastructure.repositories_pkg.savings_loan_repository import (
    SqlAlchemyLoanRepository,
    SqlAlchemySavingsGoalRepository,
)
from unionbank.infrastructure.repositories_pkg.notification_repository import (
    SqlAlchemyNotificationPreferenceRepository,
    SqlAlchemyNotificationRepository,
    SqlAlchemyRefreshTokenRepository,
)
from unionbank.infrastructure.repositories_pkg.misc_repository import (
    SqlAlchemyAuditLogRepository,
    SqlAlchemyIdempotencyRepository,
)

__all__ = [
    "SqlAlchemyAccountRepository",
    "SqlAlchemyAdminRepository",
    "SqlAlchemyAuditLogRepository",
    "SqlAlchemyIdempotencyRepository",
    "SqlAlchemyLoanRepository",
    "SqlAlchemyLoginAttemptRepository",
    "SqlAlchemyNotificationPreferenceRepository",
    "SqlAlchemyNotificationRepository",
    "SqlAlchemyRefreshTokenRepository",
    "SqlAlchemySavingsGoalRepository",
    "SqlAlchemyTokenVersionRepository",
    "SqlAlchemyTransactionRepository",
]
