"""
Simulated DB failure exceptions and shared helpers for test fakes.

These exceptions allow unit tests to verify graceful handling of
database errors without needing a real database.
"""

from __future__ import annotations

from datetime import datetime, UTC


class SimulatedDuplicateKeyError(Exception):
    """
    Raised when a fake repository simulates a unique constraint violation.

    The real DB raises IntegrityError on duplicate account_number or email.
    This fake mirrors that behavior when simulate_duplicate_key is True.

    Usage:
        fake.simulate_duplicate_key = True
        with pytest.raises(SimulatedDuplicateKeyError):
            repo.create(account)
    """


class SimulatedForeignKeyViolation(Exception):
    """
    Raised when a fake repository simulates a foreign key violation.

    The real DB raises IntegrityError when a referenced row doesn't exist.
    Usage:
        fake.simulate_fk_violation = True
        with pytest.raises(SimulatedForeignKeyViolation):
            repo.create(txn_with_bad_account)
    """


class SimulatedRaceConditionError(Exception):
    """
    Raised when a fake repository simulates a concurrent-write race.

    The real DB raises OperationalError (database is locked) in WAL mode
    under high concurrency. This fake mirrors that behavior for testing
    retry logic.

    Usage:
        fake.simulate_race_condition = True
        with pytest.raises(SimulatedRaceConditionError):
            repo.transfer_money(...)
    """


class SimulatedDatabaseTimeout(Exception):
    """
    Raised when a fake repository simulates a database timeout.

    Usage:
        fake.simulate_timeout = True
        with pytest.raises(SimulatedDatabaseTimeout):
            repo.commit()
    """


def _utcnow() -> datetime:
    return datetime.now(UTC)
