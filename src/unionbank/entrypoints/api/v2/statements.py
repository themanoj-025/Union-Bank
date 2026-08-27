"""V2 API — Statement endpoints (full, mini, keyset pagination, CSV export)."""

from __future__ import annotations

from datetime import datetime

from fastapi import Depends, Query, Response

from unionbank.entrypoints.api.common import get_current_customer
from unionbank.entrypoints.api.models import (
    ApiResponse,
    KeysetMeta,
    TransactionOut,
)
from unionbank.entrypoints.api.v2.helpers import _err, _get_container, _ok

router = __import__("fastapi").APIRouter()


@router.get("/account/statements", response_model=ApiResponse[list[TransactionOut]])
def v2_get_full_statement(customer: dict = Depends(get_current_customer)) -> ApiResponse:
    """Get the full transaction statement (newest first)."""
    acc_no = customer["account_number"]
    c = _get_container()
    domain_txns = c.transaction_repo().get_by_account(acc_no)

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


@router.get("/account/statements/mini", response_model=ApiResponse[list[TransactionOut]])
def v2_get_mini_statement(customer: dict = Depends(get_current_customer)) -> ApiResponse:
    """Get the last 5 transactions (mini statement)."""
    acc_no = customer["account_number"]
    c = _get_container()
    domain_txns = c.transaction_repo().get_mini(acc_no, 5)

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


@router.get("/account/statements/keyset", response_model=ApiResponse[list[TransactionOut]])
def v2_get_statement_keyset(
    cursor: str | None = Query(None, description="Timestamp cursor from previous page"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    customer: dict = Depends(get_current_customer),
) -> ApiResponse:
    """
    Get paginated statement using keyset (cursor-based) pagination.

    More efficient than offset-based pagination on large datasets.
    Include the `cursor` value from the previous page's meta to get the next page.
    """
    acc_no = customer["account_number"]
    c = _get_container()

    cursor_dt: datetime | None = None
    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
        except (ValueError, TypeError):
            _err("Invalid cursor format. Use ISO 8601 timestamp.")

    page = c.transaction_service().get_paginated_keyset(
        acc_no=acc_no, limit=limit, cursor=cursor_dt
    )

    items = [
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
        for t in page.items
    ]

    next_cursor = str(page.cursor) if page.cursor else None
    return _ok(
        items,
        meta=KeysetMeta(
            cursor=next_cursor,
            has_more=page.has_more,
            cursor_key=page.cursor_key,
        ).model_dump(),
    )


@router.get("/account/export-csv", response_model=None)
def v2_export_csv(customer: dict = Depends(get_current_customer)) -> ApiResponse:
    """Download transaction history as a CSV file."""
    import csv
    import io

    acc_no = customer["account_number"]
    c = _get_container()
    domain_txns = c.transaction_repo().get_by_account(acc_no)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["Transaction ID", "Date/Time", "Type", "Amount", "Balance", "Description", "Category"]
    )
    for t in domain_txns:
        sign = "+" if t.type.value in ("DEPOSIT", "TRANSFER_IN") else "-"
        writer.writerow(
            [
                t.txn_id,
                str(t.timestamp)[:19],
                t.type.value,
                f"{sign}{float(t.amount)}",
                float(t.balance),
                t.description,
                t.category or "General",
            ]
        )

    output.seek(0)
    return Response(
        content=output.getvalue().encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=statement_{acc_no}.csv"},
    )
