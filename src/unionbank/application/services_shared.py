"""
application/services_shared.py  –  Shared utilities for service classes.

Contains per-account concurrency locks, circuit breakers, and common imports.
Extracted from services.py for focused maintenance.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from collections.abc import Generator
from contextlib import contextmanager

import pybreaker

from unionbank.config import settings


# ── Circuit breaker for notifications ──
NOTIFICATION_BREAKER = pybreaker.CircuitBreaker(
    fail_max=5,
    reset_timeout=30,
)

# ── Per-account concurrency lock ──
_account_locks: dict[str, threading.Lock] = defaultdict(threading.Lock)


@contextmanager
def _account_lock(*acc_nos: str) -> Generator[None, None, None]:
    """
    Context manager that acquires per-account locks in sorted order.

    Acquires locks for *all* given accounts in ascending account-number order,
    guaranteeing deadlock-free acquisition when multiple accounts are involved
    (e.g. transfer needs both sender and receiver).  Locks are released in
    reverse order on exit.
    """
    sorted_nos = sorted(acc_nos)
    for acc_no in sorted_nos:
        _account_locks[acc_no].acquire()
    try:
        yield
    finally:
        for acc_no in sorted_nos:
            _account_locks[acc_no].release()


# ── Constants ──
TRANSACTION_CATEGORIES = settings.TRANSACTION_CATEGORIES
MAX_LOGIN_ATTEMPTS = settings.MAX_LOGIN_ATTEMPTS
LOGIN_LOCKOUT_MINUTES = settings.LOGIN_LOCKOUT_MINUTES
