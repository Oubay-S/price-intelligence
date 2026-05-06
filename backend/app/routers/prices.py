import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from google.api_core.exceptions import GoogleAPICallError

from app.models.product import (
    AlertsResponse,
    CompareResponse,
    PriceHistory,
    PriceHistoryParams,
    ProductComparison,
    SupplementCategory,
)
from app.services.analytics import get_comparison_for_product, get_price_drops
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
async def compare(
    product_ids: list[str] = Query(
        ...,
        alias="product_ids",
        description="Repeat this param up to 4 times: ?product_ids=A&product_ids=B",
    ),
) -> CompareResponse:
    # Dedupe while preserving caller's order, then enforce 1..4 cap.
    unique_ids: list[str] = []
    for pid in product_ids:
        pid = pid.strip()
        if pid and pid not in unique_ids:
            unique_ids.append(pid)

    if not unique_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one product_id is required",
        )
    if len(unique_ids) > 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Compare accepts at most 4 product_ids, got {len(unique_ids)}"
            ),
        )

    try:
        results: list[Optional[ProductComparison]] = await asyncio.gather(
            *(asyncio.to_thread(get_comparison_for_product, pid) for pid in unique_ids)
        )
    except GoogleAPICallError as exc:
        _raise_bigquery_http_500(exc)

    products = [item for item in results if item is not None]
    return CompareResponse(products=products)


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
