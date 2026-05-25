"""
services/cache.py
=================
Thin Redis-backed cache layer.

The module exposes two surfaces:

* **Manual API** — :func:`get`, :func:`set`, :func:`delete`,
  :func:`delete_pattern`. Values are JSON-serialised (with a sane default
  for datetimes / UUIDs / Enums via Pydantic's :class:`TypeAdapter` when
  needed).

* **Decorator** — :func:`redis_cached` is a drop-in replacement for
  ``cachetools.cached``. It infers the return type from the wrapped
  function's annotation and uses a :class:`TypeAdapter` to round-trip
  Pydantic models through Redis.

Cache keys live under ``{prefix}:[{key_dim_value}:]{arg_hash}`` so that a
specific product's entries can be invalidated cheaply with
``delete_pattern("bq:get_price_history:{product_id}:*")``. When ``key_dim``
isn't applicable (e.g. paginated catalogue queries) the prefix-wide
wildcard ``"bq:get_all_products:*"`` is the invalidation hammer.

Failures are *non-fatal*: if Redis is unreachable the wrapper logs a
warning and falls through to the underlying function. The cache is a
performance optimisation, not a correctness boundary.
"""

from __future__ import annotations

import functools
import hashlib
import inspect
import json
import logging
from typing import Any, Callable, Iterable, Optional, TypeVar, get_type_hints

import redis
from pydantic import TypeAdapter

from app.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")

_client: redis.Redis | None = None


# ---------------------------------------------------------------------------
# Client lifecycle
# ---------------------------------------------------------------------------

def get_client() -> redis.Redis:
    """Return the lazy-initialised module-level Redis client."""
    global _client
    if _client is None:
        _client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
    return _client


def _safe_client() -> redis.Redis | None:
    """Return the client or ``None`` if Redis is unreachable."""
    try:
        client = get_client()
        client.ping()
        return client
    except redis.RedisError as exc:
        logger.warning("redis unreachable: %s — bypassing cache", exc)
        return None


def close() -> None:
    """Close the underlying connection pool. Used on shutdown."""
    global _client
    if _client is not None:
        try:
            _client.close()
        except redis.RedisError:
            pass
        _client = None


# ---------------------------------------------------------------------------
# Manual JSON wrappers
# ---------------------------------------------------------------------------

def _json_default(value: Any) -> Any:
    """Fallback encoder for datetime/UUID/Enum/Decimal/etc."""
    try:
        return value.model_dump()
    except AttributeError:
        pass
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def get(key: str) -> Any | None:
    """Return the JSON-decoded value for ``key`` or ``None`` if absent."""
    client = _safe_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
    except redis.RedisError as exc:
        logger.warning("redis GET failed key=%s err=%s", key, exc)
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("redis GET returned non-JSON for key=%s — evicting", key)
        try:
            client.delete(key)
        except redis.RedisError:
            pass
        return None


def set(key: str, value: Any, ttl: int | None = None) -> bool:
    """Store ``value`` under ``key``. Returns True on success."""
    client = _safe_client()
    if client is None:
        return False
    try:
        payload = json.dumps(value, default=_json_default)
    except (TypeError, ValueError) as exc:
        logger.warning("redis SET serialise failed key=%s err=%s", key, exc)
        return False
    try:
        if ttl is not None and ttl > 0:
            client.setex(key, ttl, payload)
        else:
            client.set(key, payload)
        return True
    except redis.RedisError as exc:
        logger.warning("redis SET failed key=%s err=%s", key, exc)
        return False


def delete(*keys: str) -> int:
    """Delete one or more keys. Returns the count actually removed."""
    if not keys:
        return 0
    client = _safe_client()
    if client is None:
        return 0
    try:
        return int(client.delete(*keys))
    except redis.RedisError as exc:
        logger.warning("redis DEL failed err=%s", exc)
        return 0


