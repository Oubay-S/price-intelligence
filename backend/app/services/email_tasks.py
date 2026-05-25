"""High-level email tasks — one function per flow.

Routers and services should call into these helpers, not :mod:`email`
or :mod:`email_templates` directly. The helpers:

* Build the verification / reset URL from :data:`settings.FRONTEND_URL`.
* Pick the right template builder.
* Hand the rendered message to :func:`send_email_async`, so the SMTP
  round-trip runs on the email thread pool and never blocks the FastAPI
  event loop.

Every helper returns the :class:`concurrent.futures.Future` so callers
that want delivery confirmation (most don't) can await it.
"""

from __future__ import annotations

import logging
from concurrent.futures import Future
from urllib.parse import urlencode

from app.config import settings
from app.services.email import send_email_async
from app.services.email_templates import (
    build_password_reset_email,
    build_price_drop_email,
    build_verification_email,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# URL builders. The frontend owns the verify / reset pages — backend only
# embeds the opaque token in the query string.
# ---------------------------------------------------------------------------

def _frontend(path: str, **params: str) -> str:
    base = settings.FRONTEND_URL.rstrip("/")
    query = ("?" + urlencode(params)) if params else ""
    return f"{base}{path}{query}"


def build_verification_url(token: str) -> str:
    return _frontend("/verify-email", token=token)


def build_password_reset_url(token: str) -> str:
    return _frontend("/reset-password", token=token)


def build_watchlist_url() -> str:
    return _frontend("/watchlist")


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

def send_verification_email_task(
    *, to_email: str, full_name: str | None, token: str
) -> Future[None]:
    """Queue the "verify your email" message after /register."""
    url = build_verification_url(token)
    subject, html, text = build_verification_email(
        full_name=full_name,
        verification_url=url,
        ttl_hours=settings.EMAIL_VERIFICATION_TTL_HOURS,
    )
    logger.debug("queue verification email to=%s", to_email)
    return send_email_async(to=to_email, subject=subject, html=html, text=text)


def send_password_reset_email_task(
    *, to_email: str, full_name: str | None, token: str
) -> Future[None]:
    """Queue the "reset your password" message after /forgot-password."""
    url = build_password_reset_url(token)
    subject, html, text = build_password_reset_email(
        full_name=full_name,
        reset_url=url,
        ttl_hours=settings.PASSWORD_RESET_TTL_HOURS,
    )
    logger.debug("queue password-reset email to=%s", to_email)
    return send_email_async(to=to_email, subject=subject, html=html, text=text)


def send_price_drop_email_task(
    *,
    to_email: str,
    full_name: str | None,
    product_title: str,
    site: str,
    listing_url: str,
    product_image_url: str | None,
    price_before: float,
    price_after: float,
    drop_pct: float,
    currency: str = "USD",
) -> Future[None]:
    """Queue a price-drop notification (offline-channel counterpart to the
    WebSocket broadcast in :mod:`app.services.alert_service`)."""
    subject, html, text = build_price_drop_email(
        full_name=full_name,
        product_title=product_title,
        site=site,
        listing_url=listing_url,
        product_image_url=product_image_url,
        price_before=price_before,
        price_after=price_after,
        drop_pct=drop_pct,
        currency=currency,
        watchlist_url=build_watchlist_url(),
    )
    logger.debug(
        "queue price-drop email to=%s product=%s drop=%.1f%%",
        to_email,
        product_title,
        drop_pct,
    )
    return send_email_async(to=to_email, subject=subject, html=html, text=text)
