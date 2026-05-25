"""Analytics dashboard orchestration.

Sits between the router and ``repositories/analytics_repo``. Responsibilities:

* call the repo (which owns the data source),
* validate raw dicts into the typed schemas in ``models/analytics``,
* apply presentation business rules — here, dropping the junk ``unknown``
  store/category buckets so the charts only show real marketplaces/sports.

No file or BigQuery access lives here; no SQL. Swapping the repo from JSON to
a BigQuery mart leaves this module untouched.
"""
from __future__ import annotations

from typing import Any

from app.models.analytics import (
    HeatmapResponse,
    KpisResponse,
    PriceByCategoryResponse,
    PriceByStoreResponse,
    RecommendationsResponse,
    TimeSeriesResponse,
    TopDiscountsResponse,
)
from app.repositories import analytics_repo

_UNKNOWN = "unknown"


def _drop_unknown(rows: list[dict[str, Any]], *keys: str) -> list[dict[str, Any]]:
    """Filter rows whose ``store``/``category`` is the junk ``unknown`` bucket."""
    return [
        row
        for row in rows
        if all(str(row.get(k, "")).strip().lower() != _UNKNOWN for k in keys)
    ]


def get_kpis() -> KpisResponse:
    payload = analytics_repo.get_kpis()
    return KpisResponse(generated_at=payload.get("generated_at"), data=payload["data"])


def get_price_by_store() -> PriceByStoreResponse:
    payload = analytics_repo.get_price_by_store()
    rows = _drop_unknown(payload.get("data", []), "store")
    return PriceByStoreResponse(generated_at=payload.get("generated_at"), data=rows)


def get_price_by_category() -> PriceByCategoryResponse:
    payload = analytics_repo.get_price_by_category()
    rows = _drop_unknown(payload.get("data", []), "category")
    return PriceByCategoryResponse(generated_at=payload.get("generated_at"), data=rows)


def get_time_series() -> TimeSeriesResponse:
    payload = analytics_repo.get_time_series_by_store()
    rows = _drop_unknown(payload.get("data", []), "store")
    return TimeSeriesResponse(generated_at=payload.get("generated_at"), data=rows)


def get_heatmap() -> HeatmapResponse:
    payload = analytics_repo.get_heatmap_store_category()
    rows = _drop_unknown(payload.get("data", []), "store", "category")
    return HeatmapResponse(generated_at=payload.get("generated_at"), data=rows)


def get_top_discounts() -> TopDiscountsResponse:
    payload = analytics_repo.get_top_discounts()
    rows = _drop_unknown(payload.get("data", []), "store", "category")
    return TopDiscountsResponse(generated_at=payload.get("generated_at"), data=rows)


def get_recommendations() -> RecommendationsResponse:
    payload = analytics_repo.get_recommendations()
    return RecommendationsResponse(
        generated_at=payload.get("generated_at"), data=payload.get("data", [])
    )
