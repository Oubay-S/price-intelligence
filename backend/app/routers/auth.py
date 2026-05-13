"""Auth endpoints: register, login, refresh, logout, me.

Routers translate HTTP <-> service calls. Login / refresh / logout
orchestration lives in ``app.services.session_service``; persistence
in ``app.repositories.*``. This module knows nothing about SQL.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from psycopg2.extensions import connection as PgConnection

from app.api_responses import (
    ERR_400,
    ERR_401,
    ERR_403,
    ERR_409,
    ERR_422,
    ERR_429,
    ERR_500,
)
from app.config import settings
from app.database import get_db
from app.middleware.core import get_current_user, limiter
from app.models.user import (
    ForgotPasswordRequest,
    MessageResponse,
    RefreshRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokenPair,
    UserLogin,
    UserRegister,
    UserResponse,
    VerifyEmailRequest,
)
from app.repositories import audit_repo, user_repo
from app.repositories.exceptions import DuplicateError
from app.services import email_flow, session_service
from app.services.auth import hash_password
from app.services.exceptions import (
    EmailAlreadyVerifiedError,
    InvalidCredentialsError,
    RefreshTokenInvalidError,
    RefreshTokenReplayError,
    SessionRevokedError,
    TokenInvalidError,
    UserDisabledError,
)

router = APIRouter()


def _client_ip(request: Request) -> str | None:
    if request.client is None:
        return None
    return request.client.host


def _user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


# ---------------------------------------------------------------------------
# /register
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    response_description="Newly-created user record.",
    responses={**ERR_409, **ERR_422, **ERR_429, **ERR_500},
)
@limiter.limit(settings.RATE_LIMIT_REGISTER)
def register(
    request: Request,
    payload: UserRegister,
    conn: Annotated[PgConnection, Depends(get_db)],
) -> UserResponse:
    """Create a user. 409 on duplicate email."""
    hashed = hash_password(payload.password)
    try:
        user = user_repo.create(
            conn,
            email=str(payload.email),
            hashed_password=hashed,
            full_name=payload.full_name,
        )
    except DuplicateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        ) from exc

    audit_repo.log(
        conn,
        user_id=user["id"],
        action="user_register",
        entity_type="user",
        entity_id=str(user["id"]),
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
    )

    # Fire-and-forget verification email. Runs on the email thread pool
    # (see app.services.email) so the response is never blocked by SMTP.
    email_flow.issue_verification_email(
        conn,
        user_id=user["id"],
        email=str(payload.email),
        full_name=payload.full_name,
    )

    return UserResponse(**user)


# ---------------------------------------------------------------------------
# /login + /token
# ---------------------------------------------------------------------------

def _login_or_raise(
    conn: PgConnection,
    *,
    request: Request,
    email: str,
    password: str,
) -> TokenPair:
    """Map session_service.login exceptions into HTTP responses."""
    try:
        return session_service.login(
            conn,
            email=email,
            password=password,
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from exc
    except UserDisabledError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User disabled",
        ) from exc


@router.post(
    "/login",
    response_model=TokenPair,
    response_description="Access + refresh token pair for the authenticated session.",
    responses={**ERR_401, **ERR_403, **ERR_422, **ERR_429, **ERR_500},
)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
def login(
    request: Request,
    payload: UserLogin,
    conn: Annotated[PgConnection, Depends(get_db)],
) -> TokenPair:
    return _login_or_raise(
        conn, request=request, email=str(payload.email), password=payload.password
    )


@router.post(
    "/token",
    response_model=TokenPair,
    response_description="Access + refresh token pair (OAuth2 form-encoded variant).",
    responses={**ERR_401, **ERR_403, **ERR_422, **ERR_429, **ERR_500},
)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
def login_oauth2_form(
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    conn: Annotated[PgConnection, Depends(get_db)],
) -> TokenPair:
    """OAuth2 password-flow variant. The `username` field is the user's email."""
    return _login_or_raise(
        conn, request=request, email=form.username, password=form.password
    )


# ---------------------------------------------------------------------------
# /refresh
# ---------------------------------------------------------------------------

@router.post(
    "/refresh",
    response_model=TokenPair,
    response_description="Rotated access + refresh token pair. Old refresh token is now invalid.",
    responses={**ERR_401, **ERR_422, **ERR_500},
)
def refresh(
    payload: RefreshRequest,
    conn: Annotated[PgConnection, Depends(get_db)],
) -> TokenPair:
    try:
        return session_service.refresh(conn, payload.refresh_token)
    except RefreshTokenReplayError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token reuse detected; session revoked",
        ) from exc
    except SessionRevokedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session revoked",
        ) from exc
    except RefreshTokenInvalidError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from exc


