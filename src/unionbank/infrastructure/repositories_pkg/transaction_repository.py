"""Transaction repository backed by SQLAlchemy + SQLite."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from unionbank.application.interfaces import KeysetPage
from unionbank.domain.clock import utcnow as _utcnow  # noqa: F401
from unionbank.domain.entities import Transaction
from unionbank.infrastructure.mappers import map_transaction

from ..persistence import TransactionModel


class SqlAlchemyTransactionRepository:
    """Transaction repository backed by SQLAlchemy + SQLite."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_account(self, acc_no: str) -> list[Transaction]:
        models = (
            self.session.query(TransactionModel)
            .filter_by(account_number=acc_no)
            .order_by(TransactionModel.timestamp.desc())
            .all()
        )
        return [map_transaction(m) for m in models]

    def get_mini(self, acc_no: str, limit: int = 5) -> list[Transaction]:
        models = (
            self.session.query(TransactionModel)
            .filter_by(account_number=acc_no)
            .order_by(TransactionModel.timestamp.desc())
            .limit(limit)
            .all()
        )
        return [map_transaction(m) for m in models]

    def create(self, transaction: Transaction) -> Transaction:
        model = TransactionModel(
            txn_id=transaction.txn_id,
            account_number=transaction.account_number,
            type=transaction.type.value,
            amount=transaction.amount,
            balance=transaction.balance,
            description=transaction.description,
            category=transaction.category,
            target_account=transaction.target_account,
            timestamp=transaction.timestamp or _utcnow(),
        )
        self.session.add(model)
        return transaction

    def get_all(self) -> list[Transaction]:
        models = (
            self.session.query(TransactionModel).order_by(TransactionModel.timestamp.desc()).all()
        )
        return [map_transaction(m) for m in models]

    def total_by_type(self, txn_type: str) -> Decimal:
        result = (
            self.session.query(func.sum(TransactionModel.amount)).filter_by(type=txn_type).scalar()
        )
        return result or Decimal("0.00")

    def count(self) -> int:
        return self.session.query(TransactionModel).count()

    def count_by_account(self, acc_no: str) -> int:
        return self.session.query(TransactionModel).filter_by(account_number=acc_no).count()

    def get_category_totals(self) -> dict[str, Decimal]:
        results = (
            self.session.query(TransactionModel.category, func.sum(TransactionModel.amount))
            .group_by(TransactionModel.category)
            .all()
        )
        return {cat: total or Decimal("0.00") for cat, total in results}

    def get_paginated(
        self,
        acc_no: str | None = None,
        page: int = 1,
        per_page: int = 20,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        txn_type: str | None = None,
    ) -> tuple[list[Transaction], int]:
        query = self.session.query(TransactionModel)

        if acc_no:
            query = query.filter(TransactionModel.account_number == acc_no)
        if from_date:
            query = query.filter(TransactionModel.timestamp >= from_date)
        if to_date:
            query = query.filter(TransactionModel.timestamp <= to_date)
        if txn_type:
            query = query.filter(TransactionModel.type == txn_type)

        total = query.count()
        offset = (page - 1) * per_page
        models = (
            query.order_by(TransactionModel.timestamp.desc()).offset(offset).limit(per_page).all()
        )

        return [map_transaction(m) for m in models], total

    def get_paginated_keyset(
        self,
        acc_no: str | None = None,
        limit: int = 20,
        cursor: datetime | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        txn_type: str | None = None,
    ) -> KeysetPage[Transaction]:
        """
        Keyset (cursor-based) pagination for transactions.

        Instead of OFFSET/LIMIT (which degrades on large datasets), this
        uses WHERE timestamp < :cursor to fetch the next page. The cursor
        is the timestamp of the last item in the previous page.

        Returns a KeysetPage with items, next cursor, and has_more flag.
        """
        query = self.session.query(TransactionModel)

        if acc_no:
            query = query.filter(TransactionModel.account_number == acc_no)
        if from_date:
            query = query.filter(TransactionModel.timestamp >= from_date)
        if to_date:
            query = query.filter(TransactionModel.timestamp <= to_date)
        if txn_type:
            query = query.filter(TransactionModel.type == txn_type)

        # Keyset: fetch one more than needed to determine has_more
        fetch_limit = limit + 1
        if cursor is not None:
            query = query.filter(TransactionModel.timestamp < cursor)

        models = query.order_by(TransactionModel.timestamp.desc()).limit(fetch_limit).all()

        has_more = len(models) > limit
        items = [map_transaction(m) for m in models[:limit]]
        next_cursor = items[-1].timestamp if items else None

        return KeysetPage(
            items=items,
            cursor=next_cursor,
            has_more=has_more,
            cursor_key="timestamp",
        )

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
