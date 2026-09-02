"""
tests/test_api_integration.py  –  FastAPI TestClient integration tests.

These tests exercise the real FastAPI application as a black box,
using an isolated SQLite database per test. All persistence goes
through the container's repositories/services — no JSON involved.

Usage:
    pytest tests/test_api_integration.py -v --tb=short — Part 2.
"""

from __future__ import annotations
import os
import tempfile
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from unionbank.infrastructure.container import get_container, reset_container

class TestSavingsGoals:
    def test_create_goal(self, client, registered_customer) -> None:
        """POST /api/savings should create a new savings goal."""
        resp = client.post(
            "/api/savings",
            headers=registered_customer["headers"],
            json={
                "name": "Vacation Fund",
                "target_amount": 5000.0,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Vacation Fund"
        assert data["target_amount"] == 5000.0
        assert data["current_amount"] == 0.0
        assert data["progress_pct"] == 0.0

    def test_list_goals(self, client, registered_customer) -> None:
        """GET /api/savings should list all goals."""
        # Create two goals
        client.post(
            "/api/savings",
            headers=registered_customer["headers"],
            json={
                "name": "Goal 1",
                "target_amount": 1000.0,
            },
        )
        client.post(
            "/api/savings",
            headers=registered_customer["headers"],
            json={
                "name": "Goal 2",
                "target_amount": 2000.0,
            },
        )

        resp = client.get("/api/savings", headers=registered_customer["headers"])
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_goals"] >= 2
        assert len(data["goals"]) >= 2

    def test_contribute_to_goal(self, client, registered_customer) -> None:
        """POST /api/savings/{goal_id}/contribute should move funds to goal."""
        # Create a goal
        create_resp = client.post(
            "/api/savings",
            headers=registered_customer["headers"],
            json={
                "name": "New Car",
                "target_amount": 10000.0,
            },
        )
        goal_id = create_resp.json()["goal_id"]

        # Contribute
        resp = client.post(
            f"/api/savings/{goal_id}/contribute",
            headers=registered_customer["headers"],
            json={
                "amount": 500.0,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_amount"] == 500.0
        assert data["progress_pct"] == 5.0

    def test_contribute_insufficient(self, client, registered_customer) -> None:
        """Contribute more than balance should fail."""
        create_resp = client.post(
            "/api/savings",
            headers=registered_customer["headers"],
            json={
                "name": "Dream House",
                "target_amount": 500000.0,
            },
        )
        goal_id = create_resp.json()["goal_id"]

        resp = client.post(
            f"/api/savings/{goal_id}/contribute",
            headers=registered_customer["headers"],
            json={
                "amount": 99999999.0,
            },
        )
        assert resp.status_code == 400

    def test_delete_goal(self, client, registered_customer) -> None:
        """DELETE /api/savings/{goal_id} should delete a goal."""
        create_resp = client.post(
            "/api/savings",
            headers=registered_customer["headers"],
            json={
                "name": "Temporary Goal",
                "target_amount": 1000.0,
            },
        )
        goal_id = create_resp.json()["goal_id"]

        resp = client.delete(f"/api/savings/{goal_id}", headers=registered_customer["headers"])
        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()


#  6.  Admin Operations


class TestAdminOperations:
    def test_admin_view_accounts(self, client, admin_token, registered_customer) -> None:
        """GET /api/admin/accounts should return all accounts."""
        resp = client.get("/api/admin/accounts", headers=admin_token["headers"])
        assert resp.status_code == 200
        accounts = resp.json()
        assert isinstance(accounts, list)
        assert len(accounts) >= 1
        assert any(a["account_number"] == registered_customer["account_number"] for a in accounts)

    def test_admin_search_accounts(self, client, admin_token, registered_customer) -> None:
        """GET /api/admin/accounts/search should find accounts."""
        resp = client.get(
            f"/api/admin/accounts/search?q={registered_customer['account_number']}",
            headers=admin_token["headers"],
        )
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) >= 1
        assert results[0]["account_number"] == registered_customer["account_number"]

    def test_admin_freeze_account(self, client, admin_token, registered_customer) -> None:
        """POST /api/admin/accounts/{acc_no}/freeze should freeze an account."""
        acc_no = registered_customer["account_number"]
        resp = client.post(f"/api/admin/accounts/{acc_no}/freeze", headers=admin_token["headers"])
        assert resp.status_code == 200
        assert "frozen" in resp.json()["message"].lower()

    def test_admin_unfreeze_account(self, client, admin_token, registered_customer) -> None:
        """POST /api/admin/accounts/{acc_no}/unfreeze should unfreeze an account."""
        acc_no = registered_customer["account_number"]
        # Freeze first
        client.post(f"/api/admin/accounts/{acc_no}/freeze", headers=admin_token["headers"])
        # Unfreeze
        resp = client.post(f"/api/admin/accounts/{acc_no}/unfreeze", headers=admin_token["headers"])
        assert resp.status_code == 200
        assert "unfrozen" in resp.json()["message"].lower()

    def test_admin_delete_account(self, client, admin_token, registered_customer) -> None:
        """DELETE /api/admin/accounts/{acc_no} should delete an account."""
        acc_no = registered_customer["account_number"]
        resp = client.delete(f"/api/admin/accounts/{acc_no}", headers=admin_token["headers"])
        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()

        # Verify account is gone
        accounts_resp = client.get("/api/admin/accounts", headers=admin_token["headers"])
        assert all(a["account_number"] != acc_no for a in accounts_resp.json())

    def test_admin_statistics(self, client, admin_token, registered_customer) -> None:
        """GET /api/admin/statistics should return bank statistics."""
        resp = client.get("/api/admin/statistics", headers=admin_token["headers"])
        assert resp.status_code == 200
        stats = resp.json()
        assert stats["total_customers"] >= 1
        assert stats["total_transactions"] >= 1  # the deposit from fixture
        assert "total_balance" in stats
        assert "total_balance_formatted" in stats

    def test_admin_view_transactions(self, client, admin_token, registered_customer) -> None:
        """
        GET /api/admin/transactions should return all transactions.

        Returns a flat list of TransactionOut objects (not grouped by account).
        Client-side code can group by the `account_number` field.
        """
        resp = client.get("/api/admin/transactions", headers=admin_token["headers"])
        assert resp.status_code == 200
        txns = resp.json()
        assert isinstance(txns, list)
        assert len(txns) >= 1

    def test_admin_unauthorized_customer(self, client, registered_customer) -> None:
        """Admin endpoints should reject customer tokens."""
        resp = client.get("/api/admin/accounts", headers=registered_customer["headers"])
        assert resp.status_code == 403

    def test_admin_unauthorized_no_token(self, client) -> None:
        """
        Admin endpoints should reject unauthenticated requests.

        HTTPBearer (no credentials) returns 401, not 403. 403 would come
        from a valid token with wrong role.


        """
        resp = client.get("/api/admin/accounts")
        assert resp.status_code == 401

    def test_frozen_account_cannot_transact(
        self, client, admin_token, registered_customer, second_registered_customer
    ) -> None:
        """A frozen account should not be able to withdraw or transfer."""
        acc_no = registered_customer["account_number"]

        # Freeze the account
        client.post(f"/api/admin/accounts/{acc_no}/freeze", headers=admin_token["headers"])

        # Try to withdraw
        resp = client.post(
            "/api/account/withdraw",
            headers=registered_customer["headers"],
            json={
                "amount": 100.0,
            },
        )
        # Note: the v1 API uses process_withdraw directly, so it may return 400
        assert resp.status_code in (400, 403)

        # Try to transfer
        resp = client.post(
            "/api/account/transfer",
            headers=registered_customer["headers"],
            json={
                "target_account": second_registered_customer["account_number"],
                "amount": 100.0,
            },
        )
        assert resp.status_code in (400, 403)


#  7.  Error Handling & Edge Cases


class TestErrorHandling:
    def test_invalid_json_body(self, client) -> None:
        """Send invalid JSON should return 422 (Pydantic validation)."""
        resp = client.post("/api/auth/login", json={"not_correct_field": "x"})
        assert resp.status_code == 422

    def test_nonexistent_route(self, client) -> None:
        """GET a nonexistent route should return 404."""
        resp = client.get("/api/nonexistent")
        assert resp.status_code == 404

    def test_invalid_account_number_format(self, client) -> None:
        """Login with empty password should fail validation."""
        resp = client.post(
            "/api/auth/login",
            json={
                "account_number": "",
                "password": "",
            },
        )
        assert resp.status_code == 422  # Pydantic min_length validation


#  8.  V2 API Tests (ApiResponse envelope)


class TestV2API:
    def test_v2_health_check(self, client) -> None:
        """V2 health check should use ApiResponse envelope."""
        resp = client.get("/api/v2/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["status"] == "healthy"
        assert data["error"] is None

    def test_v2_register(self, client) -> None:
        """
        V2 register should return ApiResponse envelope.

        Note: "Charlie V2" contains a digit which fails validate_name()
        (letters and spaces only). Using "Charlie" instead.
        """
        resp = client.post(
            "/api/v2/auth/register",
            json={
                "name": "Charlie",
                "age": 26,
                "gender": "Male",
                "mobile": "9988776655",
                "email": "charlie@example.com",
                "password": "CharlieP@ss1",
                "confirm_password": "CharlieP@ss1",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["message"] is not None

    def test_v2_login_envelope(self, client, registered_customer) -> None:
        """V2 login should return success=true + data.access_token."""
        resp = client.post(
            "/api/v2/auth/login",
            json={
                "account_number": registered_customer["account_number"],
                "password": registered_customer["password"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["access_token"] is not None
        assert data["data"]["role"] == "customer"

    def test_v2_error_envelope(self, client) -> None:
        """
        V2 endpoint errors should use ApiResponse envelope.

        The V2 login endpoint returns 404 for 'not found' accounts
        (distinct from 401 for wrong credentials on existing accounts).
        """
        resp = client.post(
            "/api/v2/auth/login",
            json={
                "account_number": "9999999999",
                "password": "wrong",
            },
        )
        assert resp.status_code == 404
        data = resp.json()
        assert data["success"] is False
        assert data["error"] is not None
        assert data["data"] is None

    def test_v2_validate_error(self, client) -> None:
        """
        V2 validation errors should return error envelope.

        Name "A" is too short (min 2 chars). The V2 endpoint validates this
        via the validate_name() function which returns False, triggering _err()
        which raises HTTPException with an ApiResponse dict.
        """
        resp = client.post(
            "/api/v2/auth/register",
            json={
                "name": "A",  # too short
                "age": 25,
                "gender": "Male",
                "mobile": "9876543210",
                "email": "test@test.com",
                "password": "TestP@ss1",
                "confirm_password": "TestP@ss1",
            },
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["success"] is False
        assert data["error"] is not None

    def test_v2_get_balance(self, client, registered_customer) -> None:
        """V2 balance endpoint should use ApiResponse."""
        resp = client.get("/api/v2/account/balance", headers=registered_customer["headers"])
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["balance"] >= 1000.0

    def test_v2_deposit(self, client, registered_customer) -> None:
        """V2 deposit should work with ApiResponse."""
        resp = client.post(
            "/api/v2/account/deposit",
            headers=registered_customer["headers"],
            json={
                "amount": 250.0,
                "category": "Salary",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "deposited" in data["data"]["message"]

    def test_v2_transfer(self, client, registered_customer, second_registered_customer) -> None:
        """V2 transfer should work with ApiResponse."""
        resp = client.post(
            "/api/v2/account/transfer",
            headers=registered_customer["headers"],
            json={
                "target_account": second_registered_customer["account_number"],
                "amount": 200.0,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "transferred" in data["data"]["message"].lower()

    def test_v2_admin_statistics(self, client, admin_token) -> None:
        """V2 admin statistics should use ApiResponse."""
        resp = client.get("/api/v2/admin/statistics", headers=admin_token["headers"])
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["total_customers"] >= 0
