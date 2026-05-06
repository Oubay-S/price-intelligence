from __future__ import annotations

import statistics
from datetime import datetime, timedelta
from functools import lru_cache
from threading import RLock
from typing import Any, Optional

from cachetools import TTLCache, cached
from google.cloud import bigquery
from google.oauth2 import service_account

from app.config import settings
from app.models.product import (
    PriceHistory,
    PriceInfo,
    PricePoint,
    PriceTrend,
    ProductResponse,
    RatingsInfo,
    SupplementCategory,
)

# ---------------------------------------------------------------------------
# Schema-mapping tables — backing BigQuery table is the raw scraper mart
# (`price_intelligence.products`), not the analyst-curated mart the API
# domain models were originally designed against. These dictionaries bridge
# the two until dbt produces a richer table.
# ---------------------------------------------------------------------------

_RAW_TO_CATEGORY: dict[str, SupplementCategory] = {
    "basketball":    SupplementCategory.TEAM_BASKETBALL,
    "football":      SupplementCategory.TEAM_FOOTBALL,
    "volleyball":    SupplementCategory.TEAM_VOLLEYBALL,
    "racket-sports": SupplementCategory.TEAM_RACKET,
    "combat-sports": SupplementCategory.COMBAT_BOXING_MMA,
    "gym":           SupplementCategory.STRENGTH_HOME_GYM,
    "general":       SupplementCategory.STRENGTH_HOME_GYM,
}

_CATEGORY_TO_RAW: dict[SupplementCategory, list[str]] = {
    SupplementCategory.TEAM_BASKETBALL:   ["basketball"],
    SupplementCategory.TEAM_FOOTBALL:     ["football"],
    SupplementCategory.TEAM_VOLLEYBALL:   ["Volleyball"],
    SupplementCategory.TEAM_RACKET:       ["Racket-Sports"],
    SupplementCategory.COMBAT_BOXING_MMA: ["combat-sports"],
    SupplementCategory.STRENGTH_HOME_GYM: ["gym", "general"],
}

_STORE_CURRENCY: dict[str, str] = {"ebay": "USD", "walmart": "USD", "jumia": "MAD"}


@lru_cache(maxsize=1)
def get_client() -> bigquery.Client:
    creds = None
    if settings.GOOGLE_APPLICATION_CREDENTIALS:
        creds = service_account.Credentials.from_service_account_file(
            settings.GOOGLE_APPLICATION_CREDENTIALS
        )
    return bigquery.Client(project=settings.GCP_PROJECT_ID, credentials=creds)


def _table_ref() -> str:
    return (
        f"`{settings.GCP_PROJECT_ID}."
        f"{settings.BIGQUERY_DATASET}."
        f"{settings.BIGQUERY_TABLE}`"
    )


# ---------------------------------------------------------------------------
# Row-level helpers
# ---------------------------------------------------------------------------

def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        s = value.strip().replace(",", "").replace("$", "").replace("DH", "")
        if not s or s.upper() in ("N/A", "NA", "NULL"):
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
    return datetime.utcnow()


def _map_category(raw: Optional[str]) -> SupplementCategory:
    if not raw:
        return SupplementCategory.STRENGTH_HOME_GYM
    return _RAW_TO_CATEGORY.get(
        raw.strip().lower(), SupplementCategory.STRENGTH_HOME_GYM
    )


def _strip_title(value: Optional[str]) -> str:
    if not value:
        return ""
    return value.replace("Opens in a new window or tab", "").strip()


def _is_in_stock(availability: Optional[str]) -> bool:
    if not availability:
        return True
    a = availability.strip().lower()
    return "out" not in a and "unavail" not in a and a != "sold"


def _row_to_product(row: bigquery.Row) -> ProductResponse:
    current = _safe_float(row.get("current_price"))
    if current is None:
        current = 0.0  # rows with unparseable prices are filtered out in SQL
    original = _safe_float(row.get("price_before_discount"))
    stars    = _safe_float(row.get("stars"))
    store    = (row.get("store") or "").lower()
    name     = _strip_title(row.get("name")) or "(unknown)"

    pricing = PriceInfo(
        current=current,
        original=original,
        currency_raw=_STORE_CURRENCY.get(store, "USD"),
        trend=PriceTrend.STABLE,
    )

    ratings = (
        RatingsInfo(score=stars, count=0)
        if stars is not None and 0.0 <= stars <= 5.0
        else None
    )

    return ProductResponse(
        canonical_product_id=row["canonical_product_id"],
        name=name,
        site=store or "unknown",
        listing_url=row.get("product_url") or "",
        category=_map_category(row.get("category")),
        subcategory=row.get("category"),
        brand_raw=(name.split()[0] if name and name != "(unknown)" else "unknown"),
        in_stock=_is_in_stock(row.get("availability")),
        flavour=None,
        image_url=row.get("image_url") or None,
        pricing=pricing,
        ratings=ratings,
        scraped_at=_parse_dt(row.get("scraped_at")),
        data_quality_score=None,
    )


