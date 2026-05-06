"""Auth endpoints: register, login, refresh, logout, me.

Token model
-----------
* Access tokens carry `sub` (user UUID), `sid` (session UUID), `type=access`.
  Lifetime: `ACCESS_TOKEN_EXPIRE_MINUTES`.
* Refresh tokens carry the same `sid` plus `type=refresh`.
  Lifetime: 30 days. Single-use — `is_used` flips on first redeem and any
  reuse attempt revokes the entire session (replay defence).

Sessions row state
------------------
On login we insert a sessions row, then mint tokens that embed its UUID.
`token_hash` is updated to the SHA-256 of the latest access token after
each issuance. On refresh we rotate both tokens and update the row in
place. On logout we set `is_revoked=TRUE` and mark all the session's
refresh tokens used.
"""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from psycopg2 import IntegrityError
from psycopg2.extensions import connection as PgConnection
from psycopg2.extras import RealDictCursor

from app.config import settings
from app.database import get_db
from app.middleware.core import get_current_user, limiter
from app.models.user import (
    RefreshRequest,
    TokenPair,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services.auth import (
    REFRESH_TOKEN_TYPE,
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _client_ip(request: Request) -> str | None:
    if request.client is None:
        return None
    return request.client.host


def _user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


def _audit(
    cur,
    *,
    user_id: Any,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    request: Request | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    cur.execute(
        """
        INSERT INTO audit_logs
            (user_id, action, entity_type, entity_id, ip_address, user_agent, metadata)
        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
        """,
        (
            str(user_id) if user_id is not None else None,
            action,
            entity_type,
            entity_id,
            _client_ip(request) if request else None,
            _user_agent(request) if request else None,
            json.dumps(metadata) if metadata else None,
        ),
    )


# ---------------------------------------------------------------------------
# /register
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(settings.RATE_LIMIT_REGISTER)
def register(
    request: Request,
    payload: UserRegister,
    conn: Annotated[PgConnection, Depends(get_db)],
) -> UserResponse:
    hashed = hash_password(payload.password)

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        try:
            cur.execute(
                """
                INSERT INTO users (email, hashed_password, full_name)
                VALUES (%s, %s, %s)
                RETURNING id, email, full_name, role, is_active, email_verified,
                          created_at, updated_at, last_login_at
                """,
                (str(payload.email), hashed, payload.full_name),
            )
            user = cur.fetchone()
        except IntegrityError as exc:
            conn.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            ) from exc

        _audit(
            cur,
            user_id=user["id"],
            action="user_register",
            entity_type="user",
            entity_id=str(user["id"]),
            request=request,
        )

    return UserResponse(**user)


# ---------------------------------------------------------------------------
# /login
# ---------------------------------------------------------------------------

def _issue_session_tokens(
    request: Request,
    conn: PgConnection,
    email: str,
    password: str,
) -> TokenPair:
    """Shared login path used by both /auth/login (JSON) and /auth/token (form)."""
    access_lifetime = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_lifetime = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT id, hashed_password, is_active FROM users WHERE email = %s",
            (email,),
        )
        user = cur.fetchone()

        if user is None or not verify_password(password, user["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        if not user["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User disabled",
            )

        cur.execute(
            """
            INSERT INTO sessions (user_id, token_hash, ip_address, user_agent, expires_at)
            VALUES (%s, %s, %s, %s, NOW() + %s)
            RETURNING id
            """,
            (
                str(user["id"]),
                secrets.token_hex(32),
                _client_ip(request),
                _user_agent(request),
                refresh_lifetime,
            ),
        )
        session_id = cur.fetchone()["id"]

        access_token = create_access_token(
            subject=user["id"],
            extra_claims={"sid": str(session_id)},
        )
        refresh_token = create_refresh_token(
            subject=user["id"],
            session_id=session_id,
        )

        cur.execute(
            "UPDATE sessions SET token_hash = %s WHERE id = %s",
            (hash_token(access_token), str(session_id)),
        )
        cur.execute(
            """
            INSERT INTO refresh_tokens (user_id, session_id, token_hash, expires_at)
            VALUES (%s, %s, %s, NOW() + %s)
            """,
            (
                str(user["id"]),
                str(session_id),
                hash_token(refresh_token),
                refresh_lifetime,
            ),
        )
        cur.execute(
            "UPDATE users SET last_login_at = NOW() WHERE id = %s",
            (str(user["id"]),),
        )

        _audit(
            cur,
            user_id=user["id"],
            action="user_login",
            entity_type="session",
            entity_id=str(session_id),
            request=request,
        )

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int(access_lifetime.total_seconds()),
    )


@router.post("/login", response_model=TokenPair)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
def login(
    request: Request,
    payload: UserLogin,
    conn: Annotated[PgConnection, Depends(get_db)],
) -> TokenPair:
    return _issue_session_tokens(request, conn, str(payload.email), payload.password)


@router.post("/token", response_model=TokenPair)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
def login_oauth2_form(
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    conn: Annotated[PgConnection, Depends(get_db)],
) -> TokenPair:
    """OAuth2 password-flow variant. The `username` field is the user's email.

    Exists so Swagger UI's "Authorize" button (which posts an
    `application/x-www-form-urlencoded` body to `tokenUrl`) works end to end.
    `/auth/login` remains the canonical JSON endpoint for the SPA.
    """
    return _issue_session_tokens(request, conn, form.username, form.password)


# ---------------------------------------------------------------------------
# /refresh
# ---------------------------------------------------------------------------

@router.post("/refresh", response_model=TokenPair)
def refresh(
    payload: RefreshRequest,
    conn: Annotated[PgConnection, Depends(get_db)],
) -> TokenPair:
    try:
        token_payload = decode_token(payload.refresh_token, expected_type=REFRESH_TOKEN_TYPE)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from exc

    user_id = token_payload.get("sub")
    session_id = token_payload.get("sid")
    if not user_id or not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    presented_hash = hash_token(payload.refresh_token)
    access_lifetime = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_lifetime = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, is_used, expires_at
            FROM refresh_tokens
            WHERE token_hash = %s AND user_id = %s AND session_id = %s
            """,
            (presented_hash, user_id, session_id),
        )
        rt = cur.fetchone()

        if rt is None or rt["expires_at"] < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        if rt["is_used"]:
            # Replay attempt — kill the whole session and force re-login.
            cur.execute(
                "UPDATE sessions SET is_revoked = TRUE WHERE id = %s",
                (session_id,),
            )
            _audit(
                cur,
                user_id=user_id,
                action="token_revoke",
                entity_type="session",
                entity_id=session_id,
                metadata={"reason": "refresh_token_replay"},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token reuse detected; session revoked",
            )

        cur.execute(
            "SELECT is_revoked FROM sessions WHERE id = %s",
            (session_id,),
        )
        sess = cur.fetchone()
        if sess is None or sess["is_revoked"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session revoked",
            )

        cur.execute(
            "UPDATE refresh_tokens SET is_used = TRUE WHERE id = %s",
            (rt["id"],),
        )

        new_access = create_access_token(
            subject=user_id,
            extra_claims={"sid": session_id},
        )
        new_refresh = create_refresh_token(
            subject=user_id,
            session_id=session_id,
        )

        cur.execute(
            """
            UPDATE sessions
            SET token_hash = %s,
                expires_at = NOW() + %s
            WHERE id = %s
            """,
            (hash_token(new_access), refresh_lifetime, session_id),
        )
        cur.execute(
            """
            INSERT INTO refresh_tokens (user_id, session_id, token_hash, expires_at)
            VALUES (%s, %s, %s, NOW() + %s)
            """,
            (user_id, session_id, hash_token(new_refresh), refresh_lifetime),
        )

    return TokenPair(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=int(access_lifetime.total_seconds()),
    )


# ---------------------------------------------------------------------------
# /logout
# ---------------------------------------------------------------------------

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    conn: Annotated[PgConnection, Depends(get_db)],
) -> None:
    session_id = current_user["session_id"]
    user_id = current_user["id"]

    with conn.cursor() as cur:
        cur.execute(
            "UPDATE sessions SET is_revoked = TRUE WHERE id = %s",
            (str(session_id),),
        )
        cur.execute(
            "UPDATE refresh_tokens SET is_used = TRUE WHERE session_id = %s AND is_used = FALSE",
            (str(session_id),),
        )
        cur.execute(
            """
            INSERT INTO audit_logs
                (user_id, action, entity_type, entity_id, ip_address, user_agent)
            VALUES (%s, 'user_logout', 'session', %s, %s, %s)
            """,
            (
                str(user_id),
                str(session_id),
                _client_ip(request),
                _user_agent(request),
            ),
        )


# ---------------------------------------------------------------------------
# /me
# ---------------------------------------------------------------------------

@router.get("/me", response_model=UserResponse)
def me(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> UserResponse:
    return UserResponse(**current_user)
