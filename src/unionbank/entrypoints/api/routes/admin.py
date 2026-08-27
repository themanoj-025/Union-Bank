"""Admin routes: accounts management, statistics, transactions, password.

Extracted from main.py to reduce file size and improve maintainability.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from unionbank.entrypoints.api.common import get_current_admin, get_current_customer
from unionbank.utils import fmt_currency

router = APIRouter(tags=["Admin"])


# ── Request/Response Models ──────────────────────────────────────────────


class MessageResponse(BaseModel):
    message: str
    status: str = "success"


class AccountListItem(BaseModel):
    account_number: str
    name: str
    balance: float
    balance_formatted: str
    status: str
    mobile: str
    email: str
    age: int
    gender: str
    created_at: str


class TransactionOut(BaseModel):
    txn_id: str
    timestamp: str
    type: str
    amount: float
    balance: float
    description: str
    category: str
    target_account: str | None = None
    account_number: str | None = None


class StatisticsResponse(BaseModel):
    total_customers: int
    active_accounts: int
    frozen_accounts: int
    closed_accounts: int
    total_balance: float
    total_balance_formatted: str
    total_deposits: float
    total_withdrawals: float
    total_transfers: float
    total_transactions: int


class AdminChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str


# ── Helpers ──────────────────────────────────────────────────────────────


def _invalidate_admin_account_cache() -> None:
    """Invalidate all cached admin account list pages after a write."""
    try:
        from unionbank.infrastructure.cache import get_cache

        get_cache().clear_pattern("admin:accounts:*")
    except (OSError, ConnectionError) as e:
        from unionbank.utils.logger import logger

        logger.warning("Failed to invalidate admin account cache: %s", e)


def _account_to_list_item(a) -> AccountListItem:
    return AccountListItem(
        account_number=a.account_number,
        name=a.name,
        balance=float(a.balance),
        balance_formatted=fmt_currency(float(a.balance)),
        status="frozen" if a.is_frozen else ("closed" if not a.is_active else "active"),
        mobile=a.mobile,
        email=a.email,
        age=a.age,
        gender=a.gender,
        created_at=str(a.created_at)[:19],
    )


def _txn_to_out(t) -> TransactionOut:
    return TransactionOut(
        txn_id=t.txn_id,
        timestamp=str(t.timestamp)[:19],
        type=t.type.value,
        amount=float(t.amount),
        balance=float(t.balance),
        description=t.description,
        category=t.category,
        target_account=t.target_account,
        account_number=t.account_number,
    )


# ── Routes ───────────────────────────────────────────────────────────────


@router.get("/api/admin/accounts", response_model=list[AccountListItem])
def admin_view_accounts(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    admin: dict = Depends(get_current_admin),
) -> dict:
    """View all registered accounts with pagination (admin only)."""
    from unionbank.infrastructure.cache import get_cache
    from unionbank.infrastructure.container import get_container

    cache = get_cache()
    cache_key = f"admin:accounts:page:{page}:per:{per_page}"

    # Try cache first
    cached = cache.get_json(cache_key)
    if cached is not None:
        return [AccountListItem(**item) for item in cached]

    # Use SQL-level pagination instead of loading all accounts into memory
    domain_accounts, _total = (
        get_container().admin_service().list_accounts_paginated(page=page, per_page=per_page)
    )
    page_accounts = domain_accounts

    result = [_account_to_list_item(a) for a in page_accounts]

    # Cache for 60 seconds (stale data acceptable for admin list views)
    cache.set_json(cache_key, [item.model_dump() for item in result], ttl=60)

    return result


@router.get("/api/admin/accounts/search", response_model=list[AccountListItem])
def admin_search_accounts(
    request: Request,
    q: str = Query(..., min_length=1, description="Search by account number or name"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    admin: dict = Depends(get_current_admin),
) -> dict:
    """Search accounts by account number or name (admin only)."""
    from unionbank.infrastructure.cache import get_cache
    from unionbank.infrastructure.container import get_container

    cache = get_cache()
    cache_key = f"admin:accounts:search:{q}:page:{page}:per:{per_page}"

    cached = cache.get_json(cache_key)
    if cached is not None:
        return [AccountListItem(**item) for item in cached]

    # Search accounts then paginate in-memory (search is inherently bounded)
    domain_accounts = get_container().admin_service().search_accounts(q)
    start = (page - 1) * per_page
    end = start + per_page
    page_accounts = domain_accounts[start:end]

    result = [_account_to_list_item(a) for a in page_accounts]

    cache.set_json(cache_key, [item.model_dump() for item in result], ttl=60)

    return result


@router.post("/api/admin/accounts/{acc_no}/freeze", response_model=MessageResponse)
def admin_freeze_account(
    request: Request,
    acc_no: str,
    admin: dict = Depends(get_current_admin),
) -> dict:
    """Freeze a customer account (admin only)."""
    from unionbank.infrastructure.container import get_container

    result = get_container().admin_service().freeze_account(acc_no=acc_no, actor="admin")
    if not result.success:
        if "not found" in result.message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message)

    _invalidate_admin_account_cache()  # Account status changed
    return MessageResponse(message=result.message)


@router.post("/api/admin/accounts/{acc_no}/unfreeze", response_model=MessageResponse)
def admin_unfreeze_account(
    request: Request,
    acc_no: str,
    admin: dict = Depends(get_current_admin),
) -> dict:
    """Unfreeze a customer account (admin only)."""
    from unionbank.infrastructure.container import get_container

    result = get_container().admin_service().unfreeze_account(acc_no=acc_no, actor="admin")
    if not result.success:
        if "not found" in result.message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message)

    _invalidate_admin_account_cache()  # Account status changed
    return MessageResponse(message=result.message)


@router.delete("/api/admin/accounts/{acc_no}", response_model=MessageResponse)
def admin_delete_account(
    request: Request,
    acc_no: str,
    admin: dict = Depends(get_current_admin),
) -> dict:
    """Permanently delete a customer account and all its transactions (admin only)."""
    from unionbank.infrastructure.container import get_container

    result = get_container().admin_service().delete_account(acc_no=acc_no, actor="admin")
    if not result.success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.message)

    _invalidate_admin_account_cache()  # Account deleted
    return MessageResponse(message=result.message)


@router.get("/api/admin/statistics", response_model=StatisticsResponse)
def admin_statistics(request: Request, admin: dict = Depends(get_current_admin)) -> dict:
    """View bank-wide statistics (admin only)."""
    from unionbank.infrastructure.container import get_container

    s = get_container().admin_service().get_statistics()

    return StatisticsResponse(
        total_customers=s["total_customers"],
        active_accounts=s["active"],
        frozen_accounts=s["frozen"],
        closed_accounts=s["closed"],
        total_balance=s["total_balance"],
        total_balance_formatted=s["total_balance_formatted"],
        total_deposits=s["total_dep"],
        total_withdrawals=s["total_with"],
        total_transfers=s["total_trans"],
        total_transactions=s["total_txns"],
    )


@router.get("/api/admin/transactions", response_model=list[TransactionOut])
def admin_view_transactions(
    request: Request,
    account: str | None = Query(None, description="Filter by account number"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=500, description="Items per page"),
    admin: dict = Depends(get_current_admin),
) -> dict:
    """
    View all transactions, optionally filtered by account (admin only).

    Returns a flat array (not grouped by account) for easier client-side processing.
    Use the ``account_number`` field to group on the client side.
    Paginated via offset-based pagination.
    """
    from unionbank.infrastructure.container import get_container

    c = get_container()

    if account:
        domain_txns, total = c.transaction_service().get_paginated_transactions(
            acc_no=account, page=page, per_page=per_page
        )
    else:
        domain_txns, _total = c.transaction_service().get_paginated_transactions(
            page=page, per_page=per_page
        )

    return [_txn_to_out(t) for t in domain_txns]


@router.put("/api/admin/password", response_model=MessageResponse)
def admin_change_password(
    request: Request,
    req: AdminChangePasswordRequest,
    admin: dict = Depends(get_current_admin),
) -> dict:
    """Change the admin password (admin only)."""
    username = admin.get("username")
    from unionbank.infrastructure.container import get_container

    result = (
        get_container()
        .admin_service()
        .change_admin_password(
            username=username or "admin",
            current_pwd=req.current_password,
            new_pwd=req.new_password,
        )
    )
    if not result.success:
        if "not found" in result.message.lower():
            raise HTTPException(status_code=404, detail=result.message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message)

    return MessageResponse(message=result.message)


@router.post("/api/account/apply-interest", response_model=MessageResponse)
def apply_interest(request: Request, customer: dict = Depends(get_current_customer)) -> dict:
    """Apply monthly interest (3.5% p.a.) using an atomic SQLite transaction."""
    acc_no = customer["account_number"]
    from unionbank.infrastructure.container import get_container

    domain_account = get_container().account_repo().get(acc_no)
    if not domain_account:
        raise HTTPException(status_code=404, detail="Account not found.")

    result = get_container().transaction_service().apply_interest(acc_no)
    if not result.success:
        if "No interest" in result.message:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result.message
        )

    return MessageResponse(message=result.message)
