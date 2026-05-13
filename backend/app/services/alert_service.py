"""Alert fan-out orchestration for the NiFi → FastAPI ingest path.

Pure business logic + coordination. No SQL (delegated to ``alert_repo``),
no FastAPI types (the caller is a router), no HTTP concerns.

Public surface
--------------
* :func:`process_price_event` — the only entry point. Routers call it
  with a validated ``PriceEvent`` and get back a result dict suitable
  for the HTTP response.
* :func:`matches_alert` — exposed so unit tests can exercise the
  threshold rule without going through the orchestrator.
"""
from __future__ import annotations

import logging
from typing import Any

from app.models.product import (
    AlertType,
    PriceEvent,
    PriceEventBroadcast,
)
from app.repositories import alert_repo
from app.services import cache
from app.services.email_tasks import send_price_drop_email_task
from app.services.websocket import manager

logger = logging.getLogger(__name__)


def matches_alert(
    row: dict[str, Any],
    *,
    drop_pct: float | None,
    price_usd: float,
) -> tuple[bool, AlertType | None]:
    """Decide whether a watchlist row's thresholds are tripped by an event.

    Two conditions can trigger:

    * percentage drop ≥ effective_threshold — where
      ``effective_threshold = COALESCE(watchlist.alert_threshold_pct,
      user_preferences.global_alert_threshold)``.
    * absolute target — ``target_price`` set and ``price_usd`` ≤ it.
    """
    threshold = row.get("alert_threshold_pct")
    if threshold is None:
        threshold = row.get("global_alert_threshold")
    if threshold is not None and drop_pct is not None and drop_pct >= float(threshold):
        return True, AlertType.PRICE_DROP

    target = row.get("target_price")
    if target is not None and price_usd <= float(target):
        return True, AlertType.PRICE_DROP

    return False, None


async def process_price_event(event: PriceEvent) -> dict[str, Any]:
    """Run the full fan-out pipeline for one inbound price event.

    Steps (in order):

    1. Bust Redis caches that referenced this product so the next read
       sees the new price.
    2. Build a leaner ``PriceEventBroadcast`` payload for the frontend.
    3. Broadcast on the global ``/ws/live-prices`` channel.
    4. Pull every enabled watchlist row for the product, evaluate the
       threshold rule, claim a cooldown slot via the repo's atomic
       UPDATE, snapshot the alert into ``price_alerts``, and push a
       per-user alert payload on ``/ws/alerts/{user_id}``.

    Returns counters the router can put straight into its HTTP response.
    """
    invalidated = cache.invalidate_product(event.canonical_product_id)

    broadcast_payload = PriceEventBroadcast(
        canonical_product_id=event.canonical_product_id,
        product_name=event.product_title,
        site=event.site,
        listing_url=event.listing_url,
        category=event.category,
        price_usd=event.price_usd,
        price_before=event.price_original_usd,
        drop_pct=event.discount_pct,
        is_price_drop=bool(event.discount_pct and event.discount_pct > 0),
        scraped_at=event.scraped_at,
    )

    delivered_global = await manager.broadcast(broadcast_payload)

    rows = alert_repo.load_watchlist_subscribers(event.canonical_product_id)
    delivered_user = 0
    matched_users: list[str] = []
    suppressed_cooldown = 0
    persisted = 0
    emails_queued = 0

    for row in rows:
        triggered, alert_type = matches_alert(
            row, drop_pct=event.discount_pct, price_usd=event.price_usd
        )
        if not triggered:
            continue
        # Cooldown gate — atomic UPDATE…RETURNING. False means a prior
        # scrape already alerted within ALERT_COOLDOWN, so drop silently.
        if not alert_repo.claim_alert_slot(row["id"]):
            suppressed_cooldown += 1
            continue
        if alert_repo.persist_alert(
            user_id=row["user_id"],
            watchlist_item_id=row["id"],
            event=event,
            alert_type=alert_type,
        ):
            persisted += 1
        user_id = str(row["user_id"])
        alert_payload = broadcast_payload.model_copy(
            update={"is_price_drop": True, "alert_type": alert_type}
        )
        live_delivery = await manager.send_to_user(user_id, alert_payload)
        delivered_user += live_delivery
        matched_users.append(user_id)

        # Offline-channel fallback: if no live WebSocket picked up the
        # alert, email the user (subject to their preferences). The send
        # runs on the email thread pool — we don't await it.
        if live_delivery == 0 and _should_email(row):
            _queue_price_drop_email(row, event=event, broadcast=broadcast_payload)
            emails_queued += 1

    return {
        "status": "broadcast",
        "cache_invalidated": invalidated,
        "delivered_global": delivered_global,
        "delivered_user": delivered_user,
        "watchlist_rows": len(rows),
        "subscribers_alerted": len(matched_users),
        "suppressed_cooldown": suppressed_cooldown,
        "alerts_persisted": persisted,
        "emails_queued": emails_queued,
    }


# ---------------------------------------------------------------------------
# Email fallback helpers
# ---------------------------------------------------------------------------

def _should_email(row: dict[str, Any]) -> bool:
    """Email gating: user must be active, opted into email notifications,
    have a verified address, and have an address on file."""
    return bool(
        row.get("email")
        and row.get("email_verified")
        and row.get("email_notifications", True)
    )


def _queue_price_drop_email(
    row: dict[str, Any],
    *,
    event: PriceEvent,
    broadcast: PriceEventBroadcast,
) -> None:
    """Hand off to the email thread pool — never blocks the caller."""
    price_before = (
        float(event.price_original_usd)
        if event.price_original_usd is not None
        else float(event.price_usd)
    )
    drop_pct = (
        float(event.discount_pct)
        if event.discount_pct is not None and event.discount_pct > 0
        else 0.0
    )
    try:
        send_price_drop_email_task(
            to_email=row["email"],
            full_name=row.get("full_name"),
            product_title=broadcast.product_name or event.product_title,
            site=event.site,
            listing_url=str(event.listing_url),
            product_image_url=None,
            price_before=price_before,
            price_after=float(event.price_usd),
            drop_pct=drop_pct,
            currency="USD",
        )
    except Exception:
        # Swallow — email is best-effort. The Future itself also catches,
        # but a synchronous error in the task wrapper (e.g. bad URL) would
        # otherwise propagate into the request handler.
        logger.exception(
            "queue price-drop email failed user=%s product=%s",
            row.get("user_id"),
            event.canonical_product_id,
        )