# ---------------------------------------------------------------------------
# Shared SQL fragments
# ---------------------------------------------------------------------------

def _select_columns() -> str:
    return f"""
        SELECT
            TO_HEX(SHA256(product_url)) AS canonical_product_id,
            name,
            current_price,
            price_before_discount,
            product_url,
            image_url,
            stars,
            availability,
            scraped_at,
            store,
            category
        FROM {_table_ref()}
    """


_PRICE_VALID = "SAFE_CAST(current_price AS FLOAT64) IS NOT NULL"


def _site_token(value: str) -> str:
    """Accept 'jumia', 'jumia.ma', 'jumia.co.ma' alike — match on store prefix."""
    return value.lower().split(".")[0].strip()


# ---------------------------------------------------------------------------
# get_all_products
# ---------------------------------------------------------------------------

_products_cache: TTLCache = TTLCache(maxsize=128, ttl=60)
_products_cache_lock = RLock()


@cached(cache=_products_cache, lock=_products_cache_lock)
def get_all_products(
    page: int = 1,
    limit: int = 48,
    site: Optional[str] = None,
    category: Optional[SupplementCategory] = None,
) -> tuple[list[ProductResponse], int]:
    where: list[str] = [_PRICE_VALID]
    offset = (page - 1) * limit
    params: list[Any] = [
        bigquery.ScalarQueryParameter("offset", "INT64", offset),
        bigquery.ScalarQueryParameter("limit", "INT64", limit),
    ]

    if site:
        where.append("LOWER(store) = @site")
        params.append(
            bigquery.ScalarQueryParameter("site", "STRING", _site_token(site))
        )

    if category is not None:
        raw_values = _CATEGORY_TO_RAW.get(category, [])
        if not raw_values:
            return [], 0
        where.append("category IN UNNEST(@categories)")
        params.append(
            bigquery.ArrayQueryParameter("categories", "STRING", raw_values)
        )

    where_sql = "WHERE " + " AND ".join(where)

    data_query = f"""
        {_select_columns()}
        {where_sql}
        ORDER BY scraped_at DESC
        LIMIT @limit
        OFFSET @offset
    """
    count_query = f"""
        SELECT COUNT(*) AS total_count
        FROM {_table_ref()}
        {where_sql}
    """

    job_config = bigquery.QueryJobConfig(query_parameters=params)
    rows = get_client().query(data_query, job_config=job_config).result()
    count_rows = get_client().query(count_query, job_config=job_config).result()
    total_count = int(next(iter(count_rows))["total_count"])

    return [_row_to_product(row) for row in rows], total_count


# ---------------------------------------------------------------------------
# search_products  (LIKE on product name)
# ---------------------------------------------------------------------------

_search_cache: TTLCache = TTLCache(maxsize=256, ttl=60)
_search_cache_lock = RLock()


def _escape_like(value: str) -> str:
    """Neutralise SQL-LIKE wildcards in user input — '%' and '_' must be literal."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@cached(cache=_search_cache, lock=_search_cache_lock)
def search_products(
    query: str,
    category: Optional[SupplementCategory] = None,
    page: int = 1,
    limit: int = 48,
) -> tuple[list[ProductResponse], int]:
    pattern = f"%{_escape_like(query.strip().lower())}%"
    offset = (page - 1) * limit

    where: list[str] = [
        _PRICE_VALID,
        "LOWER(name) LIKE @pattern",
    ]
    params: list[Any] = [
        bigquery.ScalarQueryParameter("pattern", "STRING", pattern),
        bigquery.ScalarQueryParameter("offset", "INT64", offset),
        bigquery.ScalarQueryParameter("limit", "INT64", limit),
    ]

    if category is not None:
        raw_values = _CATEGORY_TO_RAW.get(category, [])
        if not raw_values:
            return [], 0
        where.append("category IN UNNEST(@categories)")
        params.append(
            bigquery.ArrayQueryParameter("categories", "STRING", raw_values)
        )

    where_sql = "WHERE " + " AND ".join(where)

    data_query = f"""
        {_select_columns()}
        {where_sql}
        ORDER BY scraped_at DESC
        LIMIT @limit
        OFFSET @offset
    """
    count_query = f"""
        SELECT COUNT(*) AS total_count
        FROM {_table_ref()}
        {where_sql}
    """

    job_config = bigquery.QueryJobConfig(query_parameters=params)
    rows = get_client().query(data_query, job_config=job_config).result()
    count_rows = get_client().query(count_query, job_config=job_config).result()
    total_count = int(next(iter(count_rows))["total_count"])

    return [_row_to_product(row) for row in rows], total_count


# ---------------------------------------------------------------------------
# get_product_by_id  (id = TO_HEX(SHA256(product_url)))
# ---------------------------------------------------------------------------

_product_by_id_cache: TTLCache = TTLCache(maxsize=512, ttl=60)
_product_by_id_cache_lock = RLock()


@cached(cache=_product_by_id_cache, lock=_product_by_id_cache_lock)
def get_product_by_id(product_id: str) -> Optional[ProductResponse]:
    sql = f"""
        {_select_columns()}
        WHERE TO_HEX(SHA256(product_url)) = @product_id
          AND {_PRICE_VALID}
        ORDER BY scraped_at DESC
        LIMIT 1
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
        ]
    )
    rows = list(get_client().query(sql, job_config=job_config).result())
    return _row_to_product(rows[0]) if rows else None


