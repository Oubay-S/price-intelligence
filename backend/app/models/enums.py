"""Domain enums shared across every other models module.

Pure values — no Pydantic, no FastAPI, no DB. Imported by every other
``models/*.py`` so this file must stay import-cycle-free.
"""
from __future__ import annotations

from enum import Enum


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
    SCRAPED_AT_DESC       = "scraped_at_desc"   # newest first (default)
    PRICE_ASC             = "price_asc"
    PRICE_DESC            = "price_desc"
    RATING_DESC           = "rating_desc"
    DISCOUNT_DESC         = "discount_desc"
    PRICE_PER_SERVING_ASC = "price_per_serving_asc"
