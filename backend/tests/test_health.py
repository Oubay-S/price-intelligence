from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_health_live_always_ok(client: TestClient) -> None:
    resp = client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_health_ready_all_up_returns_200(client: TestClient, monkeypatch) -> None:
    from app.routers import health as main
    monkeypatch.setattr(main, "_check_postgres", lambda: True)
    monkeypatch.setattr(main, "_check_redis", lambda: True)
    monkeypatch.setattr(main, "_check_bigquery", lambda: True)
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["checks"] == {"postgres": True, "redis": True, "bigquery": True}


def test_health_ready_postgres_down_returns_503(client: TestClient, monkeypatch) -> None:
    from app.routers import health as main
    monkeypatch.setattr(main, "_check_postgres", lambda: False)
    monkeypatch.setattr(main, "_check_redis", lambda: True)
    monkeypatch.setattr(main, "_check_bigquery", lambda: True)
    resp = client.get("/health/ready")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["checks"]["postgres"] is False


def test_health_ready_redis_down_returns_503(client: TestClient, monkeypatch) -> None:
    from app.routers import health as main
    monkeypatch.setattr(main, "_check_postgres", lambda: True)
    monkeypatch.setattr(main, "_check_redis", lambda: False)
    monkeypatch.setattr(main, "_check_bigquery", lambda: True)
    resp = client.get("/health/ready")
    assert resp.status_code == 503
    assert resp.json()["checks"]["redis"] is False


def test_health_ready_bigquery_down_returns_503(client: TestClient, monkeypatch) -> None:
    from app.routers import health as main
    monkeypatch.setattr(main, "_check_postgres", lambda: True)
    monkeypatch.setattr(main, "_check_redis", lambda: True)
    monkeypatch.setattr(main, "_check_bigquery", lambda: False)
    resp = client.get("/health/ready")
    assert resp.status_code == 503
    assert resp.json()["checks"]["bigquery"] is False


def test_unknown_route_returns_404(client: TestClient) -> None:
    # Starlette's router handles missing-route 404 directly without
    # routing through our HTTPException handler — assert just the status.
    resp = client.get("/does-not-exist")
    assert resp.status_code == 404
