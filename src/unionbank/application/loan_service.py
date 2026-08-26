"""
application/loan_service.py  –  Loan and savings goal use-cases.

Contains LoanService (apply, approve, reject, pay EMI) and SavingsGoalService.
Extracted from services.py for focused maintenance.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pybreaker

from unionbank.domain.clock import utcnow as _utcnow
from unionbank.domain.entities import (
    Loan,
    LoanStatus,
    LoanType,
    SavingsGoal,
    ServiceResult,
    Transaction,
    TransactionType,
)
from unionbank.utils.formatting import (
    calculate_emi,
    fmt_currency,
    generate_goal_id,
    generate_loan_id,
    generate_transaction_id,
)

from .interfaces import (
    AccountRepositoryProtocol,
    AuditLogRepositoryProtocol,
    LoanRepositoryProtocol,
    NotificationServiceProtocol,
    SavingsGoalRepositoryProtocol,
    TransactionRepositoryProtocol,
)
from .services_shared import NOTIFICATION_BREAKER


# Loan product config per loan type
LOAN_PRODUCTS = {
    LoanType.PERSONAL.value: {"max_rate": 15.0, "min_rate": 10.0, "max_tenure": 60},
    LoanType.HOME.value: {"max_rate": 10.0, "min_rate": 7.0, "max_tenure": 360},
    LoanType.VEHICLE.value: {"max_rate": 12.0, "min_rate": 8.0, "max_tenure": 84},
    LoanType.EDUCATION.value: {"max_rate": 11.0, "min_rate": 7.5, "max_tenure": 120},
    LoanType.BUSINESS.value: {"max_rate": 18.0, "min_rate": 12.0, "max_tenure": 120},
}

# Derive LOAN_TYPES from the enum (single source of truth)
LOAN_TYPES = [lt.value for lt in LoanType]


class LoanService:
    """Loan management use-cases (apply, approve, reject, pay EMI, view)."""

    def __init__(
        self,
        loan_repo: LoanRepositoryProtocol,
        account_repo: AccountRepositoryProtocol,
        txn_repo: TransactionRepositoryProtocol,
        audit_log_repo: AuditLogRepositoryProtocol | None = None,
        notif_service: NotificationServiceProtocol | None = None,
    ):
        self.loan_repo = loan_repo
        self.account_repo = account_repo
        self.txn_repo = txn_repo
        self.audit_log_repo = audit_log_repo
        self.notif_service = notif_service

    def _audit_log(
        self, actor: str, action: str, target: str | None = None, details: str | None = None
    ) -> None:
        if self.audit_log_repo:
            self.audit_log_repo.log(
                actor=actor,
                action=action,
                target=target,
                details=details,
            )
            self.audit_log_repo.commit()

    # ── Getters ──

    def list_loans(self, acc_no: str) -> list[Loan]:
        return self.loan_repo.get_by_account(acc_no)

    def get_loan(self, loan_id: str) -> Loan | None:
        return self.loan_repo.get(loan_id)

    def list_pending(self) -> list[Loan]:
        return self.loan_repo.get_all_pending()

    def list_active(self) -> list[Loan]:
        return self.loan_repo.get_all_active()

    def list_all(self) -> list[Loan]:
        return self.loan_repo.get_all()

    def get_loan_statistics(self) -> dict:
        return {
            "total_pending": self.loan_repo.count_by_status(LoanStatus.PENDING.value),
            "total_approved": self.loan_repo.count_by_status(LoanStatus.APPROVED.value),
            "total_active": self.loan_repo.count_by_status(LoanStatus.ACTIVE.value),
            "total_closed": self.loan_repo.count_by_status(LoanStatus.CLOSED.value),
            "total_rejected": self.loan_repo.count_by_status(LoanStatus.REJECTED.value),
            "total_disbursed": float(self.loan_repo.total_disbursed()),
            "total_outstanding": float(self.loan_repo.total_outstanding()),
        }

    # ── Apply for loan ──

    def apply_loan(
        self,
        acc_no: str,
        loan_type: str,
        principal_amount: Decimal,
        interest_rate: Decimal,
        tenure_months: int,
        purpose: str = "",
    ) -> ServiceResult:
        """Apply for a new loan."""
        account = self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")
        if not account.can_transact:
            return ServiceResult(success=False, message="Account is frozen or closed.")

        if loan_type not in LOAN_TYPES:
            return ServiceResult(
                success=False,
                message=f"Invalid loan type. Choose from: {', '.join(LOAN_TYPES)}",
            )

        min_principal = 1000
        max_principal = 10000000
        if principal_amount < min_principal:
            return ServiceResult(
                success=False,
                message=f"Minimum loan amount is {fmt_currency(min_principal)}.",
            )
        if principal_amount > max_principal:
            return ServiceResult(
                success=False,
                message=f"Maximum loan amount is {fmt_currency(max_principal)}.",
            )

        product = LOAN_PRODUCTS.get(loan_type, {})
        max_tenure = product.get("max_tenure", 60)
        if tenure_months < 1 or tenure_months > max_tenure:
            return ServiceResult(
                success=False,
                message=f"Tenure must be between 1 and {max_tenure} months for {loan_type} loans.",
            )

        min_rate = product.get("min_rate", 5.0)
        max_rate = product.get("max_rate", 20.0)
        if interest_rate < Decimal(str(min_rate)) or interest_rate > Decimal(str(max_rate)):
            return ServiceResult(
                success=False,
                message=f"Interest rate must be between {min_rate}% and {max_rate}% for {loan_type} loans.",
            )

        emi = Decimal(
            str(calculate_emi(float(principal_amount), float(interest_rate), tenure_months))
        )

        now = _utcnow()
        loan = Loan(
            loan_id=generate_loan_id(),
            account_number=acc_no,
            loan_type=loan_type,
            principal_amount=principal_amount,
            interest_rate=interest_rate,
            tenure_months=tenure_months,
            emi_amount=emi,
            amount_paid=Decimal("0.00"),
            remaining_amount=principal_amount,
            status=LoanStatus.PENDING.value,
            application_date=now,
            purpose=purpose,
        )
        self.loan_repo.create(loan)
        self.loan_repo.commit()

        self._audit_log(
            actor=acc_no,
            action="loan_apply",
            target=loan.loan_id,
            details=f"Applied for {loan_type} loan of {fmt_currency(float(principal_amount))}",
        )

        return ServiceResult(
            success=True,
            message=f"Loan application submitted! Your EMI would be {fmt_currency(float(emi))}/month.",
            data={
                "loan_id": loan.loan_id,
                "emi_amount": float(emi),
            },
        )

    # ── Admin: Approve loan ──

    def approve_loan(self, loan_id: str, admin_user: str = "admin") -> ServiceResult:
        """Approve a pending loan and disburse funds."""
        loan = self.loan_repo.get(loan_id)
        if loan is None:
            return ServiceResult(success=False, message="Loan not found.")
        if loan.status != LoanStatus.PENDING.value:
            return ServiceResult(
                success=False,
                message=f"Loan is already {loan.status.lower()}. Only pending loans can be approved.",
            )

        account = self.account_repo.get(loan.account_number)
        if account is None:
            return ServiceResult(success=False, message="Customer account not found.")
        if not account.can_transact:
            return ServiceResult(success=False, message="Customer account is frozen or closed.")

        now = _utcnow()
        first_emi_date = now + timedelta(days=30)

        loan.status = LoanStatus.ACTIVE.value
        loan.approval_date = now
        loan.next_emi_date = first_emi_date
        self.loan_repo.update(loan)

        account.balance += loan.principal_amount
        self.account_repo.update(account)

        txn = Transaction(
            txn_id=generate_transaction_id(),
            account_number=loan.account_number,
            type=TransactionType.LOAN_DISBURSEMENT,
            amount=loan.principal_amount,
            balance=account.balance,
            description=f"{loan.loan_type} loan disbursement ({loan.loan_id})",
            category="Loan",
        )
        self.txn_repo.create(txn)
        self.loan_repo.commit()

        self._audit_log(
            actor=admin_user,
            action="loan_approve",
            target=loan_id,
            details=f"Approved {loan.loan_type} loan of {fmt_currency(float(loan.principal_amount))} for {loan.account_number}",
        )

        if self.notif_service:
            try:
                NOTIFICATION_BREAKER.call(self.notif_service.notify_loan_approved)(
                    loan.account_number,
                    loan.principal_amount,
                    loan.loan_type,
                    loan.loan_id,
                )
            except pybreaker.CircuitBreakerError:
                from unionbank.utils.logger import logger

                logger.warning(
                    "Notification circuit breaker open, skipping loan approval notification"
                )
            except (OSError, ValueError, TypeError, AttributeError):
                from unionbank.utils.logger import logger

                logger.warning("Failed to send loan approval notification", exc_info=True)

        return ServiceResult(
            success=True,
            message=f"Loan approved! {fmt_currency(float(loan.principal_amount))} disbursed to account {loan.account_number}.",
            data={"balance": float(account.balance)},
        )

    # ── Admin: Reject loan ──

    def reject_loan(
        self, loan_id: str, reason: str = "", admin_user: str = "admin"
    ) -> ServiceResult:
        """Reject a pending loan application."""
        loan = self.loan_repo.get(loan_id)
        if loan is None:
            return ServiceResult(success=False, message="Loan not found.")
        if loan.status != LoanStatus.PENDING.value:
            return ServiceResult(
                success=False,
                message=f"Loan is already {loan.status.lower()}. Only pending loans can be rejected.",
            )

        loan.status = LoanStatus.REJECTED.value
        if reason:
            loan.admin_notes = reason
        self.loan_repo.update(loan)
        self.loan_repo.commit()

        self._audit_log(
            actor=admin_user,
            action="loan_reject",
            target=loan_id,
            details=f"Rejected {loan.loan_type} loan: {reason or 'No reason provided'}",
        )

        if self.notif_service:
            try:
                NOTIFICATION_BREAKER.call(self.notif_service.notify_loan_rejected)(
                    loan.account_number, loan.loan_type, loan.loan_id, reason
                )
            except pybreaker.CircuitBreakerError:
                from unionbank.utils.logger import logger

                logger.warning(
                    "Notification circuit breaker open, skipping loan rejection notification"
                )
            except (OSError, ValueError, TypeError, AttributeError):
                from unionbank.utils.logger import logger

                logger.warning("Failed to send loan rejection notification", exc_info=True)

        return ServiceResult(
            success=True,
            message="Loan application rejected." + (f" Reason: {reason}" if reason else ""),
        )

    # ── Pay EMI ──

    def pay_emi(self, acc_no: str, loan_id: str, amount: Decimal | None = None) -> ServiceResult:
        """Pay the monthly EMI for a loan."""
        loan = self.loan_repo.get(loan_id)
        if loan is None:
            return ServiceResult(success=False, message="Loan not found.")
        if loan.status not in (LoanStatus.APPROVED.value, LoanStatus.ACTIVE.value):
            return ServiceResult(
                success=False,
                message=f"Loan is {loan.status.lower()}. Only active loans can receive payments.",
            )
        if loan.account_number != acc_no:
            return ServiceResult(success=False, message="Loan does not belong to this account.")

        account = self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")
        if not account.can_transact:
            return ServiceResult(success=False, message="Account is frozen or closed.")

        payment = amount if amount is not None else loan.emi_amount
        if payment <= 0:
            return ServiceResult(success=False, message="Payment amount must be positive.")

        if payment > account.balance:
            return ServiceResult(
                success=False,
                message=f"Insufficient balance. Available: {fmt_currency(float(account.balance))}",
            )

        remaining_debt = loan.remaining_amount
        actual_payment = min(payment, remaining_debt)

        account.balance -= actual_payment
        self.account_repo.update(account)

        loan.amount_paid += actual_payment
        loan.remaining_amount -= actual_payment

        if loan.next_emi_date:
            loan.next_emi_date = loan.next_emi_date + timedelta(days=30)
        else:
            loan.next_emi_date = _utcnow() + timedelta(days=30)

        if loan.remaining_amount <= 0:
            loan.status = LoanStatus.CLOSED.value
            loan.remaining_amount = Decimal("0.00")
            loan.next_emi_date = None

        self.loan_repo.update(loan)

        txn = Transaction(
            txn_id=generate_transaction_id(),
            account_number=acc_no,
            type=TransactionType.LOAN_REPAYMENT,
            amount=actual_payment,
            balance=account.balance,
            description=f"EMI payment for {loan.loan_type} loan ({loan.loan_id})",
            category="Loan",
        )
        self.txn_repo.create(txn)
        self.loan_repo.commit()

        is_closed = loan.status == "CLOSED"
        msg = f"EMI of {fmt_currency(float(actual_payment))} paid for {loan.loan_type} loan."
        if is_closed:
            msg += " 🎉 Loan fully paid off! Congratulations!"

        if self.notif_service:
            try:
                NOTIFICATION_BREAKER.call(self.notif_service.notify_emi_paid)(
                    acc_no,
                    actual_payment,
                    loan.loan_type,
                    loan.loan_id,
                    loan.remaining_amount,
                )
                if is_closed:
                    NOTIFICATION_BREAKER.call(self.notif_service.notify_loan_closed)(
                        acc_no, loan.loan_type, loan.loan_id
                    )
            except pybreaker.CircuitBreakerError:
                from unionbank.utils.logger import logger

                logger.warning("Notification circuit breaker open, skipping EMI notification")
            except (OSError, ValueError, TypeError, AttributeError):
                from unionbank.utils.logger import logger

                logger.warning("Failed to send EMI notification", exc_info=True)

        return ServiceResult(
            success=True,
            message=msg,
            data={
                "amount_paid": float(actual_payment),
                "remaining_amount": float(loan.remaining_amount),
                "balance": float(account.balance),
                "is_closed": is_closed,
            },
        )

    # ── Calculate EMI preview ──

    def calculate_emi_preview(
        self, principal: float, annual_rate: float, tenure_months: int
    ) -> dict:
        """Calculate EMI preview without creating an application."""
        emi = calculate_emi(principal, annual_rate, tenure_months)
        total_payable = round(emi * tenure_months, 2)
        total_interest = round(total_payable - principal, 2)

        return {
            "principal": principal,
            "annual_rate": annual_rate,
            "tenure_months": tenure_months,
            "emi": emi,
            "total_payable": total_payable,
            "total_interest": total_interest,
        }


# ── Savings Goal Service ──


class SavingsGoalService:
    """Savings goal use-cases."""

    def __init__(
        self,
        goal_repo: SavingsGoalRepositoryProtocol,
        account_repo: AccountRepositoryProtocol,
        txn_repo: TransactionRepositoryProtocol,
    ):
        self.goal_repo = goal_repo
        self.account_repo = account_repo
        self.txn_repo = txn_repo

    def list_goals(self, acc_no: str) -> list[SavingsGoal]:
        return self.goal_repo.get_by_account(acc_no)

    def create_goal(
        self, acc_no: str, name: str, target_amount: Decimal, target_date: str | None = None
    ) -> ServiceResult:
        if not name or len(name) < 2:
            return ServiceResult(success=False, message="Goal name must be at least 2 characters.")
        if target_amount <= 0:
            return ServiceResult(success=False, message="Target amount must be positive.")

        goal = SavingsGoal(
            goal_id=generate_goal_id(),
            account_number=acc_no,
            name=name,
            target_amount=target_amount,
            target_date=target_date,
        )
        self.goal_repo.create(goal)
        self.goal_repo.commit()
        return ServiceResult(success=True, message=f"Goal '{name}' created!")

    def contribute(self, acc_no: str, goal_id: str, amount: Decimal) -> ServiceResult:
        if amount <= 0:
            return ServiceResult(success=False, message="Amount must be positive.")

        account = self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")
        if amount > account.balance:
            return ServiceResult(success=False, message="Insufficient balance.")

        goal = self.goal_repo.get(goal_id)
        if goal is None:
            return ServiceResult(success=False, message="Goal not found.")

        account.balance -= amount
        self.account_repo.update(account)

        txn = Transaction(
            txn_id=generate_transaction_id(),
            account_number=acc_no,
            type=TransactionType.TRANSFER_OUT,
            amount=amount,
            balance=account.balance,
            description=f"Savings goal: {goal.name}",
            category="Savings",
        )
        self.txn_repo.create(txn)

        self.goal_repo.contribute(goal_id, amount)
        self.account_repo.commit()

        return ServiceResult(
            success=True,
            message=f"{fmt_currency(float(amount))} contributed to '{goal.name}'!",
        )

    def delete_goal(self, acc_no: str, goal_id: str) -> ServiceResult:
        goal = self.goal_repo.get(goal_id)
        if goal is None:
            return ServiceResult(success=False, message="Goal not found.")

        refund = goal.current_amount
        name = goal.name
        self.goal_repo.delete(goal_id)

        if refund > 0:
            account = self.account_repo.get(acc_no)
            if account:
                account.balance += refund
                self.account_repo.update(account)

        self.goal_repo.commit()
        return ServiceResult(success=True, message=f"Goal '{name}' deleted. Amount refunded.")
