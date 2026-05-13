"""SQL for the price-event fan-out flow.

Three operations:

* ``load_watchlist_subscribers`` — return every watchlist row that's
  enabled for a given canonical product, joined with the user's
  ``user_preferences.global_alert_threshold`` so the service layer can
  resolve effective threshold without a second round-trip.
* ``claim_alert_slot`` — atomically reserve the next alert slot for a
  watchlist row using ``UPDATE … RETURNING`` against a cooldown window.
  Returns True when the slot was claimed (caller should fire), False
  when still in cooldown.
* ``persist_alert`` — snapshot a fired alert into ``price_alerts`` so
  ``GET /api/alerts`` can read the user's history.

All three open their own connection via ``app.database.get_connection``
because the price-event endpoint is invoked from NiFi without going
through the ``Depends(get_db)`` plumbing — there's no per-request
connection in scope.
"""
from __future__ import annotations

import logging
from typing import Any

from psycopg2.extras import RealDictCursor

from app.database import get_connection
from app.models.product import AlertType, PriceEvent

logger = logging.getLogger(__name__)


# Minimum gap between two alerts for the same watchlist row. Kept here
# rather than in settings because the value is tied to a SQL ``INTERVAL``
# literal, not a runtime config knob.
ALERT_COOLDOWN = "6 hours"


def load_watchlist_subscribers(product_id: str) -> list[dict[str, Any]]:
    """Return rows of (id, user_id, alert_threshold_pct, target_price,
    global_alert_threshold) for every enabled watchlist on ``product_id``.

    Falls back to an empty list on DB error so a price-event delivery
    never fails because of a transient Postgres blip.
    """
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        w.id,
                        w.user_id,
                        w.alert_threshold_pct,
                        w.target_price,
                        p.global_alert_threshold,
                        u.email,
                        u.full_name,
                        u.email_verified,
                        COALESCE(p.email_notifications, TRUE) AS email_notifications
                    FROM watchlist_items w
                    LEFT JOIN user_preferences p ON p.user_id = w.user_id
                    JOIN users u ON u.id = w.user_id
                    WHERE w.canonical_product_id = %s
                      AND w.alert_enabled = TRUE
                      AND u.is_active = TRUE
                    """,
                    (product_id,),
                )
                return [dict(row) for row in cur.fetchall()]
    except Exception:
        logger.exception("load_watchlist_subscribers failed product=%s", product_id)
        return []


def claim_alert_slot(watchlist_id: Any) -> bool:
    """Atomically reserve the next alert slot for ``watchlist_id``.

    Updates ``last_alerted_at = NOW()`` only if it has never fired or the
    last fire is older than ``ALERT_COOLDOWN``. Single statement → race-free
    against concurrent NiFi posts. Fails closed on DB error so an outage
    can't bypass cooldown and spam the user.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    UPDATE watchlist_items
                       SET last_alerted_at = NOW()
                     WHERE id = %s
                       AND (last_alerted_at IS NULL
                            OR last_alerted_at < NOW() - INTERVAL '{ALERT_COOLDOWN}')
                    RETURNING id
                    """,
                    (watchlist_id,),
                )
                return cur.fetchone() is not None
    except Exception:
        logger.exception("claim_alert_slot failed watchlist_id=%s", watchlist_id)
        return False


def persist_alert(
    *,
    user_id: Any,
    watchlist_item_id: Any,
    event: PriceEvent,
    alert_type: AlertType,
) -> bool:
    """Snapshot the fired alert into ``price_alerts`` for history/badge.

    Schema enforces ``drop_pct > 0`` and NOT NULL on ``price_before`` —
    target-price alerts where the scrape carries no ``price_original_usd``
    fall back to ``price_usd`` and a synthetic 0.01% drop so the row still
    satisfies the constraint and shows up in the history feed. Returns
    True on success, False on DB error (broadcast still fires upstream).
    """
    price_before = (
        float(event.price_original_usd)
        if event.price_original_usd is not None
        else float(event.price_usd)
    )
    drop_pct = (
        float(event.discount_pct)
        if event.discount_pct is not None and event.discount_pct > 0
        else 0.01
    )
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO price_alerts (
                        user_id, watchlist_item_id, canonical_product_id,
                        product_title, product_image_url, site, listing_url,
                        price_before, price_after, currency, drop_pct, alert_type
                    ) VALUES (
                        %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        user_id,
                        watchlist_item_id,
                        event.canonical_product_id,
                        event.product_title,
                        None,
                        event.site,
                        event.listing_url,
                        price_before,
                        float(event.price_usd),
                        "USD",
                        drop_pct,
                        alert_type.value,
                    ),
                )
                return True
    except Exception:
        logger.exception(
            "price_alerts insert failed user_id=%s product=%s",
            user_id,
            event.canonical_product_id,
        )
        return False
