"""Statistics DTOs for ``GET /stats/*``."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.enums import BrandTier, PriceTrend, SupplementCategory


class ProductStats(BaseModel):
    """Descriptive stats for one canonical product. Returned by
    ``GET /stats/{product_id}``."""
    canonical_product_id:  str
    product_name:          str
    period_days:           int = Field(30, description="Window used to compute stats")

    # descriptive
    mean_price:               float
    median_price:             float
    std_deviation:            float
    min_price:                float
    max_price:                float
    coefficient_of_variation: float = Field(
        ..., description="std / mean — > 0.15 flags the product as volatile"
    )

    # trend & velocity
    price_trend:      PriceTrend
    velocity_per_day: float = Field(
        ..., description="(price_today - price_7d_ago) / 7  — negative = falling"
    )
    is_volatile:      bool  = Field(
        ..., description="True when coefficient_of_variation > 0.15"
    )

    # predictive
    estimated_floor_30d:      Optional[float] = Field(
        None, description="Predicted lowest price in the next 30 days"
    )
    out_of_stock_probability: Optional[float] = Field(
        None, ge=0, le=1,
        description="Logistic regression output — > 0.7 triggers 'buy soon' alert"
    )

    total_observations: int
    sites_tracked:      int


class BrandRanking(BaseModel):
    """One brand's aggregated performance within a category. Returned by
    ``GET /stats/brands``."""
    brand_name:            str
    brand_tier:            BrandTier
    category:              SupplementCategory
    avg_price_usd:         float
    avg_price_per_serving: Optional[float] = None
    avg_rating:            float
    total_products:        int
    sites_present:         list[str] = Field(default_factory=list)
    rank:                  int = Field(..., description="1 = best value in category")


class BrandRankingsResponse(BaseModel):
    """Response envelope for ``GET /stats/brands``."""
    category:     SupplementCategory
    rankings:     list[BrandRanking]
    generated_at: datetime = Field(default_factory=datetime.utcnow)
