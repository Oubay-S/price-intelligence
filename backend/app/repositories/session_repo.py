"""sessions table operations used by /auth/login, /refresh, /logout."""
from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

from psycopg2.extensions import connection as PgConnection
from psycopg2.extras import RealDictCursor


def create(
    conn: PgConnection,
    *,
    user_id: Any,
    placeholder_token_hash: str,
    ip_address: str | None,
    user_agent: str | None,
    refresh_lifetime: timedelta,
) -> UUID:
    """Insert a new session row and return its UUID. The token_hash is
    a placeholder — the caller updates it via ``update_token_hash`` once
    the access token has actually been minted."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO sessions
                (user_id, token_hash, ip_address, user_agent, expires_at)
            VALUES (%s, %s, %s, %s, NOW() + %s)
            RETURNING id
            """,
            (
                str(user_id),
                placeholder_token_hash,
                ip_address,
                user_agent,
                refresh_lifetime,
            ),
        )
        return cur.fetchone()["id"]


def update_token_hash(
    conn: PgConnection, session_id: Any, token_hash: str
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE sessions SET token_hash = %s WHERE id = %s",
            (token_hash, str(session_id)),
        )


def update_token_hash_and_expiry(
    conn: PgConnection,
    session_id: Any,
    token_hash: str,
    refresh_lifetime: timedelta,
) -> None:
    """Used by /auth/refresh — rotates token hash and bumps expires_at."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE sessions
               SET token_hash = %s,
                   expires_at = NOW() + %s
             WHERE id = %s
            """,
            (token_hash, refresh_lifetime, str(session_id)),
        )


def get_revoke_status(
    conn: PgConnection, session_id: Any
) -> dict[str, Any] | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT is_revoked FROM sessions WHERE id = %s",
            (str(session_id),),
        )
        return cur.fetchone()


def revoke(conn: PgConnection, session_id: Any) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE sessions SET is_revoked = TRUE WHERE id = %s",
            (str(session_id),),
        )


def revoke_all_for_user(conn: PgConnection, user_id: Any) -> int:
    """Revoke every active session for a user. Returns the number of rows
    affected. Used by password-reset to force re-login on every device."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE sessions
               SET is_revoked = TRUE
             WHERE user_id = %s
               AND is_revoked = FALSE
            """,
            (str(user_id),),
        )
        return cur.rowcount
