"""V2 API — Customer account endpoints (profile, balance, transactions)."""

from __future__ import annotations

from decimal import Decimal

from fastapi import Depends, status

from unionbank.entrypoints.api.common import get_current_customer
from unionbank.entrypoints.api.models import (
    ApiResponse,
    BalanceData,
    ChangePasswordRequest,
    CloseAccountRequest,
    MessageData,
    ProfileData,
    TransactionRequest,
    TransferRequest,
    UpdateProfileRequest,
)
from unionbank.entrypoints.api.v2.helpers import _err, _fmt_currency, _get_container, _ok

router = __import__("fastapi").APIRouter()


@router.get("/account/profile", response_model=ApiResponse[ProfileData])
def v2_get_profile(customer: dict = Depends(get_current_customer)) -> ApiResponse:
    """Get the authenticated customer's profile details."""
    from unionbank.entrypoints.api.common import get_account_status

    return _ok(
        ProfileData(
            account_number=customer["account_number"],
            name=customer["name"],
            age=customer["age"],
            gender=customer["gender"],
            mobile=customer["mobile"],
            email=customer["email"],
            balance=customer["balance"],
            balance_formatted=_fmt_currency(customer["balance"]),
            status=get_account_status(customer),
            created_at=customer.get("created_at", "N/A"),
        )
    )


@router.put("/account/profile", response_model=ApiResponse[ProfileData])
def v2_update_profile(req: UpdateProfileRequest, customer: dict = Depends(get_current_customer)):
    """Update the authenticated customer's profile details."""
    from unionbank.entrypoints.api.common import get_account_status
    from unionbank.utils import validate_email, validate_name, validate_phone

    acc_no = customer["account_number"]
    c = _get_container()
    domain_account = c.account_repo().get(acc_no)
    if not domain_account:
        _err("Account not found.", status.HTTP_404_NOT_FOUND)

    if req.name is not None:
        if not validate_name(req.name):
            _err("Invalid name. Must be 2-50 characters (letters and spaces only).")
        domain_account.name = req.name
    if req.age is not None:
        domain_account.age = req.age
    if req.gender is not None:
        domain_account.gender = req.gender
    if req.mobile is not None:
        if not validate_phone(req.mobile):
            _err("Invalid mobile number. Must be 10 digits starting with 6-9.")
        domain_account.mobile = req.mobile
    if req.email is not None:
        if not validate_email(req.email):
            _err("Invalid email format.")
        domain_account.email = req.email

    c.account_repo().update(domain_account)
    c.account_repo().commit()

    return _ok(
        ProfileData(
            account_number=domain_account.account_number,
            name=domain_account.name,
            age=domain_account.age,
            gender=domain_account.gender,
            mobile=domain_account.mobile,
            email=domain_account.email,
            balance=float(domain_account.balance),
            balance_formatted=_fmt_currency(float(domain_account.balance)),
            status=get_account_status(
                {
                    "is_frozen": domain_account.is_frozen,
                    "is_active": domain_account.is_active,
                }
            ),
            created_at=str(domain_account.created_at)[:19],
        )
    )


@router.post("/account/change-password", response_model=ApiResponse[MessageData])
def v2_change_password(req: ChangePasswordRequest, customer: dict = Depends(get_current_customer)):
    """Change the authenticated customer's password."""
    acc_no = customer["account_number"]
    c = _get_container()
    result = c.account_service().change_password(
        acc_no=acc_no, current_pwd=req.current_password, new_pwd=req.new_password
    )
    if not result.success:
        _err(result.message)

    return _ok(MessageData(message=result.message))


@router.post("/account/close", response_model=ApiResponse[MessageData])
def v2_close_account(req: CloseAccountRequest, customer: dict = Depends(get_current_customer)) -> ApiResponse:
    """Close the authenticated customer's account."""
    if req.confirm_text != "CLOSE":
        _err("Please type 'CLOSE' to confirm.")

    from unionbank.utils import verify_password

    acc_no = customer["account_number"]
    c = _get_container()

    domain_account = c.account_repo().get(acc_no)
    if not domain_account:
        _err("Account not found.", status.HTTP_404_NOT_FOUND)

    if not verify_password(req.password, domain_account.password):
        _err("Incorrect password.")

    result = c.account_service().close_account(acc_no=acc_no, password=req.password)
    if not result.success:
        _err(result.message)

    return _ok(MessageData(message=result.message))


#  Customer Transaction Endpoints


@router.get("/account/balance", response_model=ApiResponse[BalanceData])
def v2_get_balance(customer: dict = Depends(get_current_customer)):
    """Get the current account balance."""
    c = _get_container()
    domain_account = c.account_repo().get(customer["account_number"])
    if not domain_account:
        _err("Account not found.", status.HTTP_404_NOT_FOUND)

    return _ok(
        BalanceData(
            account_number=domain_account.account_number,
            name=domain_account.name,
            balance=float(domain_account.balance),
            balance_formatted=_fmt_currency(float(domain_account.balance)),
        )
    )


@router.post("/account/deposit", response_model=ApiResponse[MessageData])
def v2_deposit_money(req: TransactionRequest, customer: dict = Depends(get_current_customer)) -> ApiResponse:
    """Deposit money into the authenticated customer's account."""
    acc_no = customer["account_number"]
    c = _get_container()
    result = c.transaction_service().deposit(
        acc_no=acc_no,
        amount=Decimal(str(req.amount)),
        category=req.category,
        idempotency_key=req.idempotency_key,
    )
    if not result.success:
        _err(result.message)

    return _ok(MessageData(message=result.message))


@router.post("/account/withdraw", response_model=ApiResponse[MessageData])
def v2_withdraw_money(req: TransactionRequest, customer: dict = Depends(get_current_customer)):
    """Withdraw money from the authenticated customer's account."""
    acc_no = customer["account_number"]
    c = _get_container()
    result = c.transaction_service().withdraw(
        acc_no=acc_no,
        amount=Decimal(str(req.amount)),
        category=req.category,
        idempotency_key=req.idempotency_key,
    )
    if not result.success:
        _err(result.message)

    return _ok(MessageData(message=result.message))


@router.post("/account/transfer", response_model=ApiResponse[MessageData])
def v2_transfer_funds(req: TransferRequest, customer: dict = Depends(get_current_customer)) -> ApiResponse:
    """Transfer funds to another account."""
    acc_no = customer["account_number"]
    c = _get_container()

    sender = c.account_repo().get(acc_no)
    if not sender:
        _err("Sender account not found.", status.HTTP_404_NOT_FOUND)

    receiver = c.account_repo().get(req.target_account)
    if not receiver:
        _err("Recipient account not found.", status.HTTP_404_NOT_FOUND)

    result = c.transaction_service().transfer(
        sender_acc_no=acc_no,
        receiver_acc_no=req.target_account,
        amount=Decimal(str(req.amount)),
        category=req.category,
        idempotency_key=req.idempotency_key,
    )
    if not result.success:
        _err(result.error_message)

    return _ok(
        MessageData(
            message=f"{_fmt_currency(req.amount)} transferred to {receiver.name} "
            f"({req.target_account}). New balance: {_fmt_currency(float(result.sender_balance))}"
        )
    )
