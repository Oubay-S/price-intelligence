"""FastAPI app factory.

Kept deliberately thin. All this module does is:

1. Build the FastAPI ``app`` and configure the lifespan (DB pool +
   Redis client startup / shutdown).
2. Wire cross-cutting middleware (CORS, slowapi rate limiter).
3. Mount routers — every route lives in ``app/routers/*``.
4. Register exception handlers so every error response conforms to
   the project's error envelope.

Business logic, SQL, WebSocket handlers, and health probes are all
out of this file. Look in:

* ``app/services/alert_service.py`` — price-event fan-out orchestration.
* ``app/repositories/*`` — every SQL statement.
* ``app/routers/internal.py`` — POST /internal/price-event.
* ``app/routers/health.py`` — /health, /health/live, /health/ready.
* ``app/routers/websocket.py`` — /ws/live-prices, /ws/alerts/{user_id}.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.database import close_pool, init_pool
from app.middleware.core import limiter
from app.routers import (
    auth,
    health,
    internal,
    prices,
    products,
    stats,
    watchlist,
    websocket,
)
from app.services import cache
from app.services.email import shutdown_email_executor

logger = logging.getLogger("priceradar.api")


# ---------------------------------------------------------------------------
# Lifespan — DB pool + Redis client lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_pool()
    yield
    close_pool()
    cache.close()
    # Drain the email thread pool last so any in-flight verification /
    # alert messages queued during the final requests still get sent.
    shutdown_email_executor()


app = FastAPI(
    title="PriceRadar API",
    description="Price intelligence backend for sports-nutrition e-commerce.",
    version="0.1.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

# slowapi: attach limiter to app state and register the 429 handler.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    # `allow_credentials=True` precludes the wildcard origin — list every
    # frontend host explicitly. Add new entries when the SPA moves hosts.
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Router mounts
# ---------------------------------------------------------------------------

app.include_router(health.router, tags=["health"])
app.include_router(websocket.router)
app.include_router(internal.router, prefix="/internal")
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(products.router, prefix="/products", tags=["products"])
app.include_router(prices.router, prefix="/prices", tags=["prices"])
app.include_router(watchlist.router, prefix="/watchlist", tags=["watchlist"])
app.include_router(stats.router, prefix="/stats", tags=["stats"])


# ---------------------------------------------------------------------------
# Exception handlers — every error response conforms to the envelope
# defined in ``app.api_responses.ErrorEnvelope``::
#
#   {"error": {"code": "...", "message": "...", "details": [...]?}}
#
# Order of registration matters: most specific first, generic ``Exception``
# last so it only catches things nothing else handled.
# ---------------------------------------------------------------------------

def _envelope_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: list[Any] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        body["details"] = details
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder({"error": body}),
    )


_HTTP_STATUS_TO_CODE: dict[int, str] = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
    502: "upstream_error",
    503: "service_unavailable",
}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Re-wrap FastAPI's HTTPException in the project's error envelope.

    ``exc.detail`` may be a string (most cases) or a dict / list — pass
    structured payloads through to ``details`` so callers don't lose
    information.
    """
    code = _HTTP_STATUS_TO_CODE.get(exc.status_code, "http_error")
    if isinstance(exc.detail, str):
        message, details = exc.detail, None
    else:
        message = _HTTP_STATUS_TO_CODE.get(exc.status_code, "Request failed")
        details = exc.detail if isinstance(exc.detail, list) else [exc.detail]
    response = _envelope_response(
        status_code=exc.status_code,
        code=code,
        message=message,
        details=details,
    )
    # Preserve auth-challenge headers (e.g. WWW-Authenticate from get_current_user).
    if exc.headers:
        for k, v in exc.headers.items():
            response.headers[k] = v
    return response


@app.exception_handler(RequestValidationError)
async def request_validation_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """422 for inbound body / query / path validation failures."""
    return _envelope_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="validation_error",
        message="Request payload failed validation",
        details=jsonable_encoder(exc.errors()),
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    """422 for Pydantic ValidationError raised manually inside route handlers
    or ``Depends()`` factories — FastAPI doesn't auto-convert these."""
    return _envelope_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="validation_error",
        message="Validation failed",
        details=jsonable_encoder(exc.errors(include_url=False)),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for anything that escaped the route. Logs the traceback
    server-side, returns a generic 500 to the client (no internals leaked)."""
    logger.exception(
        "unhandled exception on %s %s", request.method, request.url.path
    )
    return _envelope_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="internal_error",
        message="An unexpected error occurred",
    )
