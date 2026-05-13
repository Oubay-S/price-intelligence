"""watchlist_items + v_watchlist_with_unread reads/writes used by /watchlist.

`raise DuplicateError` on UNIQUE conflict (same user adding the same product
twice). `raise NotFoundError` when an UPDATE/DELETE matches no row.
"""
from __future__ import annotations

from typing import Any

from psycopg2 import IntegrityError
from psycopg2.extensions import connection as PgConnection
from psycopg2.extras import RealDictCursor

from app.repositories.exceptions import DuplicateError, NotFoundError


_VIEW_COLS = (
    "id, canonical_product_id, product_title, product_image_url, "
    "category, subcategory, alert_threshold_pct, target_price, "
    "alert_enabled, preferred_site, added_at, last_alerted_at, "
    "effective_threshold, unread_alert_count, total_alerts_fired"
)


def get_user_summary(
    conn: PgConnection, user_id: Any
) -> dict[str, int]:
    """Return ``{total_count, unread_total}`` for the user — drives both
    pagination and the navbar badge in a single round-trip."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                COUNT(*)                              AS total_count,
                COALESCE(SUM(unread_alert_count), 0)  AS unread_total
            FROM v_watchlist_with_unread
            WHERE user_id = %s
            """,
            (str(user_id),),
        )
        row = cur.fetchone() or {"total_count": 0, "unread_total": 0}
        return {
            "total_count": int(row["total_count"]),
            "unread_total": int(row["unread_total"]),
        }


def list_for_user(
    conn: PgConnection,
    *,
    user_id: Any,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            SELECT {_VIEW_COLS}
              FROM v_watchlist_with_unread
             WHERE user_id = %s
             ORDER BY added_at DESC
             LIMIT %s OFFSET %s
            """,
            (str(user_id), limit, offset),
        )
        return list(cur.fetchall())


def create(
    conn: PgConnection,
    *,
    user_id: Any,
    canonical_product_id: str,
    product_title: str,
    product_image_url: str | None,
    category: str | None,
    subcategory: str | None,
    alert_threshold_pct: float | None,
    target_price: float | None,
    alert_enabled: bool,
    preferred_site: str | None,
) -> dict[str, Any]:
    """Insert a watchlist row. Raises DuplicateError on UNIQUE conflict."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        try:
            cur.execute(
                """
                INSERT INTO watchlist_items (
                    user_id, canonical_product_id, product_title, product_image_url,
                    category, subcategory,
                    alert_threshold_pct, target_price, alert_enabled, preferred_site
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, canonical_product_id, product_title, product_image_url,
                          category, subcategory,
                          alert_threshold_pct, target_price, alert_enabled, preferred_site,
                          added_at, last_alerted_at
                """,
                (
                    str(user_id),
                    canonical_product_id,
                    product_title,
                    product_image_url,
                    category,
                    subcategory,
                    alert_threshold_pct,
                    target_price,
                    alert_enabled,
                    preferred_site,
                ),
            )
            return cur.fetchone()
        except IntegrityError as exc:
            raise DuplicateError("product already in watchlist") from exc


def get_global_alert_threshold(
    conn: PgConnection, user_id: Any
) -> float | None:
    """Pull the user's preferences row to resolve effective_threshold."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT global_alert_threshold FROM user_preferences WHERE user_id = %s",
            (str(user_id),),
        )
        row = cur.fetchone()
        return row["global_alert_threshold"] if row else None


def update(
    conn: PgConnection,
    *,
    user_id: Any,
    canonical_product_id: str,
    changes: dict[str, Any],
) -> dict[str, Any]:
    """Apply a partial update to a watchlist row.

    Returns the updated row joined with user_preferences so callers can
    read ``effective_threshold`` directly. Raises NotFoundError when no
    row matches (user_id, canonical_product_id).
    """
    if not changes:
        # PATCH with no fields — fetch + return current state instead.
        return _get_current_with_threshold(
            conn, user_id=user_id, canonical_product_id=canonical_product_id
        )

    allowed = ("alert_threshold_pct", "target_price", "alert_enabled", "preferred_site")
    set_clauses: list[str] = []
    params: list[Any] = []
    for col in allowed:
        if col in changes:
            set_clauses.append(f"{col} = %s")
            params.append(changes[col])
    set_sql = ", ".join(set_clauses)
    params.extend([str(user_id), canonical_product_id])

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            UPDATE watchlist_items w
               SET {set_sql}
              FROM user_preferences p
             WHERE w.user_id = %s
               AND w.canonical_product_id = %s
               AND p.user_id = w.user_id
            RETURNING w.id, w.canonical_product_id, w.product_title, w.product_image_url,
                      w.category, w.subcategory,
                      w.alert_threshold_pct, w.target_price, w.alert_enabled, w.preferred_site,
                      w.added_at, w.last_alerted_at,
                      COALESCE(w.alert_threshold_pct, p.global_alert_threshold)
                          AS effective_threshold
            """,
            params,
        )
        row = cur.fetchone()
        if row is None:
            raise NotFoundError("watchlist item not found")
        return row


def _get_current_with_threshold(
    conn: PgConnection, *, user_id: Any, canonical_product_id: str
) -> dict[str, Any]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT w.id, w.canonical_product_id, w.product_title, w.product_image_url,
                   w.category, w.subcategory,
                   w.alert_threshold_pct, w.target_price, w.alert_enabled, w.preferred_site,
                   w.added_at, w.last_alerted_at,
                   COALESCE(w.alert_threshold_pct, p.global_alert_threshold)
                       AS effective_threshold
              FROM watchlist_items w
              JOIN user_preferences p ON p.user_id = w.user_id
             WHERE w.user_id = %s
               AND w.canonical_product_id = %s
            """,
            (str(user_id), canonical_product_id),
        )
        row = cur.fetchone()
        if row is None:
            raise NotFoundError("watchlist item not found")
        return row


def get_alert_counters(
    conn: PgConnection, item_id: Any
) -> dict[str, int]:
    """Pull (unread_alert_count, total_alerts_fired) from the unread view."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT unread_alert_count, total_alerts_fired
              FROM v_watchlist_with_unread
             WHERE id = %s
            """,
            (str(item_id),),
        )
        row = cur.fetchone() or {}
        return {
            "unread_alert_count": row.get("unread_alert_count", 0) or 0,
            "total_alerts_fired": row.get("total_alerts_fired", 0) or 0,
        }


def delete(
    conn: PgConnection,
    *,
    user_id: Any,
    canonical_product_id: str,
) -> Any:
    """Delete a watchlist row. Returns the deleted ``id`` so the caller can
    audit-log it. Raises NotFoundError when no row matches."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            DELETE FROM watchlist_items
             WHERE user_id = %s AND canonical_product_id = %s
            RETURNING id
            """,
            (str(user_id), canonical_product_id),
        )
        row = cur.fetchone()
        if row is None:
            raise NotFoundError("watchlist item not found")
        return row["id"]
