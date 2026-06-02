import re

ALWAYS_EXCLUDED_PRODUCT_PATTERNS = (
    re.compile(r"\bmouthguards?\s+cases?\b", re.I),
)

DENTAL_MOUTHGUARD_PATTERNS = (
    re.compile(r"\banti[\s-]*snor(?:e|ing)\b", re.I),
    re.compile(r"\bsnor(?:e|ing)\b", re.I),
    re.compile(r"\bsleep(?:\s+apnea|\s+aid|right)?\b", re.I),
    re.compile(r"\bapnea\b", re.I),
    re.compile(r"\bcpap\b", re.I),
    re.compile(r"\bbruxism\b", re.I),
    re.compile(r"\bgrind(?:ing)?\b", re.I),
    re.compile(r"\bclench(?:ing)?\b", re.I),
    re.compile(r"\btmj\b", re.I),
    re.compile(r"\bnight(?:time)?\s*(?:guard|mouth\s*guard|mouthguard)?\b", re.I),
    re.compile(r"\bdental\b", re.I),
    re.compile(r"\bdentek\b", re.I),
    re.compile(r"\boral[\s-]*b\b", re.I),
    re.compile(r"\bsplint\b", re.I),
    re.compile(r"\bwhiten(?:ing)?\b", re.I),
    re.compile(r"\bretainer\b", re.I),
)

MOUTHGUARD_TERMS = re.compile(
    r"\b(mouth\s*guards?|mouthguards?|mouth\s*pieces?|mouthpieces?|gum\s*shields?|gumshields?)\b",
    re.I,
)
COMBAT_MOUTHGUARD_CONTEXT = re.compile(
    r"\b(boxing|mma|martial\s+arts?|kickboxing|muay\s+thai|ufc|combat|fight(?:ing)?|sparring|gum\s*shields?|gumshields?|rdx|meister|venum|everlast|fairtex|hayabusa|sanabul|title\s+boxing)\b",
    re.I,
)
COMBAT_CATEGORIES = {"combat-sports", "combat_boxing_mma"}
SEARCHABLE_FIELDS = (
    "name",
    "brand_raw",
    "features",
    "product_url",
    "listing_url",
)


def _clean_text(value):
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        value = " ".join(str(item) for item in value)
    return re.sub(r"\s+", " ", str(value).lower()).strip()


def product_haystack(product):
    return " ".join(
        _clean_text(product.get(field))
        for field in SEARCHABLE_FIELDS
    )


def is_mouthguard_query(query):
    return bool(query and MOUTHGUARD_TERMS.search(_clean_text(query)))


def is_excluded_product(product):
    haystack = product_haystack(product)
    if any(pattern.search(haystack) for pattern in ALWAYS_EXCLUDED_PRODUCT_PATTERNS):
        return True

    has_dental_context = any(pattern.search(haystack) for pattern in DENTAL_MOUTHGUARD_PATTERNS)
    has_combat_context = bool(COMBAT_MOUTHGUARD_CONTEXT.search(haystack))
    return has_dental_context and not has_combat_context


def is_relevant_product(product, store=None, category=None, query=None):
    if is_excluded_product(product):
        return False

    haystack = product_haystack(product)
    category_value = _clean_text(category or product.get("category") or product.get("subcategory"))
    requires_combat_context = (
        category_value in COMBAT_CATEGORIES and bool(MOUTHGUARD_TERMS.search(haystack))
    ) or is_mouthguard_query(query)

    if not requires_combat_context:
        return True

    return bool(MOUTHGUARD_TERMS.search(haystack) and COMBAT_MOUTHGUARD_CONTEXT.search(haystack))
