"""Notification, Notification Preference, and Refresh Token repositories."""

from __future__ import annotations

from datetime import datetime, timedelta, UTC

from sqlalchemy.orm import Session

from unionbank.domain.clock import utcnow as _utcnow
from unionbank.domain.entities import (
    Notification,
    NotificationPreference,
    RefreshToken,
)

_ = _utcnow  # used as default_factory in repository methods
from unionbank.infrastructure.mappers import map_notification, map_refresh_token

from ..persistence import (
    NotificationModel,
    NotificationPreferenceModel,
    RefreshTokenModel,
)


class SqlAlchemyNotificationRepository:
    """In-app notification repository backed by SQLAlchemy + SQLite."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, notif_id: str) -> Notification | None:
        model = self.session.query(NotificationModel).filter_by(notif_id=notif_id).first()
        return map_notification(model) if model else None

    def get_by_account(self, acc_no: str, limit: int = 50) -> list[Notification]:
        models = (
            self.session.query(NotificationModel)
            .filter_by(account_number=acc_no)
            .order_by(NotificationModel.created_at.desc())
            .limit(limit)
            .all()
        )
        return [map_notification(m) for m in models]

    def get_unread_count(self, acc_no: str) -> int:
        return (
            self.session.query(NotificationModel)
            .filter_by(account_number=acc_no, is_read=False)
            .count()
        )

    def get_unread(self, acc_no: str, limit: int = 20) -> list[Notification]:
        models = (
            self.session.query(NotificationModel)
            .filter_by(account_number=acc_no, is_read=False)
            .order_by(NotificationModel.created_at.desc())
            .limit(limit)
            .all()
        )
        return [map_notification(m) for m in models]

    def create(self, notification: Notification) -> Notification:
        model = NotificationModel(
            notif_id=notification.notif_id,
            account_number=notification.account_number,
            type=notification.type,
            title=notification.title,
            message=notification.message,
            is_read=notification.is_read,
            created_at=notification.created_at or _utcnow(),
            related_txn_id=notification.related_txn_id,
        )
        self.session.add(model)
        return notification

    def mark_as_read(self, notif_id: str) -> bool:
        model = self.session.query(NotificationModel).filter_by(notif_id=notif_id).first()
        if model is None:
            return False
        model.is_read = True
        return True

    def mark_all_as_read(self, acc_no: str) -> int:
        count = (
            self.session.query(NotificationModel)
            .filter_by(account_number=acc_no, is_read=False)
            .update({"is_read": True})
        )
        return count

    def delete_old(self, days: int = 30) -> int:
        cutoff = _utcnow() - timedelta(days=days)
        deleted = (
            self.session.query(NotificationModel)
            .filter(NotificationModel.created_at < cutoff)
            .delete()
        )
        return deleted

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()


class SqlAlchemyNotificationPreferenceRepository:
    """Notification preferences repository backed by SQLAlchemy + SQLite."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, acc_no: str) -> NotificationPreference | None:
        model = (
            self.session.query(NotificationPreferenceModel).filter_by(account_number=acc_no).first()
        )
        if model is None:
            return None
        return NotificationPreference(
            account_number=model.account_number,
            in_app_enabled=model.in_app_enabled,
            email_enabled=model.email_enabled,
            sms_enabled=model.sms_enabled,
            deposit_alerts=model.deposit_alerts,
            withdraw_alerts=model.withdraw_alerts,
            transfer_alerts=model.transfer_alerts,
            interest_alerts=model.interest_alerts,
            loan_alerts=model.loan_alerts,
            admin_alerts=model.admin_alerts,
            updated_at=model.updated_at,
        )

    def create_or_update(self, pref: NotificationPreference) -> NotificationPreference:
        model = (
            self.session.query(NotificationPreferenceModel)
            .filter_by(account_number=pref.account_number)
            .first()
        )
        if model is None:
            model = NotificationPreferenceModel(
                account_number=pref.account_number,
                in_app_enabled=pref.in_app_enabled,
                email_enabled=pref.email_enabled,
                sms_enabled=pref.sms_enabled,
                deposit_alerts=pref.deposit_alerts,
                withdraw_alerts=pref.withdraw_alerts,
                transfer_alerts=pref.transfer_alerts,
                interest_alerts=pref.interest_alerts,
                loan_alerts=pref.loan_alerts,
                admin_alerts=pref.admin_alerts,
            )
            self.session.add(model)
        else:
            model.in_app_enabled = pref.in_app_enabled
            model.email_enabled = pref.email_enabled
            model.sms_enabled = pref.sms_enabled
            model.deposit_alerts = pref.deposit_alerts
            model.withdraw_alerts = pref.withdraw_alerts
            model.transfer_alerts = pref.transfer_alerts
            model.interest_alerts = pref.interest_alerts
            model.loan_alerts = pref.loan_alerts
            model.admin_alerts = pref.admin_alerts
        return pref

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()


class SqlAlchemyRefreshTokenRepository:
    """Refresh token repository backed by SQLAlchemy + SQLite."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, token_id: str) -> RefreshToken | None:
        model = self.session.query(RefreshTokenModel).filter_by(token_id=token_id).first()
        return map_refresh_token(model) if model else None

    def get_by_account(self, account_number: str) -> list[RefreshToken]:
        models = (
            self.session.query(RefreshTokenModel)
            .filter_by(account_number=account_number)
            .order_by(RefreshTokenModel.created_at.desc())
            .all()
        )
        return [map_refresh_token(m) for m in models]

    def create(self, token: RefreshToken) -> RefreshToken:
        model = RefreshTokenModel(
            token_id=token.token_id,
            account_number=token.account_number,
            role=token.role,
            expires_at=token.expires_at,
            revoked_at=token.revoked_at,
        )
        self.session.add(model)
        return token

    def revoke(self, token_id: str) -> bool:
        model = self.session.query(RefreshTokenModel).filter_by(token_id=token_id).first()
        if model is None:
            return False
        model.revoked_at = datetime.now(UTC)
        return True

    def revoke_all_for_account(self, account_number: str) -> int:
        count = (
            self.session.query(RefreshTokenModel)
            .filter_by(
                account_number=account_number,
                revoked_at=None,
            )
            .update({"revoked_at": datetime.now(UTC)})
        )
        return count

    def clean_expired(self) -> int:
        now = datetime.now(UTC)
        deleted = (
            self.session.query(RefreshTokenModel)
            .filter(RefreshTokenModel.expires_at < now)
            .delete()
        )
        return deleted

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
