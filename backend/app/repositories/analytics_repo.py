"""Analytics dashboard reads — the only layer that knows the data *source*.

Today every function reads one JSON file the Data Analyst's
``export_for_dashboard.py`` produced under ``settings.ANALYTICS_DATA_DIR``
(``data-analysis/outputs/app/``). The files share the envelope
``{"generated_at": ..., "data": ...}``; these functions return that raw dict
untouched — no Pydantic, no business logic (that belongs in the service).

When the data engineer lands the analysis as a BigQuery mart (run from the
scrape DAG), swap the body of ``_load`` for ``bigquery.Client`` queries against
the mart tables. Nothing above this module changes.

Raises ``NotFoundError`` when an expected export file is absent so the router
can map it to a 404 instead of leaking a raw filesystem error.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import settings
from app.repositories.exceptions import NotFoundError

# Logical name -> export filename. Keep in sync with export_for_dashboard.py.
_FILES: dict[str, str] = {
    "kpis": "kpis.json",
    "price_by_store": "price_by_store.json",
    "price_by_category": "price_by_category.json",
    "time_series_by_store": "time_series_by_store.json",
    "heatmap_store_category": "heatmap_store_category.json",
    "top_discounts": "top_discounts.json",
    "recommendations": "recommendations.json",
}


def _load(name: str) -> dict[str, Any]:
    path = Path(settings.ANALYTICS_DATA_DIR) / _FILES[name]
    if not path.is_file():
        raise NotFoundError(
            f"Analytics export {path.name!r} not found. Run the analyst's "
            "export_for_dashboard.py (or the analysis DAG) first."
        )
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def get_kpis() -> dict[str, Any]:
    return _load("kpis")


def get_price_by_store() -> dict[str, Any]:
    return _load("price_by_store")


def get_price_by_category() -> dict[str, Any]:
    return _load("price_by_category")


def get_time_series_by_store() -> dict[str, Any]:
    return _load("time_series_by_store")


def get_heatmap_store_category() -> dict[str, Any]:
    return _load("heatmap_store_category")


def get_top_discounts() -> dict[str, Any]:
    return _load("top_discounts")


def get_recommendations() -> dict[str, Any]:
    return _load("recommendations")
