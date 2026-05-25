"""Watchlist endpoints.

Routers parse + dispatch + translate exceptions. Use-case orchestration
lives in ``app.services.watchlist_service`` and SQL in
``app.repositories.watchlist_repo``.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from psycopg2.extensions import connection as PgConnection

from app.api_responses import (
    ERR_401,
    ERR_404,
    ERR_409,
    ERR_422,
    ERR_500,
    ERR_502,
)
from app.database import get_db
from app.middleware.core import get_current_user
from app.models.watchlist import (
    WatchlistAdd,
    WatchlistItemResponse,
    WatchlistListResponse,
    WatchlistUpdate,
)
from app.repositories.exceptions import DuplicateError, NotFoundError
from app.services import watchlist_service
from app.services.exceptions import (
    BigQueryUnavailableError,
    ProductNotFoundError,
)

router = APIRouter()


# `canonical_product_id` is TO_HEX(SHA256(product_url)) → 64 lowercase hex chars.
ProductIdPath = Annotated[
    str,
    Path(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
        description="canonical_product_id (64-char SHA-256 hex)",
    ),
]


def _client_ip(request: Request) -> str | None:
    if request.client is None:
        return None
    return request.client.host


def _user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


# ---------------------------------------------------------------------------
# GET /watchlist
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=WatchlistListResponse,
    response_description="The current user's watchlist enriched with live BigQuery prices.",
    responses={**ERR_401, **ERR_422, **ERR_500},
)
async def list_watchlist(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    conn: Annotated[PgConnection, Depends(get_db)],
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
) -> WatchlistListResponse:
    return await watchlist_service.list_for_user(
        conn, user_id=current_user["id"], page=page, limit=limit
    )


# ---------------------------------------------------------------------------
# POST /watchlist/{product_id}
# ---------------------------------------------------------------------------

@router.post(
    "/{product_id}",
    response_model=WatchlistItemResponse,
    status_code=status.HTTP_201_CREATED,
    response_description="Newly-created watchlist item with effective threshold resolved.",
    responses={**ERR_401, **ERR_404, **ERR_409, **ERR_422, **ERR_500, **ERR_502},
)
async def add_watchlist_item(
    request: Request,
    product_id: ProductIdPath,
    payload: WatchlistAdd,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    conn: Annotated[PgConnection, Depends(get_db)],
) -> WatchlistItemResponse:
    try:
        return await watchlist_service.add(
            conn,
            user_id=current_user["id"],
            product_id=product_id,
            payload=payload,
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
        )
    except BigQueryUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"BigQuery error resolving product: {exc}",
        ) from exc
    except ProductNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id!r} not found in catalog",
        ) from exc
    except DuplicateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product already in watchlist",
        ) from exc


# ---------------------------------------------------------------------------
# PATCH /watchlist/{product_id}
# ---------------------------------------------------------------------------

@router.patch(
    "/{product_id}",
    response_model=WatchlistItemResponse,
    response_description="Updated watchlist item with re-resolved effective threshold.",
    responses={**ERR_401, **ERR_404, **ERR_422, **ERR_500},
)
async def update_watchlist_item(
    request: Request,
    product_id: ProductIdPath,
    payload: WatchlistUpdate,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    conn: Annotated[PgConnection, Depends(get_db)],
) -> WatchlistItemResponse:
    try:
        return await watchlist_service.update(
            conn,
            user_id=current_user["id"],
            product_id=product_id,
            payload=payload,
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist item not found",
        ) from exc


# ---------------------------------------------------------------------------
# DELETE /watchlist/{product_id}
# ---------------------------------------------------------------------------

@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_description="Watchlist item removed. No body.",
    responses={**ERR_401, **ERR_404, **ERR_422, **ERR_500},
)
def remove_watchlist_item(
    request: Request,
    product_id: ProductIdPath,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    conn: Annotated[PgConnection, Depends(get_db)],
) -> None:
    try:
        watchlist_service.remove(
            conn,
            user_id=current_user["id"],
            product_id=product_id,
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist item not found",
        ) from exc
