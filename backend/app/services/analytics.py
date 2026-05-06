"""
services/analytics.py
=====================
Read-only queries against the analyst-curated dbt mart tables. Each function
performs a single SELECT, projects directly onto a Pydantic response model,
and does no business logic. If a mart schema drifts, fix dbt — never push
the math down here.

Mart tables expected (names configurable via settings):
    - mart_product_stats       — descriptive + predictive stats per product
    - mart_brand_rankings      — best-value brands per category
    - mart_price_drops         — recent significant drops (alert feed)
    - mart_trending            — products ranked by drop_pct / view velocity
    - mart_site_prices         — latest per-(product, site) snapshot
"""
from __future__ import annotations

from threading import RLock
from typing import Any, Optional

from cachetools import TTLCache, cached
from google.cloud import bigquery

from app.config import settings
from app.models.product import (
    AlertsResponse,
    AlertType,
    BrandRanking,
    BrandRankingsResponse,
    BrandTier,
    CompareResponse,
    PriceDropAlert,
    PriceTrend,
    ProductComparison,
    ProductStats,
    SitePriceSnapshot,
    SupplementCategory,
    TrendingProduct,
    TrendingResponse,
)
from app.services.bigquery import _parse_dt, _site_token, get_client


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

_product_stats_cache: TTLCache = TTLCache(maxsize=512, ttl=300)
_product_stats_cache_lock = RLock()


@cached(cache=_product_stats_cache, lock=_product_stats_cache_lock)
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

_brand_rankings_cache: TTLCache = TTLCache(maxsize=64, ttl=300)
_brand_rankings_cache_lock = RLock()


@cached(cache=_brand_rankings_cache, lock=_brand_rankings_cache_lock)
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
# get_price_drops — recent significant price drops (alert feed)
# ---------------------------------------------------------------------------
#
# Expected mart: `mart_price_drops`
#   canonical_product_id STRING,
#   product_name STRING,
#   image_url STRING,
#   site STRING,
#   listing_url STRING,
#   category STRING,
#   price_before FLOAT64,
#   price_after FLOAT64,
#   currency STRING,
#   drop_pct FLOAT64,
#   alert_type STRING,                 -- 'price_drop' | 'back_in_stock' | ...
#   scraped_at TIMESTAMP,
#   detected_at TIMESTAMP,
#   price_per_serving_after FLOAT64,
#   price_per_kg_after FLOAT64
# ---------------------------------------------------------------------------

_price_drops_cache: TTLCache = TTLCache(maxsize=128, ttl=60)
_price_drops_cache_lock = RLock()


@cached(cache=_price_drops_cache, lock=_price_drops_cache_lock)
def get_price_drops(
    threshold: float = 10.0,
    category: Optional[SupplementCategory] = None,
    site: Optional[str] = None,
    limit: int = 20,
) -> AlertsResponse:
    where: list[str] = ["drop_pct >= @threshold"]
    params: list[Any] = [
        bigquery.ScalarQueryParameter("threshold", "FLOAT64", threshold),
        bigquery.ScalarQueryParameter("limit", "INT64", limit),
    ]

    if category is not None:
        where.append("category = @category")
        params.append(
            bigquery.ScalarQueryParameter(
                "category", "STRING", _category_to_string(category)
            )
        )

    if site:
        where.append("LOWER(site) = @site")
        params.append(
            bigquery.ScalarQueryParameter("site", "STRING", _site_token(site))
        )

    sql = f"""
        SELECT
            canonical_product_id,
            product_name,
            image_url,
            site,
            listing_url,
            category,
            price_before,
            price_after,
            currency,
            drop_pct,
            alert_type,
            scraped_at,
            detected_at,
            price_per_serving_after,
            price_per_kg_after
        FROM {_mart_ref(settings.BIGQUERY_MART_PRICE_DROPS)}
        WHERE {' AND '.join(where)}
        ORDER BY detected_at DESC
        LIMIT @limit
    """
    job_config = bigquery.QueryJobConfig(query_parameters=params)
    rows = get_client().query(sql, job_config=job_config).result()

    alerts = [
        PriceDropAlert(
            canonical_product_id=row["canonical_product_id"],
            product_name=row["product_name"],
            image_url=row.get("image_url"),
            site=row["site"],
            listing_url=row["listing_url"],
            category=SupplementCategory(row["category"]),
            price_before=float(row["price_before"]),
            price_after=float(row["price_after"]),
            currency=row["currency"] or "USD",
            drop_pct=float(row["drop_pct"]),
            alert_type=AlertType(row["alert_type"]),
            scraped_at=_parse_dt(row["scraped_at"]),
            detected_at=_parse_dt(row["detected_at"]),
            price_per_serving_after=(
                float(row["price_per_serving_after"])
                if row["price_per_serving_after"] is not None
                else None
            ),
            price_per_kg_after=(
                float(row["price_per_kg_after"])
                if row["price_per_kg_after"] is not None
                else None
            ),
        )
        for row in rows
    ]
    return AlertsResponse(
        alerts=alerts,
        count=len(alerts),
        threshold_pct=threshold,
    )


