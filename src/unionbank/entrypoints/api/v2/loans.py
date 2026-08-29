"""V2 API — Loan endpoints."""

from __future__ import annotations

from datetime import datetime, UTC
from decimal import Decimal

from fastapi import Depends, status

from unionbank.entrypoints.api.common import get_current_customer
from unionbank.entrypoints.api.models import (
    ApiResponse,
    EMICalculateRequest,
    EMIPreviewData,
    LoanApplyRequest,
    LoanOut,
    LoanPayEMIRequest,
    LoanSummaryData,
    MessageData,
)
from unionbank.entrypoints.api.v2.helpers import _err, _fmt_currency, _get_container, _ok

router = __import__("fastapi").APIRouter()


@router.get("/loans", response_model=ApiResponse[LoanSummaryData])
def v2_list_loans(customer: dict = Depends(get_current_customer)) -> ApiResponse:
    """List all loans for the authenticated customer."""
    acc_no = customer["account_number"]
    c = _get_container()
    loans = c.loan_service().list_loans(acc_no)

    loan_list = []
    for loan in loans:
        pct = (
            float(loan.amount_paid / loan.principal_amount * 100)
            if loan.principal_amount > 0
            else 0
        )
        remaining_emis = (
            int(loan.remaining_amount / loan.emi_amount)
            + (1 if loan.remaining_amount % loan.emi_amount > 0 else 0)
            if loan.emi_amount > 0
            else 0
        )
        is_overdue = False
        if loan.next_emi_date and loan.status in ("APPROVED", "ACTIVE"):
            is_overdue = datetime.now(UTC) > loan.next_emi_date

        loan_list.append(
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
                progress_pct=round(pct, 1),
                remaining_emis=remaining_emis,
                is_overdue=is_overdue,
            )
        )

    active_loans = sum(1 for loan in loans if loan.status in ("APPROVED", "ACTIVE"))
    closed_loans = sum(1 for loan in loans if loan.status == "CLOSED")
    total_disbursed = sum(
        float(loan.principal_amount)
        for loan in loans
        if loan.status in ("APPROVED", "ACTIVE", "CLOSED")
    )
    total_outstanding = sum(
        float(loan.remaining_amount) for loan in loans if loan.status in ("APPROVED", "ACTIVE")
    )

    return _ok(
        LoanSummaryData(
            total_loans=len(loans),
            active_loans=active_loans,
            closed_loans=closed_loans,
            total_disbursed=total_disbursed,
            total_disbursed_formatted=_fmt_currency(total_disbursed),
            total_outstanding=total_outstanding,
            total_outstanding_formatted=_fmt_currency(total_outstanding),
            loans=loan_list,
        )
    )


@router.post(
    "/loans/apply", response_model=ApiResponse[MessageData], status_code=status.HTTP_201_CREATED
)
def v2_apply_loan(req: LoanApplyRequest, customer: dict = Depends(get_current_customer)) -> ApiResponse:
    """Apply for a new loan."""
    acc_no = customer["account_number"]
    c = _get_container()

    result = c.loan_service().apply_loan(
        acc_no=acc_no,
        loan_type=req.loan_type,
        principal_amount=Decimal(str(req.principal_amount)),
        interest_rate=Decimal(str(req.interest_rate)),
        tenure_months=req.tenure_months,
        purpose=req.purpose,
    )
    if not result.success:
        _err(result.message)

    return _ok(MessageData(message=result.message))


@router.get("/loans/{loan_id}", response_model=ApiResponse[LoanOut])
def v2_get_loan(loan_id: str, customer: dict = Depends(get_current_customer)) -> dict[str, object]:
    """Get details of a specific loan."""
    acc_no = customer["account_number"]
    c = _get_container()
    loan = c.loan_service().get_loan(loan_id)

    if not loan:
        _err("Loan not found.", status.HTTP_404_NOT_FOUND)
    if loan.account_number != acc_no:
        _err("Loan not found for this account.", status.HTTP_404_NOT_FOUND)

    pct = float(loan.amount_paid / loan.principal_amount * 100) if loan.principal_amount > 0 else 0
    remaining_emis = (
        int(loan.remaining_amount / loan.emi_amount)
        + (1 if loan.remaining_amount % loan.emi_amount > 0 else 0)
        if loan.emi_amount > 0
        else 0
    )
    is_overdue = False
    if loan.next_emi_date and loan.status in ("APPROVED", "ACTIVE"):
        is_overdue = datetime.now(UTC) > loan.next_emi_date

    return _ok(
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
            progress_pct=round(pct, 1),
            remaining_emis=remaining_emis,
            is_overdue=is_overdue,
        )
    )


@router.post("/loans/{loan_id}/pay-emi", response_model=ApiResponse[MessageData])
def v2_pay_emi(
    loan_id: str, req: LoanPayEMIRequest, customer: dict = Depends(get_current_customer)
) -> ApiResponse:
    """Pay the monthly EMI for a loan."""
    acc_no = customer["account_number"]
    c = _get_container()

    amount = Decimal(str(req.amount)) if req.amount is not None else None
    result = c.loan_service().pay_emi(acc_no=acc_no, loan_id=loan_id, amount=amount)
    if not result.success:
        _err(result.message)

    return _ok(MessageData(message=result.message))


@router.post("/loans/calculate-emi", response_model=ApiResponse[EMIPreviewData])
def v2_calculate_emi(req: EMICalculateRequest) -> dict[str, object]:
    """Calculate EMI preview without applying for a loan."""
    c = _get_container()
    result = c.loan_service().calculate_emi_preview(
        principal=req.principal,
        annual_rate=req.annual_rate,
        tenure_months=req.tenure_months,
    )
    return _ok(EMIPreviewData(**result))
