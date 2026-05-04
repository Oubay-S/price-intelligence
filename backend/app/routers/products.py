from datetime import datetime, timezone

from fastapi import APIRouter

from app.models.product import (
    BrandInfo,
    BrandTier,
    PriceInfo,
    PriceTrend,
    ProductResponse,
    RatingsInfo,
    SupplementCategory,
)

router = APIRouter()


@router.get("", response_model=list[ProductResponse])
def list_products() -> list[ProductResponse]:
    now = datetime.now(timezone.utc)

    return [
        ProductResponse(
            canonical_product_id="a1b2c3d4e5f6",
            name="Optimum Nutrition Gold Standard 100% Whey - 2.27kg",
            site="iherb.com",
            listing_url="https://iherb.com/pr/optimum-nutrition-gold-standard-whey",
            category=SupplementCategory.STRENGTH_NUTRITION,
            subcategory="whey_protein",
            brand_raw="Optimum Nutrition",
            in_stock=True,
            brand=BrandInfo(
                brand_id="optimum-nutrition",
                name="Optimum Nutrition",
                country="US",
                tier=BrandTier.PREMIUM,
                verified=True,
            ),
            flavour="Double Rich Chocolate",
            image_url="https://cdn.iherb.com/whey-2270.jpg",
            pricing=PriceInfo(
                current=64.99,
                original=79.99,
                currency_raw="USD",
                per_serving=0.92,
                trend=PriceTrend.FALLING,
                velocity_per_day=-0.35,
            ),
            ratings=RatingsInfo(score=4.7, count=15820, composite_score=4.65),
            tags=["bestseller", "whey", "low_sugar"],
            brand_tier=BrandTier.PREMIUM,
            scraped_at=now,
            data_quality_score=94,
        ),
        ProductResponse(
            canonical_product_id="f7e6d5c4b3a2",
            name="Myprotein Creatine Monohydrate - 500g",
            site="myprotein.com",
            listing_url="https://myprotein.com/creatine-monohydrate-500g",
            category=SupplementCategory.STRENGTH_NUTRITION,
            subcategory="creatine",
            brand_raw="Myprotein",
            in_stock=True,
            brand=BrandInfo(
                brand_id="myprotein",
                name="Myprotein",
                country="UK",
                tier=BrandTier.MID,
                verified=True,
            ),
            image_url="https://cdn.myprotein.com/creatine-500g.jpg",
            pricing=PriceInfo(
                current=18.50,
                currency_raw="USD",
                per_serving=0.18,
                trend=PriceTrend.STABLE,
            ),
            ratings=RatingsInfo(score=4.5, count=8430, composite_score=4.48),
            tags=["creatine", "vegan"],
            brand_tier=BrandTier.MID,
            scraped_at=now,
            data_quality_score=88,
        ),
        ProductResponse(
            canonical_product_id="9988aabbccdd",
            name="C4 Original Pre-Workout - 30 Servings",
            site="bodybuilding.com",
            listing_url="https://bodybuilding.com/store/c4-original-30",
            category=SupplementCategory.STRENGTH_NUTRITION,
            subcategory="pre_workout",
            brand_raw="Cellucor",
            in_stock=False,
            brand=BrandInfo(
                brand_id="cellucor",
                name="Cellucor",
                country="US",
                tier=BrandTier.MID,
                verified=True,
            ),
            flavour="Fruit Punch",
            image_url="https://cdn.bodybuilding.com/c4-original.jpg",
            pricing=PriceInfo(
                current=29.99,
                original=34.99,
                currency_raw="USD",
                per_serving=1.00,
                trend=PriceTrend.RISING,
                velocity_per_day=0.12,
            ),
            ratings=RatingsInfo(score=4.3, count=12100, composite_score=4.31),
            tags=["pre_workout", "caffeine"],
            brand_tier=BrandTier.MID,
            scraped_at=now,
            data_quality_score=82,
        ),
    ]
