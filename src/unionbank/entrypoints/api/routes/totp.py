"""TOTP 2FA routes: setup, verify, disable, status.

Extracted from main.py to reduce file size and improve maintainability.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from unionbank.entrypoints.api.common import get_current_admin

router = APIRouter(tags=["2FA"])


# ── Request/Response Models ──────────────────────────────────────────────


class TOTPSetupResponse(BaseModel):
    secret: str
    qr_uri: str
    manual: str


class TOTPVerifyRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6, description="6-digit TOTP code")


class TOTPStatusResponse(BaseModel):
    enabled: bool


class MessageResponse(BaseModel):
    message: str
    status: str = "success"


# ── Routes ───────────────────────────────────────────────────────────────


@router.get("/api/admin/2fa/status", response_model=TOTPStatusResponse)
def admin_totp_status(request: Request, admin: dict = Depends(get_current_admin)) -> Response:
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
        name=username,
        issuer_name="Union Bank Admin",
    )

    # Store the secret temporarily (not enabled until verified)
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
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled.",
        )

    totp = pyotp.TOTP(admin_user.totp_secret)
    if not totp.verify(req.code, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TOTP code.",
        )

    c.admin_repo().update_totp(username, None, False)
    c.admin_repo().commit()

    return MessageResponse(message="Two-factor authentication disabled.")
