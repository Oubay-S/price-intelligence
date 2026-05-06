"""Auth + request-scope dependencies.

`get_current_user` is the canonical FastAPI dependency for protected routes.
It validates the bearer JWT, confirms the matching session row is still
live, and returns the user (plus session_id, used by /auth/logout).

`limiter` is the shared slowapi `Limiter` instance. It's exposed here so
routers can decorate sensitive endpoints (e.g. login, register) and
`main.py` can register the exception handler at startup.
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from psycopg2.extensions import connection as PgConnection
from psycopg2.extras import RealDictCursor
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
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

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=True)


_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    conn: Annotated[PgConnection, Depends(get_db)],
) -> dict[str, Any]:
    """Decode a bearer access token and return the live user record.

    Returns a dict with all `users` columns (minus `hashed_password`) plus a
    `session_id` UUID for downstream use (e.g. /auth/logout, audit logging).
    """
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
        user_uuid = UUID(sub)
        session_uuid = UUID(sid)
    except (ValueError, TypeError) as exc:
        raise _CREDENTIALS_EXC from exc

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                u.id, u.email, u.full_name, u.role, u.is_active, u.email_verified,
                u.created_at, u.updated_at, u.last_login_at,
                s.id           AS session_id,
                s.is_revoked   AS session_revoked,
                s.expires_at   AS session_expires_at
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.id = %s AND u.id = %s
            """,
            (str(session_uuid), str(user_uuid)),
        )
        row = cur.fetchone()

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
