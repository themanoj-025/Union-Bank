"""Login attempt repository backed by SQLAlchemy + SQLite."""

from __future__ import annotations

from datetime import timedelta, UTC

from sqlalchemy.orm import Session

from unionbank.domain.clock import utcnow as _utcnow
from unionbank.domain.entities import LoginAttempt

_ = _utcnow  # used as default_factory in repository methods

from ..persistence import LoginAttemptModel


class SqlAlchemyLoginAttemptRepository:
    """Login attempt repository backed by SQLAlchemy + SQLite."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, key: str) -> LoginAttempt | None:
        model = self.session.query(LoginAttemptModel).filter_by(key=key).first()
        if model is None:
            return None
        return LoginAttempt(
            key=model.key,
            count=model.count or 0,
            first_failed=model.first_failed,
            lockout_until=model.lockout_until,
            updated_at=model.updated_at,
        )

    def record_failure(self, key: str, max_attempts: int = 5, lockout_minutes: int = 15) -> int:
        record = self.get(key)
        now = _utcnow()

        if record is None:
            record = LoginAttempt(key=key, count=1, first_failed=now)
            model = LoginAttemptModel(key=key, count=1, first_failed=now)
            self.session.add(model)
        else:
            model = self.session.query(LoginAttemptModel).filter_by(key=key).first()

            if model.lockout_until and now >= model.lockout_until:
                model.count = 1
                model.first_failed = now
                model.lockout_until = None
            else:
                model.count = (model.count or 0) + 1

            if model.count >= max_attempts:
                model.lockout_until = now + timedelta(minutes=lockout_minutes)

        return max(0, max_attempts - (getattr(model, "count", record.count) or 0))

    def is_locked(self, key: str, max_attempts: int = 5) -> tuple[bool, int]:
        model = self.session.query(LoginAttemptModel).filter_by(key=key).first()
        if model is None or (model.count or 0) < max_attempts:
            return False, 0

        now = _utcnow()
        lockout_until = model.lockout_until

        # Handle timezone-naive datetimes (SQLite may strip tzinfo on roundtrip)
        if lockout_until is not None and lockout_until.tzinfo is None:
            lockout_until = lockout_until.replace(tzinfo=UTC)

        if lockout_until and now < lockout_until:
            remaining = int((lockout_until - now).total_seconds() // 60)
            return True, max(1, remaining)
        if model:
            self.session.delete(model)
        return False, 0

    def reset(self, key: str) -> None:
        model = self.session.query(LoginAttemptModel).filter_by(key=key).first()
        if model:
            self.session.delete(model)

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
