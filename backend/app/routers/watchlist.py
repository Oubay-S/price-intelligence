"""Watchlist endpoints.

All routes require an authenticated user (Bearer JWT). Rows live in
Postgres (`watchlist_items`); current-price + stock data is enriched from
BigQuery on read. The product title / image / category are cached in
Postgres at add-time so list renders don't need a BigQuery round-trip.
"""

from __future__ import annotations

import asyncio
import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from google.api_core.exceptions import GoogleAPICallError
from psycopg2 import IntegrityError
from psycopg2.extensions import connection as PgConnection
from psycopg2.extras import RealDictCursor

from app.database import get_db
from app.middleware.core import get_current_user
from app.models.product import ProductResponse
from app.models.watchlist import (
    WatchlistAdd,
    WatchlistItemResponse,
    WatchlistListResponse,
    WatchlistUpdate,
)
from app.services.bigquery import get_product_by_id

router = APIRouter()


# `canonical_product_id` is TO_HEX(SHA256(product_url)) → 64 lowercase hex chars.
ProductIdPath = Annotated[
    str,
    Path(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
        description="canonical_product_id (64-char SHA-256 hex)",
    ),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _audit(
    cur,
    *,
    user_id: Any,
    action: str,
    entity_id: str,
    request: Request,
    metadata: dict[str, Any] | None = None,
) -> None:
    cur.execute(
        """
        INSERT INTO audit_logs
            (user_id, action, entity_type, entity_id, ip_address, user_agent, metadata)
        VALUES (%s, %s, 'watchlist_item', %s, %s, %s, %s::jsonb)
        """,
        (
            str(user_id),
            action,
            entity_id,
            request.client.host if request.client else None,
            request.headers.get("user-agent"),
            json.dumps(metadata) if metadata else None,
        ),
    )


def _fetch_bq_safe(product_id: str) -> ProductResponse | None:
    """get_product_by_id wrapper that swallows BQ errors so a single bad
    product can't sink the whole watchlist render."""
    try:
        return get_product_by_id(product_id)
    except GoogleAPICallError:
        return None


def _row_to_response(
    row: dict[str, Any],
    bq: ProductResponse | None,
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
# GET /watchlist
# ---------------------------------------------------------------------------

@router.get("", response_model=WatchlistListResponse)
async def list_watchlist(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    conn: Annotated[PgConnection, Depends(get_db)],
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
) -> WatchlistListResponse:
    user_id = str(current_user["id"])
    offset = (page - 1) * limit

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Total count + per-user unread total in a single round-trip.
        cur.execute(
            """
            SELECT
                COUNT(*)                              AS total_count,
                COALESCE(SUM(unread_alert_count), 0)  AS unread_total
            FROM v_watchlist_with_unread
            WHERE user_id = %s
            """,
            (user_id,),
        )
        totals = cur.fetchone()
        total_count = int(totals["total_count"])
        unread_total = int(totals["unread_total"])

        if total_count == 0:
            return WatchlistListResponse(
                items=[], total_count=0, page=page, limit=limit, unread_total=0,
            )

        cur.execute(
            """
            SELECT
                id, canonical_product_id, product_title, product_image_url,
                category, subcategory,
                alert_threshold_pct, target_price, alert_enabled, preferred_site,
                added_at, last_alerted_at, effective_threshold,
                unread_alert_count, total_alerts_fired
            FROM v_watchlist_with_unread
            WHERE user_id = %s
            ORDER BY added_at DESC
            LIMIT %s OFFSET %s
            """,
            (user_id, limit, offset),
        )
        rows = cur.fetchall()

    # Parallel BQ enrichment — get_product_by_id is cached (TTL 60s) so
    # repeats across requests are cheap.
    bq_results = await asyncio.gather(
        *(asyncio.to_thread(_fetch_bq_safe, row["canonical_product_id"]) for row in rows)
    )

    items = [_row_to_response(row, bq) for row, bq in zip(rows, bq_results)]
    return WatchlistListResponse(
        items=items,
        total_count=total_count,
        page=page,
        limit=limit,
        unread_total=unread_total,
    )


# ---------------------------------------------------------------------------
# POST /watchlist/{product_id}
# ---------------------------------------------------------------------------

@router.post(
    "/{product_id}",
    response_model=WatchlistItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_watchlist_item(
    request: Request,
    product_id: ProductIdPath,
    payload: WatchlistAdd,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    conn: Annotated[PgConnection, Depends(get_db)],
) -> WatchlistItemResponse:
    user_id = str(current_user["id"])

    # Resolve product from BigQuery so we can cache title/image/category.
    try:
        bq_product = await asyncio.to_thread(get_product_by_id, product_id)
    except GoogleAPICallError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"BigQuery error resolving product: {exc}",
        ) from exc

    if bq_product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id!r} not found in catalog",
        )

    threshold = payload.alert_threshold_pct
    target_price = payload.target_price
    image_url = str(bq_product.image_url) if bq_product.image_url else None
    category = bq_product.category.value if bq_product.category else None
    subcategory = bq_product.subcategory

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
                    user_id,
                    product_id,
                    bq_product.name,
                    image_url,
                    category,
                    subcategory,
                    threshold,
                    target_price,
                    payload.alert_enabled,
                    payload.preferred_site,
                ),
            )
            row = cur.fetchone()
        except IntegrityError as exc:
            conn.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Product already in watchlist",
            ) from exc

        # Re-resolve effective_threshold by reading user_preferences.
        cur.execute(
            "SELECT global_alert_threshold FROM user_preferences WHERE user_id = %s",
            (user_id,),
        )
        prefs = cur.fetchone()
        effective = (
            row["alert_threshold_pct"]
            if row["alert_threshold_pct"] is not None
            else prefs["global_alert_threshold"]
        )

        _audit(
            cur,
            user_id=user_id,
            action="watchlist_add",
            entity_id=str(row["id"]),
            request=request,
            metadata={
                "canonical_product_id": product_id,
                "alert_threshold_pct": str(threshold) if threshold is not None else None,
                "target_price": str(target_price) if target_price is not None else None,
                "preferred_site": payload.preferred_site,
            },
        )

    row["effective_threshold"] = effective
    # New rows have no alerts yet; keep response shape consistent with GET.
    row["unread_alert_count"] = 0
    row["total_alerts_fired"] = 0
    return _row_to_response(row, bq_product)


