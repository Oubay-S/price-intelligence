"""
Maps the flat JSON dumps produced by /scrapers/{site}/{sport}/*.json into
ProductCreate instances. The scraper output is intentionally string-heavy and
omits site/category/subcategory/canonical_id — those are inferred from the
file path here. Parsing of the *_raw fields is the dbt layer's job.
"""

from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Iterator, Optional
from urllib.parse import parse_qs, unquote, urlparse

from app.models.product import (
    PriceInfo,
    ProductCreate,
    ProductResponse,
    RatingsInfo,
    SupplementCategory,
)


SCRAPER_ROOT = Path(__file__).resolve().parents[3] / "scrapers"

SITE_DOMAIN = {
    "jumia":   "jumia.ma",
    "ebay":    "ebay.com",
    "walmart": "walmart.com",
}

SITE_CURRENCY = {
    "jumia.ma":    "MAD",
    "ebay.com":    "USD",
    "walmart.com": "USD",
}

SPORT_TO_CATEGORY = {
    "gym":           SupplementCategory.STRENGTH_NUTRITION,
    "football":      SupplementCategory.TEAM_FOOTBALL,
    "basketball":    SupplementCategory.TEAM_BASKETBALL,
    "volleyball":    SupplementCategory.TEAM_VOLLEYBALL,
    "racket-sports": SupplementCategory.TEAM_RACKET,
    "combat-sports": SupplementCategory.COMBAT_BOXING_MMA,
}

# eBay product names are wrapped with this UI string — strip it.
_EBAY_NOISE = re.compile(r"\s+Opens in a new window or tab\s*$", re.IGNORECASE)


def _site_from_folder(name: str) -> str:
    return SITE_DOMAIN.get(name.lower(), name.lower())


def _category_from_folder(name: str) -> SupplementCategory:
    return SPORT_TO_CATEGORY.get(name.lower(), SupplementCategory.STRENGTH_NUTRITION)


def _subcategory_from_filename(filename: str) -> Optional[str]:
    stem = Path(filename).stem.lower()
    stem = re.sub(r"^(ebay|walmart|jumia)_", "", stem)
    stem = re.sub(r"_?data$", "", stem)
    stem = stem.replace("-", "_").strip("_")
    return stem or None


def _resolve_redirect(url: str) -> str:
    """Walmart's listing URLs are affiliate redirects — the real URL is in rd=."""
    if "walmart.com/sp/track" not in url:
        return url
    rd = parse_qs(urlparse(url).query).get("rd", [None])[0]
    return unquote(rd) if rd else url


def _strip_tracking(url: str) -> str:
    """Same logic as ProductCreate.strip_tracking_params — applied here so the
    canonical_product_id we compute matches the listing_url Pydantic stores."""
    return url.split("?")[0].rstrip("/")


def _canonical_id(listing_url: str) -> str:
    return hashlib.sha256(listing_url.encode("utf-8")).hexdigest()[:32]


def _clean_name(name: str) -> str:
    return _EBAY_NOISE.sub("", name).strip()


def _first_word(name: str) -> str:
    parts = _clean_name(name).split()
    return parts[0] if parts else "Unknown"


def _parse_in_stock(availability: Optional[str]) -> bool:
    if not availability:
        return True
    a = availability.strip().lower()
    if a in {"-", "n/a", ""}:
        return True
    return "out of stock" not in a and "unavailable" not in a


def _coerce_str(value: object) -> Optional[str]:
    """Scraper fields are heterogeneous: some are lists (jumia features),
    some are 'N/A' sentinels, some are missing. Normalise to str | None."""
    if value is None:
        return None
    if isinstance(value, list):
        return " | ".join(str(v) for v in value) if value else None
    s = str(value).strip()
    if s in {"", "N/A", "n/a", "-"}:
        return None
    return s


