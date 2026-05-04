from functools import lru_cache
from threading import RLock
from typing import Optional

from cachetools import TTLCache, cached
from google.cloud import bigquery
from google.oauth2 import service_account

from app.config import settings
from app.models.product import (
    BrandInfo,
    BrandTier,
    PriceInfo,
    PriceTrend,
    ProductResponse,
    RatingsInfo,
    SupplementCategory,
)


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


def _row_to_product(row: bigquery.Row) -> ProductResponse:
    brand_tier_raw = row.get("brand_tier") or BrandTier.MID.value
    brand = None
    if row.get("brand_id"):
        brand = BrandInfo(
            brand_id=row["brand_id"],
            name=row.get("brand_name") or row["brand_raw"],
            country=row.get("brand_country"),
            tier=BrandTier(brand_tier_raw),
            verified=bool(row.get("brand_verified") or False),
        )

    pricing = PriceInfo(
        current=float(row["price_usd"]),
        original=float(row["price_original_usd"]) if row.get("price_original_usd") is not None else None,
        currency_raw=row.get("currency_raw") or "USD",
        per_serving=float(row["price_per_serving"]) if row.get("price_per_serving") is not None else None,
        per_100g=float(row["price_per_100g"]) if row.get("price_per_100g") is not None else None,
        per_kg=float(row["price_per_kg"]) if row.get("price_per_kg") is not None else None,
        discount_pct=float(row["discount_pct"]) if row.get("discount_pct") is not None else None,
        trend=PriceTrend(row.get("price_trend") or PriceTrend.STABLE.value),
        velocity_per_day=float(row["velocity_per_day"]) if row.get("velocity_per_day") is not None else None,
    )

    ratings = None
    if row.get("rating_score") is not None:
        ratings = RatingsInfo(
            score=float(row["rating_score"]),
            count=int(row.get("review_count") or 0),
            composite_score=float(row["composite_score"]) if row.get("composite_score") is not None else None,
        )

    return ProductResponse(
        canonical_product_id=row["canonical_product_id"],
        name=row["product_title"],
        site=row["site"],
        listing_url=row["listing_url"],
        category=SupplementCategory(row["category"]),
        subcategory=row.get("subcategory"),
        brand_raw=row["brand_raw"],
        in_stock=bool(row.get("in_stock") if row.get("in_stock") is not None else True),
        brand=brand,
        flavour=row.get("flavour"),
        image_url=row.get("image_url"),
        pricing=pricing,
        ratings=ratings,
        certifications=list(row.get("certifications") or []),
        tags=list(row.get("tags") or []),
        purpose_tags=list(row.get("purpose_tags") or []),
        brand_tier=BrandTier(brand_tier_raw),
        scraped_at=row["scraped_at"],
        data_quality_score=row.get("data_quality_score"),
    )


_products_cache: TTLCache = TTLCache(maxsize=128, ttl=60)
_products_cache_lock = RLock()


@cached(cache=_products_cache, lock=_products_cache_lock)
def get_all_products(
    page: int = 1,
    limit: int = 48,
    site: Optional[str] = None,
    category: Optional[SupplementCategory] = None,
) -> tuple[list[ProductResponse], int]:
    where: list[str] = []
    offset = (page - 1) * limit
    params: list[bigquery.ScalarQueryParameter] = [
        bigquery.ScalarQueryParameter("offset", "INT64", offset),
        bigquery.ScalarQueryParameter("limit", "INT64", limit),
    ]

    if site:
        where.append("site = @site")
        params.append(bigquery.ScalarQueryParameter("site", "STRING", site))

    if category is not None:
        where.append("category = @category")
        params.append(
            bigquery.ScalarQueryParameter("category", "STRING", category.value)
        )

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    data_query = f"""
        SELECT *
        FROM {_table_ref()}
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


_search_cache: TTLCache = TTLCache(maxsize=256, ttl=60)
_search_cache_lock = RLock()


def _escape_like(value: str) -> str:
    """Neutralise SQL-LIKE wildcards in user input — '%' and '_' must be literal."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


_SEARCH_PRODUCTS_SQL = f"""
    SELECT *
    FROM {_table_ref()}
    WHERE (LOWER(product_title) LIKE @pattern ESCAPE '\\\\'
        OR LOWER(brand_raw)     LIKE @pattern ESCAPE '\\\\')
      AND (@category IS NULL OR category = @category)
    ORDER BY
        CASE WHEN LOWER(product_title) LIKE @pattern ESCAPE '\\\\' THEN 0 ELSE 1 END,
        scraped_at DESC
    LIMIT @limit
    OFFSET @offset
"""

_SEARCH_PRODUCTS_COUNT_SQL = f"""
    SELECT COUNT(*) AS total_count
    FROM {_table_ref()}
    WHERE (LOWER(product_title) LIKE @pattern ESCAPE '\\\\'
        OR LOWER(brand_raw)     LIKE @pattern ESCAPE '\\\\')
      AND (@category IS NULL OR category = @category)
"""


@cached(cache=_search_cache, lock=_search_cache_lock)
def search_products(
    query: str,
    category: Optional[SupplementCategory] = None,
    page: int = 1,
    limit: int = 48,
) -> tuple[list[ProductResponse], int]:
    pattern = f"%{_escape_like(query.strip().lower())}%"
    offset = (page - 1) * limit

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("pattern", "STRING", pattern),
            bigquery.ScalarQueryParameter(
                "category", "STRING", category.value if category else None
            ),
            bigquery.ScalarQueryParameter("offset", "INT64", offset),
            bigquery.ScalarQueryParameter("limit", "INT64", limit),
        ]
    )
    rows = get_client().query(_SEARCH_PRODUCTS_SQL, job_config=job_config).result()
    count_rows = get_client().query(_SEARCH_PRODUCTS_COUNT_SQL, job_config=job_config).result()
    total_count = int(next(iter(count_rows))["total_count"])
    return [_row_to_product(row) for row in rows], total_count


_product_by_id_cache: TTLCache = TTLCache(maxsize=512, ttl=60)
_product_by_id_cache_lock = RLock()


_GET_PRODUCT_BY_ID_SQL = f"""
    SELECT *
    FROM {_table_ref()}
    WHERE canonical_product_id = @product_id
    ORDER BY scraped_at DESC
    LIMIT 1
"""


@cached(cache=_product_by_id_cache, lock=_product_by_id_cache_lock)
def get_product_by_id(product_id: str) -> Optional[ProductResponse]:
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
        ]
    )
    rows = list(
        get_client().query(_GET_PRODUCT_BY_ID_SQL, job_config=job_config).result()
    )
    return _row_to_product(rows[0]) if rows else None
