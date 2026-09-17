"""
Tests for unionbank.application.services_pkg (the Async* services).

These exercise the async use-case layer against MagicMock repos with
pytest-asyncio in auto mode — no real database required.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from unionbank.application.services_pkg import (
    AsyncAccountService,
    AsyncAdminService,
    AsyncAuthService,
    AsyncTransactionService,
)

pytestmark = pytest.mark.unit


def _async_repo() -> MagicMock:
    """MagicMock whose attribute accesses return AsyncMock for coroutine use."""
    repo = MagicMock()
    repo.get = AsyncMock()
    repo.get_all = AsyncMock()
    repo.get_by_username = AsyncMock()
    repo.get_by_account = AsyncMock()
    repo.is_locked = AsyncMock(return_value=(False, 0))
    repo.record_failure = AsyncMock(return_value=1)
    repo.reset = AsyncMock()
    repo.commit = AsyncMock()
    return repo


class TestAsyncAccountService:
    """Tests for AsyncAccountService."""

    async def test_get_profile(self) -> None:
        repo = _async_repo()
        acc = MagicMock()
        acc.account_number = "123"
        repo.get.return_value = acc
        svc = AsyncAccountService(repo, MagicMock())
        result = await svc.get_profile("123")
        assert result is acc

    async def test_get_profile_not_found(self) -> None:
        repo = _async_repo()
        repo.get.return_value = None
        svc = AsyncAccountService(repo, MagicMock())
        result = await svc.get_profile("999")
        assert result is None

    async def test_get_balance(self) -> None:
        from decimal import Decimal

        repo = _async_repo()
        repo.get.return_value = MagicMock(balance=Decimal("500.00"))
        svc = AsyncAccountService(repo, MagicMock())
        result = await svc.get_balance("123")
        assert result == Decimal("500.00")


class TestAsyncAuthService:
    """Tests for AsyncAuthService.admin_login."""

    async def test_admin_login_success(self) -> None:
        from unionbank.utils.hashing import hash_password

        account_repo, admin_repo = _async_repo(), _async_repo()
        login_repo = _async_repo()
        admin = MagicMock()
        admin.username = "admin"
        admin.password = hash_password("password123")
        admin_repo.get_by_username.return_value = admin

        svc = AsyncAuthService(account_repo, admin_repo, login_repo)
        result = await svc.admin_login("admin", "password123")
        assert result.success is True

    async def test_admin_login_wrong_password(self) -> None:
        from unionbank.utils.hashing import hash_password

        account_repo, admin_repo = _async_repo(), _async_repo()
        login_repo = _async_repo()
        admin = MagicMock()
        admin.username = "admin"
        admin.password = hash_password("password123")
        admin_repo.get_by_username.return_value = admin

        svc = AsyncAuthService(account_repo, admin_repo, login_repo)
        result = await svc.admin_login("admin", "wrong")
        assert result.success is False

    async def test_admin_login_nonexistent_user(self) -> None:
        account_repo, admin_repo = _async_repo(), _async_repo()
        login_repo = _async_repo()
        admin_repo.get_by_username.return_value = None

        svc = AsyncAuthService(account_repo, admin_repo, login_repo)
        result = await svc.admin_login("ghost", "pwd")
        assert result.success is False


class TestAsyncTransactionService:
    """Tests for AsyncTransactionService statement accessors."""

    async def test_get_statement(self) -> None:
        repo = _async_repo()
        repo.get_by_account.return_value = [MagicMock(), MagicMock()]
        svc = AsyncTransactionService(MagicMock(), repo)
        result = await svc.get_statement("123")
        assert len(result) == 2

    async def test_get_statement_empty(self) -> None:
        repo = _async_repo()
        repo.get_by_account.return_value = []
        svc = AsyncTransactionService(MagicMock(), repo)
        result = await svc.get_statement("123")
        assert len(result) == 0


class TestAsyncAdminService:
    """Tests for AsyncAdminService."""

    async def test_list_accounts(self) -> None:
        account_repo = _async_repo()
        account_repo.get_all.return_value = [MagicMock(), MagicMock()]
        svc = AsyncAdminService(account_repo, MagicMock(), MagicMock())
        result = await svc.list_accounts()
        assert len(result) == 2

    async def test_list_accounts_empty(self) -> None:
        account_repo = _async_repo()
        account_repo.get_all.return_value = []
        svc = AsyncAdminService(account_repo, MagicMock(), MagicMock())
        result = await svc.list_accounts()
        assert len(result) == 0

    async def test_search_accounts(self) -> None:
        account_repo = _async_repo()
        account_repo.search = AsyncMock(return_value=[MagicMock()])
        svc = AsyncAdminService(account_repo, MagicMock(), MagicMock())
        result = await svc.search_accounts("John")
        assert len(result) == 1
