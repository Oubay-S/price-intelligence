"""Service-layer exceptions.

Use-cases raise these instead of ``HTTPException`` so the service layer
stays HTTP-agnostic. Routers catch them at the boundary and map to a
status code.
"""
from __future__ import annotations


class ServiceError(Exception):
    """Base for every service-layer error."""


# ---- session / auth -------------------------------------------------------

class InvalidCredentialsError(ServiceError):
    """Email not found or password didn't verify."""


class UserDisabledError(ServiceError):
    """User row exists but is_active is FALSE."""


class RefreshTokenInvalidError(ServiceError):
    """Refresh token decode failed, expired, or no matching row."""


class RefreshTokenReplayError(ServiceError):
    """Refresh token was already used. Session has been revoked as a
    defence-in-depth measure."""


class SessionRevokedError(ServiceError):
    """Session row is_revoked is TRUE."""


# ---- email verification / password reset ---------------------------------

class TokenInvalidError(ServiceError):
    """Verification / reset token decode failed, was already used, expired,
    or has no matching row. Routers map this to 400."""


class EmailAlreadyVerifiedError(ServiceError):
    """User clicked verify on an already-verified account."""


# ---- watchlist ------------------------------------------------------------

class ProductNotFoundError(ServiceError):
    """BigQuery returned no row for the canonical_product_id."""


class BigQueryUnavailableError(ServiceError):
    """BigQuery raised a transport / API error. Wrap the underlying
    GoogleAPICallError so the router can keep its message."""


# ---- compare --------------------------------------------------------------

class CompareValidationError(ServiceError):
    """Compare request had 0 distinct ids or more than the 4 cap."""
