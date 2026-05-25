"""Analytics dashboard reads — the only layer that knows the data *source*.

The Data Analyst's analysis is published to BigQuery by the Airflow DAG
(``upload_analysis_to_bigquery`` task → 7 ``analytics_*`` tables in
``GCP_PROJECT_ID.BIGQUERY_DATASET``). Each function returns the same envelope
the rest of the stack already expects — ``{"generated_at": ..., "data": ...}`` —
so the service / router / models / frontend are untouched by this swap.

The upload flattens that envelope into columns: every table carries a
``generated_at`` column per row, and ``analytics_kpis`` is a single row whose
columns are the KPI fields (plus ``source_file``). These functions rebuild the
envelope from the rows.

BigQuery is queried first; if it is unreachable (e.g. pure-local dev with no
network) we fall back to the Data Analyst's static JSON exports under
``settings.ANALYTICS_DATA_DIR`` so the endpoints keep working. ``NotFoundError``
is raised when neither source yields data, so the router maps it to a 404.
"""
from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import settings
from app.repositories.exceptions import NotFoundError

logger = logging.getLogger(__name__)

# Logical name -> (BigQuery table, JSON fallback file). Keep in sync with
# data-analysis/upload_analysis_to_bigquery.py and export_for_dashboard.py.
_SOURCES: dict[str, tuple[str, str]] = {
    "kpis": ("analytics_kpis", "kpis.json"),
    "price_by_store": ("analytics_price_by_store", "price_by_store.json"),
    "price_by_category": ("analytics_price_by_category", "price_by_category.json"),
    "time_series_by_store": ("analytics_time_series_by_store", "time_series_by_store.json"),
    "heatmap_store_category": ("analytics_heatmap_store_category", "heatmap_store_category.json"),
    "top_discounts": ("analytics_top_discounts", "top_discounts.json"),
    "recommendations": ("analytics_recommendations", "recommendations.json"),
}

# Envelope-level columns the upload script adds — kept out of the row payload.
_ENVELOPE_COLS = ("generated_at", "source_file")

# Optional ordering to preserve the analyst's intent (load jobs don't keep
# dataframe row order). Only set where the order is meaningful to the UI.
_ORDER_BY: dict[str, str] = {
    "top_discounts": "discount DESC",
    "time_series_by_store": "scraped_date ASC",
}

# kpis is the only single-row table — its columns *are* the data dict.
_SINGLE_ROW = {"kpis"}


@lru_cache
def _bq_client() -> Any:
    from google.cloud import bigquery

    # Use the explicit service-account file (settings, not os.environ) so this
    # works both in-container (creds mounted) and in local uvicorn runs where
    # GOOGLE_APPLICATION_CREDENTIALS isn't exported to the process env.
    creds_path = settings.GOOGLE_APPLICATION_CREDENTIALS
    if creds_path and os.path.isfile(creds_path):
        return bigquery.Client.from_service_account_json(creds_path, project=settings.GCP_PROJECT_ID)
    return bigquery.Client(project=settings.GCP_PROJECT_ID)


def _load_bq(name: str) -> dict[str, Any]:
    table = _SOURCES[name][0]
    table_id = f"{settings.GCP_PROJECT_ID}.{settings.BIGQUERY_DATASET}.{table}"
    order = _ORDER_BY.get(name)
    query = f"SELECT * FROM `{table_id}`" + (f" ORDER BY {order}" if order else "")

    rows = [dict(row) for row in _bq_client().query(query).result()]
    if not rows:
        raise NotFoundError(f"Analytics table {table!r} is empty.")

    generated_at = rows[0].get("generated_at")

    if name in _SINGLE_ROW:
        data = {k: v for k, v in rows[0].items() if k not in _ENVELOPE_COLS}
        return {"generated_at": generated_at, "data": data}

    data = [{k: v for k, v in row.items() if k not in _ENVELOPE_COLS} for row in rows]
    return {"generated_at": generated_at, "data": data}


def _load_json(name: str) -> dict[str, Any]:
    path = Path(settings.ANALYTICS_DATA_DIR) / _SOURCES[name][1]
    if not path.is_file():
        raise NotFoundError(
            f"Analytics source for {name!r} unavailable: BigQuery failed and the "
            f"JSON fallback {path.name!r} is missing."
        )
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _load(name: str) -> dict[str, Any]:
    try:
        return _load_bq(name)
    except NotFoundError:
        raise
    except Exception as exc:  # BQ unreachable / auth / lib missing — fall back.
        logger.warning("BigQuery analytics read for %r failed (%s); using JSON fallback.", name, exc)
        return _load_json(name)


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
