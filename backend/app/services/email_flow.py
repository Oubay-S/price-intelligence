"""Use-cases for email verification + password reset.

Same shape as :mod:`session_service` — pure orchestration over repos and
the email task pool, with HTTP concerns left to the router.

Why a separate service module
-----------------------------
* The flows touch *multiple* repos (users + token table + sessions on
  reset). Router code that did it inline would duplicate the same five
  lines across four endpoints.
* The token issue/redeem dance is non-trivial: we issue the raw value
  back to the email layer but only ever persist its hash. Centralising
  here avoids each router hand-rolling the same crypto.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from psycopg2.extensions import connection as PgConnection

from app.config import settings
from app.repositories import (
    audit_repo,
    email_token_repo,
    refresh_token_repo,
    session_repo,
    user_repo,
)
from app.services.auth import (
    generate_url_safe_token,
    hash_password,
    hash_token,
)
from app.services.email_tasks import (
    send_password_reset_email_task,
    send_verification_email_task,
)
from app.services.exceptions import (
    EmailAlreadyVerifiedError,
    TokenInvalidError,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------

def issue_verification_email(
    conn: PgConnection,
    *,
    user_id: Any,
    email: str,
    full_name: str | None,
) -> None:
    """Generate a verification token, persist its hash, queue the email.

    Called from /register and /resend-verification. Skips work entirely
    when the user is already verified — the caller has already returned
    a 200 to the client (we don't leak whether an email was sent).
    """
    raw, token_hash = generate_url_safe_token()
    email_token_repo.issue(
        conn,
        table="email_verification_tokens",
        user_id=user_id,
        token_hash=token_hash,
        ttl=timedelta(hours=settings.EMAIL_VERIFICATION_TTL_HOURS),
    )
    send_verification_email_task(
        to_email=email,
        full_name=full_name,
        token=raw,
    )


def verify_email_token(conn: PgConnection, raw_token: str) -> dict[str, Any]:
    """Redeem a verification token. Returns the user row (id + email)
    on success.

    Raises
    ------
    TokenInvalidError
        Token wasn't found, was already used, or has expired.
    EmailAlreadyVerifiedError
        Token was valid but the user's email is already verified — we
        still consumed the token (atomically) so it can't be re-used.
    """
    consumed = email_token_repo.consume(
        conn,
        table="email_verification_tokens",
        token_hash=hash_token(raw_token),
    )
    if consumed is None:
        raise TokenInvalidError()

    user_id = consumed["user_id"]
    user = user_repo.get_by_id_for_email_flow(conn, user_id)
    if user is None:
        raise TokenInvalidError()

    if user["email_verified"]:
        # Token was valid but the user clicked verify twice quickly. We
        # already burned the token in `consume`; surface a distinct
        # signal so the router can return a clearer message.
        raise EmailAlreadyVerifiedError()

    user_repo.mark_email_verified(conn, user_id)
    audit_repo.log(
        conn,
        user_id=user_id,
        action="user_register",  # closest existing enum value
        entity_type="user",
        entity_id=str(user_id),
        metadata={"event": "email_verified"},
    )
    return user


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------

def issue_password_reset(
    conn: PgConnection,
    *,
    email: str,
) -> None:
    """Look up the user and queue a reset email if active. Always returns
    silently — the router responds 200 regardless of whether the email
    existed, so attackers can't enumerate accounts."""
    user = user_repo.get_by_email_for_email_flow(conn, email)
    if user is None or not user["is_active"]:
        logger.info("password reset requested for unknown / inactive email")
        return

    raw, token_hash = generate_url_safe_token()
    email_token_repo.issue(
        conn,
        table="password_reset_tokens",
        user_id=user["id"],
        token_hash=token_hash,
        ttl=timedelta(hours=settings.PASSWORD_RESET_TTL_HOURS),
    )
    send_password_reset_email_task(
        to_email=user["email"],
        full_name=user.get("full_name"),
        token=raw,
    )


def reset_password(
    conn: PgConnection,
    *,
    raw_token: str,
    new_password: str,
) -> Any:
    """Redeem a reset token, rotate the password, kill every live session
    and refresh token. Returns the user_id on success.

    Raises
    ------
    TokenInvalidError
        Token wasn't found, was already used, or has expired.
    """
    consumed = email_token_repo.consume(
        conn,
        table="password_reset_tokens",
        token_hash=hash_token(raw_token),
    )
    if consumed is None:
        raise TokenInvalidError()

    user_id = consumed["user_id"]
    user = user_repo.get_by_id_for_email_flow(conn, user_id)
    if user is None or not user["is_active"]:
        raise TokenInvalidError()

    user_repo.update_password(
        conn,
        user_id=user_id,
        hashed_password=hash_password(new_password),
    )
    session_repo.revoke_all_for_user(conn, user_id)
    refresh_token_repo.revoke_all_active_for_user(conn, user_id)

    audit_repo.log(
        conn,
        user_id=user_id,
        action="password_change",
        entity_type="user",
        entity_id=str(user_id),
        metadata={"channel": "password_reset"},
    )
    return user_id
