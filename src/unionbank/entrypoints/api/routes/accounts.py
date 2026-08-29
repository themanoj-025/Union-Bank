"""
Account routes: profile, balance, deposit, withdraw, transfer, statements.

Extracted from main.py to reduce file size and improve maintainability.
"""

import csv
import io
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

from unionbank.entrypoints.api.common import (
    get_account_status as _get_account_status,
    get_current_customer,
)
from unionbank.utils import (
    fmt_currency,
    hash_password,
    validate_email,
    validate_name,
    validate_password,
    validate_phone,
    verify_password,
)
from unionbank.utils.account_rate_limit import get_account_rate_limiter

router = APIRouter(tags=["Account"])


# ── Request/Response Models ──────────────────────────────────────────────


class ProfileResponse(BaseModel):
    account_number: str
    name: str
    age: int
    gender: str
    mobile: str
    email: str
    balance: float
    balance_formatted: str
    status: str
    created_at: str


class BalanceResponse(BaseModel):
    account_number: str
    name: str
    balance: float
    balance_formatted: str


class MessageResponse(BaseModel):
    message: str


class TransactionRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Positive transaction amount")
    category: str = Field(default="General", description="Transaction category")


class TransferRequest(BaseModel):
    target_account: str = Field(..., description="Recipient account number")
    amount: float = Field(..., gt=0, description="Transfer amount")
    category: str = Field(default="General", description="Transaction category")


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str


class UpdateProfileRequest(BaseModel):
    name: str | None = None
    age: int | None = Field(default=None, ge=18, le=120)
    gender: str | None = None
    mobile: str | None = None
    email: str | None = None


class CloseAccountRequest(BaseModel):
    confirm_text: str = Field(..., description="Must be 'CLOSE'")
    password: str


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


# ── Shared helper ─────────────────────────────────────────────────────────


def _invalidate_admin_account_cache() -> None:
    """Invalidate the admin account list cache after balance-changing operations."""
    try:
        from unionbank.entrypoints.api.v2 import _admin_account_cache
        _admin_account_cache.clear()
    except (ImportError, AttributeError):
        pass


# ── Profile Endpoints ─────────────────────────────────────────────────────


@router.get("/api/account/profile", response_model=ProfileResponse)
def get_profile(request: Request, customer: dict = Depends(get_current_customer)) -> dict:
    """Get the authenticated customer's profile details."""
    return ProfileResponse(
        account_number=customer["account_number"],
        name=customer["name"],
        age=customer["age"],
        gender=customer["gender"],
        mobile=customer["mobile"],
        email=customer["email"],
        balance=customer["balance"],
        balance_formatted=fmt_currency(customer["balance"]),
        status=_get_account_status(customer),
        created_at=customer.get("created_at", "N/A"),
    )


@router.put("/api/account/profile", response_model=ProfileResponse)
def update_profile(
    request: Request,
    req: UpdateProfileRequest,
    customer: dict = Depends(get_current_customer),
) -> dict:
    """Update the authenticated customer's profile details."""
    acc_no = customer["account_number"]
    from unionbank.infrastructure.container import get_container

    c = get_container()
    domain_account = c.account_repo().get(acc_no)
    if not domain_account:
        raise HTTPException(status_code=404, detail="Account not found.")

    if req.name is not None:
        if not validate_name(req.name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid name. Must be 2-50 characters (letters and spaces only).",
            )
        domain_account.name = req.name
    if req.age is not None:
        domain_account.age = req.age
    if req.gender is not None:
        domain_account.gender = req.gender
    if req.mobile is not None:
        if not validate_phone(req.mobile):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid mobile number. Must be 10 digits starting with 6-9.",
            )
        domain_account.mobile = req.mobile
    if req.email is not None:
        if not validate_email(req.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email format."
            )
        domain_account.email = req.email

    c.account_repo().update(domain_account)
    c.account_repo().commit()

    return ProfileResponse(
        account_number=domain_account.account_number,
        name=domain_account.name,
        age=domain_account.age,
        gender=domain_account.gender,
        mobile=domain_account.mobile,
        email=domain_account.email,
        balance=float(domain_account.balance),
        balance_formatted=fmt_currency(float(domain_account.balance)),
        status=_get_account_status(
            {"is_frozen": domain_account.is_frozen, "is_active": domain_account.is_active}
        ),
        created_at=str(domain_account.created_at)[:19],
    )


@router.post("/api/account/change-password", response_model=MessageResponse)
def change_password(
    request: Request,
    req: ChangePasswordRequest,
    customer: dict = Depends(get_current_customer),
) -> dict:
    """Change the authenticated customer's password."""
    acc_no = customer["account_number"]
    from unionbank.infrastructure.container import get_container

    c = get_container()
    domain_account = c.account_repo().get(acc_no)
    if not domain_account:
        raise HTTPException(status_code=404, detail="Account not found.")

    if not verify_password(req.current_password, domain_account.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect current password."
        )
    valid_pwd, pwd_msg = validate_password(req.new_password)
    if not valid_pwd:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=pwd_msg)
    if req.new_password != req.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match."
        )

    domain_account.password = hash_password(req.new_password)
    c.account_repo().update(domain_account)
    c.account_repo().commit()
    return MessageResponse(message="Password changed successfully.")


