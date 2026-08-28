"""Idempotency and Audit Log repositories backed by SQLAlchemy + SQLite."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from unionbank.domain.entities import IdempotencyRecord

from ..persistence import AuditLogModel, IdempotencyModel


class SqlAlchemyIdempotencyRepository:
    """Idempotency key repository backed by SQLAlchemy + SQLite."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, idempotency_key: str) -> IdempotencyRecord | None:
        """Retrieve an existing idempotency record by key."""
        model = (
            self.session.query(IdempotencyModel).filter_by(idempotency_key=idempotency_key).first()
        )
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

    def create(self, record: IdempotencyRecord) -> IdempotencyRecord:
        """Store an idempotency record."""
        model = IdempotencyModel(
            idempotency_key=record.idempotency_key,
            account_number=record.account_number,
            operation=record.operation,
            result_json=record.result_json,
            amount=record.amount,
        )
        self.session.add(model)
        return record

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()


class SqlAlchemyAuditLogRepository:
    """Audit log repository — append-only, never deleted or updated."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def log(
        self,
        actor: str,
        action: str,
        target: str | None = None,
        details: str | None = None,
        ip_address: str | None = None,
        reason: str | None = None,
    ) -> None:
        """Append an immutable audit log entry."""
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

    def get_recent(self, limit: int = 50) -> list:
        models = (
            self.session.query(AuditLogModel)
            .order_by(AuditLogModel.timestamp.desc())
            .limit(limit)
            .all()
        )
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

    def get_by_actor(self, actor: str, limit: int = 50) -> list:
        models = (
            self.session.query(AuditLogModel)
            .filter_by(actor=actor)
            .order_by(AuditLogModel.timestamp.desc())
            .limit(limit)
            .all()
        )
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

    def get_by_action(self, action: str, limit: int = 50) -> list:
        models = (
            self.session.query(AuditLogModel)
            .filter_by(action=action)
            .order_by(AuditLogModel.timestamp.desc())
            .limit(limit)
            .all()
        )
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

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
