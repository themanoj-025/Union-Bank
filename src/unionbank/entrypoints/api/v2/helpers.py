"""
V2 API — Shared helpers (container access, response builders, exception handlers).

All route modules import from here instead of duplicating these utilities.
"""

from __future__ import annotations

from fastapi import HTTPException, Request

from unionbank.entrypoints.api.models import ApiResponse


def _get_container() -> Container:
    """Lazy-import the DI container."""
    from unionbank.infrastructure.container import get_container

    return get_container()


def _fmt_currency(val: float) -> str:
    from unionbank.utils import fmt_currency as _fc

    return _fc(val)


def _ok(data, meta: dict | None = None) -> ApiResponse:
    """Build a success response."""
    return ApiResponse(success=True, data=data, **({"meta": meta} if meta is not None else {}))


def _err(message: str, status_code: int = 400, error_code: str | None = None) -> Any:
    """
    Build an error response (raises HTTPException with envelope body).

    Args:
        message:     Human-readable error message.
        status_code: HTTP status code (default 400).
        error_code:  Optional structured ErrorCode for programmatic handling.

    """
    meta = {"error_code": error_code} if error_code else None
    resp = ApiResponse(success=False, error=message, meta=meta)
    raise HTTPException(status_code=status_code, detail=resp.model_dump())


async def v2_http_exception_handler(request: Request, exc: HTTPException) -> ApiResponse:
    """
    Override FastAPI's default exception handler for the v2 router.

    Instead of wrapping the error in {"detail": {...}}, we return the
    ApiResponse envelope directly as the response body.
    """
    from fastapi.responses import JSONResponse

    detail = exc.detail
    if isinstance(detail, dict):
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse(success=False, error=str(detail)).model_dump(),
    )


async def v2_generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch unhandled exceptions and return a 500 envelope response."""
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=500,
        content=ApiResponse(success=False, error="An unexpected error occurred.").model_dump(),
    )
