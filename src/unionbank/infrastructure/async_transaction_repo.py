"""
async_transaction_repo.py – Async SQLAlchemy Transaction, Idempotency,
and AuditLog repositories.

Mirrors the synchronous counterpart but uses ``AsyncSession`` for all
database operations. Used when the application is configured with a
PostgreSQL DATABASE_URL (async via asyncpg).
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from unionbank.application.interfaces import KeysetPage
from unionbank.domain.clock import utcnow as _utcnow
from unionbank.domain.entities import IdempotencyRecord, Transaction
from unionbank.infrastructure.mappers import map_transaction

from .persistence import AuditLogModel, IdempotencyModel, TransactionModel


#  Transaction Repository (async)


class AsyncSqlAlchemyTransactionRepository:
    """Transaction repository backed by async SQLAlchemy (asyncpg + PostgreSQL)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_account(self, acc_no: str) -> list[Transaction]:
        result = await self.session.execute(
            select(TransactionModel)
            .where(TransactionModel.account_number == acc_no)
            .order_by(TransactionModel.timestamp.desc())
        )
        models = result.scalars().all()
        return [map_transaction(m) for m in models]

    async def get_mini(self, acc_no: str, limit: int = 5) -> list[Transaction]:
        result = await self.session.execute(
            select(TransactionModel)
            .where(TransactionModel.account_number == acc_no)
            .order_by(TransactionModel.timestamp.desc())
            .limit(limit)
        )
        models = result.scalars().all()
        return [map_transaction(m) for m in models]

    async def create(self, transaction: Transaction) -> Transaction:
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

    async def get_all(self) -> list[Transaction]:
        result = await self.session.execute(
            select(TransactionModel).order_by(TransactionModel.timestamp.desc())
        )
        models = result.scalars().all()
        return [map_transaction(m) for m in models]

    async def total_by_type(self, txn_type: str) -> Decimal:
        result = await self.session.execute(
            select(func.sum(TransactionModel.amount)).where(TransactionModel.type == txn_type)
        )
        return result.scalar() or Decimal("0.00")

    async def count(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(TransactionModel))
        return result.scalar() or 0

    async def count_by_account(self, acc_no: str) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(TransactionModel)
            .where(TransactionModel.account_number == acc_no)
        )
        return result.scalar() or 0

    async def get_category_totals(self) -> dict[str, Decimal]:
        result = await self.session.execute(
            select(TransactionModel.category, func.sum(TransactionModel.amount)).group_by(
                TransactionModel.category
            )
        )
        rows = result.all()
        return {cat: total or Decimal("0.00") for cat, total in rows}

    async def get_paginated(
        self,
        acc_no: str | None = None,
        page: int = 1,
        per_page: int = 20,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        txn_type: str | None = None,
    ) -> tuple[list[Transaction], int]:
        query = select(TransactionModel)

        if acc_no:
            query = query.where(TransactionModel.account_number == acc_no)
        if from_date:
            query = query.where(TransactionModel.timestamp >= from_date)
        if to_date:
            query = query.where(TransactionModel.timestamp <= to_date)
        if txn_type:
            query = query.where(TransactionModel.type == txn_type)

        # Get total count
        count_query = select(func.count()).select_from(TransactionModel)
        if acc_no:
            count_query = count_query.where(TransactionModel.account_number == acc_no)
        if from_date:
            count_query = count_query.where(TransactionModel.timestamp >= from_date)
        if to_date:
            count_query = count_query.where(TransactionModel.timestamp <= to_date)
        if txn_type:
            count_query = count_query.where(TransactionModel.type == txn_type)

        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        offset = (page - 1) * per_page
        result = await self.session.execute(
            query.order_by(TransactionModel.timestamp.desc()).offset(offset).limit(per_page)
        )
        models = result.scalars().all()

        return [map_transaction(m) for m in models], total

    async def get_paginated_keyset(
        self,
        acc_no: str | None = None,
        limit: int = 20,
        cursor: datetime | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        txn_type: str | None = None,
    ) -> KeysetPage[Transaction]:
        query = select(TransactionModel)

        if acc_no:
            query = query.where(TransactionModel.account_number == acc_no)
        if from_date:
            query = query.where(TransactionModel.timestamp >= from_date)
        if to_date:
            query = query.where(TransactionModel.timestamp <= to_date)
        if txn_type:
            query = query.where(TransactionModel.type == txn_type)

        fetch_limit = limit + 1
        if cursor is not None:
            query = query.where(TransactionModel.timestamp < cursor)

        result = await self.session.execute(
            query.order_by(TransactionModel.timestamp.desc()).limit(fetch_limit)
        )
        models = result.scalars().all()

        has_more = len(models) > limit
        items = [map_transaction(m) for m in models[:limit]]
        next_cursor = items[-1].timestamp if items else None

        return KeysetPage(
            items=items,
            cursor=next_cursor,
            has_more=has_more,
            cursor_key="timestamp",
        )

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()


