"""Compare use-case for GET /prices/compare.

Owns the dedup + cap rule and the parallel BigQuery fan-out.
"""
from __future__ import annotations

import asyncio
from typing import Optional

from google.api_core.exceptions import GoogleAPICallError

from app.models.product import CompareResponse, ProductComparison
from app.services.analytics import get_comparison_for_product
from app.services.exceptions import (
    BigQueryUnavailableError,
    CompareValidationError,
)


_MAX_COMPARE = 4


async def compare_products(product_ids: list[str]) -> CompareResponse:
    """Dedupe (preserving caller order), enforce 1..4 cap, fetch each
    product's cross-site snapshot from BigQuery in parallel.

    Raises ``CompareValidationError`` for empty / oversized input,
    ``BigQueryUnavailableError`` if BQ raises.
    """
    unique_ids: list[str] = []
    for pid in product_ids:
        pid = pid.strip()
        if pid and pid not in unique_ids:
            unique_ids.append(pid)

    if not unique_ids:
        raise CompareValidationError("At least one product_id is required")
    if len(unique_ids) > _MAX_COMPARE:
        raise CompareValidationError(
            f"Compare accepts at most {_MAX_COMPARE} product_ids, got {len(unique_ids)}"
        )

    try:
        results: list[Optional[ProductComparison]] = await asyncio.gather(
            *(asyncio.to_thread(get_comparison_for_product, pid) for pid in unique_ids)
        )
    except GoogleAPICallError as exc:
        raise BigQueryUnavailableError(str(exc)) from exc

    products = [item for item in results if item is not None]
    return CompareResponse(products=products)
