"""
async_repositories.py – Async SQLAlchemy repository implementations.

Thin coordinator that re-exports all async repository classes from
focused modules. All domain logic lives in:

  - async_account_repo.py      (Account, SavingsGoal)
  - async_transaction_repo.py  (Transaction, Idempotency, AuditLog)
  - async_loan_repo.py         (Loan)
  - async_auth_repo.py         (Admin, LoginAttempt, TokenVersion, RefreshToken)
  - async_notification_repo.py (Notification, NotificationPreference)

Each repository mirrors its synchronous counterpart in repositories.py but
uses ``AsyncSession`` and ``await session.execute(select(...))`` for all
database operations. These are used when the application is configured with
a PostgreSQL DATABASE_URL (async via asyncpg).

SQLite does NOT support async access, so these repos will raise at runtime
if called with a SQLite database URL.
"""

from unionbank.infrastructure.async_account_repo import (
    AsyncSqlAlchemyAccountRepository,
    AsyncSqlAlchemySavingsGoalRepository,
)
from unionbank.infrastructure.async_auth_repo import (
    AsyncSqlAlchemyAdminRepository,
    AsyncSqlAlchemyLoginAttemptRepository,
    AsyncSqlAlchemyRefreshTokenRepository,
    AsyncSqlAlchemyTokenVersionRepository,
)
from unionbank.infrastructure.async_loan_repo import AsyncSqlAlchemyLoanRepository
from unionbank.infrastructure.async_notification_repo import (
    AsyncSqlAlchemyNotificationPreferenceRepository,
    AsyncSqlAlchemyNotificationRepository,
)
from unionbank.infrastructure.async_transaction_repo import (
    AsyncSqlAlchemyAuditLogRepository,
    AsyncSqlAlchemyIdempotencyRepository,
    AsyncSqlAlchemyTransactionRepository,
)

__all__ = [
    "AsyncSqlAlchemyAccountRepository",
    "AsyncSqlAlchemyAdminRepository",
    "AsyncSqlAlchemyAuditLogRepository",
    "AsyncSqlAlchemyIdempotencyRepository",
    "AsyncSqlAlchemyLoanRepository",
    "AsyncSqlAlchemyLoginAttemptRepository",
    "AsyncSqlAlchemyNotificationPreferenceRepository",
    "AsyncSqlAlchemyNotificationRepository",
    "AsyncSqlAlchemyRefreshTokenRepository",
    "AsyncSqlAlchemySavingsGoalRepository",
    "AsyncSqlAlchemyTokenVersionRepository",
    "AsyncSqlAlchemyTransactionRepository",
]
