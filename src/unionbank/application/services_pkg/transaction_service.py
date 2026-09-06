"""
application/async_services.py  â€“  Async use-case service classes.

These mirror the synchronous services in services.py but use async/await for
all database operations. They are used when the application is configured
with a PostgreSQL DATABASE_URL (async via asyncpg).

For SQLite (which doesn't support async), the synchronous services in
services.py are used instead.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from decimal import Decimal

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
from unionbank.utils.formatting import (
    fmt_currency,
    generate_transaction_id,
)

try:
    from sqlalchemy.exc import SQLAlchemyError, IntegrityError
except ImportError:
    SQLAlchemyError = Exception  # fallback if sqlalchemy not installed
    IntegrityError = Exception

from .interfaces import (
    KeysetPage,
)

TRANSACTION_CATEGORIES = settings.TRANSACTION_CATEGORIES
MAX_LOGIN_ATTEMPTS = settings.MAX_LOGIN_ATTEMPTS
LOGIN_LOCKOUT_MINUTES = settings.LOGIN_LOCKOUT_MINUTES


#  Async per-account concurrency lock

_account_locks: dict[str, asyncio.Lock] = {}


def _get_account_lock(*acc_nos: str) -> asyncio.Lock:
    """
    Get an asyncio.Lock for the given accounts, creating if needed.

    For single-account operations, returns the lock for that account.
    For multi-account operations (transfer), returns a lock based on the
    sorted account numbers to prevent deadlocks.
    """
    # Use a combined key for multi-account operations
    sorted_nos = sorted(acc_nos)
    key = ":".join(sorted_nos)
    if key not in _account_locks:
        _account_locks[key] = asyncio.Lock()
    return _account_locks[key]


#  Async Transaction Service



class AsyncTransactionService:
    """
    Async transaction use-cases (deposit, withdraw, transfer, statement, interest).

    All database operations are awaited. Uses asyncio.Lock for per-account
    serialization to prevent lost updates under concurrent access.
    """

    def __init__(
        self,
        account_repo,  # AsyncSqlAlchemyAccountRepository
        txn_repo,  # AsyncSqlAlchemyTransactionRepository
        notif_service=None,
        idempotency_repo=None,
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

    # ── Idempotency: claim → execute → complete ───────────────────────
    # The idempotency_key is the DB primary key, so the claim is atomic:
    # exactly one concurrent request can INSERT the pending record. Anyone
    # who finds a pending/completed record replays it instead of executing,
    # which closes the check-then-execute TOCTOU that allowed double-spend.

    _IDEMPOTENCY_PENDING_JSON = '{"status": "pending"}'
    _IDEMPOTENCY_STALE_SECONDS = 600  # 10 minutes

    @staticmethod
    def _classify_idempotency_record(
        existing: IdempotencyRecord,
    ) -> tuple[str, dict | None]:
        """Classify an existing record: replay | pending | incomplete | corrupt."""
        try:
            data = json.loads(existing.result_json)
        except (json.JSONDecodeError, TypeError):
            return "corrupt", None
        if data.get("status") == "pending":
            created_at = existing.created_at
            # SQLite stores timestamps without tzinfo even though the column
            # declares timezone=True — normalize so the staleness math holds.
            if created_at is not None and created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)
            if created_at is not None and (
                _utcnow() - created_at
            ).total_seconds() > AsyncTransactionService._IDEMPOTENCY_STALE_SECONDS:
                # A pending claim older than the staleness bound means the
                # holder crashed mid-flight — the outcome is unknowable.
                return "incomplete", data
            return "pending", data
        return "replay", data

    async def _claim_idempotency(
        self,
        idempotency_key: str | None,
        acc_no: str,
        operation: str,
        amount: Decimal,
    ) -> tuple[str, IdempotencyRecord | None]:
        """
        Atomically reserve the idempotency slot before executing money movement.

        Returns ``("claimed", None)`` when this request owns the slot — the
        caller must execute and then call ``_complete_idempotency``. Other
        statuses mean the caller must NOT execute and should replay/return
        the corresponding error instead.
        """
        if not idempotency_key or not self.idempotency_repo:
            return "claimed", None

        existing = await self.idempotency_repo.get(idempotency_key)
        if existing is not None:
            return self._classify_idempotency_record(existing)

        pending = IdempotencyRecord(
            idempotency_key=idempotency_key,
            account_number=acc_no,
            operation=operation,
            result_json=self._IDEMPOTENCY_PENDING_JSON,
            amount=amount,
        )
        try:
            await self.idempotency_repo.create(pending)
            # Flush (not commit) so the claim commits atomically with the
            # money movement in the caller's commit — and is discarded by a
            # rollback if the operation fails.
            await self.idempotency_repo.flush()
            return "claimed", None
        except IntegrityError:
            # Lost a race: a concurrent same-key request inserted first.
            await self.idempotency_repo.rollback()
            existing = await self.idempotency_repo.get(idempotency_key)
            if existing is None:
                return "incomplete", None
            return self._classify_idempotency_record(existing)
        except (SQLAlchemyError, OSError):
            # Cannot guarantee dedup — fail closed rather than risk double-spend.
            await self.idempotency_repo.rollback()
            return "storage_error", None

    async def _complete_idempotency(
        self,
        idempotency_key: str | None,
        acc_no: str,
        operation: str,
        amount: Decimal,
        result: ServiceResult | TransferResult,
    ) -> None:
        """Store the final result of an idempotent operation (updates the claim)."""
        if not idempotency_key or not self.idempotency_repo:
            return
        if isinstance(result, TransferResult):
            result_json = json.dumps(
                {
                    "success": result.success,
                    "sender_balance": float(result.sender_balance or 0),
                    "receiver_balance": float(result.receiver_balance or 0),
                    "error_message": result.error_message,
                }
            )
        else:
            result_json = json.dumps(
                {
                    "success": result.success,
                    "message": result.message,
                    "data": result.data,
                }
            )
        record = IdempotencyRecord(
            idempotency_key=idempotency_key,
            account_number=acc_no,
            operation=operation,
            result_json=result_json,
            amount=amount,
        )
        try:
            await self.idempotency_repo.update(record)
            await self.idempotency_repo.commit()
        except (SQLAlchemyError, OSError):
            from unionbank.utils.logger import logger

            logger.warning("Failed to persist idempotency result", exc_info=True)
            await self.idempotency_repo.rollback()

    def _idempotency_service_result(
        self, status: str, existing: IdempotencyRecord | None, operation: str
    ) -> ServiceResult | None:
        """Map a claim status to a ServiceResult (deposit/withdraw). None → claimed."""
        if status == "replay" and existing is not None:
            try:
                data = (
                    existing
                    if isinstance(existing, dict)
                    else json.loads(existing.result_json)
                )
                return ServiceResult(
                    success=data.get("success", True),
                    message=data.get("message", "Operation already completed."),
                    data=data.get("data"),
                )
            except (json.JSONDecodeError, KeyError):
                status = "corrupt"
        messages = {
            "corrupt": "Idempotency record corrupted; operation aborted. Contact support.",
            "pending": (
                f"{operation.capitalize()} already in progress for this idempotency key."
            ),
            "incomplete": "Previous attempt outcome unknown. Contact support before retrying.",
            "storage_error": "Idempotency storage unavailable; operation aborted. Please retry.",
        }
        message = messages.get(status)
        if message is None:
            return None
        return ServiceResult(success=False, message=message)

    def _idempotency_transfer_result(
        self, status: str, existing: IdempotencyRecord | None
    ) -> TransferResult | None:
        """Map a claim status to a TransferResult. None → claimed."""
        if status == "replay" and existing is not None:
            try:
                data = (
                    existing
                    if isinstance(existing, dict)
                    else json.loads(existing.result_json)
                )
                return TransferResult(
                    success=data.get("success", True),
                    sender_balance=Decimal(str(data.get("sender_balance", 0))),
                    receiver_balance=Decimal(str(data.get("receiver_balance", 0))),
                    error_message=data.get("error_message", ""),
                )
            except (json.JSONDecodeError, KeyError):
                status = "corrupt"
        messages = {
            "corrupt": "Idempotency record corrupted; transfer aborted. Contact support.",
            "pending": "Transfer already in progress for this idempotency key.",
            "incomplete": "Previous attempt outcome unknown. Contact support before retrying.",
            "storage_error": "Idempotency storage unavailable; transfer aborted. Please retry.",
        }
        message = messages.get(status)
        if message is None:
            return None
        return TransferResult(success=False, error_message=message)

    async def deposit(
        self,
        acc_no: str,
        amount: Decimal,
        category: str = "General",
        idempotency_key: str | None = None,
    ) -> ServiceResult:
        if amount <= 0:
            return ServiceResult(success=False, message="Amount must be positive.")

        # Serialize writes to this account
        lock = _get_account_lock(acc_no)
        async with lock:
            status, existing = await self._claim_idempotency(
                idempotency_key, acc_no, "deposit", amount
            )
            cached = self._idempotency_service_result(status, existing, "deposit")
            if cached is not None:
                return cached

            account = await self.account_repo.get(acc_no)
            if account is None:
                failure = ServiceResult(success=False, message="Account not found.")
                await self._complete_idempotency(
                    idempotency_key, acc_no, "deposit", amount, failure
                )
                return failure
            if not account.can_transact:
                acc_status = "frozen" if account.is_frozen else "closed"
                failure = ServiceResult(success=False, message=f"Account is {acc_status}.")
                await self._complete_idempotency(
                    idempotency_key, acc_no, "deposit", amount, failure
                )
                return failure

            account.balance += amount
            await self.account_repo.update(account)

            txn = Transaction(
                txn_id=generate_transaction_id(),
                account_number=acc_no,
                type=TransactionType.DEPOSIT,
                amount=amount,
                balance=account.balance,
                description="Deposit",
                category=category if category in TRANSACTION_CATEGORIES else "General",
            )
            await self.txn_repo.create(txn)
            await self.account_repo.commit()

            result = ServiceResult(
                success=True,
                message=f"{fmt_currency(float(amount))} deposited successfully. "
                f"New balance: {fmt_currency(float(account.balance))}",
                data={"balance": float(account.balance)},
            )
            await self._complete_idempotency(
                idempotency_key, acc_no, "deposit", amount, result
            )

        # Send notification (non-fatal if fails)
        if self.notif_service and account:
            try:
                await self.notif_service.notify_deposit(acc_no, amount, account.balance, txn.txn_id)
            except (OSError, TimeoutError):
                from unionbank.utils.logger import logger

                logger.warning("Failed to send deposit notification", exc_info=True)

        return result

    async def withdraw(
        self,
        acc_no: str,
        amount: Decimal,
        category: str = "General",
        idempotency_key: str | None = None,
    ) -> ServiceResult:
        if amount <= 0:
            return ServiceResult(success=False, message="Amount must be positive.")

        # Serialize writes to this account
        lock = _get_account_lock(acc_no)
        async with lock:
            status, existing = await self._claim_idempotency(
                idempotency_key, acc_no, "withdraw", amount
            )
            cached = self._idempotency_service_result(status, existing, "withdraw")
            if cached is not None:
                return cached

            account = await self.account_repo.get(acc_no)
            if account is None:
                failure = ServiceResult(success=False, message="Account not found.")
                await self._complete_idempotency(
                    idempotency_key, acc_no, "withdraw", amount, failure
                )
                return failure
            if not account.can_transact:
                acc_status = "frozen" if account.is_frozen else "closed"
                failure = ServiceResult(success=False, message=f"Account is {acc_status}.")
                await self._complete_idempotency(
                    idempotency_key, acc_no, "withdraw", amount, failure
                )
                return failure

            if amount > account.balance:
                failure = ServiceResult(
                    success=False,
                    message=f"Insufficient balance. Available: {fmt_currency(float(account.balance))}",
                )
                await self._complete_idempotency(
                    idempotency_key, acc_no, "withdraw", amount, failure
                )
                return failure

            account.balance -= amount
            self._ensure_non_negative_balance(account.balance, "withdraw")
            await self.account_repo.update(account)

            txn = Transaction(
                txn_id=generate_transaction_id(),
                account_number=acc_no,
                type=TransactionType.WITHDRAW,
                amount=amount,
                balance=account.balance,
                description="Withdrawal",
                category=category if category in TRANSACTION_CATEGORIES else "General",
            )
            await self.txn_repo.create(txn)
            await self.account_repo.commit()

            result = ServiceResult(
                success=True,
                message=f"{fmt_currency(float(amount))} withdrawn successfully. "
                f"New balance: {fmt_currency(float(account.balance))}",
                data={"balance": float(account.balance)},
            )
            await self._complete_idempotency(
                idempotency_key, acc_no, "withdraw", amount, result
            )

        # Send notification (non-fatal if fails)
        if self.notif_service and account:
            try:
                await self.notif_service.notify_withdraw(
                    acc_no, amount, account.balance, txn.txn_id
                )
            except (OSError, TimeoutError):
                from unionbank.utils.logger import logger

                logger.warning("Failed to send withdraw notification", exc_info=True)

        return result

    async def transfer(
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

        cat = category if category in TRANSACTION_CATEGORIES else "General"

        # Serialize both accounts to prevent lost updates
        lock = _get_account_lock(sender_acc_no, receiver_acc_no)
        async with lock:
            # Claim the idempotency slot BEFORE executing: the pending INSERT
            # (DB-unique key) is atomic, so a concurrent same-key request
            # either replays this result or reports in-progress — it can
            # never double-execute.
            status, existing = await self._claim_idempotency(
                idempotency_key, sender_acc_no, "transfer", amount
            )
            cached = self._idempotency_transfer_result(status, existing)
            if cached is not None:
                return cached

            sender = await self.account_repo.get(sender_acc_no)
            receiver = await self.account_repo.get(receiver_acc_no)

            if sender is None:
                failure = TransferResult(success=False, error_message="Sender account not found.")
                await self._complete_idempotency(
                    idempotency_key, sender_acc_no, "transfer", amount, failure
                )
                return failure
            if receiver is None:
                failure = TransferResult(
                    success=False, error_message="Recipient account not found."
                )
                await self._complete_idempotency(
                    idempotency_key, sender_acc_no, "transfer", amount, failure
                )
                return failure

            if not sender.can_transact:
                failure = TransferResult(
                    success=False, error_message="Your account is frozen or closed."
                )
                await self._complete_idempotency(
                    idempotency_key, sender_acc_no, "transfer", amount, failure
                )
                return failure
            if not receiver.can_transact:
                failure = TransferResult(
                    success=False, error_message="Recipient account is frozen or closed."
                )
                await self._complete_idempotency(
                    idempotency_key, sender_acc_no, "transfer", amount, failure
                )
                return failure

            if amount > sender.balance:
                failure = TransferResult(
                    success=False,
                    error_message=f"Insufficient balance. Available: {fmt_currency(float(sender.balance))}",
                )
                await self._complete_idempotency(
                    idempotency_key, sender_acc_no, "transfer", amount, failure
                )
                return failure

            # Perform atomic transfer
            try:
                sender.balance -= amount
                self._ensure_non_negative_balance(sender.balance, "transfer")
                receiver.balance += amount

                await self.account_repo.update(sender)
                await self.account_repo.update(receiver)

                # Log both transactions
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
                await self.txn_repo.create(sender_txn)
                await self.txn_repo.create(receiver_txn)
                await self.account_repo.commit()
            except (SQLAlchemyError, OSError) as exc:
                from unionbank.utils.logger import logger

                logger.error("Transfer failed, rolling back: %s", exc, exc_info=True)
                await self.account_repo.rollback()
                return TransferResult(
                    success=False,
                    error_message="Transfer failed due to a database error. Please try again.",
                )

            result = TransferResult(
                success=True,
                sender_balance=sender.balance,
                receiver_balance=receiver.balance,
            )
            await self._complete_idempotency(
                idempotency_key, sender_acc_no, "transfer", amount, result
            )

        # Send notifications (non-fatal if fails, outside lock)
        if self.notif_service:
            try:
                await self.notif_service.notify_transfer_sent(
                    sender_acc_no,
                    amount,
                    receiver_acc_no,
                    sender.balance,
                    sender_txn.txn_id,
                )
                await self.notif_service.notify_transfer_received(
                    receiver_acc_no,
                    amount,
                    sender_acc_no,
                    receiver.balance,
                    receiver_txn.txn_id,
                )
            except (OSError, TimeoutError):
                from unionbank.utils.logger import logger

                logger.warning("Failed to send transfer notification", exc_info=True)

        return result

    async def get_statement(self, acc_no: str) -> list[Transaction]:
        return await self.txn_repo.get_by_account(acc_no)

    async def get_mini_statement(self, acc_no: str, limit: int = 5) -> list[Transaction]:
        return await self.txn_repo.get_mini(acc_no, limit)

    async def apply_interest(self, acc_no: str) -> ServiceResult:
        account = await self.account_repo.get(acc_no)
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
        await self.account_repo.update(account)

        txn = Transaction(
            txn_id=generate_transaction_id(),
            account_number=acc_no,
            type=TransactionType.INTEREST,
            amount=interest,
            balance=account.balance,
            description="Monthly interest credit",
            category="Savings",
        )
        await self.txn_repo.create(txn)
        await self.account_repo.commit()

        # Send notification (non-fatal if fails)
        if self.notif_service and account:
            try:
                await self.notif_service.notify_interest(
                    acc_no, interest, account.balance, txn.txn_id
                )
            except (OSError, TimeoutError):
                from unionbank.utils.logger import logger

                logger.warning("Failed to send interest notification", exc_info=True)

        return ServiceResult(
            success=True,
            message=f"Interest of {fmt_currency(float(interest))} credited! "
            f"New balance: {fmt_currency(float(account.balance))}",
            data={"interest": float(interest), "balance": float(account.balance)},
        )

    async def get_category_totals(self) -> dict[str, Decimal]:
        return await self.txn_repo.get_category_totals()

    async def get_paginated_transactions(
        self,
        acc_no: str | None = None,
        page: int = 1,
        per_page: int = 20,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        txn_type: str | None = None,
    ) -> tuple[list[Transaction], int]:
        return await self.txn_repo.get_paginated(
            acc_no=acc_no,
            page=page,
            per_page=per_page,
            from_date=from_date,
            to_date=to_date,
            txn_type=txn_type,
        )

    async def get_paginated_keyset(
        self,
        acc_no: str | None = None,
        limit: int = 20,
        cursor: datetime | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        txn_type: str | None = None,
    ) -> KeysetPage[Transaction]:
        """Keyset (cursor-based) pagination."""
        return await self.txn_repo.get_paginated_keyset(
            acc_no=acc_no,
            limit=limit,
            cursor=cursor,
            from_date=from_date,
            to_date=to_date,
            txn_type=txn_type,
        )


#  Async Account Service


