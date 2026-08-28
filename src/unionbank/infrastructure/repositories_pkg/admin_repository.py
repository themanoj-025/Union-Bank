"""Admin and Token Version repositories backed by SQLAlchemy + SQLite."""

from __future__ import annotations

from sqlalchemy.orm import Session

from unionbank.domain.entities import AdminUser
from unionbank.infrastructure.mappers import map_admin

from ..persistence import AdminModel, TokenVersionModel


class SqlAlchemyAdminRepository:
    """Admin repository backed by SQLAlchemy + SQLite."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_username(self, username: str) -> AdminUser | None:
        model = self.session.query(AdminModel).filter_by(username=username).first()
        return map_admin(model) if model else None

    def create(self, admin: AdminUser) -> AdminUser:
        # Encrypt TOTP secret before storing if present
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

    def update_password(self, username: str, new_hashed: str) -> bool:
        model = self.session.query(AdminModel).filter_by(username=username).first()
        if model is None:
            return False
        model.password = new_hashed
        return True

    def update_totp(self, username: str, totp_secret: str | None, totp_enabled: bool) -> bool:
        model = self.session.query(AdminModel).filter_by(username=username).first()
        if model is None:
            return False
        # Encrypt TOTP secret before storing (defense-in-depth: plaintext in DB is a liability)
        from unionbank.utils.token_security import encrypt_totp_secret

        model.totp_secret = encrypt_totp_secret(totp_secret)
        model.totp_enabled = totp_enabled
        return True

    def admin_count(self) -> int:
        return self.session.query(AdminModel).count()

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()


class SqlAlchemyTokenVersionRepository:
    """Token version repository backed by SQLAlchemy + SQLite."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_version(self, account_number: str) -> int:
        model = (
            self.session.query(TokenVersionModel).filter_by(account_number=account_number).first()
        )
        return model.version if model else 0

    def increment(self, account_number: str) -> int:
        model = (
            self.session.query(TokenVersionModel).filter_by(account_number=account_number).first()
        )
        if model is None:
            model = TokenVersionModel(account_number=account_number, version=1)
            self.session.add(model)
        else:
            model.version += 1
        return model.version

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
