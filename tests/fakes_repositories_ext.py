"""Extended in-memory repository fakes — token, notification, refresh, audit."""

from __future__ import annotations

from datetime import datetime, timedelta, UTC

from unionbank.domain.entities import (
    AuditLog,
    Notification,
    NotificationPreference,
    RefreshToken,
)

from tests.fakes import _utcnow


class FakeTokenVersionRepository:
    """In-memory token version repository."""

    def __init__(self):
        self._versions: dict[str, int] = {}

    def get_version(self, account_number: str) -> int:
        return self._versions.get(account_number, 0)

    def increment(self, account_number: str) -> int:
        version = self._versions.get(account_number, 0) + 1
        self._versions[account_number] = version
        return version

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


class FakeNotificationRepository:
    """In-memory notification repository."""

    def __init__(self):
        self._notifications: list[Notification] = []

    def get(self, notif_id: str) -> Notification | None:
        for n in self._notifications:
            if n.notif_id == notif_id:
                return n
        return None

    def get_by_account(self, acc_no: str, limit: int = 50) -> list[Notification]:
        results = [n for n in self._notifications if n.account_number == acc_no]
        results.sort(key=lambda n: n.created_at, reverse=True)
        return results[:limit]

    def get_unread_count(self, acc_no: str) -> int:
        return sum(1 for n in self._notifications if n.account_number == acc_no and not n.is_read)

    def get_unread(self, acc_no: str, limit: int = 20) -> list[Notification]:
        results = [n for n in self._notifications if n.account_number == acc_no and not n.is_read]
        results.sort(key=lambda n: n.created_at, reverse=True)
        return results[:limit]

    def create(self, notification: Notification) -> Notification:
        self._notifications.append(notification)
        return notification

    def mark_as_read(self, notif_id: str) -> bool:
        for n in self._notifications:
            if n.notif_id == notif_id:
                n.is_read = True
                return True
        return False

    def mark_all_as_read(self, acc_no: str) -> int:
        count = 0
        for n in self._notifications:
            if n.account_number == acc_no and not n.is_read:
                n.is_read = True
                count += 1
        return count

    def delete_old(self, days: int = 30) -> int:
        cutoff = datetime.now(UTC) - timedelta(days=days)
        old = [n for n in self._notifications if n.created_at < cutoff]
        for n in old:
            self._notifications.remove(n)
        return len(old)

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


class FakeNotificationPreferenceRepository:
    """In-memory notification preference repository."""

    def __init__(self):
        self._prefs: dict[str, NotificationPreference] = {}

    def get(self, acc_no: str) -> NotificationPreference | None:
        return self._prefs.get(acc_no)

    def create_or_update(self, pref: NotificationPreference) -> NotificationPreference:
        self._prefs[pref.account_number] = pref
        return pref

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


class FakeRefreshTokenRepository:
    """In-memory refresh token repository."""

    def __init__(self):
        self._tokens: dict[str, RefreshToken] = {}

    def get(self, token_id: str):
        return self._tokens.get(token_id)

    def get_by_account(self, account_number: str) -> list[object]:
        return [t for t in self._tokens.values() if t.account_number == account_number]

    def create(self, token: RefreshToken):
        self._tokens[token.token_id] = token
        return token

    def revoke(self, token_id: str) -> bool:
        if token_id not in self._tokens:
            return False
        self._tokens[token_id].revoked_at = datetime.now(UTC)
        return True

    def revoke_all_for_account(self, account_number: str) -> int:
        count = 0
        for t in self._tokens.values():
            if t.account_number == account_number and t.revoked_at is None:
                t.revoked_at = datetime.now(UTC)
                count += 1
        return count

    def clean_expired(self) -> int:
        now = datetime.now(UTC)
        expired = [id for id, t in self._tokens.items() if t.expires_at < now]
        for id in expired:
            del self._tokens[id]
        return len(expired)

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


class FakeAuditLogRepository:
    """In-memory audit log repository — append-only."""

    def __init__(self):
        self._entries: list[dict] = []

    def log(
        self,
        actor: str,
        action: str,
        target: str | None = None,
        details: str | None = None,
        ip_address: str | None = None,
        reason: str | None = None,
    ) -> None:
        self._entries.append(
            {
                "actor": actor,
                "action": action,
                "target": target,
                "details": details,
                "ip_address": ip_address,
                "reason": reason,
                "timestamp": str(_utcnow())[:19],
            }
        )

    def get_recent(self, limit: int = 50) -> list:
        return list(reversed(self._entries))[:limit]

    def get_by_actor(self, actor: str, limit: int = 50) -> list:
        entries = [e for e in self._entries if e["actor"] == actor]
        return list(reversed(entries))[:limit]

    def get_by_action(self, action: str, limit: int = 50) -> list:
        entries = [e for e in self._entries if e["action"] == action]
        return list(reversed(entries))[:limit]

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass
