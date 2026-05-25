"""users table reads + writes used by /auth.

Returns plain dicts (RealDictCursor rows). Domain exceptions:
``DuplicateError`` when the email already exists.
"""
from __future__ import annotations

from typing import Any

from psycopg2 import IntegrityError
from psycopg2.extensions import connection as PgConnection
from psycopg2.extras import RealDictCursor

from app.repositories.exceptions import DuplicateError


_PUBLIC_COLS = (
    "id, email, full_name, role, is_active, email_verified, "
    "created_at, updated_at, last_login_at"
)


def create(
    conn: PgConnection,
    *,
    email: str,
    hashed_password: str,
    full_name: str | None,
) -> dict[str, Any]:
    """Insert a new user. Raises ``DuplicateError`` if the email is taken."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        try:
            cur.execute(
                f"""
                INSERT INTO users (email, hashed_password, full_name)
                VALUES (%s, %s, %s)
                RETURNING {_PUBLIC_COLS}
                """,
                (email, hashed_password, full_name),
            )
            return cur.fetchone()
        except IntegrityError as exc:
            raise DuplicateError("email already registered") from exc


def get_credentials_by_email(
    conn: PgConnection, email: str
) -> dict[str, Any] | None:
    """Return ``(id, hashed_password, is_active)`` for the login flow,
    or None if the email isn't on file."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT id, hashed_password, is_active FROM users WHERE email = %s",
            (email,),
        )
        return cur.fetchone()


def touch_last_login(conn: PgConnection, user_id: Any) -> None:
    """Stamp ``users.last_login_at`` to NOW() after a successful login."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE users SET last_login_at = NOW() WHERE id = %s",
            (str(user_id),),
        )


# ---------------------------------------------------------------------------
# Email verification + password reset support
# ---------------------------------------------------------------------------

def get_by_email_for_email_flow(
    conn: PgConnection, email: str
) -> dict[str, Any] | None:
    """Return ``(id, email, full_name, email_verified, is_active)``.

    Used by /resend-verification and /forgot-password — both want a
    deterministic shape without leaking ``hashed_password``.
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, email, full_name, email_verified, is_active
              FROM users
             WHERE email = %s
            """,
            (email,),
        )
        return cur.fetchone()


def get_by_id_for_email_flow(
    conn: PgConnection, user_id: Any
) -> dict[str, Any] | None:
    """Same projection as :func:`get_by_email_for_email_flow` but by id —
    consumed after redeeming a token where we only have ``user_id``."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, email, full_name, email_verified, is_active
              FROM users
             WHERE id = %s
            """,
            (str(user_id),),
        )
        return cur.fetchone()


def mark_email_verified(conn: PgConnection, user_id: Any) -> None:
    """Flip ``users.email_verified`` to TRUE. Idempotent — safe to call
    on an already-verified user."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE users SET email_verified = TRUE WHERE id = %s",
            (str(user_id),),
        )


def update_password(
    conn: PgConnection, *, user_id: Any, hashed_password: str
) -> None:
    """Set a new bcrypt hash on the user row. Caller is responsible for
    revoking sessions / refresh tokens (handled in session_service)."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE users SET hashed_password = %s WHERE id = %s",
            (hashed_password, str(user_id)),
        )


def get_notification_target(
    conn: PgConnection, user_id: Any
) -> dict[str, Any] | None:
    """Return ``(email, full_name, email_notifications)`` for alert fan-out.

    ``email_notifications`` is read from ``user_preferences`` (1:1 with
    users, auto-created by trigger). Returns None for soft-deleted /
    missing users.
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT u.email,
                   u.full_name,
                   u.email_verified,
                   COALESCE(p.email_notifications, TRUE) AS email_notifications
              FROM users u
              LEFT JOIN user_preferences p ON p.user_id = u.id
             WHERE u.id = %s
               AND u.is_active = TRUE
            """,
            (str(user_id),),
        )
        return cur.fetchone()
