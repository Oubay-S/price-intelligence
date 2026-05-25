"""Session use-cases for /auth/login, /auth/refresh, /auth/logout.

Pure business logic. Routers parse requests, call into here, translate
the raised exceptions into HTTP status codes. Persistence is delegated
to the repositories; nothing here knows what a SQL row looks like.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from psycopg2.extensions import connection as PgConnection

from app.config import settings
from app.models.user import TokenPair
from app.repositories import (
    audit_repo,
    refresh_token_repo,
    session_repo,
    user_repo,
)
from app.services.auth import (
    REFRESH_TOKEN_TYPE,
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
    verify_password,
)
from app.services.exceptions import (
    InvalidCredentialsError,
    RefreshTokenInvalidError,
    RefreshTokenReplayError,
    SessionRevokedError,
    UserDisabledError,
)


def login(
    conn: PgConnection,
    *,
    email: str,
    password: str,
    ip_address: str | None,
    user_agent: str | None,
) -> TokenPair:
    """Issue access + refresh tokens for an email/password pair.

    Side effects: inserts a sessions row, inserts a refresh_tokens row,
    stamps users.last_login_at, writes a ``user_login`` audit entry.
    """
    access_lifetime = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_lifetime = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    creds = user_repo.get_credentials_by_email(conn, email)
    if creds is None or not verify_password(password, creds["hashed_password"]):
        raise InvalidCredentialsError()
    if not creds["is_active"]:
        raise UserDisabledError()

    user_id = creds["id"]
    session_id = session_repo.create(
        conn,
        user_id=user_id,
        # placeholder — overwritten with hash_token(access_token) below
        placeholder_token_hash=secrets.token_hex(32),
        ip_address=ip_address,
        user_agent=user_agent,
        refresh_lifetime=refresh_lifetime,
    )

    access_token = create_access_token(
        subject=user_id,
        extra_claims={"sid": str(session_id)},
    )
    refresh_token = create_refresh_token(
        subject=user_id,
        session_id=session_id,
    )

    session_repo.update_token_hash(conn, session_id, hash_token(access_token))
    refresh_token_repo.create(
        conn,
        user_id=user_id,
        session_id=session_id,
        token_hash=hash_token(refresh_token),
        refresh_lifetime=refresh_lifetime,
    )
    user_repo.touch_last_login(conn, user_id)

    audit_repo.log(
        conn,
        user_id=user_id,
        action="user_login",
        entity_type="session",
        entity_id=str(session_id),
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int(access_lifetime.total_seconds()),
    )


def refresh(conn: PgConnection, refresh_token: str) -> TokenPair:
    """Rotate a refresh token. Single-use semantics — re-presenting the
    same token revokes the entire session (replay defence).
    """
    try:
        token_payload = decode_token(refresh_token, expected_type=REFRESH_TOKEN_TYPE)
    except TokenError as exc:
        raise RefreshTokenInvalidError() from exc

    user_id = token_payload.get("sub")
    session_id = token_payload.get("sid")
    if not user_id or not session_id:
        raise RefreshTokenInvalidError()

    presented_hash = hash_token(refresh_token)
    access_lifetime = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_lifetime = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    rt = refresh_token_repo.get_active(
        conn,
        token_hash=presented_hash,
        user_id=user_id,
        session_id=session_id,
    )
    if rt is None or rt["expires_at"] < datetime.now(timezone.utc):
        raise RefreshTokenInvalidError()

    if rt["is_used"]:
        # Replay — kill the whole session and force re-login.
        session_repo.revoke(conn, session_id)
        audit_repo.log(
            conn,
            user_id=user_id,
            action="token_revoke",
            entity_type="session",
            entity_id=session_id,
            metadata={"reason": "refresh_token_replay"},
        )
        raise RefreshTokenReplayError()

    sess = session_repo.get_revoke_status(conn, session_id)
    if sess is None or sess["is_revoked"]:
        raise SessionRevokedError()

    refresh_token_repo.mark_used(conn, rt["id"])

    new_access = create_access_token(
        subject=user_id,
        extra_claims={"sid": session_id},
    )
    new_refresh = create_refresh_token(
        subject=user_id,
        session_id=session_id,
    )

    session_repo.update_token_hash_and_expiry(
        conn, session_id, hash_token(new_access), refresh_lifetime
    )
    refresh_token_repo.create(
        conn,
        user_id=user_id,
        session_id=session_id,
        token_hash=hash_token(new_refresh),
        refresh_lifetime=refresh_lifetime,
    )

    return TokenPair(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=int(access_lifetime.total_seconds()),
    )


def logout(
    conn: PgConnection,
    *,
    user_id: Any,
    session_id: Any,
    ip_address: str | None,
    user_agent: str | None,
) -> None:
    """Revoke the session and mark every still-live refresh token used."""
    session_repo.revoke(conn, session_id)
    refresh_token_repo.revoke_all_active_for_session(conn, session_id)
    audit_repo.log(
        conn,
        user_id=user_id,
        action="user_logout",
        entity_type="session",
        entity_id=str(session_id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
