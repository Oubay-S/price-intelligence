from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from google.api_core.exceptions import GoogleAPICallError

from app.models.product import (
    AlertsResponse,
    CompareParams,
    CompareResponse,
    PriceHistory,
    PriceHistoryParams,
    SupplementCategory,
)
from app.services.analytics import get_price_drops, get_product_comparison
from app.services.bigquery import get_price_history

router = APIRouter()


def _raise_bigquery_http_500(exc: GoogleAPICallError) -> None:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"BigQuery error: {exc}",
    ) from exc


@router.get("/drops", response_model=AlertsResponse)
def price_drops(
    threshold: float = Query(10.0, ge=1, le=100, description="Minimum drop_pct"),
    category: Optional[SupplementCategory] = Query(None),
    site: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> AlertsResponse:
    try:
        return get_price_drops(
            threshold=threshold,
            category=category,
            site=site,
            limit=limit,
        )
    except GoogleAPICallError as exc:
        _raise_bigquery_http_500(exc)


@router.get("/compare", response_model=CompareResponse)
def compare(params: CompareParams = Depends()) -> CompareResponse:
    try:
        return get_product_comparison(product_ids=tuple(params.product_ids))
    except GoogleAPICallError as exc:
        _raise_bigquery_http_500(exc)


@router.get("/{product_id}/history", response_model=PriceHistory)
def price_history(
    product_id: str,
    params: PriceHistoryParams = Depends(),
) -> PriceHistory:
    try:
        history = get_price_history(
            product_id=product_id,
            start_date=params.start_date,
            end_date=params.end_date,
            site=params.site,
        )
    except GoogleAPICallError as exc:
        _raise_bigquery_http_500(exc)

    if history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No price history for product {product_id!r}",
        )
    return history
