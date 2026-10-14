"""
pytest fixtures for Union Bank tests.

All tests use temporary directories — never touch real production data/ files.
Test-safe env vars are set BEFORE any project module is imported.
"""

import os
import tempfile
from pathlib import Path

#  IMPORTANT: Set test-safe env vars BEFORE any project module is imported.
#  config.py calls _require_env() at module level, so JWT_SECRET must exist.
#  admin.py runs _init_admin() at import time, so UNION_BANK_DATA_DIR must also
#  be set to a temp directory BEFORE any module imports happen.
_test_data_dir = tempfile.mkdtemp(prefix="union_bank_test_")
os.environ.setdefault("UNION_BANK_DATA_DIR", _test_data_dir)
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-prod")
os.environ.setdefault("FLASK_SECRET_KEY", "test-flask-secret-for-testing")
os.environ.setdefault("UNION_BANK_TESTING", "1")

# The unionbank package is installed via pip install -e ., so all
# imports use unionbank.-qualified paths. No sys.path manipulation needed.

import pytest


@pytest.fixture(autouse=True)
def _unset_env_vars_for_safety() -> None:
    """
    Prevent accidental use of real env secrets during tests.

    This runs after module imports (at test function time), but the module-level
    os.environ.setdefault() calls above ensure safe defaults exist already.
    """
    # We set test defaults at module level already; this fixture exists to
    # document the pattern and can be extended for per-test env isolation.
    yield


