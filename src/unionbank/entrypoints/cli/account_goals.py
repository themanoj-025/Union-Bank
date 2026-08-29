"""account_goals.py — Savings goals and interest operations for Account CLI."""

from __future__ import annotations

from typing import Any

from unionbank.entrypoints.cli.ui import (
    BOLD,
    CYAN,
    GREEN,
    RESET,
    WHITE,
    YELLOW,
    divider,
    error,
    header,
    info,
    success,
    warning,
)
from unionbank.utils import (
    fmt_currency,
    get_float,
    get_int,
)
from unionbank.utils.logger import logger


class AccountGoalsMixin:
    """Savings goals and interest operations for the Account CLI."""

    # Attributes set by the Account class that owns this mixin
    account_number: str
    balance: float

    def _show_goal(self, goal: dict, index: int) -> Any:
        """Display a single savings goal."""
        pct = (
            (goal["current_amount"] / goal["target_amount"] * 100)
            if goal["target_amount"] > 0
            else 0
        )
        status = "✅ COMPLETED" if goal.get("is_completed") else "🔄 ACTIVE"
        bar_len = 30
        filled = int(bar_len * pct / 100)
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"  {index}. {goal['name']}")
        print(
            f"     {status}  |  {fmt_currency(goal['current_amount'])} / {fmt_currency(goal['target_amount'])}  ({pct:.1f}%)"
        )
        print(f"     [{bar}]")
        if goal.get("target_date"):
            print(f"     Target date: {goal['target_date']}")
        print()

    def _goals_to_dicts(self, domain_goals) -> list[dict]:
        """Convert domain SavingsGoal entities to dicts for display."""
        return [
            {
                "goal_id": g.goal_id,
                "name": g.name,
                "target_amount": float(g.target_amount),
                "current_amount": float(g.current_amount),
                "target_date": g.target_date or "",
                "created_at": str(g.created_at)[:19],
                "is_completed": g.is_completed,
            }
            for g in domain_goals
        ]

    def savings_goals_menu(self) -> Any:
        """Manage savings goals through an interactive menu."""
        from unionbank.infrastructure.container import get_container

        while True:
            c = get_container()
            domain_goals = c.savings_goal_service().list_goals(self.account_number)
            goals = self._goals_to_dicts(domain_goals)

            header("🎯 SAVINGS GOALS")
            if goals:
                total_saved = sum(g["current_amount"] for g in goals)
                completed = sum(1 for g in goals if g.get("is_completed"))
                print(
                    f"  Goals: {len(goals)}  |  Completed: {completed}  |  Total saved: {fmt_currency(total_saved)}"
                )
                print()
                for i, g in enumerate(goals, 1):
                    self._show_goal(g, i)
            else:
                info("No savings goals yet. Create one below!")
                print()

            print(f"  {CYAN}{'─' * 42}{RESET}")
            print(f"  {WHITE}  1) Create New Goal{RESET}")
            print(f"  {WHITE}  2) Contribute to Goal{RESET}")
            print(f"  {WHITE}  3) Edit Goal{RESET}")
            print(f"  {WHITE}  4) Delete Goal{RESET}")
            print(f"  {WHITE}  5) Back to Account Services{RESET}")
            print(f"  {CYAN}{'─' * 42}{RESET}")

            choice = input("  Enter choice: ").strip()

            if choice == "1":
                self._create_goal()
            elif choice == "2":
                self._contribute_to_goal()
            elif choice == "3":
                self._edit_goal()
            elif choice == "4":
                self._delete_goal()
            elif choice == "5":
                break
            else:
                error("Invalid choice.")

    def _create_goal(self) -> Any:
        from decimal import Decimal

        header("🎯 CREATE SAVINGS GOAL")
        name = input("  Goal name: ").strip()
        if not name or len(name) < 2:
            error("Goal name must be at least 2 characters.")
            return
        target = get_float("  Target amount: Rs.")
        if target is None:
            return
        date_str = input("  Target date (YYYY-MM-DD, optional): ").strip()

        from unionbank.infrastructure.container import get_container

        c = get_container()
        result = c.savings_goal_service().create_goal(
            acc_no=self.account_number,
            name=name,
            target_amount=Decimal(str(round(target, 2))),
            target_date=date_str if date_str else None,
        )
        if result.success:
            logger.info(f"Savings goal created -> Acc:{self.account_number}  Goal:{name}")
            success(result.message)
        else:
            error(result.message)
        divider()

    def _contribute_to_goal(self) -> Any:
        from decimal import Decimal

        from unionbank.infrastructure.container import get_container

        c = get_container()
        domain_goals = c.savings_goal_service().list_goals(self.account_number)
        active = [g for g in domain_goals if not g.is_completed]
        if not active:
            error("No active goals to contribute to.")
            return

        header("💰 CONTRIBUTE TO GOAL")
        for i, g in enumerate(active, 1):
            print(
                f"  {i}. {g.name} — {fmt_currency(float(g.current_amount))} / {fmt_currency(float(g.target_amount))}"
            )
        print()
        idx = get_int("  Select goal number: ")
        if idx is None or idx < 1 or idx > len(active):
            error("Invalid selection.")
            return
        goal = active[idx - 1]

        amount = get_float(f"  Amount to contribute to '{goal.name}': Rs.")
        if amount is None:
            return

        confirm = (
            input(f"  Contribute {YELLOW}{fmt_currency(amount)}{RESET} to '{goal.name}'? (y/n): ")
            .strip()
            .lower()
        )
        if confirm != "y":
            warning("Cancelled.")
            return

        result = c.savings_goal_service().contribute(
            acc_no=self.account_number, goal_id=goal.goal_id, amount=Decimal(str(amount))
        )
        if result.success:
            self.balance -= amount
            success(result.message)
        else:
            error(result.message)
        print(f"  {GREEN}New Balance: {BOLD}{fmt_currency(self.balance)}{RESET}")
        divider()

    def _edit_goal(self) -> Any:
        from decimal import Decimal

        from unionbank.infrastructure.container import get_container

        c = get_container()
        domain_goals = c.savings_goal_service().list_goals(self.account_number)
        if not domain_goals:
            error("No goals to edit.")
            return

        header("✏️ EDIT GOAL")
        for i, g in enumerate(domain_goals, 1):
            print(
                f"  {i}. {g.name} — {fmt_currency(float(g.current_amount))} / {fmt_currency(float(g.target_amount))}"
            )
        print()
        idx = get_int("  Select goal number: ")
        if idx is None or idx < 1 or idx > len(domain_goals):
            error("Invalid selection.")
            return
        goal = domain_goals[idx - 1]

        name = input(f"  Name [{goal.name}]: ").strip()
        if name:
            goal.name = name
        target_str = input(f"  Target amount [{float(goal.target_amount)}]: ").strip()
        if target_str:
            try:
                goal.target_amount = Decimal(str(round(float(target_str), 2)))
            except ValueError:
                error("Invalid amount.")
                return
        date_str = input(f"  Target date [{goal.target_date or 'None'}]: ").strip()
        goal.target_date = date_str if date_str else None
        goal.is_completed = goal.current_amount >= goal.target_amount

        c.savings_goal_repo().update(goal)
        c.savings_goal_repo().commit()
        logger.info(f"Goal edited -> Acc:{self.account_number}  Goal:{goal.name}")
        success("Goal updated!")
        divider()

    def _delete_goal(self) -> Any:
        from unionbank.infrastructure.container import get_container

        c = get_container()
        domain_goals = c.savings_goal_service().list_goals(self.account_number)
        if not domain_goals:
            error("No goals to delete.")
            return

        header("🗑️ DELETE GOAL")
        for i, g in enumerate(domain_goals, 1):
            print(
                f"  {i}. {g.name} — {fmt_currency(float(g.current_amount))} / {fmt_currency(float(g.target_amount))}"
            )
        print()
        idx = get_int("  Select goal number: ")
        if idx is None or idx < 1 or idx > len(domain_goals):
            error("Invalid selection.")
            return
        goal = domain_goals[idx - 1]

        confirm = input(f"  Delete '{goal.name}'? Amount will be refunded. (y/n): ").strip().lower()
        if confirm != "y":
            warning("Cancelled.")
            return

        result = c.savings_goal_service().delete_goal(
            acc_no=self.account_number, goal_id=goal.goal_id
        )
        if result.success:
            if goal.current_amount > 0:
                self.balance += float(goal.current_amount)
            success(result.message)
        else:
            error(result.message)
        divider()

    def apply_interest(self) -> Any:
        """Apply monthly interest using an atomic SQLite transaction."""
        header("INTEREST CALCULATION")
        from unionbank.infrastructure.container import get_container

        result = get_container().transaction_service().apply_interest(self.account_number)
        if result.success:
            self.balance = result.data["balance"]
            success(result.message)
        else:
            if "No interest" in result.message:
                info(result.message)
            else:
                error(result.message)
        divider()
