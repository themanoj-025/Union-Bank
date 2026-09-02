"""Tests for UNION-BANK- services_pkg."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit



class TestAccountService:
    """Tests for account_service."""

    def test_create_account(self) -> None:
        from unionbank.application.services_pkg.account_service import AccountService

        repo = MagicMock()
        repo.get_all.return_value = []
        svc = AccountService(repo)
        result = svc.create_account("John Doe", "john@test.com", "1234567890", 1000.0)
        assert result is not None
        assert result.name == "John Doe"

    def test_get_account(self) -> None:
        from unionbank.application.services_pkg.account_service import AccountService

        repo = MagicMock()
        acc = MagicMock()
        acc.account_number = "123"
        repo.get_by_number.return_value = acc
        svc = AccountService(repo)
        result = svc.get_account("123")
        assert result is acc

    def test_get_account_not_found(self) -> None:
        from unionbank.application.services_pkg.account_service import AccountService

        repo = MagicMock()
        repo.get_by_number.return_value = None
        svc = AccountService(repo)
        result = svc.get_account("999")
        assert result is None

    def test_list_accounts(self) -> None:
        from unionbank.application.services_pkg.account_service import AccountService

        repo = MagicMock()
        repo.get_all.return_value = [MagicMock(), MagicMock()]
        svc = AccountService(repo)
        result = svc.list_accounts()
        assert len(result) == 2


class TestAuthService:
    """Tests for auth_service."""

    def test_authenticate_success(self) -> None:
        from unionbank.application.services_pkg.auth_service import AuthService

        repo = MagicMock()
        admin = MagicMock()
        admin.username = "admin"
        admin.verify_password.return_value = True
        repo.get_admin.return_value = admin
        svc = AuthService(repo)
        result = svc.authenticate("admin", "password123")
        assert result is True

    def test_authenticate_wrong_password(self) -> None:
        from unionbank.application.services_pkg.auth_service import AuthService

        repo = MagicMock()
        admin = MagicMock()
        admin.username = "admin"
        admin.verify_password.return_value = False
        repo.get_admin.return_value = admin
        svc = AuthService(repo)
        result = svc.authenticate("admin", "wrong")
        assert result is False

    def test_authenticate_nonexistent_user(self) -> None:
        from unionbank.application.services_pkg.auth_service import AuthService

        repo = MagicMock()
        repo.get_admin.return_value = None
        svc = AuthService(repo)
        result = svc.authenticate("ghost", "pwd")
        assert result is False


class TestTransactionService:
    """Tests for transaction_service."""

    def test_get_transactions(self) -> None:
        from unionbank.application.services_pkg.transaction_service import TransactionService

        repo = MagicMock()
        repo.get_by_account.return_value = [MagicMock(), MagicMock()]
        svc = TransactionService(repo)
        result = svc.get_transactions("123")
        assert len(result) == 2

    def test_get_transactions_empty(self) -> None:
        from unionbank.application.services_pkg.transaction_service import TransactionService

        repo = MagicMock()
        repo.get_by_account.return_value = []
        svc = TransactionService(repo)
        result = svc.get_transactions("123")
        assert len(result) == 0


class TestAdminService:
    """Tests for admin_service."""

    def test_get_all_accounts(self) -> None:
        from unionbank.application.services_pkg.admin_service import AdminService

        svc = AdminService(MagicMock())
        svc.account_repo = MagicMock()
        svc.account_repo.get_all.return_value = [MagicMock(), MagicMock()]
        result = svc.get_all_accounts()
        assert len(result) == 2

    def test_get_account_count(self) -> None:
        from unionbank.application.services_pkg.admin_service import AdminService

        svc = AdminService(MagicMock())
        svc.account_repo = MagicMock()
        svc.account_repo.get_all.return_value = [MagicMock()]
        result = svc.get_account_count()
        assert result == 1
