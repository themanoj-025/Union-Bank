"""
async_notification_repo.py – Async SQLAlchemy Notification and
NotificationPreference repositories.

Mirrors the synchronous counterpart but uses ``AsyncSession`` for all
database operations. Used when the application is configured with a
PostgreSQL DATABASE_URL (async via asyncpg).
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from unionbank.domain.clock import utcnow as _utcnow
from unionbank.domain.entities import Notification, NotificationPreference
from unionbank.infrastructure.mappers import map_notification

from .persistence import NotificationModel, NotificationPreferenceModel


#  Notification Repository (async)


class AsyncSqlAlchemyNotificationRepository:
    """Notification repository backed by async SQLAlchemy (asyncpg + PostgreSQL)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, notif_id: str) -> Notification | None:
        result = await self.session.execute(
            select(NotificationModel).where(NotificationModel.notif_id == notif_id)
        )
        model = result.scalar_one_or_none()
        return map_notification(model) if model else None

    async def get_by_account(self, acc_no: str, limit: int = 50) -> list[Notification]:
        result = await self.session.execute(
            select(NotificationModel)
            .where(NotificationModel.account_number == acc_no)
            .order_by(NotificationModel.created_at.desc())
            .limit(limit)
        )
        models = result.scalars().all()
        return [map_notification(m) for m in models]

    async def get_unread_count(self, acc_no: str) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(NotificationModel)
            .where(
                NotificationModel.account_number == acc_no,
                NotificationModel.is_read.is_(False),
            )
        )
        return result.scalar() or 0

    async def get_unread(self, acc_no: str, limit: int = 20) -> list[Notification]:
        result = await self.session.execute(
            select(NotificationModel)
            .where(
                NotificationModel.account_number == acc_no,
                NotificationModel.is_read.is_(False),
            )
            .order_by(NotificationModel.created_at.desc())
            .limit(limit)
        )
        models = result.scalars().all()
        return [map_notification(m) for m in models]

    async def create(self, notification: Notification) -> Notification:
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

    async def mark_as_read(self, notif_id: str) -> bool:
        result = await self.session.execute(
            select(NotificationModel).where(NotificationModel.notif_id == notif_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return False
        model.is_read = True
        return True

    async def mark_all_as_read(self, acc_no: str) -> int:
        result = await self.session.execute(
            select(NotificationModel).where(
                NotificationModel.account_number == acc_no,
                NotificationModel.is_read.is_(False),
            )
        )
        models = result.scalars().all()
        count = len(models)
        for model in models:
            model.is_read = True
        return count

    async def delete_old(self, days: int = 30) -> int:
        cutoff = _utcnow() - timedelta(days=days)
        result = await self.session.execute(
            select(NotificationModel).where(NotificationModel.created_at < cutoff)
        )
        models = result.scalars().all()
        count = len(models)
        for model in models:
            await self.session.delete(model)
        return count

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()


#  Notification Preference Repository (async)


class AsyncSqlAlchemyNotificationPreferenceRepository:
    """Notification preferences repository backed by async SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, acc_no: str) -> NotificationPreference | None:
        result = await self.session.execute(
            select(NotificationPreferenceModel).where(
                NotificationPreferenceModel.account_number == acc_no
            )
        )
        model = result.scalar_one_or_none()
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

    async def create_or_update(self, pref: NotificationPreference) -> NotificationPreference:
        result = await self.session.execute(
            select(NotificationPreferenceModel).where(
                NotificationPreferenceModel.account_number == pref.account_number
            )
        )
        model = result.scalar_one_or_none()
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

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
