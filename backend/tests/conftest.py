"""Shared fixtures for backend tests.

Strategy: avoid real Postgres / BigQuery / Redis. We monkeypatch the
psycopg2 pool init so the FastAPI lifespan doesn't try to connect, and
expose a `FakeConn` whose cursor returns scripted rows so router-level
SQL paths can be exercised without a live database.
"""
from __future__ import annotations

from collections import deque
from typing import Any, Iterator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


class FakeCursor:
    """psycopg2 cursor stand-in driven by a queue of scripted return values.

    `fetchone` / `fetchall` pop the next entry from the queue. Tests prime
    the queue in the order the route under test will execute SQL. SQL
    strings themselves are recorded in `executed` so assertions can check
    that the right statement actually ran.
    """

    def __init__(self, scripted: deque[Any]) -> None:
        self._scripted = scripted
        self.executed: list[tuple[str, tuple]] = []
        self._last: Any = None

    def execute(self, sql: str, params: tuple = ()) -> None:
        self.executed.append((sql, params))
        if self._scripted:
            self._last = self._scripted.popleft()
        else:
            self._last = None

    def fetchone(self) -> Any:
        return self._last if not isinstance(self._last, list) else (
            self._last[0] if self._last else None
        )

    def fetchall(self) -> list:
        return self._last if isinstance(self._last, list) else (
            [self._last] if self._last else []
        )

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *_: object) -> None:
        return None


class FakeConn:
    """Connection stand-in that yields a single shared FakeCursor."""

    def __init__(self, scripted: deque[Any] | None = None) -> None:
        self.scripted = scripted if scripted is not None else deque()
        self.cursor_obj = FakeCursor(self.scripted)
        self.committed = False
        self.rolled_back = False

    def cursor(self, cursor_factory: Any = None) -> FakeCursor:
        return self.cursor_obj

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def __enter__(self) -> "FakeConn":
        return self

    def __exit__(self, *_: object) -> None:
        return None


@pytest.fixture(autouse=True)
def _stub_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    """Skip the real psycopg2 ThreadedConnectionPool during lifespan."""
    import app.database as db
    import app.main as main

    monkeypatch.setattr(db, "init_pool", lambda *a, **k: None)
    monkeypatch.setattr(db, "close_pool", lambda: None)
    monkeypatch.setattr(main, "init_pool", lambda *a, **k: None)
    monkeypatch.setattr(main, "close_pool", lambda: None)


@pytest.fixture(autouse=True)
def _disable_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stop slowapi from tripping under repeated test traffic."""
    from app.middleware.core import limiter
    monkeypatch.setattr(limiter, "enabled", False)


@pytest.fixture(autouse=True)
def _disable_internal_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default `/internal/*` to dev mode (no key required). Tests that
    cover the auth gate explicitly re-set the key inside the test body."""
    from app.config import settings
    monkeypatch.setattr(settings, "INTERNAL_API_KEY", "")


@pytest.fixture
def fake_conn() -> FakeConn:
    return FakeConn()


@pytest.fixture
def client(fake_conn: FakeConn) -> Iterator[TestClient]:
    """TestClient with `get_db` overridden to yield the fake connection."""
    from app.database import get_db
    from app.main import app

    def _override_get_db():
        try:
            yield fake_conn
            fake_conn.commit()
        except Exception:
            fake_conn.rollback()
            raise

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_client(client: TestClient) -> TestClient:
    """TestClient with `get_current_user` patched to return a stub user."""
    from app.main import app
    from app.middleware.core import get_current_user
    from uuid import uuid4
    from datetime import datetime, timezone

    user_id = uuid4()
    session_id = uuid4()
    now = datetime.now(timezone.utc)

    def _override_user() -> dict[str, Any]:
        return {
            "id": user_id,
            "email": "test@example.com",
            "full_name": "Test User",
            "role": "user",
            "is_active": True,
            "email_verified": True,
            "created_at": now,
            "updated_at": now,
            "last_login_at": now,
            "session_id": session_id,
        }

    app.dependency_overrides[get_current_user] = _override_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)
