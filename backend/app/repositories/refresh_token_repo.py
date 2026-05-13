"""refresh_tokens table operations used by /auth/login, /refresh, /logout."""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from psycopg2.extensions import connection as PgConnection
from psycopg2.extras import RealDictCursor


def create(
    conn: PgConnection,
    *,
    user_id: Any,
    session_id: Any,
    token_hash: str,
    refresh_lifetime: timedelta,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO refresh_tokens (user_id, session_id, token_hash, expires_at)
            VALUES (%s, %s, %s, NOW() + %s)
            """,
            (str(user_id), str(session_id), token_hash, refresh_lifetime),
        )


def get_active(
    conn: PgConnection,
    *,
    token_hash: str,
    user_id: Any,
    session_id: Any,
) -> dict[str, Any] | None:
    """Return ``(id, is_used, expires_at)`` for the refresh-flow lookup,
    or None if no row matches the (token_hash, user_id, session_id) tuple."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, is_used, expires_at
              FROM refresh_tokens
             WHERE token_hash = %s
               AND user_id = %s
               AND session_id = %s
            """,
            (token_hash, str(user_id), str(session_id)),
        )
        return cur.fetchone()


def mark_used(conn: PgConnection, token_id: Any) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE refresh_tokens SET is_used = TRUE WHERE id = %s",
            (str(token_id),),
        )


def revoke_all_active_for_session(
    conn: PgConnection, session_id: Any
) -> None:
    """Used by /auth/logout — kills every still-live refresh token for a session."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE refresh_tokens
               SET is_used = TRUE
             WHERE session_id = %s
               AND is_used = FALSE
            """,
            (str(session_id),),
        )


def revoke_all_active_for_user(conn: PgConnection, user_id: Any) -> None:
    """Mark every live refresh token for a user as used. Pair with
    ``session_repo.revoke_all_for_user`` on password reset."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE refresh_tokens
               SET is_used = TRUE
             WHERE user_id = %s
               AND is_used = FALSE
            """,
            (str(user_id),),
        )
