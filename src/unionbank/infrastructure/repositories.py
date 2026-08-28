"""
infrastructure/repositories.py  –  Backward-compatible re-exporter.

All repository implementations live in ``repositories_pkg/`` as focused modules.
This file re-exports every class so existing ``from ...repositories import X``
continues to work unchanged.
"""

from unionbank.infrastructure.repositories_pkg import (  # noqa: F401
    SqlAlchemyAccountRepository,
    SqlAlchemyAdminRepository,
    SqlAlchemyAuditLogRepository,
    SqlAlchemyIdempotencyRepository,
    SqlAlchemyLoanRepository,
    SqlAlchemyLoginAttemptRepository,
    SqlAlchemyNotificationPreferenceRepository,
    SqlAlchemyNotificationRepository,
    SqlAlchemyRefreshTokenRepository,
    SqlAlchemySavingsGoalRepository,
    SqlAlchemyTokenVersionRepository,
    SqlAlchemyTransactionRepository,
)
