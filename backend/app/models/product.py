"""
models/product.py
=================
All Pydantic v2 models for the product domain .

Structure
---------
1.  Enums & literals          — shared constants used across models
2.  Sub-models                — reusable nested objects (PriceInfo, NutritionInfo, …)
3.  Core product models       — ProductBase, ProductCreate, ProductResponse
4.  Price & history models    — PricePoint, PriceHistory, PriceComparison
5.  Stats models              — ProductStats, BrandRanking
6.  Alert models              — PriceDropAlert, AlertsResponse
7.  Trending & search         — TrendingProduct, SearchResult, PaginatedProducts
8.  Filter & query params     — ProductFilterParams (used by routers as a dependency)
9.  Internal / NiFi models    — PriceEvent (posted by NiFi to /internal/price-event)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    Field,
    field_validator,
    model_validator,
)


# ===========================================================================
# 1. ENUMS & LITERALS
# ===========================================================================


class SupplementCategory(str, Enum):
    """Top-level product categories — maps to BigQuery category column."""
    STRENGTH_NUTRITION = "strength_nutrition"
    STRENGTH_HOME_GYM  = "strength_home_gym"
    STRENGTH_WEARABLES = "strength_wearables"
    TEAM_FOOTBALL      = "team_football"
    TEAM_BASKETBALL    = "team_basketball"
    TEAM_VOLLEYBALL    = "team_volleyball"
    TEAM_RACKET        = "team_racket"
    ENDURANCE_FOOTWEAR = "endurance_footwear"
    ENDURANCE_TECH     = "endurance_tech"
    ENDURANCE_FUEL     = "endurance_fuel"
    COMBAT_BOXING_MMA  = "combat_boxing_mma"
    COMBAT_PROTECTION  = "combat_protection"


class NutritionSubcategory(str, Enum):
    WHEY_PROTEIN = "whey_protein"
    CREATINE     = "creatine"
    PRE_WORKOUT  = "pre_workout"
    AMINO_ACIDS  = "amino_acids"
    MASS_GAINER  = "mass_gainer"
    VITAMINS     = "vitamins"
    ENERGY_GEL   = "energy_gel"
    ELECTROLYTES = "electrolytes"


class PriceTrend(str, Enum):
    RISING  = "rising"
    FALLING = "falling"
    STABLE  = "stable"


class BrandTier(str, Enum):
    PREMIUM  = "premium"   # Garmin, Nike, Optimum Nutrition
    MID      = "mid"       # Myprotein, Adidas, Everlast
    BUDGET   = "budget"    # generic / unbranded


class AlertType(str, Enum):
    PRICE_DROP    = "price_drop"
    BACK_IN_STOCK = "back_in_stock"
    BUY_SOON      = "buy_soon"
    PRICE_RISE    = "price_rise"


class SortOption(str, Enum):
    SCRAPED_AT_DESC  = "scraped_at_desc"   # newest first (default)
    PRICE_ASC        = "price_asc"
    PRICE_DESC       = "price_desc"
    RATING_DESC      = "rating_desc"
    DISCOUNT_DESC    = "discount_desc"
    PRICE_PER_SERVING_ASC = "price_per_serving_asc"


# ===========================================================================
# 2. SUB-MODELS  (reusable nested objects)
# ===========================================================================


class PriceInfo(BaseModel):
    """Normalised pricing block — always in USD after analyst conversion."""
    current:         float          = Field(..., ge=0, description="Current price in USD")
    original:        Optional[float]= Field(None, ge=0, description="Pre-discount price in USD")
    currency_raw:    str            = Field(..., description="Original scraped currency code, e.g. 'MAD'")
    per_serving:     Optional[float]= Field(None, ge=0, description="price_usd / servings")
    per_100g:        Optional[float]= Field(None, ge=0, description="price_usd / total_g * 100")
    per_kg:          Optional[float]= Field(None, ge=0, description="price_usd / weight_kg (equipment)")
    discount_pct:    Optional[float]= Field(None, ge=0, le=100)
    trend:           PriceTrend     = PriceTrend.STABLE
    velocity_per_day:Optional[float]= Field(None, description="$/day change over last 7 days")

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
    protein_g:         Optional[float] = Field(None, ge=0)
    calories:          Optional[int]   = Field(None, ge=0)
    carbs_g:           Optional[float] = Field(None, ge=0)
    fat_g:             Optional[float] = Field(None, ge=0)
    sugar_g:           Optional[float] = Field(None, ge=0)
    sodium_mg:         Optional[float] = Field(None, ge=0)   # electrolytes
    caffeine_mg:       Optional[float] = Field(None, ge=0)   # pre-workout
    creatine_type:     Optional[str]   = None                # "Monohydrate" | "HCL"
    bcaa_ratio:        Optional[str]   = None                # "2:1:1"
    serving_size_g:    Optional[float] = Field(None, ge=0)
    total_servings:    Optional[int]   = Field(None, ge=1)
    total_weight_g:    Optional[float] = Field(None, ge=0)   # normalised from weight_raw


class EquipmentInfo(BaseModel):
    """Equipment-specific attributes — home gym / wearables / combat / team sports."""
    weight_kg:         Optional[float] = Field(None, ge=0)   # for dumbbells/kettlebells
    max_load_kg:       Optional[float] = Field(None, ge=0)   # bench press
    material:          Optional[str]   = None                # "Cast iron" | "Neoprene"
    adjustable:        Optional[bool]  = None
    size:              Optional[str]   = None                # "L/XL" | "EU 44"
    gender:            Optional[str]   = None                # "Men's" | "Women's" | "Unisex"
    # sport-specific
    oz_weight:         Optional[float] = None                # boxing gloves
    glove_type:        Optional[str]   = None                # "Bag" | "Sparring"
    stud_type:         Optional[str]   = None                # "FG" | "AG" | "TF"
    racket_weight_g:   Optional[float] = None
    grip_size:         Optional[str]   = None
    drop_mm:           Optional[float] = None                # running shoe heel-to-toe drop
    shoe_weight_g:     Optional[float] = None
    stack_height_mm:   Optional[float] = None
    carbon_plate:      Optional[bool]  = None
    battery_life_h:    Optional[float] = None                # GPS watches
    resistance_level:  Optional[str]   = None                # resistance bands


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
    brand_id:  str
    name:      str
    logo_url:  Optional[AnyHttpUrl] = None
    country:   Optional[str]        = None
    tier:      BrandTier            = BrandTier.MID
    verified:  bool                 = False


# ===========================================================================
# 3. CORE PRODUCT MODELS
# ===========================================================================


class ProductBase(BaseModel):
    """Fields shared by all product models."""
    canonical_product_id: str   = Field(..., description="SHA-256 hash from dbt staging")
    name:                 str   = Field(..., min_length=1, max_length=300)
    site:                 str   = Field(..., description="Source site, e.g. 'iherb.com'")
    listing_url:          str   = Field(..., description="Clean URL — tracking params stripped")
    category:             SupplementCategory
    subcategory:          Optional[str]  = None
    brand_raw:            str   = Field(..., description="Brand name as scraped")
    in_stock:             bool  = True


class ProductCreate(ProductBase):
    """
    Schema for data arriving from the scraper (via NiFi → FastAPI).
    All raw string fields preserved — parsing happens in dbt.
    Validation only: price must exist and be positive.
    """
    # raw pricing (scraper sends strings)
    price_raw:          str
    price_original_raw: Optional[str]   = None
    currency_raw:       str             = "USD"
    shipping_cost_raw:  Optional[str]   = None
    promo_label_raw:    Optional[str]   = None

    # raw ratings
    rating_raw:         Optional[str]   = None
    review_count_raw:   Optional[str]   = None
    review_snippet_raw: Optional[str]   = None

    # raw product attributes
    product_title_raw:  str
    image_url:          Optional[str]   = None
    category_raw:       Optional[str]   = None  # breadcrumb as site shows it

    # nutrition raw (null for non-nutrition)
    weight_raw:         Optional[str]   = None
    servings_raw:       Optional[str]   = None
    serving_size_raw:   Optional[str]   = None
    protein_per_serving_raw:   Optional[str] = None
    calories_per_serving_raw:  Optional[str] = None
    flavour_raw:        Optional[str]   = None
    protein_type_raw:   Optional[str]   = None
    certifications_raw: Optional[str]   = None
    ingredients_raw:    Optional[str]   = None
    creatine_type_raw:  Optional[str]   = None
    caffeine_mg_raw:    Optional[str]   = None
    bcaa_ratio_raw:     Optional[str]   = None

    # equipment raw
    material_raw:       Optional[str]   = None
    size_raw:           Optional[str]   = None
    gender_raw:         Optional[str]   = None
    adjustable_raw:     Optional[str]   = None
    weight_range_raw:   Optional[str]   = None
    max_load_raw:       Optional[str]   = None
    dimensions_raw:     Optional[str]   = None
    oz_weight_raw:      Optional[str]   = None
    glove_type_raw:     Optional[str]   = None
    stud_type_raw:      Optional[str]   = None
    racket_weight_raw:  Optional[str]   = None
    grip_size_raw:      Optional[str]   = None
    drop_raw:           Optional[str]   = None
    shoe_weight_raw:    Optional[str]   = None
    carbon_plate_raw:   Optional[str]   = None
    battery_life_raw:   Optional[str]   = None

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
    """
    Schema returned to Angular clients.
    All computed fields are present — raw strings are hidden.
    """
    # identity
    name:           str
    brand:          Optional[BrandInfo]     = None
    flavour:        Optional[str]           = None
    image_url:      Optional[str]           = None

    # normalised data (computed by analyst in dbt)
    pricing:        PriceInfo
    nutrition:      Optional[NutritionInfo] = None
    equipment:      Optional[EquipmentInfo] = None
    ratings:        Optional[RatingsInfo]   = None

    # taxonomy
    certifications: list[str]               = Field(default_factory=list)
    tags:           list[str]               = Field(default_factory=list)
    purpose_tags:   list[str]               = Field(default_factory=list)
    brand_tier:     BrandTier               = BrandTier.MID

    # meta
    scraped_at:     datetime
    data_quality_score: Optional[int]       = Field(
        None, ge=0, le=100,
        description="Great Expectations completeness score — rows < 70 are quarantined"
    )

    class Config:
        from_attributes = True


# ===========================================================================
# 4. PRICE & HISTORY MODELS
# ===========================================================================


class PricePoint(BaseModel):
    """Single price observation in a time-series."""
    price_usd:   float    = Field(..., ge=0)
    site:        str
    scraped_at:  datetime
    in_stock:    bool     = True
    discount_pct: Optional[float] = None


class PriceHistory(BaseModel):
    """Full price history for one canonical product."""
    canonical_product_id: str
    product_name:         str
    points:               list[PricePoint]
    # pre-computed summary (analyst mart)
    min_price:            float
    max_price:            float
    avg_price:            float
    median_price:         float
    floor_price_30d:      Optional[float] = Field(
        None, description="Rolling 30-day minimum — analyst's price floor proxy"
    )


class SitePriceSnapshot(BaseModel):
    """Cheapest current price for one product on one site."""
    site:             str
    price_usd:        float
    original_price:   Optional[float] = None
    discount_pct:     Optional[float] = None
    listing_url:      str
    in_stock:         bool
    last_seen:        datetime
    shipping_cost:    Optional[float] = None
    landed_cost:      Optional[float] = Field(
        None, description="price_usd + shipping_cost — Moroccan market localisation"
    )


class ProductComparison(BaseModel):
    """
    Cross-site comparison for a single canonical product.
    Returned by GET /api/prices/compare.
    """
    canonical_product_id: str
    product_name:         str
    image_url:            Optional[str]          = None
    category:             SupplementCategory
    nutrition:            Optional[NutritionInfo] = None
    equipment:            Optional[EquipmentInfo] = None
    sites:                list[SitePriceSnapshot]
    best_site:            str           = Field(..., description="Site with lowest current price")
    worst_site:           str           = Field(..., description="Site with highest current price")
    price_gap_pct:        float         = Field(
        ..., description="(max - min) / min * 100 across all sites"
    )
    tags:                 list[str]     = Field(default_factory=list)


class CompareResponse(BaseModel):
    """Response envelope for GET /api/prices/compare."""
    products:     list[ProductComparison]
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ===========================================================================
# 5. STATS MODELS
# ===========================================================================


class ProductStats(BaseModel):
    """
    Descriptive statistics for one canonical product.
    Returned by GET /api/stats/{product_id}.
    """
    canonical_product_id:  str
    product_name:          str
    period_days:           int          = Field(30, description="Window used to compute stats")

    # descriptive stats
    mean_price:            float
    median_price:          float
    std_deviation:         float
    min_price:             float
    max_price:             float
    coefficient_of_variation: float     = Field(
        ..., description="std / mean — > 0.15 flags the product as volatile"
    )

    # trend & velocity
    price_trend:           PriceTrend
    velocity_per_day:      float        = Field(
        ..., description="(price_today - price_7d_ago) / 7  — negative = falling"
    )
    is_volatile:           bool         = Field(
        ..., description="True when coefficient_of_variation > 0.15"
    )

    # predictive
    estimated_floor_30d:   Optional[float] = Field(
        None, description="Predicted lowest price in the next 30 days"
    )
    out_of_stock_probability: Optional[float] = Field(
        None, ge=0, le=1,
        description="Logistic regression output — > 0.7 triggers 'buy soon' alert"
    )

    total_observations: int
    sites_tracked:      int


class BrandRanking(BaseModel):
    """
    One brand's aggregated performance within a category.
    Returned by GET /api/stats/brands.
    """
    brand_name:         str
    brand_tier:         BrandTier
    category:           SupplementCategory
    avg_price_usd:      float
    avg_price_per_serving: Optional[float] = None
    avg_rating:         float
    total_products:     int
    sites_present:      list[str]     = Field(default_factory=list)
    rank:               int           = Field(..., description="1 = best value in category")


class BrandRankingsResponse(BaseModel):
    """Response envelope for GET /api/stats/brands."""
    category:       SupplementCategory
    rankings:       list[BrandRanking]
    generated_at:   datetime = Field(default_factory=datetime.utcnow)


# ===========================================================================
# 6. ALERT MODELS
# ===========================================================================


class PriceDropAlert(BaseModel):
    """
    A significant price drop detected by the SQL window function.
    Returned by GET /api/prices/drops and broadcast over WebSocket.
    """
    canonical_product_id: str
    product_name:         str
    image_url:            Optional[str]   = None
    site:                 str
    listing_url:          str
    category:             SupplementCategory

    price_before:         float
    price_after:          float
    currency:             str             = "USD"
    drop_pct:             float           = Field(..., gt=0)
    alert_type:           AlertType       = AlertType.PRICE_DROP

    scraped_at:           datetime
    detected_at:          datetime        = Field(default_factory=datetime.utcnow)

    # optional normalised metrics for display
    price_per_serving_after:  Optional[float] = None
    price_per_kg_after:       Optional[float] = None


class AlertsResponse(BaseModel):
    """Response envelope for GET /api/prices/drops."""
    alerts:       list[PriceDropAlert]
    count:        int
    threshold_pct: float
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class UserAlertRecord(BaseModel):
    """
    A stored alert record from the price_alerts PostgreSQL table.
    Returned by GET /api/alerts (user's personal alert history).
    """
    id:                   UUID
    canonical_product_id: str
    product_name:         str
    product_image_url:    Optional[str]  = None
    site:                 str
    listing_url:          str
    price_before:         float
    price_after:          float
    drop_pct:             float
    alert_type:           AlertType
    is_read:              bool
    triggered_at:         datetime
    read_at:              Optional[datetime] = None

    class Config:
        from_attributes = True


class UnreadAlertCount(BaseModel):
    """Returned by GET /api/alerts/unread-count — drives the navbar badge."""
    user_id:       UUID
    unread_count:  int


# ===========================================================================
# 7. TRENDING & SEARCH MODELS
# ===========================================================================


class TrendingProduct(BaseModel):
    """
    A product surfaced by GET /api/products/trending.
    Ranked by drop_pct or view velocity over the specified period.
    """
    canonical_product_id: str
    product_name:         str
    image_url:            Optional[str]    = None
    category:             SupplementCategory
    brand_raw:            str
    brand_tier:           BrandTier

    current_price:        float
    drop_pct:             Optional[float]  = None
    price_trend:          PriceTrend
    best_site:            str
    listing_url:          str

    rating_score:         Optional[float]  = None
    tags:                 list[str]        = Field(default_factory=list)
    rank:                 int              = Field(..., description="1 = top trending")


class TrendingResponse(BaseModel):
    """Response envelope for GET /api/products/trending."""
    products:     list[TrendingProduct]
    period:       str          = Field("24h", description="24h | 7d | 30d")
    generated_at: datetime     = Field(default_factory=datetime.utcnow)


class SearchResult(BaseModel):
    """
    Lightweight product representation returned by search.
    Returned by GET /api/products/search — leaner than ProductResponse.
    """
    canonical_product_id: str
    product_name:         str
    brand_raw:            str
    category:             SupplementCategory
    image_url:            Optional[str]    = None
    current_price:        float
    discount_pct:         Optional[float]  = None
    price_trend:          PriceTrend
    rating_score:         Optional[float]  = None
    best_site:            str
    listing_url:          str
    tags:                 list[str]        = Field(default_factory=list)
    relevance_score:      Optional[float]  = Field(
        None, description="BigQuery LIKE match score — higher = more relevant"
    )


class SearchResponse(BaseModel):
    """Response envelope for GET /api/products/search."""
    results:      list[SearchResult]
    query:        str
    total:        int
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class PaginatedProducts(BaseModel):
    """
    Paginated product list returned by GET /api/products.
    Includes metadata needed by the Angular CDK virtual scroll viewport.
    """
    items:       list[ProductResponse]
    total_count: int         = Field(..., description="Total matching products (for pagination UI)")
    page:        int         = Field(..., ge=1)
    limit:       int         = Field(..., ge=1, le=200)
    total_pages: int         = 1
    has_next:    bool        = False
    has_prev:    bool        = False

    @model_validator(mode="after")
    def compute_pagination(self) -> "PaginatedProducts":
        self.total_pages = max(1, -(-self.total_count // self.limit))   # ceiling division
        self.has_next    = self.page < self.total_pages
        self.has_prev    = self.page > 1
        return self


# ===========================================================================
# 8. FILTER & QUERY PARAM MODELS
# ===========================================================================


class ProductFilterParams(BaseModel):
    """
    Query parameters for GET /api/products.
    Used as a FastAPI Depends() dependency in the products router.

    Usage in router:
        @router.get("/")
        async def get_products(filters: ProductFilterParams = Depends()):
            ...
    """
    category:    Optional[SupplementCategory] = None
    subcategory: Optional[str]                = None
    site:        Optional[str]                = None
    brand:       Optional[str]                = None
    min_price:   Optional[float]              = Field(None, ge=0)
    max_price:   Optional[float]              = Field(None, ge=0)
    in_stock:    Optional[bool]               = None
    has_discount:Optional[bool]               = None
    brand_tier:  Optional[BrandTier]          = None
    tags:        Optional[list[str]]          = None    # e.g. ["vegan","halal"]
    sort:        SortOption                   = SortOption.SCRAPED_AT_DESC
    page:        int                          = Field(1, ge=1)
    limit:       int                          = Field(48, ge=1, le=200)

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
    """
    Query parameters for GET /api/products/{id}/history.
    Used as a FastAPI Depends() dependency.
    """
    start_date: Optional[datetime] = None
    end_date:   Optional[datetime] = None
    site:       Optional[str]      = None
    period:     str                = Field(
        "30d",
        pattern=r"^(7d|30d|90d|all)$",
        description="Shorthand: 7d | 30d | 90d | all (overrides start/end_date)"
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


class CompareParams(BaseModel):
    """
    Query parameters for GET /api/prices/compare.
    Enforces the 4-product maximum at model level.
    """
    product_ids: list[str] = Field(
        ..., min_length=2, max_length=4,
        description="2–4 canonical_product_id values"
    )

    @field_validator("product_ids")
    @classmethod
    def deduplicate_ids(cls, v: list[str]) -> list[str]:
        seen: list[str] = []
        for pid in v:
            if pid not in seen:
                seen.append(pid)
        return seen


class PriceDropParams(BaseModel):
    """Query parameters for GET /api/prices/drops."""
    threshold:   float                    = Field(10.0, ge=1, le=100)
    category:    Optional[SupplementCategory] = None
    site:        Optional[str]            = None
    limit:       int                      = Field(20, ge=1, le=100)


# ===========================================================================
# 9. INTERNAL / NiFi MODELS
# ===========================================================================


class PriceEvent(BaseModel):
    """
    Schema for POST /internal/price-event.
    Posted by NiFi's ListenHTTP processor after EvaluateJsonPath + ReplaceText.
    FastAPI validates, writes to BigQuery, checks watchlist thresholds,
    and broadcasts via WebSocket.
    """
    # identity
    canonical_product_id: str
    product_title:        str
    site:                 str
    listing_url:          str
    category:             SupplementCategory

    # pricing (already parsed by analyst pipeline at ingest time)
    price_usd:            float = Field(..., gt=0)
    price_original_usd:   Optional[float] = Field(None, ge=0)
    currency_raw:         str   = "USD"
    in_stock:             bool  = True

    # optional computed
    price_per_serving:    Optional[float] = None
    price_per_kg:         Optional[float] = None
    discount_pct:         Optional[float] = Field(None, ge=0, le=100)

    # scrape metadata
    scraped_at:           datetime = Field(default_factory=datetime.utcnow)
    scraper_version:      Optional[str] = None
    data_quality_score:   Optional[int] = Field(None, ge=0, le=100)

    @field_validator("price_usd")
    @classmethod
    def price_must_be_realistic(cls, v: float) -> float:
        if v > 50_000:
            raise ValueError(f"price_usd {v} looks like a parsing error — rejected")
        return round(v, 4)

    @model_validator(mode="after")
    def compute_discount_if_missing(self) -> "PriceEvent":
        if (
            self.discount_pct is None
            and self.price_original_usd is not None
            and self.price_original_usd > self.price_usd
        ):
            self.discount_pct = round(
                (self.price_original_usd - self.price_usd)
                / self.price_original_usd * 100, 2
            )
        return self


class PriceEventBroadcast(BaseModel):
    """
    WebSocket broadcast payload sent to Angular clients on ws/live-prices.
    Leaner than PriceEvent — only what the frontend needs to update the UI.
    """
    canonical_product_id: str
    product_name:         str
    site:                 str
    listing_url:          str
    category:             SupplementCategory

    price_usd:            float
    price_before:         Optional[float] = None   # previous scraped price (for drop detection)
    drop_pct:             Optional[float] = None   # set if this is a drop event
    is_price_drop:        bool            = False
    alert_type:           Optional[AlertType] = None

    scraped_at:           datetime
    broadcast_at:         datetime = Field(default_factory=datetime.utcnow)
