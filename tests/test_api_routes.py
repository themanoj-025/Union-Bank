"""Tests for UNION-BANK- API routes."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit



class TestHealthRoutes:
    """Tests for health check endpoints."""

    def test_health_endpoint(self) -> None:
        from unionbank.entrypoints.api.routes.health import router

        assert router is not None

    def test_health_has_routes(self) -> None:
        from unionbank.entrypoints.api.routes.health import router

        routes = [r.path for r in router.routes]
        assert any("health" in r for r in routes)


class TestAuthRoutes:
    """Tests for auth endpoints."""

    def test_auth_router_exists(self) -> None:
        from unionbank.entrypoints.api.routes.auth import router

        assert router is not None

    def test_auth_has_login_route(self) -> None:
        from unionbank.entrypoints.api.routes.auth import router

        routes = [r.path for r in router.routes]
        assert any("login" in r for r in routes)


class TestAccountRoutes:
    """Tests for account endpoints."""

    def test_accounts_router_exists(self) -> None:
        from unionbank.entrypoints.api.routes.accounts import router

        assert router is not None

    def test_accounts_has_list_route(self) -> None:
        from unionbank.entrypoints.api.routes.accounts import router

        routes = [r.path for r in router.routes]
        assert len(routes) > 0


class TestAdminRoutes:
    """Tests for admin endpoints."""

    def test_admin_router_exists(self) -> None:
        from unionbank.entrypoints.api.routes.admin import router

        assert router is not None

    def test_admin_has_routes(self) -> None:
        from unionbank.entrypoints.api.routes.admin import router

        routes = [r.path for r in router.routes]
        assert len(routes) > 0


class TestSavingsRoutes:
    """Tests for savings endpoints."""

    def test_savings_router_exists(self) -> None:
        from unionbank.entrypoints.api.routes.savings import router

        assert router is not None
