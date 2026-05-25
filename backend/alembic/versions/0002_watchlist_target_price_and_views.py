"""watchlist target_price + combined unread view

Wraps the hand-written sql/migrations/001_watchlist_target_price_and_views.sql
so the change is part of the alembic chain. Idempotent — safe to re-apply
against a DB that already received it via psql.

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-08
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_SQL_FILE = (
    Path(__file__).resolve().parents[2]
    / "sql" / "migrations" / "001_watchlist_target_price_and_views.sql"
)


def upgrade() -> None:
    sql = _SQL_FILE.read_text(encoding="utf-8")
    op.execute(sql)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_watchlist_with_unread;")
    op.execute("DROP VIEW IF EXISTS v_watchlist_summary;")
    op.execute("ALTER TABLE watchlist_items DROP COLUMN IF EXISTS target_price;")
