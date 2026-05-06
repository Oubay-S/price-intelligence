"""Authentication primitives: password hashing and JWT lifecycle.

Pure crypto + token helpers. No DB I/O — that lives in routers/services that
consume these helpers. Keeping this module side-effect free makes it trivial
to unit test and reuse from the alert worker, WebSocket auth, etc.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import bcrypt
from jose import ExpiredSignatureError, JWTError, jwt

from app.config import settings


# ---------------------------------------------------------------------------
# Password hashing (bcrypt)
# ---------------------------------------------------------------------------

# bcrypt has a 72-byte input limit. Pre-hashing with SHA-256 lets us accept
# arbitrarily long passwords without silent truncation, which bcrypt would
# otherwise do.
_BCRYPT_ROUNDS = 12


def _prepare_password(password: str) -> bytes:
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    # Encode digest as base64-ish hex so it stays printable bytes < 72.
    return digest.hex().encode("utf-8")


def hash_password(password: str) -> str:
    """Return a bcrypt hash safe to store in `users.hashed_password`."""
    if not password:
        raise ValueError("password must not be empty")
    salt = bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(_prepare_password(password), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    """Constant-time compare a plaintext password against a stored hash."""
    if not password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(
            _prepare_password(password),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------------------
# JWT — access + refresh tokens
# ---------------------------------------------------------------------------

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def _build_payload(
    subject: str | UUID,
    token_type: str,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": secrets.token_urlsafe(16),
    }
    if extra_claims:
        # Reserved claims must not be overwritten by callers.
        for reserved in ("sub", "type", "iat", "exp", "jti"):
            extra_claims.pop(reserved, None)
        payload.update(extra_claims)
    return payload


def create_access_token(
    subject: str | UUID,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Issue a signed access JWT. `subject` is the user UUID."""
    delta = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = _build_payload(subject, ACCESS_TOKEN_TYPE, delta, extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(
    subject: str | UUID,
    session_id: str | UUID,
    expires_delta: timedelta | None = None,
) -> str:
    """Issue a signed refresh JWT bound to a session row."""
    delta = expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = _build_payload(
        subject,
        REFRESH_TOKEN_TYPE,
        delta,
        extra_claims={"sid": str(session_id)},
    )
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


class TokenError(Exception):
    """Raised when a JWT cannot be decoded, is expired, or fails validation."""


class TokenExpiredError(TokenError):
    """Token signature is valid but `exp` has passed."""


def decode_token(
    token: str,
    expected_type: str | None = None,
) -> dict[str, Any]:
    """Decode and validate a JWT. Raises `TokenError` on any failure.

    If `expected_type` is provided, the token's `type` claim must match
    (used to reject access tokens at the refresh endpoint and vice versa).
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except ExpiredSignatureError as exc:
        raise TokenExpiredError("token expired") from exc
    except JWTError as exc:
        raise TokenError(f"invalid token: {exc}") from exc

    if expected_type is not None and payload.get("type") != expected_type:
        raise TokenError(
            f"unexpected token type: got {payload.get('type')!r}, want {expected_type!r}"
        )

    return payload


# ---------------------------------------------------------------------------
# Token hashing for DB storage
# ---------------------------------------------------------------------------

# `sessions.token_hash` and `refresh_tokens.token_hash` store SHA-256 of the
# raw JWT — never the JWT itself. Lets us revoke a session without keeping
# the bearer secret in the database.


def hash_token(token: str) -> str:
    """SHA-256 hex digest of a JWT, sized to fit the VARCHAR(255) columns."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_url_safe_token(num_bytes: int = 32) -> tuple[str, str]:
    """Generate a random opaque token + its SHA-256 hash.

    Used for email verification and password reset flows where we send the
    raw token to the user via email and store only the hash in Postgres.
    """
    raw = secrets.token_urlsafe(num_bytes)
    return raw, hash_token(raw)
