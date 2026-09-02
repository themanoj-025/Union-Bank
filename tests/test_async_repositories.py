"""Tests for infrastructure.async_repositories — async repository classes."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow


class TestAsyncRepositories:
    """Test async repository class imports and signatures."""

    def test_async_repositories_importable(self) -> None:
        from unionbank.infrastructure.async_repositories import (
            AsyncSqlAlchemyAccountRepository,
            AsyncSqlAlchemyAdminRepository,
            AsyncSqlAlchemyAuditLogRepository,
            AsyncSqlAlchemyIdempotencyRepository,
            AsyncSqlAlchemyLoanRepository,
            AsyncSqlAlchemyLoginAttemptRepository,
            AsyncSqlAlchemyNotificationPreferenceRepository,
            AsyncSqlAlchemyNotificationRepository,
            AsyncSqlAlchemyRefreshTokenRepository,
            AsyncSqlAlchemySavingsGoalRepository,
            AsyncSqlAlchemyTokenVersionRepository,
            AsyncSqlAlchemyTransactionRepository,
        )
        assert AsyncSqlAlchemyAccountRepository is not None
        assert AsyncSqlAlchemyTransactionRepository is not None


class TestAsyncAccountRepo:
    """Test AsyncSqlAlchemyAccountRepository class."""

    def test_class_exists(self) -> None:
        from unionbank.infrastructure.async_account_repo import AsyncSqlAlchemyAccountRepository
        import inspect
        assert inspect.isclass(AsyncSqlAlchemyAccountRepository)

    def test_has_required_methods(self) -> None:
        from unionbank.infrastructure.async_account_repo import AsyncSqlAlchemyAccountRepository
        methods = ["get", "get_all", "exists", "create", "update", "commit"]
        for method in methods:
            assert hasattr(AsyncSqlAlchemyAccountRepository, method), f"Missing {method}"

    def test_init_requires_session(self) -> None:
        from unionbank.infrastructure.async_account_repo import AsyncSqlAlchemyAccountRepository
        import inspect
        sig = inspect.signature(AsyncSqlAlchemyAccountRepository.__init__)
        assert "session" in sig.parameters


class TestAsyncTransactionRepo:
    """Test AsyncSqlAlchemyTransactionRepository class."""

    def test_class_exists(self) -> None:
        from unionbank.infrastructure.async_transaction_repo import AsyncSqlAlchemyTransactionRepository
        import inspect
        assert inspect.isclass(AsyncSqlAlchemyTransactionRepository)

    def test_has_required_methods(self) -> None:
        from unionbank.infrastructure.async_transaction_repo import AsyncSqlAlchemyTransactionRepository
        methods = ["get", "get_by_account", "create", "commit"]
        for method in methods:
            assert hasattr(AsyncSqlAlchemyTransactionRepository, method), f"Missing {method}"


class TestAsyncLoanRepo:
    """Test AsyncSqlAlchemyLoanRepository class."""

    def test_class_exists(self) -> None:
        from unionbank.infrastructure.async_loan_repo import AsyncSqlAlchemyLoanRepository
        import inspect
        assert inspect.isclass(AsyncSqlAlchemyLoanRepository)

    def test_has_required_methods(self) -> None:
        from unionbank.infrastructure.async_loan_repo import AsyncSqlAlchemyLoanRepository
        methods = ["get", "get_by_account", "create", "update", "commit"]
        for method in methods:
            assert hasattr(AsyncSqlAlchemyLoanRepository, method), f"Missing {method}"


class TestAsyncAuthRepo:
    """Test AsyncSqlAlchemyAdminRepository class."""

    def test_class_exists(self) -> None:
        from unionbank.infrastructure.async_auth_repo import AsyncSqlAlchemyAdminRepository
        import inspect
        assert inspect.isclass(AsyncSqlAlchemyAdminRepository)


class TestAsyncNotificationRepo:
    """Test AsyncSqlAlchemyNotificationRepository class."""

    def test_class_exists(self) -> None:
        from unionbank.infrastructure.async_notification_repo import AsyncSqlAlchemyNotificationRepository
        import inspect
        assert inspect.isclass(AsyncSqlAlchemyNotificationRepository)

    def test_has_required_methods(self) -> None:
        from unionbank.infrastructure.async_notification_repo import AsyncSqlAlchemyNotificationRepository
        methods = ["get", "get_by_account", "create", "mark_as_read", "mark_all_as_read"]
        for method in methods:
            assert hasattr(AsyncSqlAlchemyNotificationRepository, method), f"Missing {method}"


class TestAsyncSavingsGoalRepo:
    """Test AsyncSqlAlchemySavingsGoalRepository class."""

    def test_class_exists(self) -> None:
        from unionbank.infrastructure.async_account_repo import AsyncSqlAlchemySavingsGoalRepository
        import inspect
        assert inspect.isclass(AsyncSqlAlchemySavingsGoalRepository)

    def test_has_required_methods(self) -> None:
        from unionbank.infrastructure.async_account_repo import AsyncSqlAlchemySavingsGoalRepository
        methods = ["get", "get_by_account", "create", "update", "delete"]
        for method in methods:
            assert hasattr(AsyncSqlAlchemySavingsGoalRepository, method), f"Missing {method}"


class TestAsyncContainer:
    """Test async container module."""

    def test_async_container_importable(self) -> None:
        import unionbank.infrastructure.async_container as mod
        assert hasattr(mod, "__file__")
