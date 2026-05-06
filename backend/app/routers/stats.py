from fastapi import APIRouter, HTTPException, Query, status
from google.api_core.exceptions import GoogleAPICallError

from app.models.product import (
    BrandRankingsResponse,
    ProductStats,
    SupplementCategory,
)
from app.services.analytics import get_brand_rankings, get_product_stats

router = APIRouter()


def _raise_bigquery_http_500(exc: GoogleAPICallError) -> None:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"BigQuery error: {exc}",
    ) from exc


@router.get("/brands", response_model=BrandRankingsResponse)
def brand_rankings(
    category: SupplementCategory = Query(
        ..., description="Top-level category to rank brands within"
    ),
    limit: int = Query(20, ge=1, le=100),
) -> BrandRankingsResponse:
    try:
        return get_brand_rankings(category=category, limit=limit)
    except GoogleAPICallError as exc:
        _raise_bigquery_http_500(exc)


@router.get("/{product_id}", response_model=ProductStats)
def product_stats(
    product_id: str,
    period_days: int = Query(30, ge=7, le=365),
) -> ProductStats:
    try:
        result = get_product_stats(product_id=product_id, period_days=period_days)
    except GoogleAPICallError as exc:
        _raise_bigquery_http_500(exc)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No stats for product {product_id!r} over {period_days}-day window"
            ),
        )
    return result
