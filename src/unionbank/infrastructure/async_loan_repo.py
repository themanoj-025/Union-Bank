"""
async_loan_repo.py – Async SQLAlchemy Loan repository.

Mirrors the synchronous counterpart but uses ``AsyncSession`` for all
database operations. Used when the application is configured with a
PostgreSQL DATABASE_URL (async via asyncpg).
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from unionbank.domain.entities import Loan
from unionbank.infrastructure.mappers import map_loan

from .persistence import LoanModel


#  Loan Repository (async)


class AsyncSqlAlchemyLoanRepository:
    """Loan repository backed by async SQLAlchemy (asyncpg + PostgreSQL)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, loan_id: str) -> Loan | None:
        result = await self.session.execute(select(LoanModel).where(LoanModel.loan_id == loan_id))
        model = result.scalar_one_or_none()
        return map_loan(model) if model else None

    async def get_by_account(self, acc_no: str) -> list[Loan]:
        result = await self.session.execute(
            select(LoanModel)
            .where(LoanModel.account_number == acc_no)
            .order_by(LoanModel.application_date.desc())
        )
        models = result.scalars().all()
        return [map_loan(m) for m in models]

    async def get_all_pending(self) -> list[Loan]:
        result = await self.session.execute(
            select(LoanModel)
            .where(LoanModel.status == "PENDING")
            .order_by(LoanModel.application_date.asc())
        )
        models = result.scalars().all()
        return [map_loan(m) for m in models]

    async def get_all_active(self) -> list[Loan]:
        result = await self.session.execute(
            select(LoanModel)
            .where(LoanModel.status.in_(["APPROVED", "ACTIVE"]))
            .order_by(LoanModel.application_date.desc())
        )
        models = result.scalars().all()
        return [map_loan(m) for m in models]

    async def get_all(self) -> list[Loan]:
        result = await self.session.execute(
            select(LoanModel).order_by(LoanModel.application_date.desc())
        )
        models = result.scalars().all()
        return [map_loan(m) for m in models]

    async def create(self, loan: Loan) -> Loan:
        model = LoanModel(
            loan_id=loan.loan_id,
            account_number=loan.account_number,
            loan_type=loan.loan_type,
            principal_amount=loan.principal_amount,
            interest_rate=loan.interest_rate,
            tenure_months=loan.tenure_months,
            emi_amount=loan.emi_amount,
            amount_paid=loan.amount_paid,
            remaining_amount=loan.remaining_amount,
            status=loan.status,
            application_date=loan.application_date,
            approval_date=loan.approval_date,
            next_emi_date=loan.next_emi_date,
            purpose=loan.purpose,
            admin_notes=loan.admin_notes,
        )
        self.session.add(model)
        return loan

    async def update(self, loan: Loan) -> Loan:
        result = await self.session.execute(
            select(LoanModel).where(LoanModel.loan_id == loan.loan_id)
        )
        model = result.scalar_one_or_none()
        if model:
            model.loan_type = loan.loan_type
            model.principal_amount = loan.principal_amount
            model.interest_rate = loan.interest_rate
            model.tenure_months = loan.tenure_months
            model.emi_amount = loan.emi_amount
            model.amount_paid = loan.amount_paid
            model.remaining_amount = loan.remaining_amount
            model.status = loan.status
            model.approval_date = loan.approval_date
            model.next_emi_date = loan.next_emi_date
            model.purpose = loan.purpose
            model.admin_notes = loan.admin_notes
        return loan

    async def count_by_status(self, status: str) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(LoanModel).where(LoanModel.status == status)
        )
        return result.scalar() or 0

    async def total_disbursed(self) -> Decimal:
        result = await self.session.execute(
            select(func.sum(LoanModel.principal_amount)).where(
                LoanModel.status.in_(["APPROVED", "ACTIVE", "CLOSED"])
            )
        )
        return result.scalar() or Decimal("0.00")

    async def total_outstanding(self) -> Decimal:
        result = await self.session.execute(
            select(func.sum(LoanModel.remaining_amount)).where(
                LoanModel.status.in_(["APPROVED", "ACTIVE"])
            )
        )
        return result.scalar() or Decimal("0.00")

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
