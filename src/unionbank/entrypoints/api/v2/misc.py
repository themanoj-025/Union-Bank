"""V2 API — Utility endpoints (categories, analyzr, health check)."""

from __future__ import annotations

from datetime import datetime, timezone

try:
    from sqlalchemy.exc import SQLAlchemyError
except ImportError:
    SQLAlchemyError = Exception  # fallback if sqlalchemy not installed

from unionbank.entrypoints.api.models import (
    AnalyzrQueryRequest,
    ApiResponse,
    HealthData,
)
from unionbank.entrypoints.api.v2.helpers import _err, _get_container, _ok

router = __import__("fastapi").APIRouter()

@router.get("/categories", response_model=ApiResponse[list[str]])
def v2_list_categories() -> dict[str, object]:
    """List all available transaction categories."""
    from unionbank.application.services import TRANSACTION_CATEGORIES

    return _ok(TRANSACTION_CATEGORIES)


#  Analyzr — Natural-Language Search


@router.post("/analyzr/query", response_model=ApiResponse[dict])
def v2_analyzr_query(req: AnalyzrQueryRequest) -> ApiResponse:
    """
    Natural-language transaction search.

    Accepts plain English queries like:
      - "show me large deposits last month"
      - "what did I spend on food this month?"
      - "find suspicious transactions"
      - "show all deposits over 500"

    Translates the query into structured filters using pattern matching,
    executes the search, and returns formatted results.
    No external API calls — translation is deterministic and local.
    """
    from unionbank.utils.analyzr_core import execute_query as analyzr_search

    result = analyzr_search(
        query=req.query,
        account_number=req.account_number,
        max_results=req.max_results,
    )
    return _ok(result)


@router.get("/health", response_model=ApiResponse[HealthData])
def v2_health_check() -> ApiResponse:
    """
    Health check endpoint.

    Checks:
    - Database connectivity (via `SELECT 1`)
    - Cache connectivity (via Redis ping, if configured)
    - Returns a 503 status if any dependency is down
    """
    from datetime import datetime, timezone

    db_status = "connected"
    cache_status = "connected"

    try:
        from unionbank.infrastructure.database import get_engine

        engine = get_engine()
        with engine.connect() as conn:
            from sqlalchemy import text

            conn.execute(text("SELECT 1"))
    except (OSError, SQLAlchemyError, RuntimeError):
        db_status = "disconnected"

    try:
        from unionbank.infrastructure.cache import get_cache

        cache = get_cache()
        cache.ping()
    except (OSError, ConnectionError, TimeoutError):
        cache_status = "disconnected"

    overall = "healthy" if db_status == "connected" else "degraded"

    if overall == "degraded":
        from fastapi import status

        _err(
            f"Database: {db_status}, Cache: {cache_status}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return _ok(
        HealthData(
            status=overall,
            database=db_status,
            cache=cache_status,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    )
