"""Products router tests.

Building real ProductResponse fixtures is heavy (deeply nested Pydantic
shape) — these tests focus on the wiring, status codes, and the 404 /
422 paths. Domain-shape assertions live in dedicated model tests.
"""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_list_products_empty_page(client: TestClient, monkeypatch) -> None:
    from app.routers import products as products_router

    monkeypatch.setattr(
        products_router, "get_all_products", lambda **kwargs: ([], 0)
    )
    resp = client.get("/products?page=1&limit=10")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total_count"] == 0
    assert body["page"] == 1
    assert body["limit"] == 10


def test_list_products_invalid_limit_returns_422(client: TestClient) -> None:
    resp = client.get("/products?limit=999")
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


def test_search_requires_query(client: TestClient) -> None:
    resp = client.get("/products/search")
    assert resp.status_code == 422


def test_search_empty_results(client: TestClient, monkeypatch) -> None:
    from app.routers import products as products_router

    monkeypatch.setattr(
        products_router, "search_products", lambda **kwargs: ([], 0)
    )
    resp = client.get("/products/search?q=whey")
    assert resp.status_code == 200
    assert resp.json()["total_count"] == 0


def test_get_product_not_found(client: TestClient, monkeypatch) -> None:
    from app.routers import products as products_router

    monkeypatch.setattr(products_router, "get_product_by_id", lambda _id: None)
    resp = client.get("/products/MISSING-PROD-ID")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


def test_trending_invalid_period_returns_422(client: TestClient) -> None:
    resp = client.get("/products/trending?period=99y")
    assert resp.status_code == 422
