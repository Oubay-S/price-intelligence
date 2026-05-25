"""Price-event ingest tests.

Covers the four code paths in `POST /internal/price-event`:

* validation rejection on malformed body
* X-Internal-Key gate when settings.INTERNAL_API_KEY is non-empty
* happy fan-out — broadcast + persist + cooldown claim
* cooldown suppression — claim returns False, no persist, no per-user push

The endpoint delegates to ``app.services.alert_service.process_price_event``
so the patches target that module's bound names (alert_repo, cache, manager).
"""
from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient


def _payload(**overrides) -> dict:
    base = {
        "canonical_product_id": "PROD-123",
        "product_title": "Whey Protein 2kg",
        "site": "jumia.ma",
        "listing_url": "https://jumia.ma/whey",
        "category": "strength_nutrition",
        "price_usd": 25.0,
        "price_original_usd": 50.0,
        "discount_pct": 50.0,
    }
    base.update(overrides)
    return base


def _stub_service(monkeypatch, *, subscribers=None, claim=True, persist=True):
    """Common monkeypatching helper. Returns a `calls` dict for assertions."""
    from app.services import alert_service

    calls: dict[str, int] = {
        "invalidate": 0,
        "load": 0,
        "claim": 0,
        "persist": 0,
        "broadcast": 0,
        "user_send": 0,
    }

    monkeypatch.setattr(
        alert_service.cache,
        "invalidate_product",
        lambda _id: calls.__setitem__("invalidate", calls["invalidate"] + 1) or 1,
    )
    monkeypatch.setattr(
        alert_service.alert_repo,
        "load_watchlist_subscribers",
        lambda _id: calls.__setitem__("load", calls["load"] + 1) or (subscribers or []),
    )
    monkeypatch.setattr(
        alert_service.alert_repo,
        "claim_alert_slot",
        lambda _wid: calls.__setitem__("claim", calls["claim"] + 1) or claim,
    )
    monkeypatch.setattr(
        alert_service.alert_repo,
        "persist_alert",
        lambda **kw: calls.__setitem__("persist", calls["persist"] + 1) or persist,
    )

    async def _broadcast(_payload):
        calls["broadcast"] += 1
        return 3

    async def _send_to_user(_uid, _payload):
        calls["user_send"] += 1
        return 1

    monkeypatch.setattr(alert_service.manager, "broadcast", _broadcast)
    monkeypatch.setattr(alert_service.manager, "send_to_user", _send_to_user)

    return calls


def test_price_event_invalid_payload_returns_422(client: TestClient) -> None:
    resp = client.post("/internal/price-event", json={"canonical_product_id": "x"})
    assert resp.status_code == 422


def test_price_event_negative_price_returns_422(client: TestClient) -> None:
    resp = client.post("/internal/price-event", json=_payload(price_usd=-1))
    assert resp.status_code == 422


def test_price_event_internal_key_required_when_set(
    client: TestClient, monkeypatch
) -> None:
    from app.config import settings
    monkeypatch.setattr(settings, "INTERNAL_API_KEY", "topsecret")
    resp = client.post("/internal/price-event", json=_payload())
    assert resp.status_code == 401


def test_price_event_internal_key_accepts_match(
    client: TestClient, monkeypatch
) -> None:
    from app.config import settings
    monkeypatch.setattr(settings, "INTERNAL_API_KEY", "topsecret")
    _stub_service(monkeypatch, subscribers=[])

    resp = client.post(
        "/internal/price-event",
        json=_payload(),
        headers={"X-Internal-Key": "topsecret"},
    )
    assert resp.status_code == 202


def test_price_event_happy_path_persists_and_broadcasts(
    client: TestClient, monkeypatch
) -> None:
    user_id = uuid4()
    watchlist_id = uuid4()
    calls = _stub_service(
        monkeypatch,
        subscribers=[
            {
                "id": watchlist_id,
                "user_id": user_id,
                "alert_threshold_pct": 10.0,
                "target_price": None,
                "global_alert_threshold": None,
            }
        ],
        claim=True,
        persist=True,
    )

    resp = client.post("/internal/price-event", json=_payload())
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["delivered_global"] == 3
    assert body["delivered_user"] == 1
    assert body["alerts_persisted"] == 1
    assert body["suppressed_cooldown"] == 0
    assert calls["claim"] == 1
    assert calls["persist"] == 1
    assert calls["user_send"] == 1


def test_price_event_cooldown_suppresses_alert(
    client: TestClient, monkeypatch
) -> None:
    calls = _stub_service(
        monkeypatch,
        subscribers=[
            {
                "id": uuid4(),
                "user_id": uuid4(),
                "alert_threshold_pct": 10.0,
                "target_price": None,
                "global_alert_threshold": None,
            }
        ],
        claim=False,  # cooldown active
    )

    resp = client.post("/internal/price-event", json=_payload())
    assert resp.status_code == 202
    body = resp.json()
    assert body["suppressed_cooldown"] == 1
    assert body["delivered_user"] == 0
    assert body["alerts_persisted"] == 0
    assert calls["persist"] == 0
    assert calls["user_send"] == 0


def test_price_event_threshold_below_drop_skips_alert(
    client: TestClient, monkeypatch
) -> None:
    # 90% threshold, 50% drop in payload — should never reach claim.
    calls = _stub_service(
        monkeypatch,
        subscribers=[
            {
                "id": uuid4(),
                "user_id": uuid4(),
                "alert_threshold_pct": 90.0,
                "target_price": None,
                "global_alert_threshold": None,
            }
        ],
    )

    resp = client.post("/internal/price-event", json=_payload())
    assert resp.status_code == 202
    body = resp.json()
    assert body["subscribers_alerted"] == 0
    assert calls["claim"] == 0
