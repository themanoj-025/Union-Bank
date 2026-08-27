"""Auth routes: login, register, admin login, refresh, TOTP 2FA.

Extracted from main.py to reduce file size and improve maintainability.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

from unionbank.entrypoints.api.common import (
    create_token_pair,
    get_current_admin,
    revoke_refresh_token,
    verify_refresh_token,
)
from unionbank.utils import (
    hash_password,
    validate_email,
    validate_name,
    validate_password,
    validate_phone,
)
from unionbank.utils.logger import logger

router = APIRouter(tags=["Auth"])


# ── Request/Response Models ──────────────────────────────────────────────


class LoginRequest(BaseModel):
    account_number: str = Field(..., description="10-digit account number")
    password: str = Field(..., min_length=1, description="Account password")


class RegisterRequest(BaseModel):
    name: str = Field(..., description="Full name (2-50 chars, letters/spaces only)")
    age: int = Field(..., ge=18, le=120, description="Age (18-120)")
    gender: str = Field(..., description="Gender")
    mobile: str = Field(..., description="10-digit mobile number starting with 6-9")
    email: str = Field(..., description="Valid email address")
    password: str = Field(..., min_length=8, description="Password: min 8 chars, upper+lower+digit")
    confirm_password: str = Field(..., description="Must match password")


class AdminLoginRequest(BaseModel):
    username: str = Field(..., description="Admin username")
    password: str = Field(..., min_length=1, description="Admin password")
    totp_code: str | None = Field(None, description="6-digit TOTP code (if 2FA enabled)")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    expires_in: int | None = None


class MessageResponse(BaseModel):
    message: str


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token from previous login")


# ── Auth Endpoints ────────────────────────────────────────────────────────


def _get_limiter():
    from unionbank.entrypoints.api.main import limiter
    return limiter


@router.post("/api/auth/login", response_model=TokenResponse, deprecated=True)
def customer_login(request: Request, req: LoginRequest):
    """Authenticate a customer and return a JWT access + refresh token pair."""
    from unionbank.infrastructure.container import get_container
    from unionbank.utils.cookie_auth import set_auth_cookies

    c = get_container()
    auth_result = c.auth_service().customer_login(req.account_number, req.password)
    if not auth_result.success:
        if "locked" in auth_result.message.lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=auth_result.message
            )
        if "not found" in auth_result.message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=auth_result.message)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=auth_result.message)

    tokens = create_token_pair(subject=req.account_number, role="customer")
    response = Response(
        content=TokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            role="customer",
            expires_in=tokens["expires_in"],
        ).model_dump_json(),
        media_type="application/json",
    )
    response.headers["Sunset"] = "Sat, 31 Jan 2027 23:59:59 GMT"
    response.headers["Deprecation"] = "true"
    set_auth_cookies(
        response=response,
        request=request,
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        role="customer",
    )
    return response


@router.post("/api/auth/register", response_model=MessageResponse)
def customer_register(request: Request, req: RegisterRequest):
    """Register a new customer account."""
    if not validate_name(req.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name must be 2-50 characters (letters and spaces only).",
        )
    if not validate_phone(req.mobile):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid mobile number. Must be 10 digits starting with 6-9.",
        )
    if not validate_email(req.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format.",
        )
    valid_pwd, pwd_msg = validate_password(req.password)
    if not valid_pwd:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=pwd_msg)
    if req.password != req.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match."
        )

    from unionbank.infrastructure.container import get_container

    c = get_container()
    result = c.auth_service().customer_register(
        name=req.name,
        age=req.age,
        gender=req.gender,
        mobile=req.mobile,
        email=req.email,
        password=req.password,
    )
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=result.message
        )
    return MessageResponse(message=result.message)


@router.post("/api/auth/admin-login", response_model=TokenResponse)
def admin_login(request: Request, req: AdminLoginRequest):
    """Authenticate as admin and return a JWT access + refresh token pair."""
    from unionbank.infrastructure.container import get_container
    from unionbank.utils.cookie_auth import set_auth_cookies

    c = get_container()
    auth_result = c.auth_service().admin_login(req.username, req.password)
    if not auth_result.success:
        if "locked" in auth_result.message.lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=auth_result.message
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=auth_result.message
        )

    # Check TOTP 2FA if enabled
    admin_user = c.admin_repo().get_by_username(req.username)
    if admin_user and admin_user.totp_enabled:
        if not req.totp_code:
            raise HTTPException(
                status_code=status.HTTP_428_PRECONDITION_REQUIRED,
                detail="Two-factor authentication is enabled. Please provide your TOTP code.",
            )
        import pyotp

        totp = pyotp.TOTP(admin_user.totp_secret)
        if not totp.verify(req.totp_code, valid_window=1):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid TOTP code."
            )

    tokens = create_token_pair(subject=req.username, role="admin")
    response = Response(
        content=TokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            role="admin",
            expires_in=tokens["expires_in"],
        ).model_dump_json(),
        media_type="application/json",
    )
    set_auth_cookies(
        response=response,
        request=request,
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        role="admin",
    )
    return response


@router.post("/api/auth/refresh", response_model=TokenResponse)
def refresh_token(request: Request, req: RefreshRequest | None = None) -> dict:
    """Refresh an access token using a valid refresh token."""
    refresh_token_value = None

    # Try cookie first, then request body
    from unionbank.utils.cookie_auth import get_token_from_cookies

    refresh_token_value = get_token_from_cookies(request, "ub_refresh_token")
    if not refresh_token_value and req:
        refresh_token_value = req.refresh_token

    if not refresh_token_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required (cookie or request body).",
        )

    payload = verify_refresh_token(refresh_token_value)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token."
        )

    sub = payload.get("sub", "")
    role = payload.get("role", "customer")

    # Handle both formats: "username" and "account:token_id"
    if ":" in sub:
        account_number, raw_token_id = sub.rsplit(":", 1)
    else:
        account_number = sub
        raw_token_id = ""

    # Revoke the old refresh token (one-time use)
    if raw_token_id:
        revoke_refresh_token(raw_token_id)

    # Create new token pair
    tokens = create_token_pair(subject=account_number, role=role)

    from unionbank.utils.cookie_auth import set_auth_cookies

    response = Response(
        content=TokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            role=role,
            expires_in=tokens["expires_in"],
        ).model_dump_json(),
        media_type="application/json",
    )
    set_auth_cookies(
        response=response,
        request=request,
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        role=role,
    )
    return response


# ── TOTP 2FA Endpoints ───────────────────────────────────────────────────


class TOTPSetupResponse(BaseModel):
    secret: str
    qr_uri: str
    manual: str


class TOTPVerifyRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6, description="6-digit TOTP code")


class TOTPStatusResponse(BaseModel):
    enabled: bool


@router.get("/api/admin/2fa/status", response_model=TOTPStatusResponse)
def admin_totp_status(request: Request, admin: dict = Depends(get_current_admin)):
    """Check if 2FA is enabled for the current admin."""
    username = admin.get("username")
    from unionbank.infrastructure.container import get_container

    c = get_container()
    admin_user = c.admin_repo().get_by_username(username)
    return TOTPStatusResponse(enabled=bool(admin_user and admin_user.totp_enabled))


@router.get("/api/admin/2fa/setup", response_model=TOTPSetupResponse)
def admin_totp_setup(request: Request, admin: dict = Depends(get_current_admin)) -> dict:
    """Generate a new TOTP secret and provisioning URI for the admin user."""
    import pyotp

    username = admin.get("username")
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=username, issuer_name="Union Bank Admin"
    )

    from unionbank.infrastructure.container import get_container

    c = get_container()
    admin_user = c.admin_repo().get_by_username(username)
    if admin_user:
        c.admin_repo().update_totp(username, secret, False)
        c.admin_repo().commit()

    return TOTPSetupResponse(
        secret=secret,
        qr_uri=provisioning_uri,
        manual=f"otpauth://totp/Union%20Bank%20Admin:{username}?secret={secret}&issuer=Union%20Bank%20Admin",
    )


@router.post("/api/admin/2fa/verify", response_model=MessageResponse)
def admin_totp_verify(
    request: Request,
    req: TOTPVerifyRequest,
    admin: dict = Depends(get_current_admin),
) -> dict:
    """Verify a TOTP code to enable 2FA for the admin account."""
    import pyotp

    username = admin.get("username")
    from unionbank.infrastructure.container import get_container

    c = get_container()
    admin_user = c.admin_repo().get_by_username(username)
    if not admin_user or not admin_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No TOTP secret generated. Call GET /api/admin/2fa/setup first.",
        )

    totp = pyotp.TOTP(admin_user.totp_secret)
    if not totp.verify(req.code, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TOTP code. Please try again.",
        )

    c.admin_repo().update_totp(username, admin_user.totp_secret, True)
    c.admin_repo().commit()
    return MessageResponse(message="Two-factor authentication enabled successfully.")


@router.post("/api/admin/2fa/disable", response_model=MessageResponse)
def admin_totp_disable(
    request: Request,
    req: TOTPVerifyRequest,
    admin: dict = Depends(get_current_admin),
) -> dict:
    """Disable 2FA for the admin account (requires current TOTP code)."""
    import pyotp

    username = admin.get("username")
    from unionbank.infrastructure.container import get_container

    c = get_container()
    admin_user = c.admin_repo().get_by_username(username)
    if not admin_user or not admin_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="2FA is not enabled."
        )

    totp = pyotp.TOTP(admin_user.totp_secret)
    if not totp.verify(req.code, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid TOTP code."
        )

    c.admin_repo().update_totp(username, None, False)
    c.admin_repo().commit()
    return MessageResponse(message="Two-factor authentication disabled.")