@router.post("/api/account/close", response_model=MessageResponse)
def close_account(
    request: Request,
    req: CloseAccountRequest,
    customer: dict = Depends(get_current_customer),
) -> dict:
    """Close the authenticated customer's account."""
    acc_no = customer["account_number"]
    if req.confirm_text != "CLOSE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please type 'CLOSE' to confirm.",
        )
    from unionbank.infrastructure.container import get_container

    result = get_container().account_service().close_account(acc_no, req.password)
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=result.message
        )
    return MessageResponse(message=result.message)


# ── Transaction Endpoints ─────────────────────────────────────────────────


@router.get("/api/account/balance", response_model=BalanceResponse)
def get_balance(request: Request, customer: dict = Depends(get_current_customer)) -> dict:
    """Get the current account balance."""
    from unionbank.infrastructure.container import get_container

    domain_account = get_container().account_repo().get(customer["account_number"])
    if not domain_account:
        raise HTTPException(status_code=404, detail="Account not found.")
    return BalanceResponse(
        account_number=domain_account.account_number,
        name=domain_account.name,
        balance=float(domain_account.balance),
        balance_formatted=fmt_currency(float(domain_account.balance)),
    )


@router.post("/api/account/deposit", response_model=MessageResponse)
def deposit_money(
    request: Request,
    req: TransactionRequest,
    customer: dict = Depends(get_current_customer),
) -> dict:
    """Deposit money into the authenticated customer's account."""
    acc_no = customer["account_number"]
    rate_limiter = get_account_rate_limiter()
    allowed, retry_msg = rate_limiter.check_and_record(acc_no)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=retry_msg
        )

    from unionbank.infrastructure.container import get_container

    result = (
        get_container()
        .transaction_service()
        .deposit(acc_no=acc_no, amount=Decimal(str(req.amount)), category=req.category)
    )
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=result.message
        )
    _invalidate_admin_account_cache()
    return MessageResponse(message=result.message)


@router.post("/api/account/withdraw", response_model=MessageResponse)
def withdraw_money(
    request: Request,
    req: TransactionRequest,
    customer: dict = Depends(get_current_customer),
) -> dict:
    """Withdraw money from the authenticated customer's account."""
    acc_no = customer["account_number"]
    rate_limiter = get_account_rate_limiter()
    allowed, retry_msg = rate_limiter.check_and_record(acc_no)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=retry_msg
        )

    from unionbank.infrastructure.container import get_container

    result = (
        get_container()
        .transaction_service()
        .withdraw(acc_no=acc_no, amount=Decimal(str(req.amount)), category=req.category)
    )
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=result.message
        )
    _invalidate_admin_account_cache()
    return MessageResponse(message=result.message)


@router.post("/api/account/transfer", response_model=MessageResponse)
def transfer_funds(
    request: Request,
    req: TransferRequest,
    customer: dict = Depends(get_current_customer),
) -> dict:
    """Transfer funds to another account."""
    acc_no = customer["account_number"]
    target_acc_no = req.target_account

    from unionbank.infrastructure.container import get_container

    c = get_container()
    sender = c.account_repo().get(acc_no)
    if not sender:
        raise HTTPException(status_code=404, detail="Sender account not found.")
    receiver = c.account_repo().get(target_acc_no)
    if not receiver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipient account not found.",
        )
    if target_acc_no == acc_no:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot transfer to your own account.",
        )
    if receiver.is_frozen:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Recipient account is frozen."
        )
    if not receiver.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Recipient account is closed."
        )

    rate_limiter = get_account_rate_limiter()
    allowed, retry_msg = rate_limiter.check_and_record(acc_no)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=retry_msg
        )

    result = c.transaction_service().transfer(
        sender_acc_no=acc_no,
        receiver_acc_no=target_acc_no,
        amount=Decimal(str(req.amount)),
        category=req.category,
    )
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=result.error_message
        )

    _invalidate_admin_account_cache()
    return MessageResponse(
        message=f"{fmt_currency(req.amount)} transferred to {receiver.name} "
        f"({target_acc_no}). New balance: {fmt_currency(float(result.sender_balance))}",
    )


@router.get("/api/account/statements", response_model=list[TransactionOut])
def get_full_statement(
    request: Request, customer: dict = Depends(get_current_customer)
) -> dict:
    """Get the full transaction statement (newest first)."""
    acc_no = customer["account_number"]
    from unionbank.infrastructure.container import get_container

    domain_txns = get_container().transaction_repo().get_by_account(acc_no)
    return [
        TransactionOut(
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
        for t in domain_txns
    ]


@router.get("/api/account/statements/mini", response_model=list[TransactionOut])
def get_mini_statement(
    request: Request, customer: dict = Depends(get_current_customer)
) -> dict:
    """Get the last 5 transactions (mini statement)."""
    acc_no = customer["account_number"]
    from unionbank.infrastructure.container import get_container

    domain_txns = get_container().transaction_repo().get_mini(acc_no, 5)
    return [
        TransactionOut(
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
        for t in domain_txns
    ]


@router.get("/api/account/export-csv")
def export_csv(
    request: Request, customer: dict = Depends(get_current_customer)
) -> dict:
    """Download transaction history as a CSV file."""
    acc_no = customer["account_number"]
    from unionbank.infrastructure.container import get_container

    domain_txns = get_container().transaction_repo().get_by_account(acc_no)
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