#  Idempotency Repository (async)


class AsyncSqlAlchemyIdempotencyRepository:
    """Idempotency key repository backed by async SQLAlchemy (asyncpg + PostgreSQL)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, idempotency_key: str) -> IdempotencyRecord | None:
        result = await self.session.execute(
            select(IdempotencyModel).where(IdempotencyModel.idempotency_key == idempotency_key)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return IdempotencyRecord(
            idempotency_key=model.idempotency_key,
            account_number=model.account_number,
            operation=model.operation,
            result_json=model.result_json,
            amount=model.amount,
            created_at=model.created_at,
        )

    async def create(self, record: IdempotencyRecord) -> IdempotencyRecord:
        model = IdempotencyModel(
            idempotency_key=record.idempotency_key,
            account_number=record.account_number,
            operation=record.operation,
            result_json=record.result_json,
            amount=record.amount,
        )
        self.session.add(model)
        return record

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()


#  Audit Log Repository (async)


class AsyncSqlAlchemyAuditLogRepository:
    """Audit log repository — append-only, never deleted or updated. (async)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def log(
        self,
        actor: str,
        action: str,
        target: str | None = None,
        details: str | None = None,
        ip_address: str | None = None,
        reason: str | None = None,
    ) -> None:
        model = AuditLogModel(
            actor=actor,
            action=action,
            target=target,
            details=details[:500] if details else None,
            ip_address=ip_address,
            reason=reason[:200] if reason else None,
            timestamp=datetime.now(timezone.utc),
        )
        self.session.add(model)

    async def get_recent(self, limit: int = 50) -> list:
        result = await self.session.execute(
            select(AuditLogModel).order_by(AuditLogModel.timestamp.desc()).limit(limit)
        )
        models = result.scalars().all()
        return [
            {
                "id": m.id,
                "actor": m.actor,
                "action": m.action,
                "target": m.target,
                "details": m.details,
                "ip_address": m.ip_address,
                "reason": m.reason,
                "timestamp": str(m.timestamp)[:19],
            }
            for m in models
        ]

    async def get_by_actor(self, actor: str, limit: int = 50) -> list:
        result = await self.session.execute(
            select(AuditLogModel)
            .where(AuditLogModel.actor == actor)
            .order_by(AuditLogModel.timestamp.desc())
            .limit(limit)
        )
        models = result.scalars().all()
        return [
            {
                "id": m.id,
                "actor": m.actor,
                "action": m.action,
                "target": m.target,
                "details": m.details,
                "ip_address": m.ip_address,
                "reason": m.reason,
                "timestamp": str(m.timestamp)[:19],
            }
            for m in models
        ]

    async def get_by_action(self, action: str, limit: int = 50) -> list:
        result = await self.session.execute(
            select(AuditLogModel)
            .where(AuditLogModel.action == action)
            .order_by(AuditLogModel.timestamp.desc())
            .limit(limit)
        )
        models = result.scalars().all()
        return [
            {
                "id": m.id,
                "actor": m.actor,
                "action": m.action,
                "target": m.target,
                "details": m.details,
                "ip_address": m.ip_address,
                "reason": m.reason,
                "timestamp": str(m.timestamp)[:19],
            }
            for m in models
        ]

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
