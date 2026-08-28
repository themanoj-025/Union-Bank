"""
async_account_repo.py – Async SQLAlchemy Account + SavingsGoal repositories.

Mirrors the synchronous counterpart but uses ``AsyncSession`` for all
database operations. Used when the application is configured with a
PostgreSQL DATABASE_URL (async via asyncpg).
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from unionbank.domain.clock import utcnow as _utcnow
from unionbank.domain.entities import Account, SavingsGoal
from unionbank.infrastructure.mappers import (
    map_account,
    map_account_to_model,
    map_savings_goal,
)

from .persistence import AccountModel, SavingsGoalModel


#  Account Repository (async)


class AsyncSqlAlchemyAccountRepository:
    """Account repository backed by async SQLAlchemy (asyncpg + PostgreSQL)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, acc_no: str) -> Account | None:
        result = await self.session.execute(
            select(AccountModel).where(
                AccountModel.account_number == acc_no,
                AccountModel.deleted_at.is_(None),
            )
        )
        model = result.scalar_one_or_none()
        return map_account(model) if model else None

    async def get_all(self) -> list[Account]:
        result = await self.session.execute(
            select(AccountModel).where(AccountModel.deleted_at.is_(None))
        )
        models = result.scalars().all()
        return [map_account(m) for m in models]

    async def exists(self, acc_no: str) -> bool:
        result = await self.session.execute(
            select(AccountModel.account_number)
            .where(
                AccountModel.account_number == acc_no,
                AccountModel.deleted_at.is_(None),
            )
            .limit(1)
        )
        return result.first() is not None

    async def create(self, account: Account) -> Account:
        data = map_account_to_model(account)
        model = AccountModel(**data)
        self.session.add(model)
        return account

    async def update(self, account: Account) -> Account:
        result = await self.session.execute(
            select(AccountModel).where(
                AccountModel.account_number == account.account_number,
                AccountModel.deleted_at.is_(None),
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return await self.create(account)
        for key, value in map_account_to_model(account).items():
            if key != "created_at":
                setattr(model, key, value)
        return account

    async def update_balance(self, acc_no: str, new_balance: Decimal) -> bool:
        result = await self.session.execute(
            select(AccountModel).where(
                AccountModel.account_number == acc_no,
                AccountModel.deleted_at.is_(None),
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return False
        model.balance = new_balance
        return True

    async def set_active(self, acc_no: str, active: bool) -> bool:
        result = await self.session.execute(
            select(AccountModel).where(
                AccountModel.account_number == acc_no,
                AccountModel.deleted_at.is_(None),
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return False
        model.is_active = active
        return True

    async def set_frozen(self, acc_no: str, frozen: bool) -> bool:
        result = await self.session.execute(
            select(AccountModel).where(
                AccountModel.account_number == acc_no,
                AccountModel.deleted_at.is_(None),
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return False
        model.is_frozen = frozen
        return True

    async def delete(self, acc_no: str) -> bool:
        result = await self.session.execute(
            select(AccountModel).where(
                AccountModel.account_number == acc_no,
                AccountModel.deleted_at.is_(None),
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return False
        model.deleted_at = _utcnow()
        model.is_active = False
        return True

    async def undelete(self, acc_no: str) -> bool:
        result = await self.session.execute(
            select(AccountModel).where(
                AccountModel.account_number == acc_no,
                AccountModel.deleted_at.isnot(None),
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return False
        model.deleted_at = None
        model.is_active = True
        return True

    async def get_deleted(self, acc_no: str) -> Account | None:
        result = await self.session.execute(
            select(AccountModel).where(
                AccountModel.account_number == acc_no,
                AccountModel.deleted_at.isnot(None),
            )
        )
        model = result.scalar_one_or_none()
        return map_account(model) if model else None

    async def search(self, query: str) -> list[Account]:
        q = f"%{query}%"
        result = await self.session.execute(
            select(AccountModel).where(
                AccountModel.deleted_at.is_(None),
                or_(
                    AccountModel.account_number.ilike(q),
                    AccountModel.name.ilike(q),
                ),
            )
        )
        models = result.scalars().all()
        return [map_account(m) for m in models]

    async def count(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(AccountModel).where(AccountModel.deleted_at.is_(None))
        )
        return result.scalar() or 0

    async def total_balance(self) -> Decimal:
        result = await self.session.execute(
            select(func.sum(AccountModel.balance)).where(
                AccountModel.deleted_at.is_(None),
                AccountModel.is_active.is_(True),
                AccountModel.is_frozen.is_(False),
            )
        )
        return result.scalar() or Decimal("0.00")

    async def active_count(self) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(AccountModel)
            .where(
                AccountModel.deleted_at.is_(None),
                AccountModel.is_active.is_(True),
                AccountModel.is_frozen.is_(False),
            )
        )
        return result.scalar() or 0

    async def frozen_count(self) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(AccountModel)
            .where(
                AccountModel.deleted_at.is_(None),
                AccountModel.is_frozen.is_(True),
            )
        )
        return result.scalar() or 0

    async def closed_count(self) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(AccountModel)
            .where(
                AccountModel.deleted_at.is_(None),
                AccountModel.is_active.is_(False),
                AccountModel.is_frozen.is_(False),
            )
        )
        return result.scalar() or 0

    async def get_by_email(self, email: str) -> Account | None:
        result = await self.session.execute(
            select(AccountModel).where(
                AccountModel.email == email,
                AccountModel.deleted_at.is_(None),
            )
        )
        model = result.scalar_one_or_none()
        return map_account(model) if model else None

    async def get_statistics(self) -> dict:
        result = await self.session.execute(
            select(
                func.count(AccountModel.account_number).label("total"),
                func.sum(
                    case(
                        (AccountModel.is_active.is_(True) & AccountModel.is_frozen.is_(False), 1),
                        else_=0,
                    )
                ).label("active_count"),
                func.sum(case((AccountModel.is_frozen.is_(True), 1), else_=0)).label(
                    "frozen_count"
                ),
                func.sum(
                    case(
                        (AccountModel.is_active.is_(False) & AccountModel.is_frozen.is_(False), 1),
                        else_=0,
                    )
                ).label("closed_count"),
                func.sum(AccountModel.balance).label("total_balance"),
            ).where(AccountModel.deleted_at.is_(None))
        )
        row = result.one()

        return {
            "total_customers": row.total or 0,
            "active": row.active_count or 0,
            "frozen": row.frozen_count or 0,
            "closed": row.closed_count or 0,
            "total_balance": float(row.total_balance or Decimal("0.00")),
        }

    async def get_all_paginated(
        self, page: int = 1, per_page: int = 20
    ) -> tuple[list[Account], int]:
        total_result = await self.session.execute(
            select(func.count()).select_from(AccountModel).where(AccountModel.deleted_at.is_(None))
        )
        total = total_result.scalar() or 0

        offset = (page - 1) * per_page
        result = await self.session.execute(
            select(AccountModel)
            .where(AccountModel.deleted_at.is_(None))
            .order_by(AccountModel.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        models = result.scalars().all()
        return [map_account(m) for m in models], total

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()


#  Savings Goal Repository (async)


class AsyncSqlAlchemySavingsGoalRepository:
    """Savings goal repository backed by async SQLAlchemy (asyncpg + PostgreSQL)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_account(self, acc_no: str) -> list[SavingsGoal]:
        result = await self.session.execute(
            select(SavingsGoalModel).where(SavingsGoalModel.account_number == acc_no)
        )
        models = result.scalars().all()
        return [map_savings_goal(m) for m in models]

    async def get(self, goal_id: str) -> SavingsGoal | None:
        result = await self.session.execute(
            select(SavingsGoalModel).where(SavingsGoalModel.goal_id == goal_id)
        )
        model = result.scalar_one_or_none()
        return map_savings_goal(model) if model else None

    async def create(self, goal: SavingsGoal) -> SavingsGoal:
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

    async def update(self, goal: SavingsGoal) -> SavingsGoal:
        result = await self.session.execute(
            select(SavingsGoalModel).where(SavingsGoalModel.goal_id == goal.goal_id)
        )
        model = result.scalar_one_or_none()
        if model:
            model.name = goal.name
            model.target_amount = goal.target_amount
            model.current_amount = goal.current_amount
            model.target_date = goal.target_date
            model.is_completed = goal.is_completed
        return goal

    async def contribute(self, goal_id: str, amount: Decimal) -> SavingsGoal | None:
        result = await self.session.execute(
            select(SavingsGoalModel).where(SavingsGoalModel.goal_id == goal_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        model.current_amount += amount
        if model.current_amount >= model.target_amount:
            model.is_completed = True
        return map_savings_goal(model)

    async def delete(self, goal_id: str) -> SavingsGoal | None:
        result = await self.session.execute(
            select(SavingsGoalModel).where(SavingsGoalModel.goal_id == goal_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        goal = map_savings_goal(model)
        await self.session.delete(model)
        return goal

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