def delete_pattern(pattern: str) -> int:
    """Delete every key matching ``pattern`` via SCAN (non-blocking)."""
    client = _safe_client()
    if client is None:
        return 0
    deleted = 0
    try:
        for key in client.scan_iter(match=pattern, count=500):
            deleted += int(client.delete(key))
    except redis.RedisError as exc:
        logger.warning("redis SCAN/DEL failed pattern=%s err=%s", pattern, exc)
    return deleted


def delete_patterns(patterns: Iterable[str]) -> int:
    """Convenience: invalidate a batch of patterns and return total count."""
    return sum(delete_pattern(p) for p in patterns)


# ---------------------------------------------------------------------------
# Decorator — drop-in for cachetools.cached
# ---------------------------------------------------------------------------

def _hash_args(arg_values: dict[str, Any]) -> str:
    """Stable short hash of a kwarg-style mapping.

    Used to derive a Redis cache key — NOT for integrity or signing.
    ``usedforsecurity=False`` is the standard hashlib opt-out (Python
    3.9+) that documents the intent and silences Bandit B324.
    """
    blob = json.dumps(arg_values, sort_keys=True, default=str)
    return hashlib.sha1(  # nosec B324 - cache key only, not security
        blob.encode("utf-8"), usedforsecurity=False
    ).hexdigest()[:16]


def redis_cached(
    prefix: str,
    ttl: int,
    key_dim: str | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Cache the wrapped function's result in Redis.

    Parameters
    ----------
    prefix
        Logical namespace, e.g. ``"bq:get_price_history"``.
    ttl
        Seconds to keep entries before Redis expires them.
    key_dim
        Optional name of an argument whose value should be embedded in
        the key (between ``prefix`` and the args hash). Useful for
        per-product caches so invalidation can target one product.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        sig = inspect.signature(func)
        try:
            hints = get_type_hints(func)
        except Exception:
            hints = {}
        return_type = hints.get("return", Any)
        try:
            adapter: Optional[TypeAdapter] = TypeAdapter(return_type)
        except Exception:
            adapter = None

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                bound = sig.bind_partial(*args, **kwargs)
                bound.apply_defaults()
                arg_values: dict[str, Any] = dict(bound.arguments)
            except TypeError:
                arg_values = {}

            key_parts = [prefix]
            if key_dim:
                kdv = arg_values.pop(key_dim, None)
                key_parts.append("_" if kdv is None else str(kdv))
            key_parts.append(_hash_args(arg_values))
            key = ":".join(key_parts)

            client = _safe_client()
            if client is not None and adapter is not None:
                try:
                    raw = client.get(key)
                except redis.RedisError as exc:
                    logger.warning("redis GET failed key=%s err=%s", key, exc)
                    raw = None
                if raw is not None:
                    try:
                        return adapter.validate_json(raw)
                    except Exception as exc:
                        logger.warning(
                            "redis cached value invalid key=%s err=%s — recomputing",
                            key,
                            exc,
                        )

            result = func(*args, **kwargs)

            if client is not None and adapter is not None:
                try:
                    payload = adapter.dump_json(result).decode("utf-8")
                    client.setex(key, ttl, payload)
                except redis.RedisError as exc:
                    logger.warning("redis SETEX failed key=%s err=%s", key, exc)
                except Exception as exc:
                    logger.warning(
                        "redis cache encode failed key=%s err=%s", key, exc
                    )
            return result

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Invalidation helpers — invoked from the price-event handler so that a
# write upstream punches through the read-side cache. Centralising the
# pattern list here keeps every cached endpoint discoverable from one file.
# ---------------------------------------------------------------------------

def invalidate_product(product_id: str) -> int:
    """Bust every cached entry that references one canonical product."""
    patterns = [
        f"bq:get_product_by_id:{product_id}:*",
        f"bq:get_price_history:{product_id}:*",
        f"analytics:get_product_stats:{product_id}:*",
        f"analytics:get_comparison_for_product:{product_id}:*",
        # Aggregate views always include the product, so blow them away wholesale.
        "bq:get_all_products:*",
        "bq:search_products:*",
        "analytics:get_price_drops:*",
        "analytics:get_trending_products:*",
        "analytics:get_brand_rankings:*",
    ]
    return delete_patterns(patterns)
