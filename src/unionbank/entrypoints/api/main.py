"""
main.py  –  FastAPI REST API for Union Bank Management System.

Canonical location: src/unionbank/entrypoints/api/main.py

This is a thin configuration shell.  All route handlers live in
``routes/`` sub-modules and are included here.

Run with (Docker):
    uvicorn unionbank.entrypoints.api.main:app --reload --host 0.0.0.0 --port 8000

Then open http://localhost:8000/docs for interactive API documentation.
"""

import logging
import os
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from unionbank.config import settings

# ── Shared exception handler for V2 envelope ────────────────────────────

from unionbank.entrypoints.api.models import ApiResponse as _V2ApiResponse
from unionbank.infrastructure.metrics import MetricsMiddleware
from unionbank.utils.logger import JsonFormatter, clear_context, logger, set_request_id


# ── Lifespan ─────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Initialize the database on startup and clean up on shutdown.

    Using a lifespan handler instead of module-level init_db() call
    ensures that all imports are fully resolved and __package__ is
    set correctly before any database operations run.
    """
    from unionbank.infrastructure.database import init_db

    init_db()
    yield
    # No shutdown cleanup needed for SQLite


# ── App ──────────────────────────────────────────────────────────────────


app = FastAPI(
    lifespan=lifespan,
    title="Union Bank API",
    description=(
        "REST API for the Union Bank Management System.\n\n"
        "**API Versions**\n"
        "- `/api/v1/` — Legacy endpoints (bare response models, backward compatible)\n"

# --- OpenTelemetry distributed tracing (OTEL_ENABLED=true) ---
try:
    from unionbank.tracing import setup_tracing
    _otel_ok = setup_tracing("unionbank-api")
    if _otel_ok:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app)
except ImportError:
    pass

        "- `/api/v2/` — Current endpoints with standardised `ApiResponse[T]` envelope\n\n"
        "All endpoints return JSON. Authentication uses Bearer JWT tokens.\n"
        "Use `/docs` for interactive API documentation."
    ),
    version="2.0.0",
    contact={"name": "Union Bank Dev Team"},
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
    terms_of_service="https://union-bank.example.com/terms",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "v2 - Auth",
            "description": "Authentication and token management (v2 envelope)",
        },
        {
            "name": "v2 - Account",
            "description": "Customer account profile and management (v2 envelope)",
        },
        {
            "name": "v2 - Transactions",
            "description": "Deposit, withdraw, transfer, and statements (v2 envelope)",
        },
        {
            "name": "v2 - Savings Goals",
            "description": "Create, contribute to, and manage savings goals (v2 envelope)",
        },
        {
            "name": "v2 - Admin",
            "description": "Admin operations: account oversight and statistics (v2 envelope)",
        },
        {
            "name": "v2 - Utilities",
            "description": "Health check and category listing (v2 envelope)",
        },
    ],
)


# ── Middleware ────────────────────────────────────────────────────────────


@app.middleware("http")
async def add_request_id_middleware(request: Request, call_next) -> None:
    """Assign a unique request ID and set up logging context for each request."""
    request_id = request.headers.get("X-Request-ID") or secrets.token_hex(16)
    set_request_id(request_id)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        clear_context()


app.add_middleware(MetricsMiddleware)


# Disabled in testing mode so integration tests don't get rate-limited
limiter = Limiter(
    key_func=get_remote_address,
    enabled=not settings.TESTING,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), interest-cohort=()"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "connect-src 'self'"
        )
        return response


app.add_middleware(SecurityHeadersMiddleware)


class CSRFProtectMiddleware(BaseHTTPMiddleware):
    """
    CSRF protection via double-submit cookie pattern.

    On state-changing requests (POST, PUT, PATCH, DELETE), validates that
    the X-CSRF-Token header matches the ub_csrf_token cookie. This prevents
    CSRF attacks when using cookie-based authentication.

    Safe methods (GET, HEAD, OPTIONS) and auth endpoints are exempt.
    Bearer-token-only clients (no CSRF cookie) are also allowed through
    for backward compatibility.
    """

    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

    # Endpoints that set cookies (exempt from CSRF validation)
    CSRF_EXEMPT_PATHS = {
        "/api/auth/login",
        "/api/auth/admin-login",
        "/api/auth/refresh",
        "/api/auth/register",
        "/api/v2/auth/login",
        "/api/v2/auth/admin-login",
        "/api/v2/auth/refresh",
        "/api/v2/auth/register",
    }

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method in self.SAFE_METHODS:
            return await call_next(request)

        if request.url.path in self.CSRF_EXEMPT_PATHS:
            return await call_next(request)

        from unionbank.utils.cookie_auth import CSRF_TOKEN_COOKIE, validate_csrf_token

        # If no CSRF cookie is present, this is a Bearer-token-only client — allow through
        if CSRF_TOKEN_COOKIE not in request.cookies:
            return await call_next(request)

        # CSRF cookie present — must also have matching header
        if not validate_csrf_token(request):
            logger.warning(
                "CSRF token validation failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                },
            )
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token missing or invalid."},
            )

        return await call_next(request)


app.add_middleware(CSRFProtectMiddleware)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)


# ── Logging ──────────────────────────────────────────────────────────────

# Route access logs through the structured JSON logger for observability.
# Uses bank.jsonl (the JSON log file) so all structured logs live together.

# Compute project root from this file's location for log file path
_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
_JSON_LOG_DIR = os.path.join(_PROJECT_ROOT, "data")
os.makedirs(_JSON_LOG_DIR, exist_ok=True)
_JSON_LOG_FILE = os.path.join(_JSON_LOG_DIR, "bank.jsonl")
_access_json_handler = logging.FileHandler(_JSON_LOG_FILE, encoding="utf-8")
_access_json_handler.setFormatter(JsonFormatter(datefmt="%Y-%m-%dT%H:%M:%S.%fZ"))
_access_json_handler.setLevel(logging.INFO)

# Uvicorn access logger — JSON to bank.jsonl, no console (keeps terminal clean)
_uvicorn_logger = logging.getLogger("uvicorn.access")
_uvicorn_logger.handlers = []  # Replace default handlers
_uvicorn_logger.addHandler(_access_json_handler)
_uvicorn_logger.propagate = False

# Uvicorn error logger — console only (stderr errors should be visible)
_uvicorn_error_logger = logging.getLogger("uvicorn.error")
_uvicorn_error_logger.propagate = False


# ── V2 HTTPException handler ─────────────────────────────────────────────

# V2 endpoints raise HTTPException with an ApiResponse dict as the detail.
# FastAPI wraps this in {"detail": {...}}, but we need the ApiResponse dict
# directly in the response body.  We only transform V2 routes so V1 endpoints
# (which use bare {"detail": "message"}) are unaffected.


@app.exception_handler(Exception)
async def _v2_aware_http_exception_handler(request: Request, exc) -> JSONResponse:
    """For V2 routes, return the ApiResponse dict directly (not wrapped in detail)."""
    from fastapi import HTTPException
    from fastapi.responses import JSONResponse

    if isinstance(exc, HTTPException) and request.url.path.startswith("/api/v2/"):
        detail = exc.detail
        if isinstance(detail, dict) and detail.get("success") is not None:
            # Already an ApiResponse dict — return as-is
            return JSONResponse(status_code=exc.status_code, content=detail)
        # String detail — wrap in ApiResponse envelope
        return JSONResponse(
            status_code=exc.status_code,
            content=_V2ApiResponse(success=False, error=str(detail)).model_dump(),
        )
    # Fall through to default handler for non-HTTP exceptions
    raise exc


# ── Routers ──────────────────────────────────────────────────────────────

# V2 router (existing)
from unionbank.entrypoints.api.v2 import router as v2_router

app.include_router(v2_router)

# V1 route modules (extracted from the monolithic main.py)
from unionbank.entrypoints.api.routes.auth import router as auth_router
from unionbank.entrypoints.api.routes.accounts import router as accounts_router
from unionbank.entrypoints.api.routes.savings import router as savings_router
from unionbank.entrypoints.api.routes.admin import router as admin_router
from unionbank.entrypoints.api.routes.health import router as health_router
from unionbank.entrypoints.api.routes.totp import router as totp_router

app.include_router(auth_router)
app.include_router(accounts_router)
app.include_router(savings_router)
app.include_router(admin_router)
app.include_router(health_router)
app.include_router(totp_router)


# ── Entry point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    logger.info("Union Bank API starting — docs=/docs openapi=/openapi.json metrics=/metrics health=/api/health")

    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True, access_log=True)
