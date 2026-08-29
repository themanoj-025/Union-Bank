"""
account.py  –  Account model + all account-level operations (with logging).

Core class defined here; financial operations are in account_operations.py
and savings goals are in account_goals.py.
"""

from __future__ import annotations

import contextlib
from datetime import datetime
from typing import Any

from unionbank.domain.clock import utcnow as _utcnow
from unionbank.entrypoints.cli.account_goals import AccountGoalsMixin
from unionbank.entrypoints.cli.account_operations import AccountOperationsMixin
from unionbank.entrypoints.cli.ui import (
    BOLD,
    CYAN,
    GREEN,
    RED,
    RESET,
    WHITE,
    YELLOW,
    divider,
    error,
    header,
    info,
    prompt_password,
    success,
    warning,
)
from unionbank.utils import (
    fmt_currency,
    generate_transaction_id,
    now_str,
    verify_password,
)
from unionbank.utils.logger import logger

# Ensure SQLite tables exist
from unionbank.infrastructure.database import init_db

init_db()


class Account(AccountOperationsMixin, AccountGoalsMixin):
    def __init__(self, data: dict) -> None:
        self.account_number = data["account_number"]
        self.name = data["name"]
        self.age = data["age"]
        self.gender = data["gender"]
        self.mobile = data["mobile"]
        self.email = data["email"]
        self.password = data["password"]
        self.balance = data.get("balance", 0.0)
        self.is_active = data.get("is_active", True)
        self.is_frozen = data.get("is_frozen", False)
        self.created_at = data.get("created_at", now_str())

    def to_dict(self) -> Any:
        return {
            "account_number": self.account_number,
            "name": self.name,
            "age": self.age,
            "gender": self.gender,
            "mobile": self.mobile,
            "email": self.email,
            "password": self.password,
            "balance": self.balance,
            "is_active": self.is_active,
            "is_frozen": self.is_frozen,
            "created_at": self.created_at,
        }

    def save(self) -> Any:
        """Save the account — writes to SQLite only (no JSON)."""
        from decimal import Decimal

        from unionbank.domain.entities import Account as DomainAccount
        from unionbank.infrastructure.container import get_container

        c = get_container()
        repo = c.account_repo()

        # Preserve original created_at if account already exists
        existing = repo.get(self.account_number)
        original_created_at = None
        if existing:
            original_created_at = existing.created_at

        # Parse string created_at to datetime if it's a string
        created_at_dt = None
        if isinstance(self.created_at, str) and self.created_at:
            with contextlib.suppress(ValueError, TypeError):
                created_at_dt = datetime.fromisoformat(self.created_at.replace(" ", "T"))

        domain_acc = DomainAccount(
            account_number=self.account_number,
            name=self.name,
            age=self.age,
            gender=self.gender,
            mobile=self.mobile,
            email=self.email,
            password=self.password,
            balance=Decimal(str(self.balance)),
            is_active=self.is_active,
            is_frozen=self.is_frozen,
            created_at=original_created_at or created_at_dt or _utcnow(),
        )

        if existing:
            repo.update(domain_acc)
        else:
            repo.create(domain_acc)
        repo.commit()

        logger.debug(f"Account {self.account_number} saved to database.")

    def log_transaction(self, txn_type, amount, description, target_acc=None, category=None) -> Any:
        """Log a transaction — writes to SQLite only (no JSON)."""
        from decimal import Decimal

        from sqlalchemy.exc import IntegrityError

        from unionbank.domain.entities import Transaction as DomainTransaction
        from unionbank.domain.entities import TransactionType
        from unionbank.infrastructure.container import get_container

        c = get_container()
        txn_id = generate_transaction_id()

        # Ensure the account row exists in SQLite first (in case it was only in JSON)
        acc_repo = c.account_repo()
        if not acc_repo.exists(self.account_number):
            from unionbank.domain.entities import Account as DomainAccount

            acc_repo.create(
                DomainAccount(
                    account_number=self.account_number,
                    name=self.name,
                    password=self.password,
                    balance=Decimal(str(self.balance)),
                    is_active=self.is_active,
                    is_frozen=self.is_frozen,
                )
            )
            acc_repo.commit()

        domain_txn = DomainTransaction(
            txn_id=txn_id,
            account_number=self.account_number,
            type=TransactionType(txn_type.upper()),
            amount=Decimal(str(amount)),
            balance=Decimal(str(self.balance)),
            description=description,
            category=category or "General",
            target_account=target_acc,
        )
        try:
            c.transaction_repo().create(domain_txn)
            c.transaction_repo().commit()
        except IntegrityError:
            c.transaction_repo().rollback()
            logger.warning(
                f"Transaction logging skipped for {txn_id} "
                f"(account {self.account_number} may not exist)"
            )

        logger.info(
            f"TXN [{txn_id}]  {txn_type:<14}  Acc:{self.account_number}  "
            f"Amt:{fmt_currency(amount)}  Bal:{fmt_currency(self.balance)}"
            + (f"  -> {target_acc}" if target_acc else "")
        )
        return txn_id

    def check_balance(self) -> Any:
        header("ACCOUNT BALANCE")
        print(f"  {GREEN}Account No : {BOLD}{self.account_number}{RESET}")
        print(f"  {GREEN}Name       : {BOLD}{self.name}{RESET}")
        print(f"  {GREEN}Balance    : {BOLD}{fmt_currency(self.balance)}{RESET}")
        divider()
        logger.info(
            f"Balance checked -> Acc:{self.account_number}  Bal:{fmt_currency(self.balance)}"
        )

    def mini_statement(self) -> Any:
        header("MINI STATEMENT  (Last 5 transactions)")
        from unionbank.infrastructure.container import get_container

        c = get_container()
        from unionbank.domain.entities import TransactionType

        records = []
        for txn in c.transaction_repo().get_mini(self.account_number, limit=5):
            sign = (
                "+" if txn.type in (TransactionType.DEPOSIT, TransactionType.TRANSFER_IN) else "-"
            )
            color = GREEN if sign == "+" else RED
            cat = txn.category or ""
            ts = str(txn.timestamp)[:19] if txn.timestamp else ""
            print(
                f"  {ts}  |  {txn.type.value:<14}  |  "
                f"{color}{sign}{fmt_currency(float(txn.amount))}{RESET}  |  Bal: {fmt_currency(float(txn.balance))}"
            )
            if cat:
                print(f"  {'':>12}[{cat}]")
        if not records:
            info("No transactions found.")
        divider()
        logger.info(f"Mini statement viewed -> Acc:{self.account_number}")

    def full_statement(self) -> Any:
        header("FULL TRANSACTION HISTORY")
        from unionbank.infrastructure.container import get_container

        c = get_container()
        from unionbank.domain.entities import TransactionType

        records = c.transaction_repo().get_by_account(self.account_number)
        if not records:
            info("No transactions found.")
        else:
            # Show oldest first for full statement
            for txn in reversed(records):
                sign = (
                    "+"
                    if txn.type in (TransactionType.DEPOSIT, TransactionType.TRANSFER_IN)
                    else "-"
                )
                color = GREEN if sign == "+" else RED
                cat = txn.category or ""
                ts = str(txn.timestamp)[:19] if txn.timestamp else ""
                print(
                    f"  [{txn.txn_id}]  {ts}  |  "
                    f"{txn.type.value:<14}  |  {color}{sign}{fmt_currency(float(txn.amount))}{RESET}  |  "
                    f"Bal: {fmt_currency(float(txn.balance))}"
                )
                if cat and cat != "General":
                    print(f"    {CYAN}    Category: {cat}{RESET}")
                if txn.description:
                    print(f"    {CYAN}    Note: {txn.description}{RESET}")
        divider()
        logger.info(f"Full statement viewed -> Acc:{self.account_number}")

    def view_profile(self) -> Any:
        status = "FROZEN" if self.is_frozen else ("ACTIVE" if self.is_active else "CLOSED")
        status_color = RED if self.is_frozen else (GREEN if self.is_active else YELLOW)
        header("PROFILE DETAILS")
        print(f"  {CYAN}Name           :{WHITE} {self.name}{RESET}")
        print(f"  {CYAN}Age            :{WHITE} {self.age}{RESET}")
        print(f"  {CYAN}Gender         :{WHITE} {self.gender}{RESET}")
        print(f"  {CYAN}Mobile         :{WHITE} {self.mobile}{RESET}")
        print(f"  {CYAN}Email          :{WHITE} {self.email}{RESET}")
        print(f"  {CYAN}Account Number :{WHITE} {self.account_number}{RESET}")
        print(f"  {CYAN}Balance        :{WHITE} {fmt_currency(self.balance)}{RESET}")
        print(f"  {CYAN}Account Status :{WHITE} {status_color}{status}{RESET}")
        print(f"  {CYAN}Member Since   :{WHITE} {self.created_at}{RESET}")
        divider()
