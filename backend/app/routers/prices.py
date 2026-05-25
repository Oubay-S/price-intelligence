"""Price endpoints: drops, compare, history.

Routers do parse + dispatch + exception → HTTP mapping. Compare logic
(dedup + cap + parallel BQ fan-out) lives in
``app.services.compare_service``.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from google.api_core.exceptions import GoogleAPICallError

from app.api_responses import ERR_400, ERR_404, ERR_422, ERR_500
from app.models.product import (
    AlertsResponse,
    CompareResponse,
    PriceHistory,
    PriceHistoryParams,
    SupplementCategory,
)
from app.services import compare_service
from app.services.analytics import get_price_drops
from app.services.bigquery import get_price_history
from app.services.exceptions import (
    BigQueryUnavailableError,
    CompareValidationError,
)

router = APIRouter()


def _raise_bigquery_http_500(exc: GoogleAPICallError) -> None:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"BigQuery error: {exc}",
    ) from exc


@router.get(
    "/drops",
    response_model=AlertsResponse,
    response_description="Recent price drops above the threshold, newest first.",
    responses={**ERR_422, **ERR_500},
)
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


@router.get(
    "/compare",
    response_model=CompareResponse,
    response_description="Cross-site latest snapshots for up to 4 product IDs.",
    responses={**ERR_400, **ERR_422, **ERR_500},
)
async def compare(
    product_ids: list[str] = Query(
        ...,
        alias="product_ids",
        description="Repeat this param up to 4 times: ?product_ids=A&product_ids=B",
    ),
) -> CompareResponse:
    try:
        return await compare_service.compare_products(product_ids)
    except CompareValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except BigQueryUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"BigQuery error: {exc}",
        ) from exc


@router.get(
    "/{product_id}/history",
    response_model=PriceHistory,
    response_description="Time-series of every scraped price point for one product.",
    responses={**ERR_404, **ERR_422, **ERR_500},
)
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