# ---------------------------------------------------------------------------
# get_trending_products — ranked by drop_pct or view velocity
# ---------------------------------------------------------------------------
#
# Expected mart: `mart_trending`
#   canonical_product_id STRING,
#   product_name STRING,
#   image_url STRING,
#   category STRING,
#   brand_raw STRING,
#   brand_tier STRING,
#   current_price FLOAT64,
#   drop_pct FLOAT64,
#   price_trend STRING,
#   best_site STRING,
#   listing_url STRING,
#   rating_score FLOAT64,
#   tags ARRAY<STRING>,
#   rank INT64,
#   period STRING                       -- '24h' | '7d' | '30d'
# ---------------------------------------------------------------------------

_trending_cache: TTLCache = TTLCache(maxsize=64, ttl=120)
_trending_cache_lock = RLock()


@cached(cache=_trending_cache, lock=_trending_cache_lock)
def get_trending_products(
    period: str = "24h",
    category: Optional[SupplementCategory] = None,
    limit: int = 20,
) -> TrendingResponse:
    where: list[str] = ["period = @period"]
    params: list[Any] = [
        bigquery.ScalarQueryParameter("period", "STRING", period),
        bigquery.ScalarQueryParameter("limit", "INT64", limit),
    ]

    if category is not None:
        where.append("category = @category")
        params.append(
            bigquery.ScalarQueryParameter(
                "category", "STRING", _category_to_string(category)
            )
        )

    sql = f"""
        SELECT
            canonical_product_id,
            product_name,
            image_url,
            category,
            brand_raw,
            brand_tier,
            current_price,
            drop_pct,
            price_trend,
            best_site,
            listing_url,
            rating_score,
            tags,
            rank
        FROM {_mart_ref(settings.BIGQUERY_MART_TRENDING)}
        WHERE {' AND '.join(where)}
        ORDER BY rank ASC
        LIMIT @limit
    """
    job_config = bigquery.QueryJobConfig(query_parameters=params)
    rows = get_client().query(sql, job_config=job_config).result()

    products = [
        TrendingProduct(
            canonical_product_id=row["canonical_product_id"],
            product_name=row["product_name"],
            image_url=row.get("image_url"),
            category=SupplementCategory(row["category"]),
            brand_raw=row["brand_raw"],
            brand_tier=BrandTier(row["brand_tier"]),
            current_price=float(row["current_price"]),
            drop_pct=(
                float(row["drop_pct"])
                if row["drop_pct"] is not None
                else None
            ),
            price_trend=PriceTrend(row["price_trend"]),
            best_site=row["best_site"],
            listing_url=row["listing_url"],
            rating_score=(
                float(row["rating_score"])
                if row["rating_score"] is not None
                else None
            ),
            tags=list(row["tags"] or []),
            rank=int(row["rank"]),
        )
        for row in rows
    ]
    return TrendingResponse(products=products, period=period)


