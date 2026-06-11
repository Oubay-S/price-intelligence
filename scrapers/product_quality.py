import re
import unicodedata

ALWAYS_EXCLUDED_PRODUCT_PATTERNS = (
    re.compile(r"\bmouthguards?\s+cases?\b", re.I),
)


SPORT_DIRECT_EXCLUDED_PRODUCT_PATTERNS = (
    re.compile(r"\blaptop[\s_-]+sleeves?\b", re.I),
    re.compile(r"women", re.I),
)


JUMIA_EXCLUDED_PRODUCT_PATTERNS = (
    re.compile(r"\bvr[\s_-]*box\b", re.I),
    re.compile(r"\bvrbox\b", re.I),
    re.compile(r"\bvirtual[\s_-]*reality\b", re.I),
    re.compile(r"\brealite[\s_-]*virtuelle\b", re.I),
    re.compile(r"\bcasque[\s_-]+vr\b", re.I),
    re.compile(r"\blunettes?[\s_-]+vr\b", re.I),
    re.compile(r"\b3d[\s_-]+vr\b", re.I),
    re.compile(r"\bdentifrice\b", re.I),
    re.compile(r"\bmousse[\s_-]+blanchissante?\b", re.I),
    re.compile(r"\beelhoe\b", re.I),
    re.compile(r"\bmenthe[\s_-]+poivree\b", re.I),
    re.compile(r"\bdents?[\s_-]+sensibles?\b", re.I),
    re.compile(r"\bhaleine\b", re.I),
    re.compile(r"\bsacs?\b", re.I),
    re.compile(r"\bmachines?\b", re.I),
    re.compile(r"\brevelateurs?\b", re.I),
    re.compile(r"\bcahiers?\b", re.I),
    re.compile(r"\bstickers?\b", re.I),
    re.compile(r"\bleds?\b", re.I),
    re.compile(r"\bnotebooks?\b", re.I),
    re.compile(r"\bjeux?\b", re.I),
    re.compile(r"\bespadrilles?\b", re.I),
    re.compile(r"\bt[\s-]*shirts?\b", re.I),
    re.compile(r"\btee[\s-]*shirts?\b", re.I),
    re.compile(r"\bmugs?\b", re.I),
    re.compile(r"\bsandales?\b", re.I),
    re.compile(r"\bpiege[\s_-]+aquatique\b", re.I),
    re.compile(r"\bbraces?\b", re.I),
    re.compile(r"\bbracelets?\b", re.I),
    re.compile(r"\bpoissons?\b", re.I),
    re.compile(r"\bmontres?\b", re.I),
    re.compile(r"\bcasquettes?\b", re.I),
    re.compile(r"\bmedical(?:e|es|s|aux)?\b", re.I),
    re.compile(r"\bdentaire\b", re.I),
    re.compile(r"\bdental\b", re.I),
    re.compile(r"\bbrosses?\b", re.I),
    re.compile(r"\blet\b", re.I),
    re.compile(r"\btop[\s_-]*coat\b", re.I),
    re.compile(r"\bvernis\b", re.I),
    re.compile(r"\bcirage\b", re.I),
    re.compile(r"\bnettoyant[\s_-]+chaussures?\b", re.I),
    re.compile(r"\bnettoyant[\s_-]+auto\b", re.I),
    re.compile(r"\bcar[\s_-]+interior\b", re.I),
    re.compile(r"\bvinyle?\b", re.I),
    re.compile(r"\bvinyl\b", re.I),
    re.compile(r"\bcaoutchouc\b", re.I),
    re.compile(r"\brenovation[\s_-]+treatment\b", re.I),
    re.compile(r"\bapplication[\s_-]+sponge\b", re.I),
    re.compile(r"\bshine\s*(?:&|and)?\s*protect\b", re.I),
    re.compile(r"\bflamingo\b", re.I),
    re.compile(r"\bkiwi\b", re.I),
    re.compile(r"\bopi\b", re.I),
    re.compile(r"\bbellota\b", re.I),
    re.compile(r"\bscies?\b", re.I),
    re.compile(r"\bjardinage\b", re.I),
    re.compile(r"\belagage\b", re.I),
    re.compile(r"\bdents?[\s_-]+japonaises?\b", re.I),
    re.compile(r"\blame[\s_-]+incurvee\b", re.I),
    re.compile(r"\bprotege[\s_-]*main\b", re.I),
    re.compile(r"\bpeignes?\b", re.I),
    re.compile(r"\banti[\s_-]*poux\b", re.I),
    re.compile(r"\bpoux\b", re.I),
    re.compile(r"\blentes?\b", re.I),
    re.compile(r"\bcuir[\s_-]+chevelu\b", re.I),
    re.compile(r"\bpelage[\s_-]+animal\b", re.I),
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
    normalized = unicodedata.normalize("NFKD", str(value).lower())
    without_accents = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return re.sub(r"\s+", " ", without_accents).strip()


def product_haystack(product):
    return " ".join(
        _clean_text(product.get(field))
        for field in SEARCHABLE_FIELDS
    )


def is_mouthguard_query(query):
    return bool(query and MOUTHGUARD_TERMS.search(_clean_text(query)))


def _store_name(product, store=None):
    return _clean_text(store or product.get("store") or product.get("source"))


def is_excluded_product(product, store=None):
    haystack = product_haystack(product)
    if any(pattern.search(haystack) for pattern in ALWAYS_EXCLUDED_PRODUCT_PATTERNS):
        return True

    store_name = _store_name(product, store)
    if store_name == "jumia" and any(
        pattern.search(haystack) for pattern in JUMIA_EXCLUDED_PRODUCT_PATTERNS
    ):
        return True

    if store_name == "sport-direct" and any(
        pattern.search(haystack) for pattern in SPORT_DIRECT_EXCLUDED_PRODUCT_PATTERNS
    ):
        return True

    has_dental_context = any(pattern.search(haystack) for pattern in DENTAL_MOUTHGUARD_PATTERNS)
    has_combat_context = bool(COMBAT_MOUTHGUARD_CONTEXT.search(haystack))
    return has_dental_context and not has_combat_context


def is_relevant_product(product, store=None, category=None, query=None):
    if is_excluded_product(product, store=store):
        return False

    haystack = product_haystack(product)
    category_value = _clean_text(category or product.get("category") or product.get("subcategory"))
    requires_combat_context = (
        category_value in COMBAT_CATEGORIES and bool(MOUTHGUARD_TERMS.search(haystack))
    ) or is_mouthguard_query(query)

    if not requires_combat_context:
        return True

    return bool(MOUTHGUARD_TERMS.search(haystack) and COMBAT_MOUTHGUARD_CONTEXT.search(haystack))
