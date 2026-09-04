"""V2 API — Savings goals endpoints."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, status

from unionbank.entrypoints.api.common import get_current_customer
from unionbank.entrypoints.api.models import (
    ApiResponse,
    MessageData,
    SavingsGoalContribute,
    SavingsGoalCreate,
    SavingsGoalOut,
    SavingsGoalsSummary,
)
from unionbank.entrypoints.api.v2.helpers import _err, _fmt_currency, _get_container, _ok

router = APIRouter()


@router.get("/savings", response_model=ApiResponse[SavingsGoalsSummary])
def v2_list_savings_goals(customer: dict = Depends(get_current_customer)) -> ApiResponse:
    """List all savings goals for the authenticated customer."""
    acc_no = customer["account_number"]
    c = _get_container()
    goals = c.savings_goal_repo().get_by_account(acc_no)

    goal_list = []
    for g in goals:
        pct = (
            round((float(g.current_amount) / float(g.target_amount) * 100), 1)
            if float(g.target_amount) > 0
            else 0
        )
        goal_list.append(
            SavingsGoalOut(
                goal_id=g.goal_id,
                name=g.name,
                target_amount=float(g.target_amount),
                current_amount=float(g.current_amount),
                target_date=g.target_date,
                created_at=str(g.created_at)[:19],
                is_completed=g.is_completed,
                progress_pct=pct,
            )
        )

    total_saved = sum(float(g.current_amount) for g in goals)
    total_target = sum(float(g.target_amount) for g in goals)
    completed = sum(1 for g in goals if g.is_completed)

    return _ok(
        SavingsGoalsSummary(
            total_goals=len(goals),
            completed=completed,
            total_saved=total_saved,
            total_saved_formatted=_fmt_currency(total_saved),
            total_target=total_target,
            total_target_formatted=_fmt_currency(total_target),
            goals=goal_list,
        )
    )


@router.post(
    "/savings", response_model=ApiResponse[SavingsGoalOut], status_code=status.HTTP_201_CREATED
)
def v2_create_savings_goal(req: SavingsGoalCreate, customer: dict = Depends(get_current_customer)) -> ApiResponse:
    """Create a new savings goal."""
    acc_no = customer["account_number"]
    c = _get_container()
    result = c.savings_goal_service().create_goal(
        acc_no=acc_no,
        name=req.name,
        target_amount=Decimal(str(req.target_amount)),
        target_date=req.target_date,
    )
    if not result.success:
        _err(result.message)

    goals = c.savings_goal_repo().get_by_account(acc_no)
    if goals:
        g = goals[-1]
        return _ok(
            SavingsGoalOut(
                goal_id=g.goal_id,
                name=g.name,
                target_amount=float(g.target_amount),
                current_amount=float(g.current_amount),
                target_date=g.target_date,
                created_at=str(g.created_at)[:19],
                is_completed=False,
                progress_pct=0.0,
            )
        )
    _err("Failed to create goal.", status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.post("/savings/{goal_id}/contribute", response_model=ApiResponse[SavingsGoalOut])
def v2_contribute_to_goal(
    goal_id: str, req: SavingsGoalContribute, customer: dict = Depends(get_current_customer)
) -> ApiResponse:
    """Contribute money from your balance to a savings goal."""
    acc_no = customer["account_number"]
    c = _get_container()

    result = c.savings_goal_service().contribute(
        acc_no=acc_no, goal_id=goal_id, amount=Decimal(str(req.amount))
    )
    if not result.success:
        _err(result.message)

    goal = c.savings_goal_repo().get(goal_id)
    if not goal:
        _err("Goal not found.", status.HTTP_404_NOT_FOUND)

    pct = (
        round((float(goal.current_amount) / float(goal.target_amount) * 100), 1)
        if float(goal.target_amount) > 0
        else 0
    )
    return _ok(
        SavingsGoalOut(
            goal_id=goal.goal_id,
            name=goal.name,
            target_amount=float(goal.target_amount),
            current_amount=float(goal.current_amount),
            target_date=goal.target_date,
            created_at=str(goal.created_at)[:19],
            is_completed=goal.is_completed,
            progress_pct=pct,
        )
    )


@router.delete("/savings/{goal_id}", response_model=ApiResponse[MessageData])
def v2_delete_savings_goal(goal_id: str, customer: dict = Depends(get_current_customer)) -> dict[str, str]:
    """Delete a savings goal and refund the amount to your balance."""
    acc_no = customer["account_number"]
    c = _get_container()
    result = c.savings_goal_service().delete_goal(acc_no=acc_no, goal_id=goal_id)
    if not result.success:
        _err(result.message)

    return _ok(MessageData(message=result.message))


#  Loan Endpoints
