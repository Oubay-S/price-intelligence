import uuid

ACCENT_SOURCE = "àáâãäåçèéêëìíîïñòóôõöùúûüýÿ"
ACCENT_TARGET = "aaaaaaceeeeiiiinooooouuuuyy"


def _normalize_sql(expression):
    return f"translate(lower({expression}), '{ACCENT_SOURCE}', '{ACCENT_TARGET}')"


JUMIA_STORE_SQL = _normalize_sql("concat(coalesce(store, ''), ' ', coalesce(source, ''))")
JUMIA_TEXT_SQL = _normalize_sql(
    "concat(coalesce(name, ''), ' ', coalesce(product_url, ''), ' ', "
    "coalesce(features, ''), ' ', coalesce(category, ''))"
)

JUMIA_IRRELEVANT_PATTERN = r"""
\b(
    vr[\s_-]*box|vrbox|virtual[\s_-]*reality|realite[\s_-]*virtuelle|
    casque[\s_-]+vr|lunettes?[\s_-]+vr|3d[\s_-]+vr|
    dentifrice|mousse[\s_-]+blanchissante?|eelhoe|menthe[\s_-]+poivree|
    dents?[\s_-]+sensibles?|haleine|sacs?|machines?|revelateurs?|cahiers?|
    stickers?|leds?|notebooks?|jeux?|espadrilles?|t[\s-]*shirts?|tee[\s-]*shirts?|
    mugs?|sandales?|piege[\s_-]+aquatique|braces?|bracelets?|poissons?|montres?|casquettes?|
    medical(?:e|es|s|aux)?|dentaire|dental|brosses?|let|top[\s_-]*coat|vernis|
    cirage|nettoyant[\s_-]+chaussures?|nettoyant[\s_-]+auto|car[\s_-]+interior|
    vinyle?|vinyl|caoutchouc|renovation[\s_-]+treatment|application[\s_-]+sponge|
    shine\s*(?:&|and)?\s*protect|flamingo|kiwi|opi|bellota|scies?|jardinage|
    elagage|dents?[\s_-]+japonaises?|lame[\s_-]+incurvee|protege[\s_-]*main|
    peignes?|anti[\s_-]*poux|poux|lentes?|cuir[\s_-]+chevelu|pelage[\s_-]+animal
)\b
""".replace("\n", "").replace(" ", "")

COMBAT_MOUTHGUARD_FILTER_SQL = r"""
lower(coalesce(category, '')) = 'combat-sports'
and regexp_contains(lower(coalesce(name, '')), r'\b(mouth\s*guards?|mouthguards?|mouth\s*pieces?|mouthpieces?|gum\s*shields?|gumshields?)\b')
and (
    regexp_contains(lower(coalesce(name, '')), r'\bmouthguards?\s+cases?\b')
    or (
        regexp_contains(lower(coalesce(name, '')), r'\b(anti[\s-]*snor(?:e|ing)|snor(?:e|ing)|sleep(?:\s+apnea|\s+aid|right)?|apnea|cpap|bruxism|grind(?:ing)?|clench(?:ing)?|tmj|night(?:time)?\s*(?:guard|mouth\s*guard|mouthguard)?|dental|dentek|oral[\s-]*b|splint|whiten(?:ing)?|retainer)\b')
        and not regexp_contains(lower(coalesce(name, '')), r'\b(boxing|mma|martial\s+arts?|kickboxing|muay\s+thai|ufc|combat|fight(?:ing)?|sparring|gum\s*shields?|gumshields?|rdx|meister|venum|everlast|fairtex|hayabusa|sanabul|title\s+boxing)\b')
    )
    or not regexp_contains(lower(coalesce(name, '')), r'\b(boxing|mma|martial\s+arts?|kickboxing|muay\s+thai|ufc|combat|fight(?:ing)?|sparring|gum\s*shields?|gumshields?|rdx|meister|venum|everlast|fairtex|hayabusa|sanabul|title\s+boxing)\b')
)
"""

JUMIA_IRRELEVANT_FILTER_SQL = f"""
regexp_contains({JUMIA_STORE_SQL}, r'\\bjumia\\b')
and regexp_contains({JUMIA_TEXT_SQL}, r'{JUMIA_IRRELEVANT_PATTERN}')
"""

SPORT_DIRECT_TEXT_SQL = _normalize_sql(
    "concat(coalesce(name, ''), ' ', coalesce(product_url, ''), ' ', "
    "coalesce(features, ''), ' ', coalesce(category, ''))"
)
SPORT_DIRECT_IRRELEVANT_PATTERN = r"(laptop[\s_-]+sleeves?|women)"

SPORT_DIRECT_IRRELEVANT_FILTER_SQL = f"""
regexp_contains({JUMIA_STORE_SQL}, r'\\bsport-direct\\b')
and regexp_contains({SPORT_DIRECT_TEXT_SQL}, r'{SPORT_DIRECT_IRRELEVANT_PATTERN}')
"""

IRRELEVANT_PRODUCT_FILTER_SQL = f"""
(
    ({COMBAT_MOUTHGUARD_FILTER_SQL})
    or ({JUMIA_IRRELEVANT_FILTER_SQL})
    or ({SPORT_DIRECT_IRRELEVANT_FILTER_SQL})
)
"""


def _temp_table_id_for(table_id):
    parts = table_id.split(".")
    if len(parts) != 3:
        raise ValueError("table_id must be in project.dataset.table format")
    project, dataset, _table = parts
    return f"{project}.{dataset}._products_without_irrelevant_rows_{uuid.uuid4().hex[:12]}"


def count_irrelevant_product_rows(client, table_id):
    query = f"""
        select count(*) as row_count
        from `{table_id}`
        where {IRRELEVANT_PRODUCT_FILTER_SQL}
    """
    return next(client.query(query).result()).row_count


def cleanup_irrelevant_product_rows(client, table_id):
    from google.cloud import bigquery

    temp_table_id = _temp_table_id_for(table_id)
    row_count = count_irrelevant_product_rows(client, table_id)
    print(f"Irrelevant product rows in {table_id}: {row_count}")
    if row_count == 0:
        print("No irrelevant product rows to remove")
        return 0

    rewrite_query = f"""
        select *
        from `{table_id}`
        where not ({IRRELEVANT_PRODUCT_FILTER_SQL})
    """
    rewrite_config = bigquery.QueryJobConfig(
        destination=temp_table_id,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )
    client.query(rewrite_query, job_config=rewrite_config).result()
    print(f"Created cleaned replacement table: {temp_table_id}")

    copy_config = bigquery.CopyJobConfig(write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE)
    client.copy_table(temp_table_id, table_id, job_config=copy_config).result()
    client.delete_table(temp_table_id, not_found_ok=True)
    print(f"Removed {row_count} irrelevant product rows from {table_id}")
    return row_count
