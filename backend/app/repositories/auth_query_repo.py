"""Read-only joins used by the auth dependencies.

Both ``get_current_user`` (HTTP) and ``authenticate_ws_token``
(WebSocket) need the same sessions+users row but project different
columns. One repo query covers both — caller picks what to read off
the dict, and decides what to do with revoked/disabled rows.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg2.extensions import connection as PgConnection
from psycopg2.extras import RealDictCursor


def get_session_with_user(
    conn: PgConnection,
    *,
    session_id: UUID | str,
    user_id: UUID | str,
) -> dict[str, Any] | None:
    """Return the joined session+user row, or None if it doesn't exist.

    Returns every public ``users`` column (no hashed_password), plus
    ``session_id``, ``session_revoked``, ``session_expires_at``. Caller
    is expected to check ``session_revoked`` / ``is_active`` and convert
    those into HTTP 401 / 403 (or WebSocket close codes) themselves —
    the repo layer is HTTP-agnostic.
    """
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
            (str(session_id), str(user_id)),
        )
        return cur.fetchone()
