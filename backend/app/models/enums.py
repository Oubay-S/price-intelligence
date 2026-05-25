"""Domain enums shared across every other models module.

Pure values — no Pydantic, no FastAPI, no DB. Imported by every other
``models/*.py`` so this file must stay import-cycle-free.
"""
from __future__ import annotations

from enum import Enum


class SupplementCategory(str, Enum):
    """Top-level product categories — maps to the BigQuery ``category`` column.

    Only categories that actually exist in the scraped data are listed; the
    raw↔enum bridge lives in ``services/bigquery.py``. The earlier
    nutrition / endurance / wearables / combat-protection buckets were dropped
    because no scraped product maps to them (they returned empty catalogue
    results).
    """
    STRENGTH_HOME_GYM  = "strength_home_gym"   # raw: gym, general
    TEAM_FOOTBALL      = "team_football"        # raw: football
    TEAM_BASKETBALL    = "team_basketball"      # raw: basketball
    TEAM_VOLLEYBALL    = "team_volleyball"      # raw: Volleyball
    TEAM_RACKET        = "team_racket"          # raw: Racket-Sports
    COMBAT_BOXING_MMA  = "combat_boxing_mma"    # raw: combat-sports


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
