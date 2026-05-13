"""Watchlist use-cases for /watchlist/* endpoints.

Owns the orchestration: BigQuery enrichment, effective_threshold
resolution, parallel fan-out for list rendering, audit log writes.
Routers do parsing + exception → HTTP mapping only.
"""
from __future__ import annotations

import asyncio
from typing import Any

from google.api_core.exceptions import GoogleAPICallError
from psycopg2.extensions import connection as PgConnection

from app.models.product import ProductResponse
from app.models.watchlist import (
    WatchlistAdd,
    WatchlistItemResponse,
    WatchlistListResponse,
    WatchlistUpdate,
)
from app.repositories import audit_repo, watchlist_repo
from app.services.bigquery import get_product_by_id
from app.services.exceptions import (
    BigQueryUnavailableError,
    ProductNotFoundError,
)


# ---------------------------------------------------------------------------
# BigQuery enrichment helpers
# ---------------------------------------------------------------------------

def _fetch_bq_safe(product_id: str) -> ProductResponse | None:
    """get_product_by_id wrapper that swallows BQ errors so a single bad
    product can't sink a whole watchlist render."""
    try:
        return get_product_by_id(product_id)
    except GoogleAPICallError:
        return None


def _row_to_response(
    row: dict[str, Any], bq: ProductResponse | None
) -> WatchlistItemResponse:
    base = {
        "id": row["id"],
        "canonical_product_id": row["canonical_product_id"],
        "product_title": row["product_title"],
        "product_image_url": row["product_image_url"],
        "category": row["category"],
        "subcategory": row["subcategory"],
        "alert_threshold_pct": row["alert_threshold_pct"],
        "target_price": row.get("target_price"),
        "effective_threshold": row["effective_threshold"],
        "alert_enabled": row["alert_enabled"],
        "preferred_site": row["preferred_site"],
        "added_at": row["added_at"],
        "last_alerted_at": row["last_alerted_at"],
        "unread_alert_count": row.get("unread_alert_count", 0) or 0,
        "total_alerts_fired": row.get("total_alerts_fired", 0) or 0,
    }
    if bq is not None:
        base.update(
            current_price=bq.pricing.current,
            currency=bq.pricing.currency_raw,
            in_stock=bq.in_stock,
            site=bq.site,
            listing_url=str(bq.listing_url) if bq.listing_url else None,
        )
    return WatchlistItemResponse(**base)


# ---------------------------------------------------------------------------
# Use-cases
# ---------------------------------------------------------------------------

async def list_for_user(
    conn: PgConnection,
    *,
    user_id: Any,
    page: int,
    limit: int,
) -> WatchlistListResponse:
    offset = (page - 1) * limit

    summary = watchlist_repo.get_user_summary(conn, user_id)
    if summary["total_count"] == 0:
        return WatchlistListResponse(
            items=[], total_count=0, page=page, limit=limit, unread_total=0,
        )

    rows = watchlist_repo.list_for_user(
        conn, user_id=user_id, limit=limit, offset=offset
    )

    # Parallel BQ enrichment — get_product_by_id is cached (TTL 60s) so
    # repeats across requests are cheap.
    bq_results = await asyncio.gather(
        *(asyncio.to_thread(_fetch_bq_safe, row["canonical_product_id"]) for row in rows)
    )

    items = [_row_to_response(row, bq) for row, bq in zip(rows, bq_results)]
    return WatchlistListResponse(
        items=items,
        total_count=summary["total_count"],
        page=page,
        limit=limit,
        unread_total=summary["unread_total"],
    )


async def add(
    conn: PgConnection,
    *,
    user_id: Any,
    product_id: str,
    payload: WatchlistAdd,
    ip_address: str | None,
    user_agent: str | None,
) -> WatchlistItemResponse:
    """Resolve product from BigQuery, persist the watchlist row,
    re-resolve effective_threshold for the response, audit-log."""
    try:
        bq_product = await asyncio.to_thread(get_product_by_id, product_id)
    except GoogleAPICallError as exc:
        raise BigQueryUnavailableError(str(exc)) from exc

    if bq_product is None:
        raise ProductNotFoundError(product_id)

    image_url = str(bq_product.image_url) if bq_product.image_url else None
    category = bq_product.category.value if bq_product.category else None

    # Repo raises DuplicateError on UNIQUE conflict — let it bubble; the
    # router catches that one (it's a repository-layer exception).
    row = watchlist_repo.create(
        conn,
        user_id=user_id,
        canonical_product_id=product_id,
        product_title=bq_product.name,
        product_image_url=image_url,
        category=category,
        subcategory=bq_product.subcategory,
        alert_threshold_pct=payload.alert_threshold_pct,
        target_price=payload.target_price,
        alert_enabled=payload.alert_enabled,
        preferred_site=payload.preferred_site,
    )

    # effective_threshold = COALESCE(item.threshold, user.global_threshold).
    # Read the user's pref row separately rather than re-querying the row
    # joined with user_preferences — the threshold rule is a service
    # concern; the repo just returns the watchlist columns.
    global_threshold = watchlist_repo.get_global_alert_threshold(conn, user_id)
    row["effective_threshold"] = (
        row["alert_threshold_pct"]
        if row["alert_threshold_pct"] is not None
        else global_threshold
    )
    row["unread_alert_count"] = 0
    row["total_alerts_fired"] = 0

    audit_repo.log(
        conn,
        user_id=user_id,
        action="watchlist_add",
        entity_type="watchlist_item",
        entity_id=str(row["id"]),
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={
            "canonical_product_id": product_id,
            "alert_threshold_pct": (
                str(payload.alert_threshold_pct)
                if payload.alert_threshold_pct is not None else None
            ),
            "target_price": (
                str(payload.target_price)
                if payload.target_price is not None else None
            ),
            "preferred_site": payload.preferred_site,
        },
    )

    return _row_to_response(row, bq_product)


async def update(
    conn: PgConnection,
    *,
    user_id: Any,
    product_id: str,
    payload: WatchlistUpdate,
    ip_address: str | None,
    user_agent: str | None,
) -> WatchlistItemResponse:
    changes = payload.model_dump(exclude_unset=True)

    # Repo raises NotFoundError when no row matches — let it bubble.
    row = watchlist_repo.update(
        conn,
        user_id=user_id,
        canonical_product_id=product_id,
        changes=changes,
    )

    counters = watchlist_repo.get_alert_counters(conn, row["id"])
    row.update(counters)

    audit_repo.log(
        conn,
        user_id=user_id,
        action="watchlist_threshold_update",
        entity_type="watchlist_item",
        entity_id=str(row["id"]),
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={
            "canonical_product_id": product_id,
            "changes": {
                k: (str(v) if v is not None else None) for k, v in changes.items()
            },
        },
    )

    bq = await asyncio.to_thread(_fetch_bq_safe, product_id)
    return _row_to_response(row, bq)


def remove(
    conn: PgConnection,
    *,
    user_id: Any,
    product_id: str,
    ip_address: str | None,
    user_agent: str | None,
) -> None:
    # Repo raises NotFoundError — let it bubble.
    deleted_id = watchlist_repo.delete(
        conn, user_id=user_id, canonical_product_id=product_id
    )

    audit_repo.log(
        conn,
        user_id=user_id,
        action="watchlist_remove",
        entity_type="watchlist_item",
        entity_id=str(deleted_id),
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"canonical_product_id": product_id},
    )
