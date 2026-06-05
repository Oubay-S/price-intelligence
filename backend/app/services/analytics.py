"""
services/analytics.py
=====================
Read-only analytics queries.

Two flavours:

1. Mart-backed (assumes analyst's dbt pipeline produced the table):
       - mart_product_stats       — descriptive + predictive stats per product
       - mart_brand_rankings      — best-value brands per category
       - mart_site_prices         — latest per-(product, site) snapshot
   These functions only SELECT/filter — no math in Python.

2. On-the-fly (no mart dependency, runs window functions on the raw
   `products` table so the endpoints work before the mart exists):
       - get_price_drops          — LAG-based drop detection
       - get_trending_products    — most-dropped in last 24h
   When the analyst ships the equivalent marts, swap these back to a single
   SELECT against the mart and delete the window-function SQL.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from google.cloud import bigquery

from app.config import settings
from app.models.product import (
    AlertsResponse,
    AlertType,
    BrandRanking,
    BrandRankingsResponse,
    BrandTier,
    PriceDropAlert,
    PriceTrend,
    ProductComparison,
    ProductStats,
    SitePriceSnapshot,
    SupplementCategory,
    TrendingProduct,
    TrendingResponse,
)
from app.services.bigquery import (
    _CANON_ID,
    _CANON_URL,
    _CATEGORY_TO_RAW,
    _PRICE_CURRENCY,
    _discount_pct,
    _is_in_stock,
    _map_category,
    _parse_dt,
    _safe_float,
    _site_token,
    _strip_title,
    _table_ref,
    get_client,
)
from app.services.cache import redis_cached


def _mart_ref(table: str) -> str:
    return f"`{settings.GCP_PROJECT_ID}.{settings.BIGQUERY_DATASET}.{table}`"


def _category_to_string(category: SupplementCategory) -> str:
    return category.value


# ---------------------------------------------------------------------------
# get_product_stats — descriptive + predictive stats for one product
# ---------------------------------------------------------------------------
#
# Expected mart: `mart_product_stats`
#   canonical_product_id STRING,
#   product_name STRING,
#   period_days INT64,
#   mean_price FLOAT64,
#   median_price FLOAT64,
#   std_deviation FLOAT64,
#   min_price FLOAT64,
#   max_price FLOAT64,
#   coefficient_of_variation FLOAT64,
#   price_trend STRING,            -- 'rising' | 'falling' | 'stable'
#   velocity_per_day FLOAT64,
#   is_volatile BOOL,
#   estimated_floor_30d FLOAT64,
#   out_of_stock_probability FLOAT64,
#   total_observations INT64,
#   sites_tracked INT64
# ---------------------------------------------------------------------------

@redis_cached(prefix="analytics:get_product_stats", ttl=300, key_dim="product_id")
def get_product_stats(
    product_id: str,
    period_days: int = 30,
) -> Optional[ProductStats]:
    sql = f"""
        SELECT
            canonical_product_id,
            product_name,
            period_days,
            mean_price,
            median_price,
            std_deviation,
            min_price,
            max_price,
            coefficient_of_variation,
            price_trend,
            velocity_per_day,
            is_volatile,
            estimated_floor_30d,
            out_of_stock_probability,
            total_observations,
            sites_tracked
        FROM {_mart_ref(settings.BIGQUERY_MART_PRODUCT_STATS)}
        WHERE canonical_product_id = @product_id
          AND period_days = @period_days
        LIMIT 1
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
            bigquery.ScalarQueryParameter("period_days", "INT64", period_days),
        ]
    )
    rows = list(get_client().query(sql, job_config=job_config).result())
    if not rows:
        return None

    row = rows[0]
    return ProductStats(
        canonical_product_id=row["canonical_product_id"],
        product_name=row["product_name"],
        period_days=int(row["period_days"]),
        mean_price=float(row["mean_price"]),
        median_price=float(row["median_price"]),
        std_deviation=float(row["std_deviation"]),
        min_price=float(row["min_price"]),
        max_price=float(row["max_price"]),
        coefficient_of_variation=float(row["coefficient_of_variation"]),
        price_trend=PriceTrend(row["price_trend"]),
        velocity_per_day=float(row["velocity_per_day"]),
        is_volatile=bool(row["is_volatile"]),
        estimated_floor_30d=(
            float(row["estimated_floor_30d"])
            if row["estimated_floor_30d"] is not None
            else None
        ),
        out_of_stock_probability=(
            float(row["out_of_stock_probability"])
            if row["out_of_stock_probability"] is not None
            else None
        ),
        total_observations=int(row["total_observations"]),
        sites_tracked=int(row["sites_tracked"]),
    )


