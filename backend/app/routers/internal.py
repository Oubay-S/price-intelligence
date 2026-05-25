"""Internal service-to-service endpoints (NiFi → FastAPI).

Mounted under ``/internal/*``. Not exposed to the public CORS allowlist
and gated by an ``X-Internal-Key`` header so it can run on the same port
as the public API without leaking write access. Nginx is expected to
either route ``/internal/*`` separately or block it from the public LB.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status

from app.api_responses import ERR_401, ERR_422, ERR_500
from app.middleware.core import require_internal_key
from app.models.product import PriceEvent
from app.services import alert_service

router = APIRouter()


@router.post(
    "/price-event",
    status_code=status.HTTP_202_ACCEPTED,
    tags=["internal"],
    dependencies=[Depends(require_internal_key)],
    response_description=(
        "Event accepted. Returns delivery counters: cache keys busted, "
        "global WS clients reached, watchlist subscribers alerted, "
        "alerts persisted to history, and cooldown-suppressed events."
    ),
    responses={**ERR_401, **ERR_422, **ERR_500},
)
async def ingest_price_event(event: PriceEvent) -> dict[str, Any]:
    """Receive a price event from NiFi and fan it out via WebSocket.

    Delegates the whole pipeline (cache invalidation → broadcast →
    threshold evaluation → cooldown claim → history snapshot → per-user
    push) to ``alert_service.process_price_event``. Router stays thin.
    """
    return await alert_service.process_price_event(event)
