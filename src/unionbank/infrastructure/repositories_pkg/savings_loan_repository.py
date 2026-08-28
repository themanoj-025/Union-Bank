"""Savings Goal and Loan repositories backed by SQLAlchemy + SQLite."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from unionbank.domain.entities import Loan, SavingsGoal
from unionbank.infrastructure.mappers import map_loan, map_savings_goal

from ..persistence import LoanModel, SavingsGoalModel


class SqlAlchemySavingsGoalRepository:
    """Savings goal repository backed by SQLAlchemy + SQLite."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_account(self, acc_no: str) -> list[SavingsGoal]:
        models = self.session.query(SavingsGoalModel).filter_by(account_number=acc_no).all()
        return [map_savings_goal(m) for m in models]

    def get(self, goal_id: str) -> SavingsGoal | None:
        model = self.session.query(SavingsGoalModel).filter_by(goal_id=goal_id).first()
        return map_savings_goal(model) if model else None

    def create(self, goal: SavingsGoal) -> SavingsGoal:
        model = SavingsGoalModel(
            goal_id=goal.goal_id,
            account_number=goal.account_number,
            name=goal.name,
            target_amount=goal.target_amount,
            current_amount=goal.current_amount,
            target_date=goal.target_date,
        )
        self.session.add(model)
        return goal

    def update(self, goal: SavingsGoal) -> SavingsGoal:
        model = self.session.query(SavingsGoalModel).filter_by(goal_id=goal.goal_id).first()
        if model:
            model.name = goal.name
            model.target_amount = goal.target_amount
            model.current_amount = goal.current_amount
            model.target_date = goal.target_date
            model.is_completed = goal.is_completed
        return goal

    def contribute(self, goal_id: str, amount: Decimal) -> SavingsGoal | None:
        model = self.session.query(SavingsGoalModel).filter_by(goal_id=goal_id).first()
        if model is None:
            return None
        model.current_amount += amount
        if model.current_amount >= model.target_amount:
            model.is_completed = True
        return map_savings_goal(model)

    def delete(self, goal_id: str) -> SavingsGoal | None:
        model = self.session.query(SavingsGoalModel).filter_by(goal_id=goal_id).first()
        if model is None:
            return None
        goal = map_savings_goal(model)
        self.session.delete(model)
        return goal

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()


class SqlAlchemyLoanRepository:
    """Loan repository backed by SQLAlchemy + SQLite."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, loan_id: str) -> Loan | None:
        model = self.session.query(LoanModel).filter_by(loan_id=loan_id).first()
        return map_loan(model) if model else None

    def get_by_account(self, acc_no: str) -> list[Loan]:
        models = (
            self.session.query(LoanModel)
            .filter_by(account_number=acc_no)
            .order_by(LoanModel.application_date.desc())
            .all()
        )
        return [map_loan(m) for m in models]

    def get_all_pending(self) -> list[Loan]:
        models = (
            self.session.query(LoanModel)
            .filter_by(status="PENDING")
            .order_by(LoanModel.application_date.asc())
            .all()
        )
        return [map_loan(m) for m in models]

    def get_all_active(self) -> list[Loan]:
        models = (
            self.session.query(LoanModel)
            .filter(LoanModel.status.in_(["APPROVED", "ACTIVE"]))
            .order_by(LoanModel.application_date.desc())
            .all()
        )
        return [map_loan(m) for m in models]

    def get_all(self) -> list[Loan]:
        models = self.session.query(LoanModel).order_by(LoanModel.application_date.desc()).all()
        return [map_loan(m) for m in models]

    def create(self, loan: Loan) -> Loan:
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

    def update(self, loan: Loan) -> Loan:
        model = self.session.query(LoanModel).filter_by(loan_id=loan.loan_id).first()
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

    def count_by_status(self, status: str) -> int:
        return self.session.query(LoanModel).filter_by(status=status).count()

    def total_disbursed(self) -> Decimal:
        result = (
            self.session.query(func.sum(LoanModel.principal_amount))
            .filter(LoanModel.status.in_(["APPROVED", "ACTIVE", "CLOSED"]))
            .scalar()
        )
        return result or Decimal("0.00")

    def total_outstanding(self) -> Decimal:
        result = (
            self.session.query(func.sum(LoanModel.remaining_amount))
            .filter(LoanModel.status.in_(["APPROVED", "ACTIVE"]))
            .scalar()
        )
        return result or Decimal("0.00")

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
