"""
application/services.py  –  Use-case service classes.

Thin coordinator that re-exports all service classes from the focused
sub-modules:

- auth_service.py      – authentication and authorization
- account_service.py   – account management and admin oversight
- transfer_service.py  – transactions (deposit, withdraw, transfer, interest)
- loan_service.py      – loans and savings goals
- services_shared.py   – shared utilities (locks, breakers, constants)
"""

# Re-export all service classes so existing imports keep working
from .auth_service import AuthService
from .account_service import AccountService, AdminService
from .transfer_service import TransactionService
from .loan_service import LoanService, SavingsGoalService

# Re-export shared utilities used by other modules
from .services_shared import (
    NOTIFICATION_BREAKER,
    TRANSACTION_CATEGORIES,
    _account_lock,
)

__all__ = [
    "AuthService",
    "AccountService",
    "AdminService",
    "TransactionService",
    "LoanService",
    "SavingsGoalService",
    "NOTIFICATION_BREAKER",
    "TRANSACTION_CATEGORIES",
    "_account_lock",
]

