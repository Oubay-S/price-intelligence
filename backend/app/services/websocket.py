"""
services/websocket.py
=====================
WebSocket connection management for live price events and personalised
alerts.

Two channels are supported:

* **Global feed** — every connected client receives every broadcast.
  Used by the public live-prices view in the Angular frontend.
  Endpoint: ``/ws/live-prices``.

* **Per-user feed** — a client subscribes with their ``user_id`` and only
  receives alerts that match one of *their* watchlist items.
  Endpoint: ``/ws/alerts/{user_id}``.

The :class:`ConnectionManager` is a process-local singleton (``manager``).
If the FastAPI service is ever scaled horizontally, replace the in-memory
sets with a Redis Pub/Sub fan-out — each replica subscribes to the same
channel and forwards messages to its locally-connected sockets.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any

from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Track active WebSocket connections and fan out messages to them."""

    def __init__(self) -> None:
        # Global subscribers — every connected socket receives every broadcast.
        self._global: set[WebSocket] = set()
        # Per-user subscribers — keyed by stringified user_id.
        self._by_user: dict[str, set[WebSocket]] = defaultdict(set)
        # Guards mutation of the two sets above so concurrent connect /
        # disconnect / broadcast calls don't race on the underlying data.
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        *,
        user_id: str | None = None,
    ) -> None:
        """Accept the handshake and register the socket.

        Pass ``user_id`` to register on the per-user channel instead of
        the global feed.
        """
        await websocket.accept()
        await self.register(websocket, user_id=user_id)

    async def register(
        self,
        websocket: WebSocket,
        *,
        user_id: str | None = None,
    ) -> None:
        """Add an *already-accepted* socket to a channel.

        Used when the route handler had to call ``accept()`` itself —
        for example to send a 4xxx close frame on failed auth instead
        of an HTTP 403 on the upgrade request.
        """
        async with self._lock:
            if user_id is None:
                self._global.add(websocket)
            else:
                self._by_user[user_id].add(websocket)
        logger.info(
            "ws connected user=%s clients_global=%d clients_user=%d",
            user_id or "-",
            len(self._global),
            sum(len(s) for s in self._by_user.values()),
        )

    async def disconnect(
        self,
        websocket: WebSocket,
        *,
        user_id: str | None = None,
    ) -> None:
        """Remove the socket from whichever channel it was on."""
        async with self._lock:
            if user_id is None:
                self._global.discard(websocket)
            else:
                bucket = self._by_user.get(user_id)
                if bucket is not None:
                    bucket.discard(websocket)
                    if not bucket:
                        self._by_user.pop(user_id, None)
        logger.info("ws disconnected user=%s", user_id or "-")

    async def broadcast(self, payload: BaseModel | dict[str, Any]) -> int:
        """Send ``payload`` to every globally-subscribed client.

        Returns the number of clients the message was successfully
        delivered to. Dead sockets are pruned automatically.
        """
        message = self._encode(payload)
        async with self._lock:
            targets = list(self._global)

        delivered = await self._send_many(targets, message, channel="global")
        return delivered

    async def send_to_user(
        self,
        user_id: str,
        payload: BaseModel | dict[str, Any],
    ) -> int:
        """Send ``payload`` only to sockets registered for ``user_id``."""
        message = self._encode(payload)
        async with self._lock:
            targets = list(self._by_user.get(user_id, ()))

        if not targets:
            return 0

        delivered = await self._send_many(
            targets, message, channel=f"user:{user_id}"
        )
        return delivered

    async def _send_many(
        self,
        sockets: list[WebSocket],
        message: dict[str, Any],
        *,
        channel: str,
    ) -> int:
        """Send a pre-encoded message to a list of sockets, prune failures."""
        if not sockets:
            return 0

        results = await asyncio.gather(
            *(ws.send_json(message) for ws in sockets),
            return_exceptions=True,
        )

        delivered = 0
        dead: list[WebSocket] = []
        for ws, result in zip(sockets, results):
            if isinstance(result, Exception):
                logger.warning(
                    "ws send failed channel=%s err=%s — pruning", channel, result
                )
                dead.append(ws)
            else:
                delivered += 1

        if dead:
            async with self._lock:
                self._global.difference_update(dead)
                for bucket in self._by_user.values():
                    bucket.difference_update(dead)

        return delivered

    @staticmethod
    def _encode(payload: BaseModel | dict[str, Any]) -> dict[str, Any]:
        """Convert Pydantic models / datetimes / UUIDs into JSON-safe dicts."""
        if isinstance(payload, BaseModel):
            return jsonable_encoder(payload.model_dump())
        return jsonable_encoder(payload)

    @property
    def global_count(self) -> int:
        return len(self._global)

    @property
    def user_count(self) -> int:
        return sum(len(s) for s in self._by_user.values())


# Module-level singleton — import from anywhere as `from app.services.websocket import manager`.
manager = ConnectionManager()
