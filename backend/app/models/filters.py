"""FastAPI ``Depends()``-bound query-param classes.

These are delivery-layer concerns (HTTP query strings) but live with the
other Pydantic models for cohesion. Each class is consumed via
``Depends(SomeParams)`` in the matching router.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.models.enums import BrandTier, SortOption, SupplementCategory


class ProductFilterParams(BaseModel):
    """Query parameters for ``GET /products``.

    Usage in router::

        @router.get("/")
        async def get_products(filters: ProductFilterParams = Depends()):
            ...
    """
    category:     Optional[SupplementCategory] = None
    subcategory:  Optional[str]                = None
    site:         Optional[str]                = None
    brand:        Optional[str]                = None
    min_price:    Optional[float]              = Field(None, ge=0)
    max_price:    Optional[float]              = Field(None, ge=0)
    in_stock:     Optional[bool]               = None
    has_discount: Optional[bool]               = None
    brand_tier:   Optional[BrandTier]          = None
    tags:         Optional[list[str]]          = None
    sort:         SortOption                   = SortOption.SCRAPED_AT_DESC
    page:         int                          = Field(1, ge=1)
    limit:        int                          = Field(48, ge=1, le=200)

    @model_validator(mode="after")
    def max_must_exceed_min(self) -> "ProductFilterParams":
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.max_price < self.min_price
        ):
            raise ValueError("max_price must be greater than or equal to min_price")
        return self


class PriceHistoryParams(BaseModel):
    """Query parameters for ``GET /prices/{id}/history``."""
    start_date: Optional[datetime] = None
    end_date:   Optional[datetime] = None
    site:       Optional[str]      = None
    period:     str                = Field(
        "30d",
        pattern=r"^(7d|30d|90d|all)$",
        description="Shorthand: 7d | 30d | 90d | all (overrides start/end_date)",
    )

    @model_validator(mode="after")
    def end_must_be_after_start(self) -> "PriceHistoryParams":
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date <= self.start_date
        ):
            raise ValueError("end_date must be after start_date")
        return self


class PriceDropParams(BaseModel):
    """Query parameters for ``GET /prices/drops``."""
    threshold: float                       = Field(10.0, ge=1, le=100)
    category:  Optional[SupplementCategory] = None
    site:      Optional[str]               = None
    limit:     int                         = Field(20, ge=1, le=100)
