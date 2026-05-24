"""``/api/analytics/*`` — Data Analyst dashboard feed.

Thin HTTP layer over ``services/analytics_dashboard``. Each endpoint serves one
chart's data for the frontend (Chart.js). A missing export file surfaces as 404
so the UI can show a "analysis not generated yet" state instead of a 500.
"""
from fastapi import APIRouter, HTTPException, status

from app.api_responses import ERR_404, ERR_500
from app.models.analytics import (
    HeatmapResponse,
    KpisResponse,
    PriceByCategoryResponse,
    PriceByStoreResponse,
    RecommendationsResponse,
    TimeSeriesResponse,
    TopDiscountsResponse,
)
from app.repositories.exceptions import NotFoundError
from app.services import analytics_dashboard

router = APIRouter()


def _not_found(exc: NotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/kpis", response_model=KpisResponse, responses={**ERR_404, **ERR_500})
def kpis() -> KpisResponse:
    try:
        return analytics_dashboard.get_kpis()
    except NotFoundError as exc:
        raise _not_found(exc) from exc


@router.get(
    "/price-by-store",
    response_model=PriceByStoreResponse,
    responses={**ERR_404, **ERR_500},
)
def price_by_store() -> PriceByStoreResponse:
    try:
        return analytics_dashboard.get_price_by_store()
    except NotFoundError as exc:
        raise _not_found(exc) from exc


@router.get(
    "/price-by-category",
    response_model=PriceByCategoryResponse,
    responses={**ERR_404, **ERR_500},
)
def price_by_category() -> PriceByCategoryResponse:
    try:
        return analytics_dashboard.get_price_by_category()
    except NotFoundError as exc:
        raise _not_found(exc) from exc


@router.get(
    "/time-series",
    response_model=TimeSeriesResponse,
    responses={**ERR_404, **ERR_500},
)
def time_series() -> TimeSeriesResponse:
    try:
        return analytics_dashboard.get_time_series()
    except NotFoundError as exc:
        raise _not_found(exc) from exc


@router.get(
    "/heatmap",
    response_model=HeatmapResponse,
    responses={**ERR_404, **ERR_500},
)
def heatmap() -> HeatmapResponse:
    try:
        return analytics_dashboard.get_heatmap()
    except NotFoundError as exc:
        raise _not_found(exc) from exc


@router.get(
    "/top-discounts",
    response_model=TopDiscountsResponse,
    responses={**ERR_404, **ERR_500},
)
def top_discounts() -> TopDiscountsResponse:
    try:
        return analytics_dashboard.get_top_discounts()
    except NotFoundError as exc:
        raise _not_found(exc) from exc


@router.get(
    "/recommendations",
    response_model=RecommendationsResponse,
    responses={**ERR_404, **ERR_500},
)
def recommendations() -> RecommendationsResponse:
    try:
        return analytics_dashboard.get_recommendations()
    except NotFoundError as exc:
        raise _not_found(exc) from exc
