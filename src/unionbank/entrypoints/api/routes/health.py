"""
Health and utility routes: health check, readiness, liveness, metrics, categories.

Extracted from main.py to reduce file size and improve maintainability.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel

from unionbank.utils import TRANSACTION_CATEGORIES

router = APIRouter(tags=["Utilities"])


# ── Response Models ──────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    status: str = "healthy"
    service: str = "Union Bank API"
    version: str = "2.0.0"


# ── Routes ───────────────────────────────────────────────────────────────


@router.get("/api/categories", response_model=list[str])
def list_categories(request: Request) -> dict[str, object]:
    """List all available transaction categories."""
    return TRANSACTION_CATEGORIES


@router.get("/api/health", response_model=HealthResponse)
def health_check(request: Request) -> dict:
    """Health check endpoint."""
    return HealthResponse()


@router.get("/api/healthz")
def liveness_probe() -> dict[str, object]:
    """Kubernetes liveness probe — returns 200 if the process is alive."""
    return {"status": "alive"}


@router.get("/api/readyz")
def readiness_probe() -> dict:
    """Kubernetes readiness probe — checks database connectivity."""
    from sqlalchemy import text

    from unionbank.infrastructure.database import get_session

    try:
        session = get_session()
        session.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except (OSError, ConnectionError) as e:
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=503,
            content={"status": "not ready", "database": str(e)},
        )


@router.get("/metrics")
def metrics_endpoint() -> dict:
    """Prometheus metrics endpoint. Scraped by Prometheus or any metrics collector."""
    from fastapi.responses import Response

    content, content_type = metrics_response()
    return Response(content=content, media_type=content_type)


def metrics_response() -> dict[str, object]:
    """Lazy import wrapper to avoid circular import at module load time."""
    from unionbank.infrastructure.metrics import metrics_response as _metrics_response

    return _metrics_response()
