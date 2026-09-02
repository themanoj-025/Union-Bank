"""Tests for application.notifications — notification service with fakes."""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.fakes import (
    FakeAccountRepository,
    FakeNotificationPreferenceRepository,
    FakeNotificationRepository,
)
from unionbank.application.notifications import (
    NOTIFICATION_TYPES,
    LogNotificationSender,
    NotificationService,
)
from unionbank.domain.entities import Account, NotificationPreference

pytestmark = pytest.mark.slow


@pytest.fixture
def notif_repo() -> FakeNotificationRepository:
    return FakeNotificationRepository()


@pytest.fixture
def pref_repo() -> FakeNotificationPreferenceRepository:
    return FakeNotificationPreferenceRepository()


@pytest.fixture
def account_repo() -> FakeAccountRepository:
    return FakeAccountRepository()


@pytest.fixture
def sender() -> LogNotificationSender:
    return LogNotificationSender()


@pytest.fixture
def sample_account() -> Account:
    return Account(
        account_number="1000000001",
        name="Test User",
        email="test@example.com",
        mobile="9876543210",
    )


@pytest.fixture
def service(
    notif_repo: FakeNotificationRepository,
    pref_repo: FakeNotificationPreferenceRepository,
    account_repo: FakeAccountRepository,
    sender: LogNotificationSender,
) -> NotificationService:
    return NotificationService(notif_repo, pref_repo, account_repo, sender)


class TestNotificationTypes:
    """Verify notification type constants."""

    def test_all_types_defined(self) -> None:
        assert len(NOTIFICATION_TYPES) >= 14
        assert "deposit" in NOTIFICATION_TYPES
        assert "withdraw" in NOTIFICATION_TYPES
        assert "transfer_sent" in NOTIFICATION_TYPES
        assert "transfer_received" in NOTIFICATION_TYPES
        assert "loan_approved" in NOTIFICATION_TYPES
        assert "welcome" in NOTIFICATION_TYPES


class TestLogNotificationSender:
    """LogNotificationSender logs instead of sending."""

    def test_send_email_returns_true(self) -> None:
        sender = LogNotificationSender()
        assert sender.send_email("test@example.com", "Subject", "Body") is True

    def test_send_sms_returns_true(self) -> None:
        sender = LogNotificationSender()
        assert sender.send_sms("9876543210", "Message") is True


