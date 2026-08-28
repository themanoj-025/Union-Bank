"""Account repository backed by SQLAlchemy + SQLite."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from unionbank.domain.clock import utcnow as _utcnow
from unionbank.domain.entities import Account

_ = _utcnow  # used as default_factory in repository methods
from unionbank.infrastructure.mappers import map_account, map_account_to_model

from ..persistence import AccountModel


class SqlAlchemyAccountRepository:
    """Account repository backed by SQLAlchemy + SQLite."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, acc_no: str) -> Account | None:
        model = (
            self.session.query(AccountModel)
            .filter_by(account_number=acc_no, deleted_at=None)
            .first()
        )
        return map_account(model) if model else None

    def get_all(self) -> list[Account]:
        models = self.session.query(AccountModel).filter_by(deleted_at=None).all()
        return [map_account(m) for m in models]

    def exists(self, acc_no: str) -> bool:
        return (
            self.session.query(AccountModel)
            .filter_by(account_number=acc_no, deleted_at=None)
            .first()
            is not None
        )

    def create(self, account: Account) -> Account:
        data = map_account_to_model(account)
        model = AccountModel(**data)
        self.session.add(model)
        return account

    def update(self, account: Account) -> Account:
        model = (
            self.session.query(AccountModel)
            .filter_by(account_number=account.account_number, deleted_at=None)
            .first()
        )
        if model is None:
            return self.create(account)
        for key, value in map_account_to_model(account).items():
            if key != "created_at":
                setattr(model, key, value)
        return account

    def update_balance(self, acc_no: str, new_balance: Decimal) -> bool:
        model = (
            self.session.query(AccountModel)
            .filter_by(account_number=acc_no, deleted_at=None)
            .first()
        )
        if model is None:
            return False
        model.balance = new_balance
        return True

    def set_active(self, acc_no: str, active: bool) -> bool:
        model = (
            self.session.query(AccountModel)
            .filter_by(account_number=acc_no, deleted_at=None)
            .first()
        )
        if model is None:
            return False
        model.is_active = active
        return True

    def set_frozen(self, acc_no: str, frozen: bool) -> bool:
        """
        Set the frozen status of an account.

        NOTE: This does NOT change is_active. Freezing does not imply
        closing, and unfreezing does not imply reactivating.
        Callers that need to change both must call set_active() separately.
        """
        model = (
            self.session.query(AccountModel)
            .filter_by(account_number=acc_no, deleted_at=None)
            .first()
        )
        if model is None:
            return False
        model.is_frozen = frozen
        return True

    def delete(self, acc_no: str) -> bool:
        """
        Soft-delete: set deleted_at timestamp instead of removing the row.

        Transaction history and related records are preserved for audit/compliance.
        Soft-deleted accounts are excluded from all default queries via the
        `_active_query()` helper but remain recoverable via `get_deleted()`.
        """
        model = (
            self.session.query(AccountModel)
            .filter_by(account_number=acc_no, deleted_at=None)
            .first()
        )
        if model is None:
            return False
        from unionbank.domain.clock import utcnow as _now

        model.deleted_at = _now()
        model.is_active = False
        return True

    def undelete(self, acc_no: str) -> bool:
        """Restore a soft-deleted account by clearing deleted_at."""
        model = (
            self.session.query(AccountModel)
            .filter(
                AccountModel.account_number == acc_no,
                AccountModel.deleted_at.isnot(None),
            )
            .first()
        )
        if model is None:
            return False
        model.deleted_at = None
        model.is_active = True
        return True

    def get_deleted(self, acc_no: str) -> Account | None:
        """Get a soft-deleted account (bypasses the active-only filter)."""
        model = (
            self.session.query(AccountModel)
            .filter_by(account_number=acc_no)
            .filter(AccountModel.deleted_at.isnot(None))
            .first()
        )
        return map_account(model) if model else None

    def search(self, query: str) -> list[Account]:
        q = f"%{query}%"
        models = (
            self.session.query(AccountModel)
            .filter(
                AccountModel.deleted_at.is_(None),
                or_(
                    AccountModel.account_number.ilike(q),
                    AccountModel.name.ilike(q),
                ),
            )
            .all()
        )
        return [map_account(m) for m in models]

    def count(self) -> int:
        return self.session.query(AccountModel).filter_by(deleted_at=None).count()

    def total_balance(self) -> Decimal:
        result = (
            self.session.query(func.sum(AccountModel.balance))
            .filter(
                AccountModel.deleted_at.is_(None),
                AccountModel.is_active.is_(True),
                AccountModel.is_frozen.is_(False),
            )
            .scalar()
        )
        return result or Decimal("0.00")

    def active_count(self) -> int:
        return (
            self.session.query(AccountModel)
            .filter(
                AccountModel.deleted_at.is_(None),
                AccountModel.is_active.is_(True),
                AccountModel.is_frozen.is_(False),
            )
            .count()
        )

    def frozen_count(self) -> int:
        return (
            self.session.query(AccountModel)
            .filter(
                AccountModel.deleted_at.is_(None),
                AccountModel.is_frozen.is_(True),
            )
            .count()
        )

    def closed_count(self) -> int:
        return (
            self.session.query(AccountModel)
            .filter(
                AccountModel.deleted_at.is_(None),
                AccountModel.is_active.is_(False),
                AccountModel.is_frozen.is_(False),
            )
            .count()
        )

    def get_by_email(self, email: str) -> Account | None:
        model = self.session.query(AccountModel).filter_by(email=email, deleted_at=None).first()
        return map_account(model) if model else None

    def get_statistics(self) -> dict:
        """
        Get bank-wide account statistics in a single aggregate query.

        Returns:
            dict with keys: total_customers, active, frozen, closed, total_balance
        """
        row = (
            self.session.query(
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
            )
            .filter(AccountModel.deleted_at.is_(None))
            .first()
        )

        return {
            "total_customers": row.total or 0,
            "active": row.active_count or 0,
            "frozen": row.frozen_count or 0,
            "closed": row.closed_count or 0,
            "total_balance": float(row.total_balance or Decimal("0.00")),
        }

    def get_all_paginated(self, page: int = 1, per_page: int = 20) -> tuple[list[Account], int]:
        """
        Get accounts with offset-based pagination.

        Returns:
            Tuple of (accounts list, total count).
        """
        base_q = self.session.query(AccountModel).filter_by(deleted_at=None)
        total = base_q.count()
        offset = (page - 1) * per_page
        models = (
            base_q.order_by(AccountModel.created_at.desc()).offset(offset).limit(per_page).all()
        )
        return [map_account(m) for m in models], total

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
