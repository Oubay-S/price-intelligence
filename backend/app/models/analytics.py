"""
models/analytics.py
===================
Response schemas for the Data Analyst dashboard endpoints (``/api/analytics/*``).

Each payload mirrors one file the analyst's ``export_for_dashboard.py`` writes
to ``data-analysis/outputs/app/``. Every list endpoint wraps its rows in an
envelope carrying ``generated_at`` so the frontend can show data freshness.

When the analysis moves to a BigQuery mart, these schemas stay the same — only
the repository's data source changes.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AnalyticsKpis(BaseModel):
    """Single object of global KPIs (``kpis.json`` -> ``data``)."""

    total_products: int
    total_stores: int
    total_categories: int
    average_price: float
    median_price: float
    minimum_price: float
    maximum_price: float
    average_discount: float
    first_scrape: Optional[datetime] = None
    last_scrape: Optional[datetime] = None


class StorePriceStat(BaseModel):
    """One row of ``price_by_store.json``."""

    store: str
    products: int
    average_price: float
    median_price: float
    min_price: float
    max_price: float
    std_price: float


class CategoryPriceStat(BaseModel):
    """One row of ``price_by_category.json``."""

    category: str
    products: int
    average_price: float
    median_price: float
    min_price: float
    max_price: float
    std_price: float


class TimeSeriesPoint(BaseModel):
    """One (date, store) point of ``time_series_by_store.json``."""

    scraped_date: str
    store: str
    products: int
    average_price: float
    median_price: float


class HeatmapCell(BaseModel):
    """One (store, category) cell of ``heatmap_store_category.json``."""

    store: str
    category: str
    products: int
    median_price: float
    average_price: float


class TopDiscount(BaseModel):
    """One product row of ``top_discounts.json``."""

    store: str
    category: str
    name: str
    price: float
    discount: float
    stars: float


class Recommendation(BaseModel):
    """One business recommendation of ``recommendations.json`` (French text)."""

    priorite: str
    recommandation: str
    justification: str


# ---------------------------------------------------------------------------
# Envelopes — every endpoint returns ``generated_at`` for freshness display.
# ---------------------------------------------------------------------------

class KpisResponse(BaseModel):
    generated_at: Optional[datetime] = None
    data: AnalyticsKpis


class PriceByStoreResponse(BaseModel):
    generated_at: Optional[datetime] = None
    data: list[StorePriceStat] = Field(default_factory=list)


class PriceByCategoryResponse(BaseModel):
    generated_at: Optional[datetime] = None
    data: list[CategoryPriceStat] = Field(default_factory=list)


class TimeSeriesResponse(BaseModel):
    generated_at: Optional[datetime] = None
    data: list[TimeSeriesPoint] = Field(default_factory=list)


class HeatmapResponse(BaseModel):
    generated_at: Optional[datetime] = None
    data: list[HeatmapCell] = Field(default_factory=list)


class TopDiscountsResponse(BaseModel):
    generated_at: Optional[datetime] = None
    data: list[TopDiscount] = Field(default_factory=list)


class RecommendationsResponse(BaseModel):
    generated_at: Optional[datetime] = None
    data: list[Recommendation] = Field(default_factory=list)