class TestNotificationService:
    """NotificationService create and manage notifications."""

    def test_notify_creates_notification(
        self, service: NotificationService, account_repo: FakeAccountRepository, sample_account: Account
    ) -> None:
        account_repo.create(sample_account)
        notif = service.notify(
            "1000000001", "deposit", "Deposit Received", "You got ₹1000", "TXN001"
        )
        assert notif.account_number == "1000000001"
        assert notif.type == "deposit"
        assert notif.title == "Deposit Received"
        assert notif.is_read is False

    def test_notify_and_commit(
        self, service: NotificationService, account_repo: FakeAccountRepository, sample_account: Account
    ) -> None:
        account_repo.create(sample_account)
        notif = service.notify_and_commit(
            "1000000001", "welcome", "Welcome!", "Thanks for joining"
        )
        assert notif.type == "welcome"

    def test_notify_deposit(
        self, service: NotificationService, account_repo: FakeAccountRepository, sample_account: Account
    ) -> None:
        account_repo.create(sample_account)
        notif = service.notify_deposit("1000000001", Decimal("5000"), Decimal("15000"), "TXN001")
        assert notif.type == "deposit"
        assert "₹5,000" in notif.message

    def test_notify_withdraw(
        self, service: NotificationService, account_repo: FakeAccountRepository, sample_account: Account
    ) -> None:
        account_repo.create(sample_account)
        notif = service.notify_withdraw("1000000001", Decimal("2000"), Decimal("8000"), "TXN002")
        assert notif.type == "withdraw"
        assert "₹2,000" in notif.message

    def test_notify_transfer_sent(
        self, service: NotificationService, account_repo: FakeAccountRepository, sample_account: Account
    ) -> None:
        account_repo.create(sample_account)
        notif = service.notify_transfer_sent(
            "1000000001", Decimal("3000"), "1000000002", Decimal("7000"), "TXN003"
        )
        assert notif.type == "transfer_sent"
        assert "1000000002" in notif.message

    def test_notify_transfer_received(
        self, service: NotificationService, account_repo: FakeAccountRepository, sample_account: Account
    ) -> None:
        account_repo.create(sample_account)
        notif = service.notify_transfer_received(
            "1000000001", Decimal("1500"), "1000000003", Decimal("11500"), "TXN004"
        )
        assert notif.type == "transfer_received"
        assert "1000000003" in notif.message

    def test_notify_interest(
        self, service: NotificationService, account_repo: FakeAccountRepository, sample_account: Account
    ) -> None:
        account_repo.create(sample_account)
        notif = service.notify_interest("1000000001", Decimal("291.67"), Decimal("100291.67"), "TXN005")
        assert notif.type == "interest"

    def test_notify_loan_approved(
        self, service: NotificationService, account_repo: FakeAccountRepository, sample_account: Account
    ) -> None:
        account_repo.create(sample_account)
        notif = service.notify_loan_approved(
            "1000000001", Decimal("500000"), "Personal", "LOAN001"
        )
        assert notif.type == "loan_approved"
        assert "LOAN001" in notif.message

    def test_notify_loan_rejected(
        self, service: NotificationService, account_repo: FakeAccountRepository, sample_account: Account
    ) -> None:
        account_repo.create(sample_account)
        notif = service.notify_loan_rejected(
            "1000000001", "Home", "LOAN002", "Insufficient income"
        )
        assert notif.type == "loan_rejected"
        assert "Insufficient income" in notif.message

    def test_notify_emi_paid(
        self, service: NotificationService, account_repo: FakeAccountRepository, sample_account: Account
    ) -> None:
        account_repo.create(sample_account)
        notif = service.notify_emi_paid(
            "1000000001", Decimal("10000"), "Personal", "LOAN001", Decimal("490000")
        )
        assert notif.type == "loan_emi_paid"
        assert "₹10,000" in notif.message

    def test_notify_loan_closed(
        self, service: NotificationService, account_repo: FakeAccountRepository, sample_account: Account
    ) -> None:
        account_repo.create(sample_account)
        notif = service.notify_loan_closed("1000000001", "Home", "LOAN003")
        assert notif.type == "loan_closed"
        assert "🎉" in notif.title

    def test_notify_account_frozen(
        self, service: NotificationService, account_repo: FakeAccountRepository, sample_account: Account
    ) -> None:
        account_repo.create(sample_account)
        notif = service.notify_account_frozen("1000000001", "Suspicious activity")
        assert notif.type == "account_frozen"
        assert "Suspicious activity" in notif.message

    def test_notify_account_unfrozen(
        self, service: NotificationService, account_repo: FakeAccountRepository, sample_account: Account
    ) -> None:
        account_repo.create(sample_account)
        notif = service.notify_account_unfrozen("1000000001")
        assert notif.type == "account_unfrozen"

    def test_notify_welcome(
        self, service: NotificationService, account_repo: FakeAccountRepository, sample_account: Account
    ) -> None:
        account_repo.create(sample_account)
        notif = service.notify_welcome("1000000001")
        assert notif.type == "welcome"
        assert "🏦" in notif.title


class TestPreferences:
    """Notification preference management."""

    def test_get_preferences_creates_defaults(
        self, service: NotificationService, pref_repo: FakeNotificationPreferenceRepository
    ) -> None:
        pref = service.get_preferences("1000000001")
        assert pref.account_number == "1000000001"
        assert pref.email_enabled is True
        assert pref.sms_enabled is True

    def test_get_preferences_returns_existing(
        self, service: NotificationService, pref_repo: FakeNotificationPreferenceRepository
    ) -> None:
        existing = NotificationPreference(account_number="1000000001", email_enabled=False)
        pref_repo.create_or_update(existing)
        pref = service.get_preferences("1000000001")
        assert pref.email_enabled is False

    def test_update_preferences(
        self, service: NotificationService, account_repo: FakeAccountRepository, sample_account: Account
    ) -> None:
        account_repo.create(sample_account)
        result = service.update_preferences("1000000001", email_enabled=False)
        assert result.success is True
        pref = service.get_preferences("1000000001")
        assert pref.email_enabled is False
