"""
application/transfer_service.py  –  Transaction use-cases.

Contains deposit, withdraw, transfer, statement, interest, and pagination.
Extracted from services.py for focused maintenance.
"""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal

import pybreaker

from unionbank.config import settings
from unionbank.domain.clock import utcnow as _utcnow
from unionbank.domain.entities import (
    IdempotencyRecord,
    ServiceResult,
    Transaction,
    TransactionType,
    TransferResult,
)
from unionbank.domain.interest import calculate_monthly_interest
from unionbank.utils.formatting import fmt_currency, generate_transaction_id

from .interfaces import (
    AccountRepositoryProtocol,
    IdempotencyRepositoryProtocol,
    KeysetPage,
    NotificationServiceProtocol,
    TransactionRepositoryProtocol,
)
from .services_shared import (
    TRANSACTION_CATEGORIES,
    NOTIFICATION_BREAKER,
    _account_lock,
)


class TransactionService:
    """
    Transaction use-cases (deposit, withdraw, transfer, statement, interest).

    Idempotency: deposit/withdraw/transfer operations check the idempotency
    repository before executing. If a duplicate key is found, the cached
    result is returned instead of re-executing.
    """

    def __init__(
        self,
        account_repo: AccountRepositoryProtocol,
        txn_repo: TransactionRepositoryProtocol,
        notif_service: NotificationServiceProtocol | None = None,
        idempotency_repo: IdempotencyRepositoryProtocol | None = None,
    ):
        self.account_repo = account_repo
        self.txn_repo = txn_repo
        self.notif_service = notif_service
        self.idempotency_repo = idempotency_repo

    def _ensure_non_negative_balance(
        self, balance: Decimal, operation: str = "transaction"
    ) -> None:
        """App-level guard: raise ValueError if balance would go negative."""
        if balance < Decimal("0.00"):
            raise ValueError(f"Insufficient balance for {operation}.")

    def _check_idempotency(
        self, idempotency_key: str | None, acc_no: str, operation: str, amount: Decimal
    ) -> ServiceResult | None:
        """Check if a request with this idempotency_key has already been processed."""
        if not idempotency_key or not self.idempotency_repo:
            return None
        existing = self.idempotency_repo.get(idempotency_key)
        if existing is not None:
            try:
                data = json.loads(existing.result_json)
                return ServiceResult(
                    success=data.get("success", True),
                    message=data.get("message", "Operation already completed."),
                    data=data.get("data"),
                )
            except (json.JSONDecodeError, KeyError):
                from unionbank.utils.logger import logger

                logger.warning("Failed to parse cached idempotency result", exc_info=True)
                return ServiceResult(
                    success=True,
                    message="Operation already completed.",
                )
        return None

    def _store_idempotency(
        self,
        idempotency_key: str | None,
        acc_no: str,
        operation: str,
        amount: Decimal,
        result: ServiceResult,
    ) -> None:
        """Store the result of an idempotent operation for future dedup."""
        if not idempotency_key or not self.idempotency_repo:
            return
        record = IdempotencyRecord(
            idempotency_key=idempotency_key,
            account_number=acc_no,
            operation=operation,
            result_json=json.dumps(
                {
                    "success": result.success,
                    "message": result.message,
                    "data": result.data,
                }
            ),
            amount=amount,
        )
        try:
            self.idempotency_repo.create(record)
            self.idempotency_repo.commit()
        except (OSError, ValueError, TypeError):
            from unionbank.utils.logger import logger

            logger.warning("Failed to persist idempotency record", exc_info=True)
            self.idempotency_repo.rollback()

    def deposit(
        self,
        acc_no: str,
        amount: Decimal,
        category: str = "General",
        idempotency_key: str | None = None,
    ) -> ServiceResult:
        if amount <= 0:
            return ServiceResult(success=False, message="Amount must be positive.")

        cached = self._check_idempotency(idempotency_key, acc_no, "deposit", amount)
        if cached is not None:
            return cached

        with _account_lock(acc_no):
            account = self.account_repo.get(acc_no)
            if account is None:
                return ServiceResult(success=False, message="Account not found.")
            if not account.can_transact:
                status = "frozen" if account.is_frozen else "closed"
                return ServiceResult(success=False, message=f"Account is {status}.")

            account.balance += amount
            self.account_repo.update(account)

            txn = Transaction(
                txn_id=generate_transaction_id(),
                account_number=acc_no,
                type=TransactionType.DEPOSIT,
                amount=amount,
                balance=account.balance,
                description="Deposit",
                category=category if category in TRANSACTION_CATEGORIES else "General",
            )
            self.txn_repo.create(txn)
            self.account_repo.commit()

        result = ServiceResult(
            success=True,
            message=f"{fmt_currency(float(amount))} deposited successfully. "
            f"New balance: {fmt_currency(float(account.balance))}",
            data={"balance": float(account.balance)},
        )

        self._store_idempotency(idempotency_key, acc_no, "deposit", amount, result)

        if self.notif_service and account:
            try:
                NOTIFICATION_BREAKER.call(self.notif_service.notify_deposit)(
                    acc_no, amount, account.balance, txn.txn_id
                )
            except pybreaker.CircuitBreakerError:
                from unionbank.utils.logger import logger

                logger.warning("Notification circuit breaker open, skipping deposit notification")
            except (OSError, ValueError, TypeError, AttributeError):
                from unionbank.utils.logger import logger

                logger.warning("Failed to send deposit notification", exc_info=True)

        return result

    def withdraw(
        self,
        acc_no: str,
        amount: Decimal,
        category: str = "General",
        idempotency_key: str | None = None,
    ) -> ServiceResult:
        if amount <= 0:
            return ServiceResult(success=False, message="Amount must be positive.")

        cached = self._check_idempotency(idempotency_key, acc_no, "withdraw", amount)
        if cached is not None:
            return cached

        with _account_lock(acc_no):
            account = self.account_repo.get(acc_no)
            if account is None:
                return ServiceResult(success=False, message="Account not found.")
            if not account.can_transact:
                status = "frozen" if account.is_frozen else "closed"
                return ServiceResult(success=False, message=f"Account is {status}.")

            if amount > account.balance:
                return ServiceResult(
                    success=False,
                    message=f"Insufficient balance. Available: {fmt_currency(float(account.balance))}",
                )

            account.balance -= amount
            self._ensure_non_negative_balance(account.balance, "withdraw")
            self.account_repo.update(account)

            txn = Transaction(
                txn_id=generate_transaction_id(),
                account_number=acc_no,
                type=TransactionType.WITHDRAW,
                amount=amount,
                balance=account.balance,
                description="Withdrawal",
                category=category if category in TRANSACTION_CATEGORIES else "General",
            )
            self.txn_repo.create(txn)
            self.account_repo.commit()

        result = ServiceResult(
            success=True,
            message=f"{fmt_currency(float(amount))} withdrawn successfully. "
            f"New balance: {fmt_currency(float(account.balance))}",
            data={"balance": float(account.balance)},
        )

        self._store_idempotency(idempotency_key, acc_no, "withdraw", amount, result)

        if self.notif_service and account:
            try:
                NOTIFICATION_BREAKER.call(self.notif_service.notify_withdraw)(
                    acc_no, amount, account.balance, txn.txn_id
                )
            except pybreaker.CircuitBreakerError:
                from unionbank.utils.logger import logger

                logger.warning("Notification circuit breaker open, skipping withdraw notification")
            except (OSError, ValueError, TypeError, AttributeError):
                from unionbank.utils.logger import logger

                logger.warning("Failed to send withdraw notification", exc_info=True)

        return result

    def transfer(
        self,
        sender_acc_no: str,
        receiver_acc_no: str,
        amount: Decimal,
        category: str = "General",
        idempotency_key: str | None = None,
    ) -> TransferResult:
        if amount <= 0:
            return TransferResult(success=False, error_message="Amount must be positive.")
        if sender_acc_no == receiver_acc_no:
            return TransferResult(
                success=False, error_message="Cannot transfer to your own account."
            )

        # Check idempotency first (outside lock — read-only)
        if idempotency_key and self.idempotency_repo:
            existing = self.idempotency_repo.get(idempotency_key)
            if existing is not None:
                try:
                    data = json.loads(existing.result_json)
                    return TransferResult(
                        success=data.get("success", True),
                        sender_balance=Decimal(str(data.get("sender_balance", 0))),
                        receiver_balance=Decimal(str(data.get("receiver_balance", 0))),
                        error_message=data.get("error_message", ""),
                    )
                except (json.JSONDecodeError, KeyError):
                    pass

        cat = category if category in TRANSACTION_CATEGORIES else "General"

        try:
            with _account_lock(sender_acc_no, receiver_acc_no):
                sender = self.account_repo.get(sender_acc_no)
                receiver = self.account_repo.get(receiver_acc_no)

                if sender is None:
                    return TransferResult(success=False, error_message="Sender account not found.")
                if receiver is None:
                    return TransferResult(
                        success=False, error_message="Recipient account not found."
                    )

                if not sender.can_transact:
                    return TransferResult(
                        success=False, error_message="Your account is frozen or closed."
                    )
                if not receiver.can_transact:
                    return TransferResult(
                        success=False, error_message="Recipient account is frozen or closed."
                    )

                if amount > sender.balance:
                    return TransferResult(
                        success=False,
                        error_message=(
                            f"Insufficient balance. "
                            f"Available: {fmt_currency(float(sender.balance))}"
                        ),
                    )

                with self.account_repo.session.begin_nested():
                    sender.balance -= amount
                    self._ensure_non_negative_balance(sender.balance, "transfer")
                    receiver.balance += amount

                    self.account_repo.update(sender)
                    self.account_repo.update(receiver)

                    now = _utcnow()
                    sender_txn = Transaction(
                        txn_id=generate_transaction_id(),
                        account_number=sender_acc_no,
                        type=TransactionType.TRANSFER_OUT,
                        amount=amount,
                        balance=sender.balance,
                        description=f"Transfer to {receiver_acc_no}",
                        category=cat,
                        target_account=receiver_acc_no,
                        timestamp=now,
                    )
                    receiver_txn = Transaction(
                        txn_id=generate_transaction_id(),
                        account_number=receiver_acc_no,
                        type=TransactionType.TRANSFER_IN,
                        amount=amount,
                        balance=receiver.balance,
                        description=f"Transfer from {sender_acc_no}",
                        category=cat,
                        target_account=sender_acc_no,
                        timestamp=now,
                    )
                    self.txn_repo.create(sender_txn)
                    self.txn_repo.create(receiver_txn)

                self.account_repo.commit()

                sender_balance = sender.balance
                receiver_balance = receiver.balance
                sender_txn_id = sender_txn.txn_id
                receiver_txn_id = receiver_txn.txn_id

        except (OSError, ValueError, TypeError) as exc:
            from unionbank.utils.logger import logger

            logger.error("Transfer failed, rolling back: %s", exc)
            self.account_repo.rollback()
            return TransferResult(
                success=False,
                error_message="Transfer failed due to a database error. Please try again.",
            )

        # Send notifications (non-fatal if fails, outside lock)
        if self.notif_service:
            try:
                NOTIFICATION_BREAKER.call(self.notif_service.notify_transfer_sent)(
                    sender_acc_no,
                    amount,
                    receiver_acc_no,
                    sender_balance,
                    sender_txn_id,
                )
                NOTIFICATION_BREAKER.call(self.notif_service.notify_transfer_received)(
                    receiver_acc_no,
                    amount,
                    sender_acc_no,
                    receiver_balance,
                    receiver_txn_id,
                )
            except pybreaker.CircuitBreakerError:
                from unionbank.utils.logger import logger

                logger.warning("Notification circuit breaker open, skipping transfer notification")
            except (OSError, ValueError, TypeError, AttributeError):
                from unionbank.utils.logger import logger

                logger.warning("Failed to send transfer notification", exc_info=True)

        result = TransferResult(
            success=True,
            sender_balance=sender_balance,
            receiver_balance=receiver_balance,
        )

        # Store idempotency result (non-fatal if fails, outside lock)
        if idempotency_key and self.idempotency_repo:
            try:
                record = IdempotencyRecord(
                    idempotency_key=idempotency_key,
                    account_number=sender_acc_no,
                    operation="transfer",
                    result_json=json.dumps(
                        {
                            "success": result.success,
                            "sender_balance": float(result.sender_balance),
                            "receiver_balance": float(result.receiver_balance),
                            "error_message": result.error_message,
                        }
                    ),
                    amount=amount,
                )
                self.idempotency_repo.create(record)
                self.idempotency_repo.commit()
            except (OSError, ValueError, TypeError):
                from unionbank.utils.logger import logger

                logger.warning("Failed to persist idempotency record for transfer", exc_info=True)
                self.idempotency_repo.rollback()

        return result

    def get_statement(self, acc_no: str) -> list[Transaction]:
        return self.txn_repo.get_by_account(acc_no)

    def get_mini_statement(self, acc_no: str, limit: int = 5) -> list[Transaction]:
        return self.txn_repo.get_mini(acc_no, limit)

    def apply_interest(self, acc_no: str) -> ServiceResult:
        account = self.account_repo.get(acc_no)
        if account is None:
            return ServiceResult(success=False, message="Account not found.")
        if not account.can_transact:
            return ServiceResult(success=False, message="Account is frozen or closed.")

        interest = Decimal(
            str(calculate_monthly_interest(float(account.balance), settings.SAVINGS_INTEREST_RATE))
        )
        if interest <= 0:
            return ServiceResult(success=False, message="No interest to apply.")

        account.balance += interest
        self.account_repo.update(account)

        txn = Transaction(
            txn_id=generate_transaction_id(),
            account_number=acc_no,
            type=TransactionType.INTEREST,
            amount=interest,
            balance=account.balance,
            description="Monthly interest credit",
            category="Savings",
        )
        self.txn_repo.create(txn)
        self.account_repo.commit()

        if self.notif_service and account:
            try:
                NOTIFICATION_BREAKER.call(self.notif_service.notify_interest)(
                    acc_no, interest, account.balance, txn.txn_id
                )
            except pybreaker.CircuitBreakerError:
                from unionbank.utils.logger import logger

                logger.warning("Notification circuit breaker open, skipping interest notification")
            except (OSError, ValueError, TypeError, AttributeError):
                from unionbank.utils.logger import logger

                logger.warning("Failed to send interest notification", exc_info=True)

        return ServiceResult(
            success=True,
            message=f"Interest of {fmt_currency(float(interest))} credited! "
            f"New balance: {fmt_currency(float(account.balance))}",
            data={"interest": float(interest), "balance": float(account.balance)},
        )

    def get_category_totals(self) -> dict[str, Decimal]:
        return self.txn_repo.get_category_totals()

    def get_paginated_transactions(
        self,
        acc_no: str | None = None,
        page: int = 1,
        per_page: int = 20,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        txn_type: str | None = None,
    ) -> tuple[list[Transaction], int]:
        return self.txn_repo.get_paginated(
            acc_no=acc_no,
            page=page,
            per_page=per_page,
            from_date=from_date,
            to_date=to_date,
            txn_type=txn_type,
        )

    def get_paginated_keyset(
        self,
        acc_no: str | None = None,
        limit: int = 20,
        cursor: datetime | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        txn_type: str | None = None,
    ) -> KeysetPage[Transaction]:
        """Keyset (cursor-based) pagination — more efficient than OFFSET on large datasets."""
        return self.txn_repo.get_paginated_keyset(
            acc_no=acc_no,
            limit=limit,
            cursor=cursor,
            from_date=from_date,
            to_date=to_date,
            txn_type=txn_type,
        )
