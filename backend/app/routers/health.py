"""Health probes.

* ``GET /health/live`` — process liveness only. No external touch.
* ``GET /health/ready`` — Postgres + Redis + BigQuery dependency check.
  503 when any one is down so load balancers stop routing traffic.
* ``GET /health`` — backwards-compat alias for /health/live so existing
  Docker / uptime probes don't break.

The ``_check_*`` helpers are module-level (not inlined) so tests can
``monkeypatch.setattr(health, "_check_postgres", lambda: False)`` to
exercise the 503 branch without spinning up real dependencies.
"""
from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.api_responses import ERR_500
from app.config import settings
from app.services import cache

router = APIRouter()


def _check_postgres() -> bool:
    """Ping the OLTP pool with SELECT 1. Swallows all errors → False."""
    try:
        from app.database import check_connection
        return bool(check_connection())
    except Exception:
        return False


def _check_redis() -> bool:
    """Ping Redis. False on any redis-py error or unreachable URL."""
    try:
        client = cache.get_client()
        return bool(client.ping())
    except Exception:
        return False


def _check_bigquery() -> bool:
    """Touch the configured BigQuery dataset with a 3-second deadline.

    ``get_dataset`` issues a single metadata HTTP call — no scan, no
    billing. Broad except: transport, auth, or 404 errors all mean BQ
    can't serve requests right now.
    """
    try:
        from google.cloud import bigquery
        client = bigquery.Client(project=settings.GCP_PROJECT_ID)
        client.get_dataset(settings.BIGQUERY_DATASET, timeout=3.0)
        return True
    except Exception:
        return False


@router.get(
    "/health",
    tags=["health"],
    response_description="Process liveness — alias for /health/live for legacy probes.",
    responses={**ERR_500},
)
def health() -> dict[str, str]:
    """Backwards-compat alias. Prefer /health/live or /health/ready."""
    return {"status": "ok"}


@router.get(
    "/health/live",
    tags=["health"],
    response_description="Process is up and the event loop is responsive.",
)
def health_live() -> dict[str, str]:
    """Liveness probe — answers 200 as long as the FastAPI process is
    accepting requests. Does NOT touch external dependencies."""
    return {"status": "ok"}


@router.get(
    "/health/ready",
    tags=["health"],
    response_description=(
        "Aggregated dependency check. 200 with status='ok' when Postgres, "
        "Redis, and BigQuery all respond; 503 with status='degraded' and "
        "a per-check breakdown otherwise."
    ),
)
def health_ready() -> JSONResponse:
    """Readiness probe — verifies the service can serve requests.

    Pings Postgres (SELECT 1), Redis (PING), BigQuery (get_dataset).
    Returns 503 if any fails so an L7 load balancer stops routing
    traffic to this replica until it recovers.
    """
    checks = {
        "postgres": _check_postgres(),
        "redis": _check_redis(),
        "bigquery": _check_bigquery(),
    }
    healthy = all(checks.values())
    body = {
        "status": "ok" if healthy else "degraded",
        "checks": checks,
    }
    return JSONResponse(
        status_code=200 if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        content=body,
    )
