"""WebSocket endpoints.

Two channels:

* ``/ws/live-prices`` — public global feed. Every connected client gets
  every broadcast pushed by ``alert_service.process_price_event``.
* ``/ws/alerts/{user_id}`` — per-user alert feed. Bearer JWT in a query
  param (browsers can't set headers on a WS handshake) gates access.

Note: FastAPI doesn't include WebSocket routes from an ``APIRouter``
prefix the way HTTP routes work, but ``include_router`` does propagate
them. Keep the path with no extra prefix on the router so the URL stays
``/ws/...`` after mounting in ``main.py``.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.database import get_connection
from app.middleware.core import WebSocketAuthError, authenticate_ws_token
from app.services.websocket import manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/live-prices")
async def ws_live_prices(websocket: WebSocket) -> None:
    """Public global feed — every price event is fanned out here."""
    await manager.connect(websocket)
    try:
        while True:
            # Inbound messages aren't expected, but receiving keeps the
            # coroutine alive and surfaces client disconnects promptly.
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)


@router.websocket("/ws/alerts/{user_id}")
async def ws_alerts(
    websocket: WebSocket,
    user_id: str,
    token: str | None = Query(
        default=None,
        description=(
            "Access JWT for the user_id in the path. Must be passed as a "
            "query param because browsers can't set headers on the WS "
            "handshake. Issued by POST /auth/login."
        ),
    ),
) -> None:
    """Per-user alert feed — only the authenticated user can subscribe.

    Auth: client connects with ``?token=<access JWT>``; the JWT's ``sub``
    claim must equal ``user_id`` in the URL path. Otherwise the handshake
    is closed with a 4xxx code:

    * ``4401`` — missing / invalid / expired token, or session revoked.
    * ``4403`` — token belongs to a different user, or user disabled.
    """
    # Accept the handshake before the auth check so failures return as
    # WebSocket close frames (with our 4xxx codes) instead of an HTTP 403
    # to the upgrade request — closing before accept makes Starlette
    # respond at the HTTP layer.
    await websocket.accept()

    # One-shot DB connection for the auth check. Can't use Depends(get_db)
    # here because we want to release the connection before the WS
    # receive-loop blocks for hours.
    try:
        with get_connection() as conn:
            authenticate_ws_token(token, expected_user_id=user_id, conn=conn)
    except WebSocketAuthError as exc:
        await websocket.close(code=exc.code, reason=exc.reason)
        return
    except Exception:
        logger.exception("ws auth crashed for user_id=%s", user_id)
        await websocket.close(code=1011, reason="internal error")
        return

    # Auth passed — register on the per-user channel. Already accepted
    # the handshake above, so use register() not connect().
    await manager.register(websocket, user_id=user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket, user_id=user_id)
