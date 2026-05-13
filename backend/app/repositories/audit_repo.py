"""audit_logs writes.

Append-only by trigger (see first_setup.sql) — the only SQL operation
this repo supports is INSERT. Every router that mutates user-owned
state should call ``log()`` before the request returns.
"""
from __future__ import annotations

import json
from typing import Any

from psycopg2.extensions import connection as PgConnection


def log(
    conn: PgConnection,
    *,
    user_id: Any,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO audit_logs
                (user_id, action, entity_type, entity_id,
                 ip_address, user_agent, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
            """,
            (
                str(user_id) if user_id is not None else None,
                action,
                entity_type,
                entity_id,
                ip_address,
                user_agent,
                json.dumps(metadata) if metadata else None,
            ),
        )
