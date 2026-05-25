"""Product catalog DTOs.

Owns:

* Reusable nested sub-models (PriceInfo, NutritionInfo, EquipmentInfo,
  RatingsInfo, BrandInfo).
* Core product shapes (ProductBase, ProductCreate, ProductResponse).
* Trending / search / pagination envelopes.

Cross-cutting models live next door:

* ``app.models.enums``        — domain enums (SupplementCategory, AlertType, …)
* ``app.models.price``        — PricePoint, PriceHistory, ProductComparison, CompareResponse
* ``app.models.stats``        — ProductStats, BrandRanking, BrandRankingsResponse
* ``app.models.alerts``       — PriceDropAlert, AlertsResponse, UserAlertRecord, UnreadAlertCount
* ``app.models.filters``      — ProductFilterParams, PriceHistoryParams, PriceDropParams
* ``app.models.integration``  — PriceEvent, PriceEventBroadcast (NiFi ↔ WS)

For backward compatibility, the bottom of this module re-exports every
class that used to live here so existing ``from app.models.product
import X`` sites keep working. New code should import from the focused
module instead.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.models.enums import (
    BrandTier,
    PriceTrend,
    SupplementCategory,
)


# ===========================================================================
# Sub-models (reusable nested objects)
# ===========================================================================

class PriceInfo(BaseModel):
    """Normalised pricing block — always in USD after analyst conversion."""
    current:          float          = Field(..., ge=0, description="Current price in USD")
    original:         Optional[float]= Field(None, ge=0, description="Pre-discount price in USD")
    currency_raw:     str            = Field(..., description="Original scraped currency code, e.g. 'MAD'")
    per_serving:      Optional[float]= Field(None, ge=0, description="price_usd / servings")
    per_100g:         Optional[float]= Field(None, ge=0, description="price_usd / total_g * 100")
    per_kg:           Optional[float]= Field(None, ge=0, description="price_usd / weight_kg (equipment)")
    discount_pct:     Optional[float]= Field(None, ge=0, le=100)
    trend:            PriceTrend     = PriceTrend.STABLE
    velocity_per_day: Optional[float]= Field(None, description="$/day change over last 7 days")

    @model_validator(mode="after")
    def compute_discount(self) -> "PriceInfo":
        """Auto-compute discount_pct when original is present and not already set."""
        if (
            self.discount_pct is None
            and self.original is not None
            and self.original > 0
        ):
            self.discount_pct = round(
                (self.original - self.current) / self.original * 100, 2
            )
        return self


class NutritionInfo(BaseModel):
    """Per-serving nutrition facts — Nutrition category only, null for equipment."""
    protein_g:      Optional[float] = Field(None, ge=0)
    calories:       Optional[int]   = Field(None, ge=0)
    carbs_g:        Optional[float] = Field(None, ge=0)
    fat_g:          Optional[float] = Field(None, ge=0)
    sugar_g:        Optional[float] = Field(None, ge=0)
    sodium_mg:      Optional[float] = Field(None, ge=0)
    caffeine_mg:    Optional[float] = Field(None, ge=0)
    creatine_type:  Optional[str]   = None
    bcaa_ratio:     Optional[str]   = None
    serving_size_g: Optional[float] = Field(None, ge=0)
    total_servings: Optional[int]   = Field(None, ge=1)
    total_weight_g: Optional[float] = Field(None, ge=0)


class EquipmentInfo(BaseModel):
    """Equipment-specific attributes — home gym / wearables / combat / team sports."""
    weight_kg:        Optional[float] = Field(None, ge=0)
    max_load_kg:      Optional[float] = Field(None, ge=0)
    material:         Optional[str]   = None
    adjustable:       Optional[bool]  = None
    size:             Optional[str]   = None
    gender:           Optional[str]   = None
    oz_weight:        Optional[float] = None
    glove_type:       Optional[str]   = None
    stud_type:        Optional[str]   = None
    racket_weight_g:  Optional[float] = None
    grip_size:        Optional[str]   = None
    drop_mm:          Optional[float] = None
    shoe_weight_g:    Optional[float] = None
    stack_height_mm:  Optional[float] = None
    carbon_plate:     Optional[bool]  = None
    battery_life_h:   Optional[float] = None
    resistance_level: Optional[str]   = None


class RatingsInfo(BaseModel):
    """Composite rating weighted by review volume across all sites."""
    score:           float = Field(..., ge=0, le=5)
    count:           int   = Field(..., ge=0)
    composite_score: Optional[float] = Field(
        None, ge=0, le=5,
        description="Weighted composite across all sites: SUM(score*log(count+1))/SUM(log(count+1))"
    )


class BrandInfo(BaseModel):
    """Brand identity and tier classification."""
    brand_id: str
    name:     str
    logo_url: Optional[AnyHttpUrl] = None
    country:  Optional[str]        = None
    tier:     BrandTier            = BrandTier.MID
    verified: bool                 = False


# ===========================================================================
# Core product models
# ===========================================================================

class ProductBase(BaseModel):
    """Fields shared by all product models."""
    canonical_product_id: str = Field(..., description="SHA-256 hash from dbt staging")
    name:                 str = Field(..., min_length=1, max_length=300)
    site:                 str = Field(..., description="Source site, e.g. 'iherb.com'")
    listing_url:          str = Field(..., description="Clean URL — tracking params stripped")
    category:             SupplementCategory
    subcategory:          Optional[str] = None
    brand_raw:            str = Field(..., description="Brand name as scraped")
    in_stock:             bool = True


class ProductCreate(ProductBase):
    """Schema for data arriving from the scraper (via NiFi → FastAPI).

    All raw string fields preserved — parsing happens in dbt. Validation
    only: price must exist and be positive.
    """
    # raw pricing (scraper sends strings)
    price_raw:          str
    price_original_raw: Optional[str] = None
    currency_raw:       str           = "USD"
    shipping_cost_raw:  Optional[str] = None
    promo_label_raw:    Optional[str] = None

    # raw ratings
    rating_raw:         Optional[str] = None
    review_count_raw:   Optional[str] = None
    review_snippet_raw: Optional[str] = None

    # raw product attributes
    product_title_raw:  str
    image_url:          Optional[str] = None
    category_raw:       Optional[str] = None  # breadcrumb as site shows it

    # nutrition raw (null for non-nutrition)
    weight_raw:                Optional[str] = None
    servings_raw:              Optional[str] = None
    serving_size_raw:          Optional[str] = None
    protein_per_serving_raw:   Optional[str] = None
    calories_per_serving_raw:  Optional[str] = None
    flavour_raw:               Optional[str] = None
    protein_type_raw:          Optional[str] = None
    certifications_raw:        Optional[str] = None
    ingredients_raw:           Optional[str] = None
    creatine_type_raw:         Optional[str] = None
    caffeine_mg_raw:           Optional[str] = None
    bcaa_ratio_raw:            Optional[str] = None

    # equipment raw
    material_raw:      Optional[str] = None
    size_raw:          Optional[str] = None
    gender_raw:        Optional[str] = None
    adjustable_raw:    Optional[str] = None
    weight_range_raw:  Optional[str] = None
    max_load_raw:      Optional[str] = None
    dimensions_raw:    Optional[str] = None
    oz_weight_raw:     Optional[str] = None
    glove_type_raw:    Optional[str] = None
    stud_type_raw:     Optional[str] = None
    racket_weight_raw: Optional[str] = None
    grip_size_raw:     Optional[str] = None
    drop_raw:          Optional[str] = None
    shoe_weight_raw:   Optional[str] = None
    carbon_plate_raw:  Optional[str] = None
    battery_life_raw:  Optional[str] = None

    scraped_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("price_raw")
    @classmethod
    def price_raw_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("price_raw cannot be empty")
        return v.strip()

    @field_validator("listing_url")
    @classmethod
    def strip_tracking_params(cls, v: str) -> str:
        """Remove ?ref=... and similar tracking query strings."""
        return v.split("?")[0].rstrip("/")


class ProductResponse(ProductBase):
    """Schema returned to Angular clients. All computed fields are
    present — raw strings are hidden."""
    model_config = ConfigDict(from_attributes=True)

    # identity
    name:      str
    brand:     Optional[BrandInfo] = None
    flavour:   Optional[str]       = None
    image_url: Optional[str]       = None

    # normalised data (computed by analyst in dbt)
    pricing:   PriceInfo
    nutrition: Optional[NutritionInfo] = None
    equipment: Optional[EquipmentInfo] = None
    ratings:   Optional[RatingsInfo]   = None

    # taxonomy
    certifications: list[str] = Field(default_factory=list)
    tags:           list[str] = Field(default_factory=list)
    purpose_tags:   list[str] = Field(default_factory=list)
    brand_tier:     BrandTier = BrandTier.MID

    # meta
    scraped_at:         datetime
    data_quality_score: Optional[int] = Field(
        None, ge=0, le=100,
        description="Great Expectations completeness score — rows < 70 are quarantined"
    )


# ===========================================================================
# Trending & search & pagination envelopes
# ===========================================================================

class TrendingProduct(BaseModel):
    """A product surfaced by ``GET /products/trending``. Ranked by
    drop_pct or view velocity over the specified period."""
    canonical_product_id: str
    product_name:         str
    image_url:            Optional[str] = None
    category:             SupplementCategory
    brand_raw:            str
    brand_tier:           BrandTier

    current_price: float
    drop_pct:      Optional[float] = None
    price_trend:   PriceTrend
    best_site:     str
    listing_url:   str

    rating_score: Optional[float] = None
    tags:         list[str]       = Field(default_factory=list)
    rank:         int             = Field(..., description="1 = top trending")


class TrendingResponse(BaseModel):
    """Response envelope for ``GET /products/trending``."""
    products:     list[TrendingProduct]
    period:       str = Field("24h", description="24h | 7d | 30d")
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class SearchResult(BaseModel):
    """Lightweight product representation returned by search.
    Returned by ``GET /products/search`` — leaner than ProductResponse."""
    canonical_product_id: str
    product_name:         str
    brand_raw:            str
    category:             SupplementCategory
    image_url:            Optional[str] = None
    current_price:        float
    discount_pct:         Optional[float] = None
    price_trend:          PriceTrend
    rating_score:         Optional[float] = None
    best_site:            str
    listing_url:          str
    tags:                 list[str]       = Field(default_factory=list)
    relevance_score:      Optional[float] = Field(
        None, description="BigQuery LIKE match score — higher = more relevant"
    )


class SearchResponse(BaseModel):
    """Response envelope for ``GET /products/search``."""
    results:      list[SearchResult]
    query:        str
    total:        int
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class PaginatedProducts(BaseModel):
    """Paginated product list returned by ``GET /products``. Includes
    metadata needed by the Angular CDK virtual scroll viewport."""
    items:       list[ProductResponse]
    total_count: int  = Field(..., description="Total matching products (for pagination UI)")
    page:        int  = Field(..., ge=1)
    limit:       int  = Field(..., ge=1, le=200)
    total_pages: int  = 1
    has_next:    bool = False
    has_prev:    bool = False

    @model_validator(mode="after")
    def compute_pagination(self) -> "PaginatedProducts":
        self.total_pages = max(1, -(-self.total_count // self.limit))   # ceiling division
        self.has_next    = self.page < self.total_pages
        self.has_prev    = self.page > 1
        return self


# ===========================================================================
# Backward-compat re-exports
# ---------------------------------------------------------------------------
# Existing ``from app.models.product import X`` keeps working for every
# class that used to live here. New code should import from the focused
# module (enums / price / stats / alerts / filters / integration) instead.
# ===========================================================================

# noqa imports placed at the bottom on purpose: child modules import
# NutritionInfo / EquipmentInfo / SupplementCategory back from this file,
# so those classes must be defined above before the re-exports trigger.

from app.models.enums import (  # noqa: E402, F401
    AlertType,
    NutritionSubcategory,
    SortOption,
)
from app.models.price import (  # noqa: E402, F401
    CompareResponse,
    PriceHistory,
    PricePoint,
    ProductComparison,
    SitePriceSnapshot,
)
from app.models.stats import (  # noqa: E402, F401
    BrandRanking,
    BrandRankingsResponse,
    ProductStats,
)
from app.models.alerts import (  # noqa: E402, F401
    AlertsResponse,
    PriceDropAlert,
    UnreadAlertCount,
    UserAlertRecord,
)
from app.models.filters import (  # noqa: E402, F401
    PriceDropParams,
    PriceHistoryParams,
    ProductFilterParams,
)
from app.models.integration import (  # noqa: E402, F401
    PriceEvent,
    PriceEventBroadcast,
)
