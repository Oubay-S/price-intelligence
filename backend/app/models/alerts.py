"""Alert DTOs.

* ``PriceDropAlert`` / ``AlertsResponse`` — backed by the BigQuery mart
  feed (``GET /prices/drops``); also broadcast over WebSocket.
* ``UserAlertRecord`` / ``UnreadAlertCount`` — backed by the Postgres
  ``price_alerts`` table (``GET /api/alerts``, ``/api/alerts/unread-count``).
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AlertType, SupplementCategory


class PriceDropAlert(BaseModel):
    """A significant price drop detected by the SQL window function.
    Returned by ``GET /prices/drops`` and broadcast over WebSocket."""
    canonical_product_id: str
    product_name:         str
    image_url:            Optional[str] = None
    site:                 str
    listing_url:          str
    category:             SupplementCategory

    price_before:         float
    price_after:          float
    currency:             str       = "USD"
    drop_pct:             float     = Field(..., gt=0)
    alert_type:           AlertType = AlertType.PRICE_DROP

    scraped_at:           datetime
    detected_at:          datetime  = Field(default_factory=datetime.utcnow)

    # optional normalised metrics for display
    price_per_serving_after: Optional[float] = None
    price_per_kg_after:      Optional[float] = None


class AlertsResponse(BaseModel):
    """Response envelope for ``GET /prices/drops``."""
    alerts:        list[PriceDropAlert]
    count:         int
    threshold_pct: float
    generated_at:  datetime = Field(default_factory=datetime.utcnow)


class UserAlertRecord(BaseModel):
    """A stored alert record from the ``price_alerts`` PostgreSQL table.
    Returned by ``GET /api/alerts`` (user's personal alert history)."""
    model_config = ConfigDict(from_attributes=True)

    id:                   UUID
    canonical_product_id: str
    product_name:         str
    product_image_url:    Optional[str] = None
    site:                 str
    listing_url:          str
    price_before:         float
    price_after:          float
    drop_pct:             float
    alert_type:           AlertType
    is_read:              bool
    triggered_at:         datetime
    read_at:              Optional[datetime] = None


class UnreadAlertCount(BaseModel):
    """Returned by ``GET /api/alerts/unread-count`` — drives the navbar badge."""
    user_id:      UUID
    unread_count: int
