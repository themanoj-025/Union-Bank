"""V2 API — Admin endpoints (loan management, account management, statistics)."""

from __future__ import annotations

from fastapi import Depends, Query, Response, status

from unionbank.entrypoints.api.common import get_current_admin
from unionbank.entrypoints.api.models import (
    AccountListItem,
    ApiResponse,
    LoanAdminStats,
    LoanOut,
    LoanRejectRequest,
    MessageData,
    StatisticsData,
    TransactionOut,
)
from unionbank.entrypoints.api.v2.helpers import _err, _fmt_currency, _get_container, _ok

router = __import__("fastapi").APIRouter()

@router.get("/admin/loans", response_model=ApiResponse[LoanAdminStats])
def v2_admin_list_loans(admin: dict = Depends(get_current_admin)) -> ApiResponse:
    """View all loan applications with statistics (admin only)."""
    c = _get_container()
    stats = c.loan_service().get_loan_statistics()

    return _ok(
        LoanAdminStats(
            total_pending=stats["total_pending"],
            total_approved=stats["total_approved"],
            total_active=stats["total_active"],
            total_closed=stats["total_closed"],
            total_rejected=stats["total_rejected"],
            total_disbursed=stats["total_disbursed"],
            total_disbursed_formatted=_fmt_currency(stats["total_disbursed"]),
            total_outstanding=stats["total_outstanding"],
            total_outstanding_formatted=_fmt_currency(stats["total_outstanding"]),
        )
    )


@router.get("/admin/loans/pending", response_model=ApiResponse[list[LoanOut]])
def v2_admin_list_pending_loans(admin: dict = Depends(get_current_admin)) -> ApiResponse:
    """View all pending loan applications (admin only)."""
    c = _get_container()
    loans = c.loan_service().list_pending()

    return _ok(
        [
            LoanOut(
                loan_id=loan.loan_id,
                account_number=loan.account_number,
                loan_type=loan.loan_type,
                principal_amount=float(loan.principal_amount),
                interest_rate=float(loan.interest_rate),
                tenure_months=loan.tenure_months,
                emi_amount=float(loan.emi_amount),
                amount_paid=float(loan.amount_paid),
                remaining_amount=float(loan.remaining_amount),
                status=loan.status,
                application_date=str(loan.application_date)[:19],
                purpose=loan.purpose,
                progress_pct=0.0,
                remaining_emis=loan.tenure_months,
                is_overdue=False,
            )
            for loan in loans
        ]
    )


@router.post("/admin/loans/{loan_id}/approve", response_model=ApiResponse[MessageData])
def v2_admin_approve_loan(loan_id: str, admin: dict = Depends(get_current_admin)) -> dict[str, str]:
    """Approve a pending loan application and disburse funds (admin only)."""
    c = _get_container()
    result = c.loan_service().approve_loan(
        loan_id=loan_id, admin_user=admin.get("username", "admin")
    )
    if not result.success:
        if "not found" in result.message.lower():
            _err(result.message, status.HTTP_404_NOT_FOUND)
        _err(result.message)

    return _ok(MessageData(message=result.message))


@router.post("/admin/loans/{loan_id}/reject", response_model=ApiResponse[MessageData])
def v2_admin_reject_loan(
    loan_id: str, req: LoanRejectRequest, admin: dict = Depends(get_current_admin)
) -> ApiResponse:
    """Reject a pending loan application (admin only)."""
    c = _get_container()
    result = c.loan_service().reject_loan(
        loan_id=loan_id,
        reason=req.reason,
        admin_user=admin.get("username", "admin"),
    )
    if not result.success:
        if "not found" in result.message.lower():
            _err(result.message, status.HTTP_404_NOT_FOUND)
        _err(result.message)

    return _ok(MessageData(message=result.message))


@router.get("/admin/loans/all", response_model=ApiResponse[list[LoanOut]])
def v2_admin_list_all_loans(admin: dict = Depends(get_current_admin)) -> ApiResponse:
    """View all loan applications (admin only)."""
    c = _get_container()
    loans = c.loan_service().list_all()

    return _ok(
        [
            LoanOut(
                loan_id=loan.loan_id,
                account_number=loan.account_number,
                loan_type=loan.loan_type,
                principal_amount=float(loan.principal_amount),
                interest_rate=float(loan.interest_rate),
                tenure_months=loan.tenure_months,
                emi_amount=float(loan.emi_amount),
                amount_paid=float(loan.amount_paid),
                remaining_amount=float(loan.remaining_amount),
                status=loan.status,
                application_date=str(loan.application_date)[:19],
                approval_date=str(loan.approval_date)[:19] if loan.approval_date else None,
                next_emi_date=str(loan.next_emi_date)[:19] if loan.next_emi_date else None,
                purpose=loan.purpose,
                admin_notes=loan.admin_notes,
                progress_pct=0.0,
                remaining_emis=0,
                is_overdue=False,
            )
            for loan in loans
        ]
    )


#  Admin Endpoints


