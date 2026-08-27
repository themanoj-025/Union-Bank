"""
V2 API — Assembled router.

This package replaces the monolithic ``v2.py`` (1363 lines) with focused
route modules.  The ``router`` object exported here is identical to the
one previously defined in ``v2.py`` and is imported by ``main.py``.
"""

from __future__ import annotations

from fastapi import APIRouter

from unionbank.entrypoints.api.v2.accounts import router as accounts_router
from unionbank.entrypoints.api.v2.admin import router as admin_router
from unionbank.entrypoints.api.v2.auth import router as auth_router
from unionbank.entrypoints.api.v2.helpers import (
    v2_generic_exception_handler,
    v2_http_exception_handler,
)
from unionbank.entrypoints.api.v2.loans import router as loans_router
from unionbank.entrypoints.api.v2.misc import router as misc_router
from unionbank.entrypoints.api.v2.savings import router as savings_router
from unionbank.entrypoints.api.v2.statements import router as statements_router

# The composite router — same prefix as the old monolithic v2.router
router = APIRouter(prefix="/api/v2")

router.include_router(auth_router)
router.include_router(accounts_router)
router.include_router(statements_router)
router.include_router(savings_router)
router.include_router(loans_router)
router.include_router(admin_router)
router.include_router(misc_router)

__all__ = [
    "router",
    "v2_http_exception_handler",
    "v2_generic_exception_handler",
]
