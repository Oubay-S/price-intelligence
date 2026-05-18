from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from google.api_core.exceptions import GoogleAPICallError

from app.api_responses import ERR_404, ERR_422, ERR_500
from app.models.product import (
    PaginatedProducts,
    ProductResponse,
    SupplementCategory,
    TrendingResponse,
)
from app.services.analytics import get_trending_products
from app.services.bigquery import (
    get_all_products,
    get_product_by_id,
    search_products,
)

router = APIRouter()


def _raise_bigquery_http_500(exc: GoogleAPICallError) -> None:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"BigQuery error: {exc}",
    ) from exc


@router.get(
    "",
    response_model=PaginatedProducts,
    response_description="Paginated catalogue slice ordered by most recent scrape.",
    responses={**ERR_422, **ERR_500},
)
def list_products(
    page: int = Query(1, ge=1),
    limit: int = Query(48, ge=1, le=200),
    site: Optional[list[str]] = Query(
        None, description="Repeatable — e.g. ?site=ebay&site=walmart"
    ),
    category: Optional[SupplementCategory] = Query(None),
) -> PaginatedProducts:
    try:
        items, total_count = get_all_products(
            page=page,
            limit=limit,
            sites=site,
            category=category,
        )
    except GoogleAPICallError as exc:
        _raise_bigquery_http_500(exc)

    return PaginatedProducts(
        items=items,
        total_count=total_count,
        page=page,
        limit=limit,
    )


@router.get(
    "/search",
    response_model=PaginatedProducts,
    response_description="Products whose name matches the search query (case-insensitive LIKE).",
    responses={**ERR_422, **ERR_500},
)
def search(
    q: str = Query(..., min_length=1, max_length=200, description="Match against product title and brand"),
    page: int = Query(1, ge=1),
    category: Optional[SupplementCategory] = Query(None),
    site: Optional[list[str]] = Query(
        None, description="Repeatable — e.g. ?site=ebay&site=walmart"
    ),
    limit: int = Query(48, ge=1, le=200),
) -> PaginatedProducts:
    try:
        items, total_count = search_products(
            query=q,
            category=category,
            page=page,
            limit=limit,
            sites=site,
        )
    except GoogleAPICallError as exc:
        _raise_bigquery_http_500(exc)

    return PaginatedProducts(
        items=items,
        total_count=total_count,
        page=page,
        limit=limit,
    )


@router.get(
    "/trending",
    response_model=TrendingResponse,
    response_description="Top products by drop magnitude over the requested window.",
    responses={**ERR_422, **ERR_500},
)
def trending(
    period: str = Query("24h", pattern=r"^(24h|7d|30d)$"),
    category: Optional[SupplementCategory] = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> TrendingResponse:
    try:
        return get_trending_products(period=period, category=category, limit=limit)
    except GoogleAPICallError as exc:
        _raise_bigquery_http_500(exc)


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    response_description="Latest snapshot for the given canonical product ID.",
    responses={**ERR_404, **ERR_500},
)
def get_product(product_id: str) -> ProductResponse:
    try:
        product = get_product_by_id(product_id)
    except GoogleAPICallError as exc:
        _raise_bigquery_http_500(exc)

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id!r} not found",
        )
    return product
