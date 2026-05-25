"""Auth + request-scope dependencies.

`get_current_user` is the canonical FastAPI dependency for protected
routes. It validates the bearer JWT and looks up the matching session
via ``auth_query_repo`` — middleware does not touch the database
directly. The repo returns the joined session+user row; this module
just enforces the access rules (token shape, session not revoked,
user active) and translates the outcome into HTTP responses or
WebSocket close codes.

`limiter` is the shared slowapi `Limiter` instance. Routers decorate
sensitive endpoints with it (e.g. login, register); `main.py`
registers the 429 exception handler at startup.
"""

from __future__ import annotations

import hmac
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from psycopg2.extensions import connection as PgConnection
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings
from app.database import get_db
from app.repositories import auth_query_repo
from app.services.auth import (
    ACCESS_TOKEN_TYPE,
    TokenError,
    TokenExpiredError,
    decode_token,
)


# In-memory limiter — fine for a single backend process. If we ever scale
# the FastAPI service horizontally, swap the storage URI to Redis (already
# in env: settings.REDIS_URL) so limits are shared across replicas.
limiter = Limiter(key_func=get_remote_address)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=True)


_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def _decode_access_token_or_raise_http(token: str) -> dict[str, Any]:
    """Shared JWT decode + shape check for HTTP-side auth."""
    try:
        payload = decode_token(token, expected_type=ACCESS_TOKEN_TYPE)
    except TokenExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except TokenError as exc:
        raise _CREDENTIALS_EXC from exc

    sub = payload.get("sub")
    sid = payload.get("sid")
    if not sub or not sid:
        raise _CREDENTIALS_EXC
    try:
        UUID(sub)
        UUID(sid)
    except (ValueError, TypeError) as exc:
        raise _CREDENTIALS_EXC from exc
    return payload


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    conn: Annotated[PgConnection, Depends(get_db)],
) -> dict[str, Any]:
    """Decode a bearer access token and return the live user record.

    Returns a dict with every public ``users`` column plus a
    ``session_id`` UUID for downstream use (e.g. /auth/logout, audit
    logging).
    """
    payload = _decode_access_token_or_raise_http(token)
    row = auth_query_repo.get_session_with_user(
        conn, session_id=payload["sid"], user_id=payload["sub"]
    )

    if row is None:
        raise _CREDENTIALS_EXC
    if row["session_revoked"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not row["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User disabled",
        )

    return {
        "id": row["id"],
        "email": row["email"],
        "full_name": row["full_name"],
        "role": row["role"],
        "is_active": row["is_active"],
        "email_verified": row["email_verified"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "last_login_at": row["last_login_at"],
        "session_id": row["session_id"],
    }


def require_admin(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> dict[str, Any]:
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin only",
        )
    return current_user


class WebSocketAuthError(Exception):
    """Raised when a WebSocket handshake's bearer token can't be validated.

    Carries a 4xxx close code so the route handler can forward it to the
    client via ``websocket.close(code=...)``. The codes follow the custom
    application-private range (4000-4999) defined by RFC 6455.
    """

    def __init__(self, code: int, reason: str) -> None:
        super().__init__(reason)
        self.code = code
        self.reason = reason


def authenticate_ws_token(
    token: str | None,
    expected_user_id: str,
    conn: PgConnection,
) -> dict[str, Any]:
    """Validate a WebSocket query-param JWT against the live session row.

    Mirrors the checks ``get_current_user`` performs for HTTP, but raises
    :class:`WebSocketAuthError` (with a WS close code) instead of
    :class:`HTTPException`. The token is expected as a query parameter
    because browsers can't set arbitrary headers on the WS handshake.

    Returns ``{user_id, session_id}`` on success.
    """
    if not token:
        raise WebSocketAuthError(4401, "missing token")

    try:
        payload = decode_token(token, expected_type=ACCESS_TOKEN_TYPE)
    except TokenExpiredError as exc:
        raise WebSocketAuthError(4401, "token expired") from exc
    except TokenError as exc:
        raise WebSocketAuthError(4401, "invalid token") from exc

    sub = payload.get("sub")
    sid = payload.get("sid")
    if not sub or not sid:
        raise WebSocketAuthError(4401, "malformed token")

    try:
        user_uuid = UUID(sub)
        session_uuid = UUID(sid)
    except (ValueError, TypeError) as exc:
        raise WebSocketAuthError(4401, "malformed token") from exc

    # Subject must match the channel being subscribed to: a JWT for user A
    # cannot subscribe to /ws/alerts/{B}.
    if str(user_uuid) != expected_user_id:
        raise WebSocketAuthError(4403, "token does not match channel user_id")

    row = auth_query_repo.get_session_with_user(
        conn, session_id=session_uuid, user_id=user_uuid
    )
    if row is None:
        raise WebSocketAuthError(4401, "session not found")
    if row["session_revoked"]:
        raise WebSocketAuthError(4401, "session revoked")
    if not row["is_active"]:
        raise WebSocketAuthError(4403, "user disabled")

    return {
        "user_id": str(row["id"]),
        "session_id": str(row["session_id"]),
    }


def require_internal_key(
    x_internal_key: Annotated[str | None, Header(alias="X-Internal-Key")] = None,
) -> None:
    """Gate for service-to-service `/internal/*` endpoints (e.g. NiFi → FastAPI).

    Compares the request's `X-Internal-Key` header against
    `settings.INTERNAL_API_KEY` in constant time.

    If `INTERNAL_API_KEY` is empty (dev default), auth is disabled and
    every request passes. To enforce, set a non-empty value in `.env`
    and ensure NiFi's InvokeHTTP processor sends the same value as
    `X-Internal-Key`.
    """
    expected = settings.INTERNAL_API_KEY
    if not expected:
        return  # dev mode — auth disabled

    if x_internal_key is None or not hmac.compare_digest(
        x_internal_key, expected
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing internal API key",
        )
