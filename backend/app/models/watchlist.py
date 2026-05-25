"""Pydantic models for the watchlist domain.

Backed by the `watchlist_items` table (Postgres) plus on-the-fly enrichment
from BigQuery (current price, stock, listing URL). The Postgres row caches
the product title/image at add-time so a watchlist render does not need to
hit BigQuery just to display names.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ---------------------------------------------------------------------------
# Inbound — add / update
# ---------------------------------------------------------------------------

class WatchlistAdd(BaseModel):
    """Body for POST /watchlist/{product_id}.

    `product_id` itself comes from the path. The product title / image /
    category are NOT accepted from the client — we resolve them from
    BigQuery on the server so the cached snapshot stays trustworthy.
    """

    alert_threshold_pct: Optional[Decimal] = Field(
        default=None,
        gt=0,
        le=100,
        description="Per-item override of the user's global threshold. Null = inherit.",
    )
    target_price: Optional[Decimal] = Field(
        default=None,
        gt=0,
        description="Absolute price floor — alert when current_price <= target_price.",
    )
    alert_enabled: bool = True
    preferred_site: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Restrict alerts to this site (e.g. 'jumia.ma'). Null = any site.",
    )


class WatchlistUpdate(BaseModel):
    """Body for PATCH /watchlist/{product_id}. All fields optional."""

    alert_threshold_pct: Optional[Decimal] = Field(default=None, gt=0, le=100)
    target_price: Optional[Decimal] = Field(default=None, gt=0)
    alert_enabled: Optional[bool] = None
    preferred_site: Optional[str] = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def _at_least_one(self) -> "WatchlistUpdate":
        allowed = {"alert_threshold_pct", "target_price", "alert_enabled", "preferred_site"}
        if not (self.model_fields_set & allowed):
            raise ValueError(
                "At least one of alert_threshold_pct, target_price, "
                "alert_enabled, preferred_site must be provided"
            )
        return self


# ---------------------------------------------------------------------------
# Outbound
# ---------------------------------------------------------------------------

class WatchlistItemResponse(BaseModel):
    """Single watchlist row, BigQuery-enriched.

    `current_price`, `currency`, `in_stock`, `site`, `listing_url` are
    null when the canonical_product_id can no longer be found in the
    BigQuery mart (e.g. delisted product) — the watchlist row stays
    around so the user can still see and remove it.
    """

    model_config = ConfigDict(from_attributes=True)

    # Postgres-owned
    id: UUID
    canonical_product_id: str
    product_title: str
    product_image_url: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None

    alert_threshold_pct: Optional[Decimal] = None
    target_price: Optional[Decimal] = None
    effective_threshold: Decimal  # COALESCE(alert_threshold_pct, user.global_alert_threshold)
    alert_enabled: bool
    preferred_site: Optional[str] = None

    added_at: datetime
    last_alerted_at: Optional[datetime] = None

    # Alert-history fields from v_watchlist_with_unread
    unread_alert_count: int = 0
    total_alerts_fired: int = 0

    # BigQuery-enriched (nullable if lookup misses)
    current_price: Optional[float] = None
    currency: Optional[str] = None
    in_stock: Optional[bool] = None
    site: Optional[str] = None
    listing_url: Optional[str] = None


class WatchlistListResponse(BaseModel):
    items: list[WatchlistItemResponse]
    total_count: int
    page: int
    limit: int
    unread_total: int  # SUM of unread_alert_count across the user's full watchlist