# ---------------------------------------------------------------------------
# get_price_history  (time-series for one canonical product)
# ---------------------------------------------------------------------------

_price_history_cache: TTLCache = TTLCache(maxsize=256, ttl=60)
_price_history_cache_lock = RLock()

_SCRAPED_AT_TS = "SAFE.PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%E*S', scraped_at)"


def _discount_pct(current: float, original: Optional[float]) -> Optional[float]:
    if original is None or original <= 0 or current > original:
        return None
    return round((original - current) / original * 100, 2)


@cached(cache=_price_history_cache, lock=_price_history_cache_lock)
def get_price_history(
    product_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    site: Optional[str] = None,
) -> Optional[PriceHistory]:
    """
    Time-series for one canonical_product_id (= TO_HEX(SHA256(product_url))).
    Note: `price_usd` on each point is the raw scraped value — Jumia rows are
    actually MAD until dbt currency-normalises the mart. Document this in the
    router response if exposing externally.
    """
    where: list[str] = [
        "TO_HEX(SHA256(product_url)) = @product_id",
        _PRICE_VALID,
    ]
    params: list[Any] = [
        bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
    ]

    if start_date is not None:
        where.append(f"{_SCRAPED_AT_TS} >= @start_date")
        params.append(
            bigquery.ScalarQueryParameter("start_date", "TIMESTAMP", start_date)
        )

    if end_date is not None:
        where.append(f"{_SCRAPED_AT_TS} <= @end_date")
        params.append(
            bigquery.ScalarQueryParameter("end_date", "TIMESTAMP", end_date)
        )

    if site:
        where.append("LOWER(store) = @site")
        params.append(
            bigquery.ScalarQueryParameter("site", "STRING", _site_token(site))
        )

    sql = f"""
        {_select_columns()}
        WHERE {' AND '.join(where)}
        ORDER BY scraped_at ASC
    """

    job_config = bigquery.QueryJobConfig(query_parameters=params)
    rows = list(get_client().query(sql, job_config=job_config).result())
    if not rows:
        return None

    points: list[PricePoint] = []
    prices: list[float] = []
    product_name = ""

    for row in rows:
        current = _safe_float(row.get("current_price"))
        if current is None:
            continue
        original = _safe_float(row.get("price_before_discount"))
        ts = _parse_dt(row.get("scraped_at"))
        store = (row.get("store") or "unknown").lower()

        points.append(
            PricePoint(
                price_usd=current,
                site=store,
                scraped_at=ts,
                in_stock=_is_in_stock(row.get("availability")),
                discount_pct=_discount_pct(current, original),
            )
        )
        prices.append(current)
        if not product_name:
            product_name = _strip_title(row.get("name")) or "(unknown)"

    if not points:
        return None

    floor_cutoff = (end_date or points[-1].scraped_at) - timedelta(days=30)
    floor_30d = min(
        (p.price_usd for p in points if p.scraped_at >= floor_cutoff),
        default=None,
    )

    return PriceHistory(
        canonical_product_id=product_id,
        product_name=product_name,
        points=points,
        min_price=min(prices),
        max_price=max(prices),
        avg_price=round(statistics.fmean(prices), 4),
        median_price=round(statistics.median(prices), 4),
        floor_price_30d=floor_30d,
    )
