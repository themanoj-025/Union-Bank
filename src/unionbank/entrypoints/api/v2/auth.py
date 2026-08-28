"""V2 API — Authentication endpoints (login, register, admin-login, refresh)."""

from __future__ import annotations

import jwt
from fastapi import Depends, Request, Response, status

from unionbank.entrypoints.api.common import (
    create_token_pair,
    get_current_admin,
    get_current_customer,
    revoke_refresh_token,
    verify_refresh_token,
)
from unionbank.entrypoints.api.models import (
    AdminLoginRequest,
    ApiResponse,
    ErrorCode,
    LoginRequest,
    MessageData,
    RefreshRequest,
    RegisterRequest,
    TokenData,
)
from unionbank.entrypoints.api.v2.helpers import _err, _get_container, _ok

router = __import__("fastapi").APIRouter()


@router.post("/auth/login", response_model=ApiResponse[TokenData])
def v2_customer_login(req: LoginRequest, request: Request, response: Response) -> ApiResponse:
    """
    Authenticate a customer and return a JWT access + refresh token pair.

    Tokens are set as httpOnly cookies (primary) and returned in the
    response body (backward compatibility).
    """
    from unionbank.utils.cookie_auth import set_auth_cookies

    c = _get_container()
    auth_result = c.auth_service().customer_login(req.account_number, req.password)

    if not auth_result.success:
        msg = auth_result.message.lower()
        if "locked" in msg:
            _err(
                auth_result.message,
                status.HTTP_429_TOO_MANY_REQUESTS,
                ErrorCode.AUTH_ACCOUNT_LOCKED,
            )
        if "not found" in msg:
            _err(auth_result.message, status.HTTP_404_NOT_FOUND, ErrorCode.ACCOUNT_NOT_FOUND)
        _err(auth_result.message, status.HTTP_401_UNAUTHORIZED, ErrorCode.AUTH_INVALID_CREDENTIALS)

    tokens = create_token_pair(subject=req.account_number, role="customer")

    # Set httpOnly cookies — primary token storage
    set_auth_cookies(
        response=response,
        request=request,
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        role="customer",
    )

    return _ok(
        TokenData(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            role="customer",
            expires_in=tokens["expires_in"],
        )
    )


@router.post("/auth/register", response_model=ApiResponse[MessageData])
def v2_customer_register(req: RegisterRequest) -> dict[str, str]:
    """Register a new customer account."""
    from unionbank.utils import validate_email, validate_name, validate_password, validate_phone

    if not validate_name(req.name):
        _err("Name must be 2-50 characters (letters and spaces only).")
    if not validate_phone(req.mobile):
        _err("Invalid mobile number. Must be 10 digits starting with 6-9.")
    if not validate_email(req.email):
        _err("Invalid email format.")
    valid_pwd, pwd_msg = validate_password(req.password)
    if not valid_pwd:
        _err(pwd_msg)
    if req.password != req.confirm_password:
        _err("Passwords do not match.")

    c = _get_container()
    result = c.auth_service().customer_register(
        name=req.name,
        age=req.age,
        gender=req.gender,
        mobile=req.mobile,
        email=req.email,
        password=req.password,
    )
    if not result.success:
        _err(result.message)

    return _ok(MessageData(message=result.message))


@router.post("/auth/admin-login", response_model=ApiResponse[TokenData])
def v2_admin_login(req: AdminLoginRequest, request: Request, response: Response) -> ApiResponse:
    """
    Authenticate as admin and return a JWT access + refresh token pair.

    Tokens are set as httpOnly cookies (primary) and returned in the
    response body (backward compatibility).
    """
    from unionbank.utils.cookie_auth import set_auth_cookies

    c = _get_container()
    auth_result = c.auth_service().admin_login(req.username, req.password)

    if not auth_result.success:
        msg = auth_result.message.lower()
        if "locked" in msg:
            _err(auth_result.message, status.HTTP_429_TOO_MANY_REQUESTS)
        _err(auth_result.message, status.HTTP_401_UNAUTHORIZED)

    tokens = create_token_pair(subject=req.username, role="admin")

    # Set httpOnly cookies — primary token storage
    set_auth_cookies(
        response=response,
        request=request,
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        role="admin",
    )

    return _ok(
        TokenData(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            role="admin",
            expires_in=tokens["expires_in"],
        )
    )


@router.post("/auth/refresh", response_model=ApiResponse[TokenData])
def v2_refresh_token(request: Request, response: Response, req: RefreshRequest | None = None) -> ApiResponse:
    """
    Exchange a refresh token for a new access + refresh token pair.

    Accepts the refresh token from either:
    1. The request body (backward compatibility)
    2. The ub_refresh_token httpOnly cookie (new cookie-based flow)

    The previous refresh token is revoked (rotation) so it cannot be reused.
    """
    from unionbank.utils.cookie_auth import (
        get_token_from_cookies,
        set_auth_cookies,
    )
    from unionbank.utils.logger import logger

    # Get refresh token from body or cookie
    refresh_token_value = None
    if req and req.refresh_token:
        refresh_token_value = req.refresh_token
    else:
        refresh_token_value = get_token_from_cookies(request, "ub_refresh_token")

    if not refresh_token_value:
        _err("No refresh token provided.", status.HTTP_401_UNAUTHORIZED)

    result = verify_refresh_token(refresh_token_value)
    if result is None:
        _err("Invalid or expired refresh token.", status.HTTP_401_UNAUTHORIZED)

    # Revoke old refresh token (rotation)
    try:
        old_payload = jwt.decode(
            refresh_token_value,
            _get_verifying_key(),
            algorithms=["RS256", "HS256"],
            options={"verify_exp": False},
        )
        old_sub = old_payload.get("sub", "")
        if ":" in old_sub:
            _, old_token_id = old_sub.rsplit(":", 1)
            revoke_refresh_token(old_token_id)
    except (jwt.InvalidTokenError, jwt.DecodeError, ValueError, KeyError):
        logger.warning("Failed to revoke old refresh token during rotation", exc_info=True)

    tokens = create_token_pair(subject=result["account_number"], role=result["role"])

    # Set new httpOnly cookies
    set_auth_cookies(
        response=response,
        request=request,
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        role=result["role"],
    )

    return _ok(
        TokenData(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            role=result["role"],
            expires_in=tokens["expires_in"],
        )
    )
