"""Auth router smoke tests.

These exercise the HTTP shape and DB-error contract of /auth/* without
touching a real Postgres. The cursor's scripted queue feeds row results
in the order each handler executes them.
"""
from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from uuid import uuid4

import psycopg2
from fastapi.testclient import TestClient

from tests.conftest import FakeConn


def _user_row() -> dict:
    now = datetime.now(timezone.utc)
    return {
        "id": uuid4(),
        "email": "alice@example.com",
        "full_name": "Alice",
        "role": "user",
        "is_active": True,
        "email_verified": False,
        "created_at": now,
        "updated_at": now,
        "last_login_at": None,
    }


def test_register_success(client: TestClient, fake_conn: FakeConn) -> None:
    fake_conn.scripted.extend([_user_row(), None])  # INSERT users RETURNING, audit_logs
    resp = client.post(
        "/api/auth/register",
        json={"email": "alice@example.com", "password": "supersecret", "full_name": "Alice"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["email"] == "alice@example.com"
    assert "hashed_password" not in body


def test_register_duplicate_email_returns_409(
    client: TestClient, fake_conn: FakeConn, monkeypatch
) -> None:
    def _raise(_sql, _params=()):
        raise psycopg2.IntegrityError("duplicate key value violates users_email_key")

    monkeypatch.setattr(fake_conn.cursor_obj, "execute", _raise)
    resp = client.post(
        "/api/auth/register",
        json={"email": "alice@example.com", "password": "supersecret"},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "conflict"


def test_register_short_password_returns_422(client: TestClient) -> None:
    resp = client.post(
        "/api/auth/register",
        json={"email": "alice@example.com", "password": "short"},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


def test_login_wrong_password_returns_401(client: TestClient, fake_conn: FakeConn) -> None:
    # Hash that won't match — ensures verify_password returns False.
    fake_conn.scripted.append({
        "id": uuid4(),
        "hashed_password": "$2b$12$" + "A" * 53,
        "is_active": True,
    })
    resp = client.post(
        "/api/auth/login",
        json={"email": "alice@example.com", "password": "nope"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"


def test_login_unknown_email_returns_401(client: TestClient, fake_conn: FakeConn) -> None:
    fake_conn.scripted.append(None)  # no row from SELECT users
    resp = client.post(
        "/api/auth/login",
        json={"email": "ghost@example.com", "password": "whatever1"},
    )
    assert resp.status_code == 401


def test_me_without_token_returns_401(client: TestClient) -> None:
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"


def test_me_with_overridden_user_returns_profile(auth_client: TestClient) -> None:
    resp = auth_client.get("/api/auth/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "test@example.com"
    assert body["role"] == "user"


def test_refresh_with_garbage_token_returns_401(client: TestClient) -> None:
    resp = client.post("/api/auth/refresh", json={"refresh_token": "not-a-jwt"})
    assert resp.status_code == 401
