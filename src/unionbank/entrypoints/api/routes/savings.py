"""Savings goal routes: list, create, update, contribute, delete.

Extracted from main.py to reduce file size and improve maintainability.
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from unionbank.entrypoints.api.common import get_current_customer
from unionbank.utils import fmt_currency

router = APIRouter(tags=["Savings Goals"])


# ── Request/Response Models ──────────────────────────────────────────────


class SavingsGoalCreate(BaseModel):
    name: str = Field(..., min_length=2, description="Goal name")
    target_amount: float = Field(..., gt=0, description="Savings target")
    target_date: str | None = Field(None, description="Optional target date (YYYY-MM-DD)")


class SavingsGoalUpdate(BaseModel):
    name: str | None = None
    target_amount: float | None = Field(default=None, gt=0)
    target_date: str | None = None


class SavingsGoalContribute(BaseModel):
    amount: float = Field(..., gt=0, description="Amount to contribute")


class SavingsGoalOut(BaseModel):
    goal_id: str
    name: str
    target_amount: float
    current_amount: float
    target_date: str | None = None
    created_at: str
    is_completed: bool
    progress_pct: float = 0.0


class SavingsGoalsSummary(BaseModel):
    total_goals: int
    completed: int
    total_saved: float
    total_saved_formatted: str
    total_target: float
    total_target_formatted: str
    goals: list[SavingsGoalOut]


class MessageResponse(BaseModel):
    message: str
    status: str = "success"


# ── Helper ───────────────────────────────────────────────────────────────


def _goal_to_out(goal) -> SavingsGoalOut:
    pct = (
        round((float(goal.current_amount) / float(goal.target_amount) * 100), 1)
        if float(goal.target_amount) > 0
        else 0
    )
    return SavingsGoalOut(
        goal_id=goal.goal_id,
        name=goal.name,
        target_amount=float(goal.target_amount),
        current_amount=float(goal.current_amount),
        target_date=goal.target_date,
        created_at=str(goal.created_at)[:19],
        is_completed=goal.is_completed,
        progress_pct=pct,
    )


# ── Routes ───────────────────────────────────────────────────────────────


@router.get("/api/savings", response_model=SavingsGoalsSummary)
def list_savings_goals(request: Request, customer: dict = Depends(get_current_customer)) -> dict:
    """List all savings goals for the authenticated customer."""
    acc_no = customer["account_number"]
    from unionbank.infrastructure.container import get_container

    goals = get_container().savings_goal_repo().get_by_account(acc_no)

    goal_list = [_goal_to_out(g) for g in goals]

    total_saved = sum(float(g.current_amount) for g in goals)
    total_target = sum(float(g.target_amount) for g in goals)
    completed = sum(1 for g in goals if g.is_completed)

    return SavingsGoalsSummary(
        total_goals=len(goals),
        completed=completed,
        total_saved=total_saved,
        total_saved_formatted=fmt_currency(total_saved),
        total_target=total_target,
        total_target_formatted=fmt_currency(total_target),
        goals=goal_list,
    )


@router.post("/api/savings", response_model=SavingsGoalOut, status_code=status.HTTP_201_CREATED)
def create_savings_goal(
    request: Request,
    req: SavingsGoalCreate,
    customer: dict = Depends(get_current_customer),
) -> dict:
    """Create a new savings goal."""
    acc_no = customer["account_number"]
    from unionbank.infrastructure.container import get_container

    result = (
        get_container()
        .savings_goal_service()
        .create_goal(
            acc_no=acc_no,
            name=req.name,
            target_amount=Decimal(str(req.target_amount)),
            target_date=req.target_date,
        )
    )
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)

    # Fetch the newly created goal
    goals = get_container().savings_goal_repo().get_by_account(acc_no)
    if goals:
        g = goals[-1]
        return SavingsGoalOut(
            goal_id=g.goal_id,
            name=g.name,
            target_amount=float(g.target_amount),
            current_amount=float(g.current_amount),
            target_date=g.target_date,
            created_at=str(g.created_at)[:19],
            is_completed=False,
            progress_pct=0.0,
        )
    raise HTTPException(status_code=500, detail="Failed to create goal.")


@router.put("/api/savings/{goal_id}", response_model=SavingsGoalOut)
def update_savings_goal(
    request: Request,
    goal_id: str,
    req: SavingsGoalUpdate,
    customer: dict = Depends(get_current_customer),
) -> dict:
    """Update a savings goal."""
    from unionbank.infrastructure.container import get_container

    goal_repo = get_container().savings_goal_repo()

    goal = goal_repo.get(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found.")

    if req.name is not None:
        goal.name = req.name
    if req.target_amount is not None:
        goal.target_amount = Decimal(str(req.target_amount))
    if req.target_date is not None:
        goal.target_date = req.target_date

    goal.is_completed = goal.current_amount >= goal.target_amount
    goal_repo.update(goal)
    goal_repo.commit()

    return _goal_to_out(goal)


@router.post("/api/savings/{goal_id}/contribute", response_model=SavingsGoalOut)
def contribute_to_goal(
    request: Request,
    goal_id: str,
    req: SavingsGoalContribute,
    customer: dict = Depends(get_current_customer),
) -> dict:
    """Contribute money from your balance to a savings goal."""
    acc_no = customer["account_number"]
    from unionbank.infrastructure.container import get_container

    c = get_container()

    # Check current balance from DB
    domain_acc = c.account_repo().get(acc_no)
    if not domain_acc:
        raise HTTPException(status_code=404, detail="Account not found.")
    if req.amount > float(domain_acc.balance):
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance. Available: {fmt_currency(float(domain_acc.balance))}",
        )

    result = c.savings_goal_service().contribute(
        acc_no=acc_no, goal_id=goal_id, amount=Decimal(str(req.amount))
    )
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)

    # Return updated goal
    goal = c.savings_goal_repo().get(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found.")

    return _goal_to_out(goal)


@router.delete("/api/savings/{goal_id}", response_model=MessageResponse)
def delete_savings_goal(
    request: Request,
    goal_id: str,
    customer: dict = Depends(get_current_customer),
) -> dict:
    """Delete a savings goal and refund the amount to your balance."""
    acc_no = customer["account_number"]
    from unionbank.infrastructure.container import get_container

    result = get_container().savings_goal_service().delete_goal(acc_no=acc_no, goal_id=goal_id)
    if not result.success:
        raise HTTPException(status_code=404, detail=result.message)

    return MessageResponse(message=result.message)
