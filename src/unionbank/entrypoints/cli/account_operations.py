"""
account_operations.py — Financial operations mixin for Account CLI.

Deposit, withdraw, transfer, profile updates, password changes,
account closure, and CSV export.
"""

from __future__ import annotations

from typing import Any

from unionbank.domain.clock import utcnow as _utcnow
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
    export_transactions_to_csv,
    fmt_currency,
    generate_csv_filename,
    get_category_choice,
    get_float,
    now_str,
    validate_email,
    validate_name,
    validate_password,
    validate_phone,
)

_ = _utcnow


class AccountOperationsMixin:
    """Financial operations for the Account CLI."""

    # Attributes set by the Account class that owns this mixin
    account_number: str
    name: str
    balance: float
    mobile: str
    email: str
    password: str
    is_active: bool

    def deposit(self) -> Any:
        header("DEPOSIT MONEY")
        amount = get_float("  Enter amount to deposit : Rs.")
        if amount is None:
            return
        category = get_category_choice()

        from decimal import Decimal

        from unionbank.infrastructure.container import get_container

        result = (
            get_container()
            .transaction_service()
            .deposit(self.account_number, Decimal(str(amount)), category)
        )
        if result.success:
            self.balance = result.data["balance"]
            success(result.message)
        else:
            error(result.message)
        divider()

    def withdraw(self) -> Any:
        header("WITHDRAW MONEY")
        amount = get_float("  Enter amount to withdraw : Rs.")
        if amount is None:
            return
        category = get_category_choice()

        from decimal import Decimal

        from unionbank.infrastructure.container import get_container

        result = (
            get_container()
            .transaction_service()
            .withdraw(self.account_number, Decimal(str(amount)), category)
        )
        if result.success:
            self.balance = result.data["balance"]
            success(result.message)
        else:
            error(result.message)
        divider()

    def transfer_funds(self) -> Any:
        """Transfer funds using an atomic SQLite transaction (via service layer)."""
        header("TRANSFER FUNDS")
        target_acc_no = input("  Enter recipient account number : ").strip()

        from unionbank.infrastructure.container import get_container

        c = get_container()
        target_account = c.account_repo().get(target_acc_no)

        if target_account is None:
            error("Recipient account not found.")
            divider()
            return
        if target_acc_no == self.account_number:
            error("Cannot transfer to your own account.")
            divider()
            return

        if target_account.is_frozen:
            error("Recipient account is frozen.")
            divider()
            return
        if not target_account.is_active:
            error("Recipient account is closed.")
            divider()
            return

        print(f"  {CYAN}Recipient : {BOLD}{target_account.name}{RESET}")
        amount = get_float("  Enter amount to transfer : Rs.")
        if amount is None:
            return

        category = get_category_choice()
        confirm = input(
            f"  Confirm transfer of {YELLOW}{fmt_currency(amount)}{RESET} to {CYAN}{target_account.name}{RESET}? (y/n): "
        )
        if confirm.lower() != "y":
            warning("Transfer cancelled.")
            divider()
            return

        from decimal import Decimal

        result = c.transaction_service().transfer(
            sender_acc_no=self.account_number,
            receiver_acc_no=target_acc_no,
            amount=Decimal(str(amount)),
            category=category,
        )

        if result.success:
            self.balance = float(result.sender_balance)
            success(f"{fmt_currency(amount)} transferred to {target_account.name} successfully!")
            print(f"  {GREEN}Your New Balance : {BOLD}{fmt_currency(self.balance)}{RESET}")
        else:
            error(result.error_message)
        divider()

    def update_profile(self) -> Any:
        header("UPDATE PROFILE")
        print(f"  {WHITE}(Press Enter to keep current value)\n{RESET}")
        name = input(f"  Name   [{CYAN}{self.name}{RESET}]   : ").strip()
        age = input(f"  Age    [{CYAN}{self.age}{RESET}]    : ").strip()
        gender = input(f"  Gender [{CYAN}{self.gender}{RESET}] : ").strip()
        mobile = input(f"  Mobile [{CYAN}{self.mobile}{RESET}] : ").strip()
        email = input(f"  Email  [{CYAN}{self.email}{RESET}]  : ").strip()
        old_name = self.name
        if name:
            err = validate_name(name)
            if err:
                error(err)
                divider()
                return
            self.name = name
        if age:
            self.age = int(age)
        if gender:
            self.gender = gender
        if mobile:
            err = validate_phone(mobile)
            if err:
                error(err)
                divider()
                return
            self.mobile = mobile
        if email:
            err = validate_email(email)
            if err:
                error(err)
                divider()
                return
            self.email = email

        from unionbank.infrastructure.container import get_container

        get_container().account_repo().update(self._domain_obj)
        get_container().account_repo().commit()
        success(f"Profile updated! (Name changed: {old_name} → {self.name})")
        logger.info(f"Profile updated -> Acc:{self.account_number}  Name:{self.name}")
        divider()

    def change_password(self) -> Any:
        header("CHANGE PASSWORD")
        current = prompt_password("  Current password : ")
        if not current:
            warning("Cancelled.")
            divider()
            return
        if not verify_password(current, self.password):
            error("Incorrect current password.")
            divider()
            return
        new_pw = prompt_password("  New password     : ")
        if not new_pw:
            warning("Cancelled.")
            divider()
            return
        err = validate_password(new_pw)
        if err:
            error(err)
            divider()
            return
        confirm = prompt_password("  Confirm password : ")
        if new_pw != confirm:
            error("Passwords do not match.")
            divider()
            return
        self.password = hash_password(new_pw)
        from unionbank.infrastructure.container import get_container

        get_container().account_repo().update(self._domain_obj)
        get_container().account_repo().commit()
        success("Password changed successfully!")
        logger.info(f"Password changed -> Acc:{self.account_number}")
        divider()

    def close_account(self) -> Any:
        header("CLOSE ACCOUNT")
        confirm = input(
            f"  Are you sure you want to close account {CYAN}{self.account_number}{RESET}? (y/n): "
        ).strip()
        if confirm.lower() != "y":
            warning("Account closure cancelled.")
            divider()
            return
        from unionbank.infrastructure.container import get_container

        result = get_container().account_service().close_account(self.account_number)
        if result.success:
            self.is_active = False
            success(result.message)
            logger.info(f"Account closed -> Acc:{self.account_number}")
        else:
            error(result.message)
        divider()

    def export_csv(self) -> Any:
        header("EXPORT TRANSACTIONS TO CSV")
        from unionbank.infrastructure.container import get_container

        c = get_container()
        txns = c.transaction_repo().list_by_account(self.account_number)
        if not txns:
            info("No transactions to export.")
            divider()
            return
        filename = generate_csv_filename(self.account_number)
        export_transactions_to_csv(txns, filename)
        success(f"Statement exported to: {filename}")
        logger.info(f"CSV exported -> Acc:{self.account_number}  File:{filename}")
        divider()