def _to_product_create(
    item: dict,
    site: str,
    category: SupplementCategory,
    subcategory: Optional[str],
) -> Optional[ProductCreate]:
    name_raw = item.get("name")
    raw_url = item.get("product_url")
    price_raw = _coerce_str(item.get("current_price"))
    if not name_raw or not raw_url or not price_raw:
        return None

    listing_url = _strip_tracking(_resolve_redirect(raw_url))
    name = _clean_name(name_raw)[:300]

    return ProductCreate(
        canonical_product_id=_canonical_id(listing_url),
        name=name,
        site=site,
        listing_url=listing_url,
        category=category,
        subcategory=subcategory,
        brand_raw=_first_word(name),
        in_stock=_parse_in_stock(item.get("availability")),
        # raw pricing
        price_raw=price_raw,
        price_original_raw=_coerce_str(item.get("price_before_discount")),
        currency_raw=SITE_CURRENCY.get(site, "USD"),
        promo_label_raw=_coerce_str(item.get("discount")),
        # raw ratings
        rating_raw=_coerce_str(item.get("stars")),
        # raw product attributes
        product_title_raw=name_raw,
        image_url=_coerce_str(item.get("image_url")),
        category_raw=subcategory,
        # raw nutrition / equipment hints
        weight_raw=_coerce_str(item.get("weight")),
        size_raw=_coerce_str(item.get("sizes")),
        # scrape metadata
        scraped_at=item.get("scraped_at"),
    )


def load_file(path: Path) -> list[ProductCreate]:
    """Load one scraper JSON; site/category/subcategory come from the path."""
    parts = path.relative_to(SCRAPER_ROOT).parts
    if len(parts) < 3:
        return []
    site_folder, sport_folder, filename = parts[0], parts[1], parts[-1]
    site = _site_from_folder(site_folder)
    category = _category_from_folder(sport_folder)
    subcategory = _subcategory_from_filename(filename)

    with path.open(encoding="utf-8") as f:
        items = json.load(f)
    if not isinstance(items, list):
        return []

    products: list[ProductCreate] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            product = _to_product_create(item, site, category, subcategory)
        except Exception:
            continue
        if product is not None:
            products.append(product)
    return products


def iter_all(root: Path = SCRAPER_ROOT) -> Iterator[ProductCreate]:
    """Walk every {site}/{sport}/*.json under root and yield ProductCreate items."""
    if not root.exists():
        return
    for site_dir in sorted(root.iterdir()):
        if not site_dir.is_dir() or site_dir.name.lower() not in SITE_DOMAIN:
            continue
        for json_file in sorted(site_dir.rglob("*.json")):
            yield from load_file(json_file)


def load_all(root: Path = SCRAPER_ROOT) -> list[ProductCreate]:
    return list(iter_all(root))


# ---------------------------------------------------------------------------
# Dev-time adapter: ProductCreate (raw) -> ProductResponse (normalised).
# Production parsing of *_raw fields belongs in dbt — this is the placeholder
# path used while the BigQuery mart is not yet populated.
# ---------------------------------------------------------------------------

_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")


def _parse_first_float(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    match = _NUMBER_RE.search(value.replace(",", ""))
    return float(match.group()) if match else None


def to_response(p: ProductCreate) -> Optional[ProductResponse]:
    current = _parse_first_float(p.price_raw)
    if current is None or current <= 0:
        return None

    original = _parse_first_float(p.price_original_raw)
    if original is not None and original <= current:
        original = None

    pricing = PriceInfo(
        current=current,
        original=original,
        currency_raw=p.currency_raw,
    )

    ratings: Optional[RatingsInfo] = None
    score = _parse_first_float(p.rating_raw)
    if score is not None and 0 < score <= 5:
        ratings = RatingsInfo(score=score, count=0)

    return ProductResponse(
        canonical_product_id=p.canonical_product_id,
        name=p.name,
        site=p.site,
        listing_url=p.listing_url,
        category=p.category,
        subcategory=p.subcategory,
        brand_raw=p.brand_raw,
        in_stock=p.in_stock,
        image_url=p.image_url,
        pricing=pricing,
        ratings=ratings,
        scraped_at=p.scraped_at,
    )


@lru_cache(maxsize=1)
def load_all_responses() -> list[ProductResponse]:
    """Cached, normalised view of every scraper JSON. Cleared on process restart."""
    return [r for r in (to_response(p) for p in iter_all()) if r is not None]