# ---------------------------------------------------------------------------
# get_product_comparison — cross-site snapshot for 2-4 products
# ---------------------------------------------------------------------------
#
# Expected mart: `mart_site_prices` (one row per (product, site) latest snapshot)
#   canonical_product_id STRING,
#   product_name STRING,
#   image_url STRING,
#   category STRING,
#   site STRING,
#   price_usd FLOAT64,
#   original_price FLOAT64,
#   discount_pct FLOAT64,
#   listing_url STRING,
#   in_stock BOOL,
#   last_seen TIMESTAMP,
#   shipping_cost FLOAT64,
#   landed_cost FLOAT64
# ---------------------------------------------------------------------------

_compare_cache: TTLCache = TTLCache(maxsize=256, ttl=60)
_compare_cache_lock = RLock()


def _comparison_cache_key(product_ids: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted(product_ids))


@cached(cache=_compare_cache, lock=_compare_cache_lock, key=_comparison_cache_key)
def get_product_comparison(
    product_ids: tuple[str, ...],
) -> CompareResponse:
    if not product_ids:
        return CompareResponse(products=[])

    sql = f"""
        SELECT
            canonical_product_id,
            product_name,
            image_url,
            category,
            site,
            price_usd,
            original_price,
            discount_pct,
            listing_url,
            in_stock,
            last_seen,
            shipping_cost,
            landed_cost
        FROM {_mart_ref(settings.BIGQUERY_MART_SITE_PRICES)}
        WHERE canonical_product_id IN UNNEST(@product_ids)
        ORDER BY canonical_product_id, price_usd ASC
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter(
                "product_ids", "STRING", list(product_ids)
            ),
        ]
    )
    rows = list(get_client().query(sql, job_config=job_config).result())

    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        pid = row["canonical_product_id"]
        bucket = grouped.setdefault(
            pid,
            {
                "product_name": row["product_name"],
                "image_url": row.get("image_url"),
                "category": SupplementCategory(row["category"]),
                "sites": [],
            },
        )
        bucket["sites"].append(
            SitePriceSnapshot(
                site=row["site"],
                price_usd=float(row["price_usd"]),
                original_price=(
                    float(row["original_price"])
                    if row["original_price"] is not None
                    else None
                ),
                discount_pct=(
                    float(row["discount_pct"])
                    if row["discount_pct"] is not None
                    else None
                ),
                listing_url=row["listing_url"],
                in_stock=bool(row["in_stock"]),
                last_seen=_parse_dt(row["last_seen"]),
                shipping_cost=(
                    float(row["shipping_cost"])
                    if row["shipping_cost"] is not None
                    else None
                ),
                landed_cost=(
                    float(row["landed_cost"])
                    if row["landed_cost"] is not None
                    else None
                ),
            )
        )

    products: list[ProductComparison] = []
    for pid, bucket in grouped.items():
        sites: list[SitePriceSnapshot] = bucket["sites"]
        if not sites:
            continue
        prices = [s.price_usd for s in sites]
        min_price = min(prices)
        max_price = max(prices)
        best_site = next(s.site for s in sites if s.price_usd == min_price)
        worst_site = next(s.site for s in sites if s.price_usd == max_price)
        gap_pct = (
            round((max_price - min_price) / min_price * 100, 2)
            if min_price > 0
            else 0.0
        )
        products.append(
            ProductComparison(
                canonical_product_id=pid,
                product_name=bucket["product_name"],
                image_url=bucket["image_url"],
                category=bucket["category"],
                sites=sites,
                best_site=best_site,
                worst_site=worst_site,
                price_gap_pct=gap_pct,
            )
        )

    return CompareResponse(products=products)