# ---------------------------------------------------------------------------
# /logout
# ---------------------------------------------------------------------------

@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_description="Session and all its refresh tokens revoked. No body.",
    responses={**ERR_401, **ERR_500},
)
def logout(
    request: Request,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    conn: Annotated[PgConnection, Depends(get_db)],
) -> None:
    session_service.logout(
        conn,
        user_id=current_user["id"],
        session_id=current_user["session_id"],
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
    )


# ---------------------------------------------------------------------------
# /me
# ---------------------------------------------------------------------------

@router.get(
    "/me",
    response_model=UserResponse,
    response_description="The authenticated user's own profile.",
    responses={**ERR_401, **ERR_500},
)
def me(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> UserResponse:
    return UserResponse(**current_user)


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------
#
# Two endpoints power the flow:
#
# * POST /auth/verify-email           — redeem the token from the email link.
# * POST /auth/resend-verification    — generate + send a fresh token.
#
# `/forgot-password` and `/reset-password` follow the same redeem-by-token
# pattern below.  All four are intentionally rate-limited via slowapi
# (re-uses RATE_LIMIT_REGISTER as it's the closest "expensive-side-effect
# anonymous endpoint" knob already in config).
# ---------------------------------------------------------------------------

@router.post(
    "/verify-email",
    response_model=MessageResponse,
    response_description="Email successfully verified.",
    responses={**ERR_400, **ERR_422, **ERR_429, **ERR_500},
)
@limiter.limit(settings.RATE_LIMIT_REGISTER)
def verify_email(
    request: Request,
    payload: VerifyEmailRequest,
    conn: Annotated[PgConnection, Depends(get_db)],
) -> MessageResponse:
    try:
        email_flow.verify_email_token(conn, payload.token)
    except EmailAlreadyVerifiedError:
        return MessageResponse(message="Email was already verified.")
    except TokenInvalidError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token is invalid or has expired.",
        ) from exc
    return MessageResponse(message="Email verified successfully.")


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    response_description=(
        "Always returns 200 to avoid leaking which emails exist. If the "
        "email is registered and unverified, a fresh verification message "
        "is queued for delivery."
    ),
    responses={**ERR_422, **ERR_429, **ERR_500},
)
@limiter.limit(settings.RATE_LIMIT_REGISTER)
def resend_verification(
    request: Request,
    payload: ResendVerificationRequest,
    conn: Annotated[PgConnection, Depends(get_db)],
) -> MessageResponse:
    user = user_repo.get_by_email_for_email_flow(conn, str(payload.email))
    if user is not None and user["is_active"] and not user["email_verified"]:
        email_flow.issue_verification_email(
            conn,
            user_id=user["id"],
            email=user["email"],
            full_name=user.get("full_name"),
        )
    # Same response shape whether the email was real or not — never confirm
    # / deny existence at this boundary.
    return MessageResponse(
        message="If an account exists for that email, a verification "
                "message has been sent."
    )


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------

@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    response_description=(
        "Always returns 200. If the email is registered, a reset link is "
        "queued for delivery."
    ),
    responses={**ERR_422, **ERR_429, **ERR_500},
)
@limiter.limit(settings.RATE_LIMIT_REGISTER)
def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    conn: Annotated[PgConnection, Depends(get_db)],
) -> MessageResponse:
    email_flow.issue_password_reset(conn, email=str(payload.email))
    return MessageResponse(
        message="If an account exists for that email, a password reset "
                "link has been sent."
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    response_description=(
        "Password updated; every session and refresh token for the user "
        "is revoked, so all devices must log in again."
    ),
    responses={**ERR_400, **ERR_422, **ERR_429, **ERR_500},
)
@limiter.limit(settings.RATE_LIMIT_REGISTER)
def reset_password(
    request: Request,
    payload: ResetPasswordRequest,
    conn: Annotated[PgConnection, Depends(get_db)],
) -> MessageResponse:
    try:
        email_flow.reset_password(
            conn,
            raw_token=payload.token,
            new_password=payload.new_password,
        )
    except TokenInvalidError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token is invalid or has expired.",
        ) from exc
    return MessageResponse(
        message="Password updated. Please sign in again."
    )
