"""email_verification_tokens + password_reset_tokens table operations.

Both tables follow the same shape (id, user_id, token_hash, is_used,
expires_at, created_at), so we share helpers and just parametrise the
table name. The raw token is sent to the user in the email; only the
SHA-256 hash lives in Postgres — a DB leak does not yield usable tokens.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any, Literal

from psycopg2.extensions import connection as PgConnection
from psycopg2.extras import RealDictCursor

TokenTable = Literal["email_verification_tokens", "password_reset_tokens"]


def _invalidate_active(conn: PgConnection, table: TokenTable, user_id: Any) -> None:
    """Mark every unused, unexpired token for this user as used. Called
    before issuing a fresh one so only the latest token is acceptable."""
    with conn.cursor() as cur:
        cur.execute(
            f"""
            UPDATE {table}
               SET is_used = TRUE
             WHERE user_id = %s
               AND is_used = FALSE
               AND expires_at > NOW()
            """,
            (str(user_id),),
        )


def issue(
    conn: PgConnection,
    *,
    table: TokenTable,
    user_id: Any,
    token_hash: str,
    ttl: timedelta,
) -> None:
    """Invalidate any prior live token for ``user_id`` and insert a new
    row with ``expires_at = NOW() + ttl``. The raw token is *not* stored —
    callers pass the hash; they keep the raw value for the email body."""
    _invalidate_active(conn, table, user_id)
    with conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO {table} (user_id, token_hash, expires_at)
            VALUES (%s, %s, NOW() + %s)
            """,
            (str(user_id), token_hash, ttl),
        )


def consume(
    conn: PgConnection,
    *,
    table: TokenTable,
    token_hash: str,
) -> dict[str, Any] | None:
    """Atomically mark a token used and return its row, or ``None`` if it
    doesn't exist / is already used / has expired. The single UPDATE …
    RETURNING removes the race where two requests redeem the same token."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            UPDATE {table}
               SET is_used = TRUE
             WHERE token_hash = %s
               AND is_used = FALSE
               AND expires_at > NOW()
         RETURNING id, user_id, expires_at
            """,
            (token_hash,),
        )
        return cur.fetchone()
