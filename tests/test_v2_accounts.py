"""Tests for entrypoints.api.v2.accounts — V2 account endpoints."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow


class TestV2AccountRoutes:
    """Test V2 account route function signatures and imports."""

    def test_accounts_router_importable(self) -> None:
        from unionbank.entrypoints.api.v2.accounts import router
        assert router is not None

    def test_accounts_router_has_routes(self) -> None:
        from unionbank.entrypoints.api.v2.accounts import router
        routes = [r.path for r in router.routes]
        assert "/account/profile" in routes

    def test_get_profile_function_exists(self) -> None:
        from unionbank.entrypoints.api.v2.accounts import v2_get_profile
        import inspect
        sig = inspect.signature(v2_get_profile)
        assert "customer" in sig.parameters

    def test_update_profile_function_exists(self) -> None:
        from unionbank.entrypoints.api.v2.accounts import v2_update_profile
        import inspect
        sig = inspect.signature(v2_update_profile)
        assert "req" in sig.parameters
        assert "customer" in sig.parameters


class TestV2AuthRoutes:
    """Test V2 auth route function signatures."""

    def test_auth_router_importable(self) -> None:
        from unionbank.entrypoints.api.v2.auth import router
        assert router is not None

    def test_auth_router_has_routes(self) -> None:
        from unionbank.entrypoints.api.v2.auth import router
        routes = [r.path for r in router.routes]
        assert "/auth/login" in routes
        assert "/auth/register" in routes

    def test_login_function_exists(self) -> None:
        from unionbank.entrypoints.api.v2.auth import v2_customer_login
        import inspect
        sig = inspect.signature(v2_customer_login)
        assert "req" in sig.parameters
        assert "request" in sig.parameters
        assert "response" in sig.parameters

    def test_register_function_exists(self) -> None:
        from unionbank.entrypoints.api.v2.auth import v2_customer_register
        import inspect
        sig = inspect.signature(v2_customer_register)
        assert "req" in sig.parameters


class TestV2LoanRoutes:
    """Test V2 loan route function signatures."""

    def test_loans_router_importable(self) -> None:
        from unionbank.entrypoints.api.v2.loans import router
        assert router is not None

    def test_loans_router_has_routes(self) -> None:
        from unionbank.entrypoints.api.v2.loans import router
        routes = [r.path for r in router.routes]
        assert "/loans" in routes

    def test_list_loans_function_exists(self) -> None:
        from unionbank.entrypoints.api.v2.loans import v2_list_loans
        import inspect
        sig = inspect.signature(v2_list_loans)
        assert "customer" in sig.parameters

    def test_apply_loan_function_exists(self) -> None:
        from unionbank.entrypoints.api.v2.loans import v2_apply_loan
        import inspect
        sig = inspect.signature(v2_apply_loan)
        assert "req" in sig.parameters
        assert "customer" in sig.parameters


class TestV2AdminRoutes:
    """Test V2 admin route function signatures."""

    def test_admin_router_importable(self) -> None:
        from unionbank.entrypoints.api.v2.admin import router
        assert router is not None

    def test_admin_router_has_routes(self) -> None:
        from unionbank.entrypoints.api.v2.admin import router
        routes = [r.path for r in router.routes]
        assert "/admin/loans" in routes
        assert "/admin/accounts" in routes

    def test_admin_list_loans_function_exists(self) -> None:
        from unionbank.entrypoints.api.v2.admin import v2_admin_list_loans
        import inspect
        sig = inspect.signature(v2_admin_list_loans)
        assert "admin" in sig.parameters

    def test_admin_approve_loan_function_exists(self) -> None:
        from unionbank.entrypoints.api.v2.admin import v2_admin_approve_loan
        import inspect
        sig = inspect.signature(v2_admin_approve_loan)
        assert "loan_id" in sig.parameters
        assert "admin" in sig.parameters


class TestV2SavingsRoutes:
    """Test V2 savings route function signatures."""

    def test_savings_router_importable(self) -> None:
        from unionbank.entrypoints.api.v2.savings import router
        assert router is not None

    def test_savings_router_has_routes(self) -> None:
        from unionbank.entrypoints.api.v2.savings import router
        routes = [r.path for r in router.routes]
        assert "/savings" in routes

    def test_list_savings_goals_function_exists(self) -> None:
        from unionbank.entrypoints.api.v2.savings import v2_list_savings_goals
        import inspect
        sig = inspect.signature(v2_list_savings_goals)
        assert "customer" in sig.parameters

    def test_create_savings_goal_function_exists(self) -> None:
        from unionbank.entrypoints.api.v2.savings import v2_create_savings_goal
        import inspect
        sig = inspect.signature(v2_create_savings_goal)
        assert "req" in sig.parameters
        assert "customer" in sig.parameters


class TestV2MiscRoutes:
    """Test V2 misc route function signatures."""

    def test_misc_router_importable(self) -> None:
        from unionbank.entrypoints.api.v2.misc import router
        assert router is not None

    def test_misc_router_has_health_route(self) -> None:
        from unionbank.entrypoints.api.v2.misc import router
        routes = [r.path for r in router.routes]
        assert "/health" in routes or "/misc/health" in routes


class TestV2StatementsRoutes:
    """Test V2 statements route function signatures."""

    def test_statements_router_importable(self) -> None:
        from unionbank.entrypoints.api.v2.statements import router
        assert router is not None

    def test_statements_router_has_routes(self) -> None:
        from unionbank.entrypoints.api.v2.statements import router
        routes = [r.path for r in router.routes]
        assert any("statement" in r for r in routes)
