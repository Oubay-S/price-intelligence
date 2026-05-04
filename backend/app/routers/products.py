from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from google.api_core.exceptions import GoogleAPICallError

from app.models.product import PaginatedProducts, ProductResponse, SupplementCategory
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


@router.get("", response_model=PaginatedProducts)
def list_products(
    page: int = Query(1, ge=1),
    limit: int = Query(48, ge=1, le=200),
    site: Optional[str] = Query(None, description="e.g. 'jumia.ma', 'ebay.com', 'walmart.com'"),
    category: Optional[SupplementCategory] = Query(None),
) -> PaginatedProducts:
    try:
        items, total_count = get_all_products(
            page=page,
            limit=limit,
            site=site,
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


@router.get("/search", response_model=PaginatedProducts)
def search(
    q: str = Query(..., min_length=1, max_length=200, description="Match against product title and brand"),
    page: int = Query(1, ge=1),
    category: Optional[SupplementCategory] = Query(None),
    limit: int = Query(48, ge=1, le=200),
) -> PaginatedProducts:
    try:
        items, total_count = search_products(
            query=q,
            category=category,
            page=page,
            limit=limit,
        )
    except GoogleAPICallError as exc:
        _raise_bigquery_http_500(exc)

    return PaginatedProducts(
        items=items,
        total_count=total_count,
        page=page,
        limit=limit,
    )


@router.get("/{product_id}", response_model=ProductResponse)
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