# ---------------------------------------------------------------------------
# get_brand_rankings — best-value brands per category
# ---------------------------------------------------------------------------
#
# Expected mart: `mart_brand_rankings`
#   brand_name STRING,
#   brand_tier STRING,             -- 'premium' | 'mid' | 'budget'
#   category STRING,               -- SupplementCategory.value
#   avg_price_usd FLOAT64,
#   avg_price_per_serving FLOAT64,
#   avg_rating FLOAT64,
#   total_products INT64,
#   sites_present ARRAY<STRING>,
#   rank INT64                     -- 1 = best value
# ---------------------------------------------------------------------------

@redis_cached(prefix="analytics:get_brand_rankings", ttl=300)
def get_brand_rankings(
    category: SupplementCategory,
    limit: int = 20,
) -> BrandRankingsResponse:
    sql = f"""
        SELECT
            brand_name,
            brand_tier,
            category,
            avg_price_usd,
            avg_price_per_serving,
            avg_rating,
            total_products,
            sites_present,
            rank
        FROM {_mart_ref(settings.BIGQUERY_MART_BRAND_RANKINGS)}
        WHERE category = @category
        ORDER BY rank ASC
        LIMIT @limit
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter(
                "category", "STRING", _category_to_string(category)
            ),
            bigquery.ScalarQueryParameter("limit", "INT64", limit),
        ]
    )
    rows = get_client().query(sql, job_config=job_config).result()

    rankings = [
        BrandRanking(
            brand_name=row["brand_name"],
            brand_tier=BrandTier(row["brand_tier"]),
            category=SupplementCategory(row["category"]),
            avg_price_usd=float(row["avg_price_usd"]),
            avg_price_per_serving=(
                float(row["avg_price_per_serving"])
                if row["avg_price_per_serving"] is not None
                else None
            ),
            avg_rating=float(row["avg_rating"]),
            total_products=int(row["total_products"]),
            sites_present=list(row["sites_present"] or []),
            rank=int(row["rank"]),
        )
        for row in rows
    ]
    return BrandRankingsResponse(category=category, rankings=rankings)


# ---------------------------------------------------------------------------
# get_price_drops — on-the-fly LAG window over the raw products table
# ---------------------------------------------------------------------------
# For each product_url, LAG() over scraped_at gives the previous scrape's
# price. Definition of a drop:
#       drop_pct = (price_before - price_after) / price_before * 100
# Filter: drop_pct >= @threshold AND price_after < price_before AND
#         price_before > 0 (defensive — divide-by-zero guard).
# Results de-duped to one row per (product_url, scraped_at) pair, ordered
# newest-first.
# Expensive scan; cached 5 minutes.
# ---------------------------------------------------------------------------

_TS_PARSE = "SAFE.PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%E*S', scraped_at)"

@redis_cached(prefix="analytics:get_price_drops", ttl=300)
def get_price_drops(
    threshold: float = 10.0,
    category: Optional[SupplementCategory] = None,
    site: Optional[str] = None,
    limit: int = 20,
) -> AlertsResponse:
    extra_where: list[str] = []
    params: list[Any] = [
        bigquery.ScalarQueryParameter("threshold", "FLOAT64", threshold),
        bigquery.ScalarQueryParameter("limit", "INT64", limit),
    ]

    if category is not None:
        raw_values = _CATEGORY_TO_RAW.get(category, [])
        if not raw_values:
            return AlertsResponse(alerts=[], count=0, threshold_pct=threshold)
        extra_where.append("raw_category IN UNNEST(@categories)")
        params.append(
            bigquery.ArrayQueryParameter("categories", "STRING", raw_values)
        )

    if site:
        extra_where.append("site = @site")
        params.append(
            bigquery.ScalarQueryParameter("site", "STRING", _site_token(site))
        )

    extra_sql = (" AND " + " AND ".join(extra_where)) if extra_where else ""

    sql = f"""
        WITH series AS (
            SELECT
                {_CANON_ID} AS canonical_product_id,
                name,
                image_url,
                LOWER(store) AS site,
                product_url AS listing_url,
                category AS raw_category,
                SAFE_CAST(current_price AS FLOAT64) AS price_after,
                {_TS_PARSE} AS scraped_ts,
                LAG(SAFE_CAST(current_price AS FLOAT64))
                    OVER (PARTITION BY {_CANON_URL} ORDER BY scraped_at ASC)
                    AS price_before
            FROM {_table_ref()}
            WHERE SAFE_CAST(current_price AS FLOAT64) IS NOT NULL
        )
        SELECT
            canonical_product_id,
            name,
            image_url,
            site,
            listing_url,
            raw_category,
            price_before,
            price_after,
            scraped_ts,
            ROUND(
                SAFE_DIVIDE(price_before - price_after, price_before) * 100,
                2
            ) AS drop_pct
        FROM series
        WHERE price_before IS NOT NULL
          AND price_before > 0
          AND price_after < price_before
          AND SAFE_DIVIDE(price_before - price_after, price_before) * 100
              >= @threshold
          {extra_sql}
        ORDER BY scraped_ts DESC
        LIMIT @limit
    """
    job_config = bigquery.QueryJobConfig(query_parameters=params)
    rows = get_client().query(sql, job_config=job_config).result()

    detected = datetime.utcnow()
    alerts: list[PriceDropAlert] = []
    for row in rows:
        site_name = row["site"] or "unknown"
        alerts.append(
            PriceDropAlert(
                canonical_product_id=row["canonical_product_id"],
                product_name=_strip_title(row["name"]) or "(unknown)",
                image_url=row.get("image_url") or None,
                site=site_name,
                listing_url=row["listing_url"] or "",
                category=_map_category(row["raw_category"]),
                price_before=float(row["price_before"]),
                price_after=float(row["price_after"]),
                currency=_PRICE_CURRENCY,
                drop_pct=float(row["drop_pct"]),
                alert_type=AlertType.PRICE_DROP,
                scraped_at=row["scraped_ts"] or detected,
                detected_at=detected,
                price_per_serving_after=None,
                price_per_kg_after=None,
            )
        )
    return AlertsResponse(
        alerts=alerts,
        count=len(alerts),
        threshold_pct=threshold,
    )


# ---------------------------------------------------------------------------
# get_trending_products — most-dropped products in the last 24 hours
# ---------------------------------------------------------------------------
# Reuses the LAG window from get_price_drops, but:
#   - filters drop events whose `scraped_ts` falls in the last @lookback hours
#     (default 24h — the only period currently exposed by the router),
#   - keeps the single biggest drop per canonical_product_id (one row per
#     product, not per scrape),
#   - ranks descending by drop_pct.
# Expensive scan; cached 5 minutes.
# ---------------------------------------------------------------------------

_PERIOD_HOURS: dict[str, int] = {"24h": 24, "7d": 24 * 7, "30d": 24 * 30}

@redis_cached(prefix="analytics:get_trending_products", ttl=300)
def get_trending_products(
    period: str = "24h",
    category: Optional[SupplementCategory] = None,
    limit: int = 20,
) -> TrendingResponse:
    lookback_hours = _PERIOD_HOURS.get(period, 24)
    extra_where: list[str] = []
    params: list[Any] = [
        bigquery.ScalarQueryParameter("lookback", "INT64", lookback_hours),
        bigquery.ScalarQueryParameter("limit", "INT64", limit),
    ]

    if category is not None:
        raw_values = _CATEGORY_TO_RAW.get(category, [])
        if not raw_values:
            return TrendingResponse(products=[], period=period)
        extra_where.append("raw_category IN UNNEST(@categories)")
        params.append(
            bigquery.ArrayQueryParameter("categories", "STRING", raw_values)
        )

    extra_sql = (" AND " + " AND ".join(extra_where)) if extra_where else ""

    sql = f"""
        WITH series AS (
            SELECT
                {_CANON_ID} AS canonical_product_id,
                name,
                image_url,
                LOWER(store) AS site,
                product_url AS listing_url,
                category AS raw_category,
                SAFE_CAST(current_price AS FLOAT64) AS price_after,
                {_TS_PARSE} AS scraped_ts,
                LAG(SAFE_CAST(current_price AS FLOAT64))
                    OVER (PARTITION BY {_CANON_URL} ORDER BY scraped_at ASC)
                    AS price_before
            FROM {_table_ref()}
            WHERE SAFE_CAST(current_price AS FLOAT64) IS NOT NULL
        ),
        events AS (
            SELECT
                canonical_product_id,
                name,
                image_url,
                site,
                listing_url,
                raw_category,
                price_after,
                scraped_ts,
                ROUND(
                    SAFE_DIVIDE(price_before - price_after, price_before) * 100,
                    2
                ) AS drop_pct
            FROM series
            WHERE price_before IS NOT NULL
              AND price_before > 0
              AND price_after < price_before
              AND scraped_ts >= TIMESTAMP_SUB(
                    CURRENT_TIMESTAMP(), INTERVAL @lookback HOUR
                  )
              {extra_sql}
        ),
        ranked AS (
            SELECT
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY canonical_product_id
                    ORDER BY drop_pct DESC, scraped_ts DESC
                ) AS pn
            FROM events
        )
        SELECT
            canonical_product_id,
            name,
            image_url,
            site,
            listing_url,
            raw_category,
            price_after,
            drop_pct
        FROM ranked
        WHERE pn = 1
        ORDER BY drop_pct DESC
        LIMIT @limit
    """
    job_config = bigquery.QueryJobConfig(query_parameters=params)
    rows = list(get_client().query(sql, job_config=job_config).result())

    products: list[TrendingProduct] = []
    for index, row in enumerate(rows, start=1):
        name = _strip_title(row["name"]) or "(unknown)"
        brand = name.split()[0] if name and name != "(unknown)" else "unknown"
        products.append(
            TrendingProduct(
                canonical_product_id=row["canonical_product_id"],
                product_name=name,
                image_url=row.get("image_url") or None,
                category=_map_category(row["raw_category"]),
                brand_raw=brand,
                brand_tier=BrandTier.MID,
                current_price=float(row["price_after"]),
                drop_pct=float(row["drop_pct"]),
                price_trend=PriceTrend.FALLING,
                best_site=row["site"] or "unknown",
                listing_url=row["listing_url"] or "",
                rating_score=None,
                tags=[],
                rank=index,
            )
        )
    return TrendingResponse(products=products, period=period)


# ---------------------------------------------------------------------------
# get_comparison_for_product — per-store snapshot from the raw products table
# ---------------------------------------------------------------------------
#
# There is no `mart_site_prices` mart yet, and the raw `products` table keys
# each listing by product_url (one row per store), so a canonical_product_id
# (= TO_HEX(SHA256(product_url))) resolves to a single store's latest scrape.
# We build the ProductComparison straight off the raw table; the compare page
# shows each selected product with its store. (Cross-store matching of the
# *same* product needs a canonical link the raw data doesn't carry — that's a
# future mart job.)
# ---------------------------------------------------------------------------

@redis_cached(prefix="analytics:get_comparison_for_product", ttl=60, key_dim="product_id")
def get_comparison_for_product(product_id: str) -> Optional[ProductComparison]:
    """
    Build a ProductComparison for one product from the raw `products` table.
    Returns None if the product_id has no rows.

    The compare endpoint calls this once per product_id under
    asyncio.to_thread + asyncio.gather so each BigQuery job runs in parallel.
    Keep this function synchronous — bigquery.Client.query is blocking.
    """
    sql = f"""
        SELECT
            {_CANON_ID} AS canonical_product_id,
            name,
            image_url,
            category,
            store,
            current_price,
            price_before_discount,
            product_url,
            availability,
            scraped_at
        FROM {_table_ref()}
        WHERE {_CANON_ID} = @product_id
          AND SAFE_CAST(current_price AS FLOAT64) IS NOT NULL
        QUALIFY ROW_NUMBER() OVER
            (PARTITION BY {_CANON_URL} ORDER BY scraped_at DESC) = 1
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
        ]
    )
    rows = list(get_client().query(sql, job_config=job_config).result())
    if not rows:
        return None

    sites_prices: list[SitePriceSnapshot] = []
    for row in rows:
        current = _safe_float(row.get("current_price"))
        if current is None:
            continue
        original = _safe_float(row.get("price_before_discount"))
        sites_prices.append(
            SitePriceSnapshot(
                site=(row.get("store") or "unknown").lower(),
                price_usd=current,
                original_price=original,
                discount_pct=_discount_pct(current, original),
                listing_url=row.get("product_url") or "",
                in_stock=_is_in_stock(row.get("availability")),
                last_seen=_parse_dt(row.get("scraped_at")),
                shipping_cost=None,
                landed_cost=None,
            )
        )
    if not sites_prices:
        return None

    first = rows[0]
    prices = [s.price_usd for s in sites_prices]
    min_price = min(prices)
    max_price = max(prices)
    best_site = next(s.site for s in sites_prices if s.price_usd == min_price)
    worst_site = next(s.site for s in sites_prices if s.price_usd == max_price)
    gap_pct = (
        round((max_price - min_price) / min_price * 100, 2)
        if min_price > 0
        else 0.0
    )

    return ProductComparison(
        canonical_product_id=first["canonical_product_id"],
        product_name=_strip_title(first.get("name")) or "(unknown)",
        image_url=first.get("image_url") or None,
        category=_map_category(first.get("category")),
        sites_prices=sites_prices,
        best_site=best_site,
        worst_site=worst_site,
        price_gap_pct=gap_pct,
    )
