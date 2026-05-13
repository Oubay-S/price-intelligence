"""Integration boundary shapes — NiFi inbound, WebSocket outbound.

* ``PriceEvent`` — the body NiFi POSTs to ``/internal/price-event``
  after EvaluateJsonPath + ReplaceText. Already in USD with parsed
  numeric pricing.
* ``PriceEventBroadcast`` — leaner payload pushed over
  ``/ws/live-prices`` and ``/ws/alerts/{user_id}`` for the Angular
  frontend.

These are not "product" DTOs — they're transport contracts with
external pipes. Kept in their own module so changing the NiFi schema
doesn't ripple into the catalog model file.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import AlertType, SupplementCategory


class PriceEvent(BaseModel):
    """Schema for ``POST /internal/price-event``.

    Posted by NiFi's ListenHTTP processor. FastAPI validates, busts the
    cache for the product, and runs the watchlist fan-out via
    ``alert_service.process_price_event``.
    """
    # identity
    canonical_product_id: str
    product_title:        str
    site:                 str
    listing_url:          str
    category:             SupplementCategory

    # pricing (already parsed by analyst pipeline at ingest time)
    price_usd:            float = Field(..., gt=0)
    price_original_usd:   Optional[float] = Field(None, ge=0)
    currency_raw:         str = "USD"
    in_stock:             bool = True

    # optional computed
    price_per_serving:    Optional[float] = None
    price_per_kg:         Optional[float] = None
    discount_pct:         Optional[float] = Field(None, ge=0, le=100)

    # scrape metadata
    scraped_at:           datetime = Field(default_factory=datetime.utcnow)
    scraper_version:      Optional[str] = None
    data_quality_score:   Optional[int] = Field(None, ge=0, le=100)

    @field_validator("price_usd")
    @classmethod
    def price_must_be_realistic(cls, v: float) -> float:
        if v > 50_000:
            raise ValueError(f"price_usd {v} looks like a parsing error — rejected")
        return round(v, 4)

    @model_validator(mode="after")
    def compute_discount_if_missing(self) -> "PriceEvent":
        if (
            self.discount_pct is None
            and self.price_original_usd is not None
            and self.price_original_usd > self.price_usd
        ):
            self.discount_pct = round(
                (self.price_original_usd - self.price_usd)
                / self.price_original_usd * 100, 2
            )
        return self


class PriceEventBroadcast(BaseModel):
    """WebSocket broadcast payload sent to Angular clients on
    ``/ws/live-prices``. Leaner than ``PriceEvent`` — only what the
    frontend needs to update the UI."""
    canonical_product_id: str
    product_name:         str
    site:                 str
    listing_url:          str
    category:             SupplementCategory

    price_usd:            float
    price_before:         Optional[float]    = None
    drop_pct:             Optional[float]    = None
    is_price_drop:        bool               = False
    alert_type:           Optional[AlertType] = None

    scraped_at:           datetime
    broadcast_at:         datetime = Field(default_factory=datetime.utcnow)
