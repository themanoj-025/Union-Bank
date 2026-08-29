"""
async_auth_repo.py – Async SQLAlchemy auth-related repositories.

Covers Admin, LoginAttempt, TokenVersion, and RefreshToken repos.
Mirrors the synchronous counterpart but uses ``AsyncSession`` for all
database operations. Used when the application is configured with a
PostgreSQL DATABASE_URL (async via asyncpg).
"""

from __future__ import annotations

from datetime import datetime, timedelta, UTC

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from unionbank.domain.clock import utcnow as _utcnow
from unionbank.domain.entities import AdminUser, LoginAttempt, RefreshToken
from unionbank.infrastructure.mappers import map_admin, map_refresh_token

from .persistence import (
    AdminModel,
    LoginAttemptModel,
    RefreshTokenModel,
    TokenVersionModel,
)


#  Admin Repository (async)


class AsyncSqlAlchemyAdminRepository:
    """Admin repository backed by async SQLAlchemy (asyncpg + PostgreSQL)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_username(self, username: str) -> AdminUser | None:
        result = await self.session.execute(
            select(AdminModel).where(AdminModel.username == username)
        )
        model = result.scalar_one_or_none()
        return map_admin(model) if model else None

    async def create(self, admin: AdminUser) -> AdminUser:
        from unionbank.utils.token_security import encrypt_totp_secret

        model = AdminModel(
            username=admin.username,
            password=admin.password,
            role=admin.role or "admin",
            totp_secret=encrypt_totp_secret(admin.totp_secret),
            totp_enabled=admin.totp_enabled,
        )
        self.session.add(model)
        return admin

    async def update_password(self, username: str, new_hashed: str) -> bool:
        result = await self.session.execute(
            select(AdminModel).where(AdminModel.username == username)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return False
        model.password = new_hashed
        return True

    async def update_totp(
        self, username: str, totp_secret: str | None, totp_enabled: bool
    ) -> bool:
        from unionbank.utils.token_security import encrypt_totp_secret

        result = await self.session.execute(
            select(AdminModel).where(AdminModel.username == username)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return False
        model.totp_secret = encrypt_totp_secret(totp_secret)
        model.totp_enabled = totp_enabled
        return True

    async def admin_count(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(AdminModel))
        return result.scalar() or 0

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()


#  Login Attempt Repository (async)


class AsyncSqlAlchemyLoginAttemptRepository:
    """Login attempt repository backed by async SQLAlchemy (asyncpg + PostgreSQL)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, key: str) -> LoginAttempt | None:
        result = await self.session.execute(
            select(LoginAttemptModel).where(LoginAttemptModel.key == key)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return LoginAttempt(
            key=model.key,
            count=model.count or 0,
            first_failed=model.first_failed,
            lockout_until=model.lockout_until,
            updated_at=model.updated_at,
        )

    async def record_failure(
        self, key: str, max_attempts: int = 5, lockout_minutes: int = 15
    ) -> int:
        record = await self.get(key)
        now = _utcnow()

        if record is None:
            model = LoginAttemptModel(key=key, count=1, first_failed=now)
            self.session.add(model)
        else:
            result = await self.session.execute(
                select(LoginAttemptModel).where(LoginAttemptModel.key == key)
            )
            model = result.scalar_one_or_none()

            if model and model.lockout_until and now >= model.lockout_until:
                model.count = 1
                model.first_failed = now
                model.lockout_until = None
            else:
                if model:
                    model.count = (model.count or 0) + 1

            if model and model.count >= max_attempts:
                model.lockout_until = now + timedelta(minutes=lockout_minutes)

        current_count = getattr(model, "count", 0) if model else 1
        return max(0, max_attempts - (current_count or 0))

    async def is_locked(self, key: str, max_attempts: int = 5) -> tuple[bool, int]:
        result = await self.session.execute(
            select(LoginAttemptModel).where(LoginAttemptModel.key == key)
        )
        model = result.scalar_one_or_none()
        if model is None or (model.count or 0) < max_attempts:
            return False, 0

        now = _utcnow()
        lockout_until = model.lockout_until

        if lockout_until is not None and lockout_until.tzinfo is None:
            lockout_until = lockout_until.replace(tzinfo=UTC)

        if lockout_until and now < lockout_until:
            remaining = int((lockout_until - now).total_seconds() // 60)
            return True, max(1, remaining)
        if model:
            await self.session.delete(model)
        return False, 0

    async def reset(self, key: str) -> None:
        result = await self.session.execute(
            select(LoginAttemptModel).where(LoginAttemptModel.key == key)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()


#  Token Version Repository (async)


class AsyncSqlAlchemyTokenVersionRepository:
    """Token version repository backed by async SQLAlchemy (asyncpg + PostgreSQL)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_version(self, account_number: str) -> int:
        result = await self.session.execute(
            select(TokenVersionModel).where(TokenVersionModel.account_number == account_number)
        )
        model = result.scalar_one_or_none()
        return model.version if model else 0

    async def increment(self, account_number: str) -> int:
        result = await self.session.execute(
            select(TokenVersionModel).where(TokenVersionModel.account_number == account_number)
        )
        model = result.scalar_one_or_none()
        if model is None:
            model = TokenVersionModel(account_number=account_number, version=1)
            self.session.add(model)
        else:
            model.version += 1
        return model.version

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()


#  Refresh Token Repository (async)


class AsyncSqlAlchemyRefreshTokenRepository:
    """Refresh token repository backed by async SQLAlchemy (asyncpg + PostgreSQL)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, token_id: str) -> RefreshToken | None:
        result = await self.session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.token_id == token_id)
        )
        model = result.scalar_one_or_none()
        return map_refresh_token(model) if model else None

    async def get_by_account(self, account_number: str) -> list[RefreshToken]:
        result = await self.session.execute(
            select(RefreshTokenModel)
            .where(RefreshTokenModel.account_number == account_number)
            .order_by(RefreshTokenModel.created_at.desc())
        )
        models = result.scalars().all()
        return [map_refresh_token(m) for m in models]

    async def create(self, token: RefreshToken) -> RefreshToken:
        model = RefreshTokenModel(
            token_id=token.token_id,
            account_number=token.account_number,
            role=token.role,
            expires_at=token.expires_at,
            revoked_at=token.revoked_at,
        )
        self.session.add(model)
        return token

    async def revoke(self, token_id: str) -> bool:
        result = await self.session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.token_id == token_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return False
        model.revoked_at = datetime.now(UTC)
        return True

    async def revoke_all_for_account(self, account_number: str) -> int:
        result = await self.session.execute(
            select(RefreshTokenModel).where(
                RefreshTokenModel.account_number == account_number,
                RefreshTokenModel.revoked_at.is_(None),
            )
        )
        models = result.scalars().all()
        now = datetime.now(UTC)
        for model in models:
            model.revoked_at = now
        return len(models)

    async def clean_expired(self) -> int:
        now = datetime.now(UTC)
        result = await self.session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.expires_at < now)
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