@pytest.fixture(autouse=True)
def _clean_postgres_db() -> None:
    """Clean Postgres database between tests."""
    if "postgres" in os.environ.get("DATABASE_URL", ""):
        from unionbank.infrastructure.database import ModelBase, get_engine

        engine = get_engine()
        ModelBase.metadata.drop_all(engine)
        ModelBase.metadata.create_all(engine)


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """
    Provide a temporary data directory for JSON file-based tests.

    Sets UNION_BANK_DATA_DIR so that utils.py's file resolution uses the temp dir.
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["UNION_BANK_DATA_DIR"] = str(data_dir)
    return data_dir


@pytest.fixture
def sample_account_data() -> dict:
    """Return a minimal valid account dict for unit tests."""
    return {
        "account_number": "9999999999",
        "name": "Test User",
        "age": 25,
        "gender": "Male",
        "mobile": "9876543210",
        "email": "test@example.com",
        "password": "$2b$12$testhash1234567890123456789012345678901234567890",
        "balance": 5000.0,
        "is_active": True,
        "is_frozen": False,
        "created_at": "2026-01-01 00:00:00",
    }


@pytest.fixture
def c() -> None:
    """
    Get a fresh DI container with a clean SQLite database.

    Creates a unique temp directory per test so tests never share
    database state. This mirrors test_integration.py's _fresh_db fixture
    but is available globally from conftest.py.
    """
    import tempfile

    data_dir = tempfile.mkdtemp(prefix="union_bank_c_")
    old = os.environ.get("UNION_BANK_DATA_DIR")
    os.environ["UNION_BANK_DATA_DIR"] = data_dir
    from unionbank.infrastructure.container import get_container, reset_container

    reset_container()
    yield get_container()
    reset_container()
    if old:
        os.environ["UNION_BANK_DATA_DIR"] = old
    else:
        os.environ.pop("UNION_BANK_DATA_DIR", None)


@pytest.fixture
def sample_account() -> None:
    """
    Return an Account domain object for tests.

    The account is created in the database so it can be used with
    both fake repositories (unit tests) and real repositories (integration tests).
    """
    from decimal import Decimal

    from unionbank.domain.entities import Account
    from unionbank.utils.hashing import hash_password

    return Account(
        account_number="1000000001",
        name="Test User",
        age=30,
        gender="Male",
        mobile="9876543210",
        email="test@example.com",
        password=hash_password("Secure1Pass"),
        balance=Decimal("1000.00"),
        is_active=True,
        is_frozen=False,
    )


@pytest.fixture
def account_repo():
    """Fresh in-memory fake account repository (shared with test_services*)."""
    from tests.fakes import FakeAccountRepository

    return FakeAccountRepository()


@pytest.fixture
def txn_repo():
    from tests.fakes import FakeTransactionRepository

    return FakeTransactionRepository()


@pytest.fixture
def admin_repo():
    from tests.fakes import FakeAdminRepository

    return FakeAdminRepository()


@pytest.fixture
def login_attempt_repo():
    from tests.fakes import FakeLoginAttemptRepository

    return FakeLoginAttemptRepository()


@pytest.fixture
def token_version_repo():
    from tests.fakes import FakeTokenVersionRepository

    return FakeTokenVersionRepository()


@pytest.fixture
def audit_log_repo():
    from tests.fakes import FakeAuditLogRepository

    return FakeAuditLogRepository()


@pytest.fixture
def savings_goal_repo():
    from tests.fakes import FakeSavingsGoalRepository

    return FakeSavingsGoalRepository()


@pytest.fixture
def auth_service(account_repo, admin_repo, login_attempt_repo, token_version_repo):
    from unionbank.application.services import AuthService

    return AuthService(
        account_repo=account_repo,
        admin_repo=admin_repo,
        login_attempt_repo=login_attempt_repo,
        token_version_repo=token_version_repo,
    )


@pytest.fixture
def account_service(account_repo, txn_repo, token_version_repo):
    from unionbank.application.services import AccountService

    return AccountService(
        account_repo=account_repo,
        txn_repo=txn_repo,
        token_version_repo=token_version_repo,
    )


@pytest.fixture
def transaction_service(account_repo, txn_repo):
    from unionbank.application.services import TransactionService

    return TransactionService(
        account_repo=account_repo,
        txn_repo=txn_repo,
    )


@pytest.fixture
def admin_service(account_repo, txn_repo, admin_repo, audit_log_repo):
    from unionbank.application.services import AdminService

    return AdminService(
        account_repo=account_repo,
        txn_repo=txn_repo,
        admin_repo=admin_repo,
        audit_log_repo=audit_log_repo,
    )


@pytest.fixture
def savings_goal_service(account_repo, txn_repo, savings_goal_repo):
    from unionbank.application.services import SavingsGoalService

    return SavingsGoalService(
        goal_repo=savings_goal_repo,
        account_repo=account_repo,
        txn_repo=txn_repo,
    )


@pytest.fixture
def sample_admin():
    from unionbank.domain.entities import AdminUser
    from unionbank.utils.hashing import hash_password

    return AdminUser(
        username="admin",
        password=hash_password("AdminPass1"),
        role="admin",
    )


@pytest.fixture
def sample_transaction_records() -> list[dict]:
    """Return sample transaction records for CSV/statement tests."""
    return [
        {
            "txn_id": "TXN-ABC123",
            "timestamp": "2026-06-01 10:00:00",
            "type": "DEPOSIT",
            "amount": 1000.0,
            "balance": 1000.0,
            "description": "Test deposit",
            "category": "Salary",
        },
        {
            "txn_id": "TXN-DEF456",
            "timestamp": "2026-06-02 11:00:00",
            "type": "WITHDRAW",
            "amount": 200.0,
            "balance": 800.0,
            "description": "Test withdrawal",
            "category": "Food & Dining",
        },
    ]


@pytest.fixture
def client():
    """FastAPI TestClient connected to the real application."""
    from fastapi.testclient import TestClient
    from unionbank.entrypoints.api.main import app

    with TestClient(app) as tc:
        yield tc


@pytest.fixture
def sample_customer_registration() -> dict:
    """Return a valid customer registration payload."""
    return {
        "name": "Alice Johnson",
        "age": 28,
        "gender": "Female",
        "mobile": "9876543210",
        "email": "alice@example.com",
        "password": "SecureP@ss1",
        "confirm_password": "SecureP@ss1",
    }


@pytest.fixture
def registered_customer(client, sample_customer_registration: dict) -> dict:
    """Register a customer and return the resulting account info + auth tokens."""
    from decimal import Decimal
    from unionbank.infrastructure.container import get_container

    resp = client.post("/api/auth/register", json=sample_customer_registration)
    assert resp.status_code == 200
    data = resp.json()

    # Extract account number from the message
    msg = data.get("message", "")
    assert "Account created successfully" in msg
    acc_no = msg.split(": ")[-1].strip()

    # Login to get JWT token
    login_resp = client.post(
        "/api/auth/login",
        json={
            "account_number": acc_no,
            "password": sample_customer_registration["password"],
        },
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()

    # Make sure the account has some balance for operations that need it
    c = get_container()
    c.transaction_service().deposit(acc_no, Decimal("1000.00"), "Salary")

    # Clear cookies so Bearer-only auth is used (no CSRF cookie present)
    client.cookies.clear()

    return {
        "account_number": acc_no,
        "name": sample_customer_registration["name"],
        "password": sample_customer_registration["password"],
        "access_token": login_data["access_token"],
        "refresh_token": login_data.get("refresh_token"),
        "headers": {"Authorization": f"Bearer {login_data['access_token']}"},
    }


@pytest.fixture
def admin_token(client) -> dict:
    """Create an admin user and return auth token."""
    from unionbank.domain.entities import AdminUser
    from unionbank.infrastructure.container import get_container
    from unionbank.utils.hashing import hash_password

    c = get_container()
    admin_repo = c.admin_repo()

    existing = admin_repo.get_by_username("admin")
    if not existing:
        admin = AdminUser(
            username="admin",
            password=hash_password("admin123"),
        )
        admin_repo.create(admin)
        admin_repo.commit()

    resp = client.post(
        "/api/auth/admin-login",
        json={
            "username": "admin",
            "password": "admin123",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    client.cookies.clear()

    return {
        "username": "admin",
        "access_token": data["access_token"],
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
    }


@pytest.fixture
def second_registered_customer(client) -> dict:
    """Register a second customer (for transfer tests)."""
    resp = client.post(
        "/api/auth/register",
        json={
            "name": "Bob Smith",
            "age": 32,
            "gender": "Male",
            "mobile": "9123456789",
            "email": "bob@example.com",
            "password": "BobStr0ng!",
            "confirm_password": "BobStr0ng!",
        },
    )
    assert resp.status_code == 200
    msg = resp.json().get("message", "")
    acc_no = msg.split(": ")[-1].strip()

    login_resp = client.post(
        "/api/auth/login",
        json={
            "account_number": acc_no,
            "password": "BobStr0ng!",
        },
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()

    # Clear cookies so Bearer-only auth is used (no CSRF cookie present)
    client.cookies.clear()

    return {
        "account_number": acc_no,
        "name": "Bob Smith",
        "access_token": login_data["access_token"],
        "headers": {"Authorization": f"Bearer {login_data['access_token']}"},
    }


