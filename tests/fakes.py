"""
tests/fakes.py  –  In-memory repository fakes for unit testing.

Each fake implements the corresponding Protocol from application/interfaces.py
using plain dicts/lists instead of SQLite. This makes unit tests:
- Blazingly fast (no I/O, no DB setup)
- Deterministic (no shared state between tests when fresh instance created)
- Easy to debug (inspectable in-memory state)

Simulated DB Failures:
    Fakes can optionally simulate database errors to test error handling:
        fake.simulate_duplicate_key = True   # raises on duplicate create()
        fake.simulate_fk_violation = True    # raises on FK constraint
        fake.simulate_race_condition = True  # fails atomic operations randomly
        fake.simulate_timeout = True         # hangs the commit() call

    Use these in tests that verify graceful handling of database errors.
    Fakes default to realistic behavior (no errors).

Implementation split across:
- fakes_helpers.py: exception classes and _utcnow()
- fakes_repositories.py: Account, Transaction, Admin, SavingsGoal, LoginAttempt repos
- fakes_repositories_ext.py: Token, Notification, NotificationPref, RefreshToken, AuditLog repos
"""

from __future__ import annotations

from datetime import datetime, timedelta, UTC
from decimal import Decimal

from unionbank.application.interfaces import KeysetPage
from unionbank.domain.entities import (
    Account,
    AdminUser,
    LoginAttempt,
    Notification,
    NotificationPreference,
    RefreshToken,
    SavingsGoal,
    Transaction,
)

# Re-export helpers
from tests.fakes_helpers import (  # noqa: F401
    SimulatedDatabaseTimeout,
    SimulatedDuplicateKeyError,
    SimulatedForeignKeyViolation,
    SimulatedRaceConditionError,
    _utcnow,
)


class _FakeSession:
    """
    Minimal fake SQLAlchemy session stub for fake repositories.

    Provides a no-op begin_nested() context manager so services that use
    savepoints (e.g. atomic transfer) work transparently with fakes without
    requiring a real SQLAlchemy session.
    """

    def begin_nested(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        return False  # Do not suppress exceptions


# Re-export all repository fakes from split modules
from tests.fakes_repositories import (  # noqa: F401
    FakeAccountRepository,
    FakeAdminRepository,
    FakeLoginAttemptRepository,
    FakeSavingsGoalRepository,
    FakeTransactionRepository,
)
from tests.fakes_repositories_ext import (  # noqa: F401
    FakeAuditLogRepository,
    FakeNotificationPreferenceRepository,
    FakeNotificationRepository,
    FakeRefreshTokenRepository,
    FakeTokenVersionRepository,
)
