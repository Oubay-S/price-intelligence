"""Pydantic models for the user / auth domain.

Mirrors the tables in `backend/sql/first_setup.sql` (users, sessions,
refresh_tokens, user_preferences). Inbound shapes accept raw client input
and never expose `hashed_password`. Outbound shapes are safe to serialise
straight to the API consumer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

UserRole = Literal["user", "admin"]


# ---------------------------------------------------------------------------
# Inbound — registration / login / refresh
# ---------------------------------------------------------------------------

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128, repr=False)
    full_name: str | None = Field(default=None, max_length=120)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128, repr=False)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


# ---------------------------------------------------------------------------
# Email verification + password reset
# ---------------------------------------------------------------------------

class VerifyEmailRequest(BaseModel):
    """POST /auth/verify-email — token is the raw URL-safe string from
    the email link (we hash it server-side before lookup)."""
    token: str = Field(..., min_length=16, max_length=128)


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=16, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128, repr=False)


class MessageResponse(BaseModel):
    """Generic ``{"message": "..."}`` shape for endpoints that don't
    return a resource (verify-email, forgot-password, reset-password)."""
    message: str


# ---------------------------------------------------------------------------
# Outbound — tokens and the public user shape
# ---------------------------------------------------------------------------

class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int  # seconds until access token expiry


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str | None = None
    role: UserRole = "user"
    is_active: bool = True
    email_verified: bool = False
    created_at: datetime
    updated_at: datetime | None = None
    last_login_at: datetime | None = None
