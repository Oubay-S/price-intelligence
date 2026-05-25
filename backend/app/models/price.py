"""Price-history + cross-site comparison DTOs.

Used by ``GET /prices/{id}/history`` and ``GET /prices/compare``.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.enums import SupplementCategory
from app.models.product import EquipmentInfo, NutritionInfo


class PricePoint(BaseModel):
    """Single price observation in a time-series."""
    price_usd:    float = Field(..., ge=0)
    site:         str
    scraped_at:   datetime
    in_stock:     bool  = True
    discount_pct: Optional[float] = None


class PriceHistory(BaseModel):
    """Full price history for one canonical product."""
    canonical_product_id: str
    product_name:         str
    points:               list[PricePoint]
    # pre-computed summary (analyst mart)
    min_price:            float
    max_price:            float
    avg_price:            float
    median_price:         float
    floor_price_30d:      Optional[float] = Field(
        None, description="Rolling 30-day minimum — analyst's price floor proxy"
    )


class SitePriceSnapshot(BaseModel):
    """Cheapest current price for one product on one site."""
    site:           str
    price_usd:      float
    original_price: Optional[float] = None
    discount_pct:   Optional[float] = None
    listing_url:    str
    in_stock:       bool
    last_seen:      datetime
    shipping_cost:  Optional[float] = None
    landed_cost:    Optional[float] = Field(
        None, description="price_usd + shipping_cost — Moroccan market localisation"
    )


class ProductComparison(BaseModel):
    """Cross-site comparison for a single canonical product. Returned by
    ``GET /prices/compare``."""
    canonical_product_id: str
    product_name:         str
    image_url:            Optional[str]           = None
    category:             SupplementCategory
    nutrition:            Optional[NutritionInfo] = None
    equipment:            Optional[EquipmentInfo] = None
    sites_prices:         list[SitePriceSnapshot]
    best_site:            str   = Field(..., description="Site with lowest current price")
    worst_site:           str   = Field(..., description="Site with highest current price")
    price_gap_pct:        float = Field(
        ..., description="(max - min) / min * 100 across all sites"
    )
    tags:                 list[str] = Field(default_factory=list)


class CompareResponse(BaseModel):
    """Response envelope for ``GET /prices/compare``."""
    products:     list[ProductComparison]
    generated_at: datetime = Field(default_factory=datetime.utcnow)
