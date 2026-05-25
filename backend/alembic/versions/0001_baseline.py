"""baseline schema (= sql/first_setup.sql)

Revision ID: 0001
Revises:
Create Date: 2026-05-08

For *fresh* databases:
    alembic upgrade head      # runs first_setup.sql, then any later revisions

For databases that *already* have first_setup.sql applied (every dev's
local Postgres-app, since postgres-app's docker-entrypoint-initdb.d ran
first_setup.sql on first volume init):
    alembic stamp 0001        # mark this revision as applied without running

After stamping, every subsequent schema change goes through alembic and
the team no longer has to wipe volumes (`docker-compose down -v`) to
pick up a teammate's edits.
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence, Union

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_SQL_FILE = Path(__file__).resolve().parents[2] / "sql" / "first_setup.sql"


def upgrade() -> None:
    sql = _SQL_FILE.read_text(encoding="utf-8")
    op.execute(sql)


def downgrade() -> None:
    # Baseline rollback would drop the entire user-domain schema —
    # destructive enough that we refuse to do it implicitly. Run a
    # manual `DROP SCHEMA public CASCADE` if you really need to start over.
    raise RuntimeError(
        "Baseline downgrade is destructive — drop the schema manually "
        "(e.g. `docker-compose down -v`) instead of `alembic downgrade base`."
    )