@router.get("/admin/transactions", response_model=ApiResponse[list[TransactionOut]])
def v2_admin_view_transactions(
    account: str | None = Query(None, description="Filter by account number"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=500, description="Results per page"),
    admin: dict = Depends(get_current_admin),
) -> ApiResponse:
    """
    View all transactions across all accounts (admin only).

    Optionally filter by account number via the `account` query parameter.
    Transactions are returned newest first with keyset pagination.
    """
    c = _get_container()
    tx_repo = c.transaction_repo()

    if account:
        domain_txns = tx_repo.get_by_account(account)
    else:
        # Paginated: iterate accounts but limit total scan
        all_accounts = c.account_repo().get_all()
        domain_txns = []
        for acct in all_accounts:
            domain_txns.extend(tx_repo.get_by_account(acct.account_number))
            # Safety cap to avoid unbounded memory usage
            if len(domain_txns) >= page * per_page:
                break

    # Sort by timestamp descending
    domain_txns.sort(key=lambda t: t.timestamp, reverse=True)

    # Apply pagination
    start = (page - 1) * per_page
    domain_txns = domain_txns[start : start + per_page]

    return _ok(
        [
            TransactionOut(
                txn_id=t.txn_id,
                timestamp=str(t.timestamp)[:19],
                type=t.type.value,
                amount=float(t.amount),
                balance=float(t.balance),
                description=t.description,
                category=t.category,
                target_account=t.target_account,
            )
            for t in domain_txns
        ]
    )


@router.get("/admin/accounts", response_model=ApiResponse[list[AccountListItem]])
def v2_admin_view_accounts(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    response: Response = None,
    admin: dict = Depends(get_current_admin),
) -> ApiResponse:
    """
    View all registered accounts with pagination (admin only).

    Returns X-Total-Count header for pagination-aware UIs.
    """
    c = _get_container()
    domain_accounts, total = c.admin_service().list_accounts_paginated(page=page, per_page=per_page)
    response.headers["X-Total-Count"] = str(total)
    return _ok(
        [
            AccountListItem(
                account_number=a.account_number,
                name=a.name,
                balance=float(a.balance),
                balance_formatted=_fmt_currency(float(a.balance)),
                status="frozen" if a.is_frozen else ("closed" if not a.is_active else "active"),
                mobile=a.mobile,
                email=a.email,
                age=a.age,
                gender=a.gender,
                created_at=str(a.created_at)[:19],
            )
            for a in domain_accounts
        ],
        meta={"page": page, "per_page": per_page, "total": total},
    )


@router.get("/admin/accounts/search", response_model=ApiResponse[list[AccountListItem]])
def v2_admin_search_accounts(
    q: str = Query(..., min_length=1, description="Search by account number or name"),
    admin: dict = Depends(get_current_admin),
) -> ApiResponse:
    """Search accounts by account number or name (admin only)."""
    c = _get_container()
    domain_accounts = c.admin_service().search_accounts(q)
    return _ok(
        [
            AccountListItem(
                account_number=a.account_number,
                name=a.name,
                balance=float(a.balance),
                balance_formatted=_fmt_currency(float(a.balance)),
                status="frozen" if a.is_frozen else ("closed" if not a.is_active else "active"),
                mobile=a.mobile,
                email=a.email,
                age=a.age,
                gender=a.gender,
                created_at=str(a.created_at)[:19],
            )
            for a in domain_accounts
        ]
    )


@router.post("/admin/accounts/{acc_no}/freeze", response_model=ApiResponse[MessageData])
def v2_admin_freeze_account(acc_no: str, admin: dict = Depends(get_current_admin)) -> dict[str, str]:
    """Freeze a customer account (admin only)."""
    c = _get_container()
    result = c.admin_service().freeze_account(acc_no=acc_no, actor="admin")
    if not result.success:
        if "not found" in result.message.lower():
            _err(result.message, status.HTTP_404_NOT_FOUND)
        _err(result.message)

    return _ok(MessageData(message=result.message))


@router.post("/admin/accounts/{acc_no}/unfreeze", response_model=ApiResponse[MessageData])
def v2_admin_unfreeze_account(acc_no: str, admin: dict = Depends(get_current_admin)) -> dict[str, str]:
    """Unfreeze a customer account (admin only)."""
    c = _get_container()
    result = c.admin_service().unfreeze_account(acc_no=acc_no, actor="admin")
    if not result.success:
        if "not found" in result.message.lower():
            _err(result.message, status.HTTP_404_NOT_FOUND)
        _err(result.message)

    return _ok(MessageData(message=result.message))


@router.delete("/admin/accounts/{acc_no}", response_model=ApiResponse[MessageData])
def v2_admin_delete_account(acc_no: str, admin: dict = Depends(get_current_admin)) -> dict[str, str]:
    """Permanently delete a customer account and all its transactions (admin only)."""
    c = _get_container()
    result = c.admin_service().delete_account(acc_no=acc_no, actor="admin")
    if not result.success:
        _err(result.message, status.HTTP_404_NOT_FOUND)

    return _ok(MessageData(message=result.message))


@router.get("/admin/statistics", response_model=ApiResponse[StatisticsData])
def v2_admin_statistics(admin: dict = Depends(get_current_admin)) -> ApiResponse:
    """View bank-wide statistics (admin only)."""
    c = _get_container()
    s = c.admin_service().get_statistics()

    return _ok(
        StatisticsData(
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
    )