# ---------------------------------------------------------------------------
# PATCH /watchlist/{product_id}
# ---------------------------------------------------------------------------

@router.patch("/{product_id}", response_model=WatchlistItemResponse)
async def update_watchlist_item(
    request: Request,
    product_id: ProductIdPath,
    payload: WatchlistUpdate,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    conn: Annotated[PgConnection, Depends(get_db)],
) -> WatchlistItemResponse:
    user_id = str(current_user["id"])
    changes = payload.model_dump(exclude_unset=True)

    set_clauses: list[str] = []
    params: list[Any] = []
    for col in ("alert_threshold_pct", "target_price", "alert_enabled", "preferred_site"):
        if col in changes:
            set_clauses.append(f"{col} = %s")
            params.append(changes[col])

    set_sql = ", ".join(set_clauses)
    params.extend([user_id, product_id])

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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Watchlist item not found",
            )

        # Pull alert counters from the view so PATCH response matches GET shape.
        cur.execute(
            """
            SELECT unread_alert_count, total_alerts_fired
            FROM v_watchlist_with_unread
            WHERE id = %s
            """,
            (str(row["id"]),),
        )
        counters = cur.fetchone() or {}
        row["unread_alert_count"] = counters.get("unread_alert_count", 0) or 0
        row["total_alerts_fired"] = counters.get("total_alerts_fired", 0) or 0

        _audit(
            cur,
            user_id=user_id,
            action="watchlist_threshold_update",
            entity_id=str(row["id"]),
            request=request,
            metadata={
                "canonical_product_id": product_id,
                "changes": {
                    k: (str(v) if v is not None else None) for k, v in changes.items()
                },
            },
        )

    bq = await asyncio.to_thread(_fetch_bq_safe, product_id)
    return _row_to_response(row, bq)


# ---------------------------------------------------------------------------
# DELETE /watchlist/{product_id}
# ---------------------------------------------------------------------------

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_watchlist_item(
    request: Request,
    product_id: ProductIdPath,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    conn: Annotated[PgConnection, Depends(get_db)],
) -> None:
    user_id = str(current_user["id"])

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            DELETE FROM watchlist_items
            WHERE user_id = %s AND canonical_product_id = %s
            RETURNING id
            """,
            (user_id, product_id),
        )
        deleted = cur.fetchone()
        if deleted is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Watchlist item not found",
            )

        _audit(
            cur,
            user_id=user_id,
            action="watchlist_remove",
            entity_id=str(deleted["id"]),
            request=request,
            metadata={"canonical_product_id": product_id},
        )
