import datetime
import json
import os
import re
import uuid
from pathlib import Path

from google.cloud import bigquery

BQ_PROJECT = os.environ.get("BQ_PROJECT", "price-intelligence-495411")
BQ_DATASET = os.environ.get("BQ_DATASET", "price_intelligence")
BQ_TABLE = os.environ.get("BQ_TABLE", "products")
STORES = ("jumia", "sport-direct", "ebay")
SCRAPER_OUTPUT_ROOT = Path(os.environ.get("SCRAPER_OUTPUT_ROOT", "/app"))
if not SCRAPER_OUTPUT_ROOT.exists() or not any((SCRAPER_OUTPUT_ROOT / store).exists() for store in STORES):
    SCRAPER_OUTPUT_ROOT = Path(__file__).resolve().parent


def _get_bq_client():
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "/opt/airflow/gcp-credentials.json")
    if os.path.exists(creds_path):
        return bigquery.Client.from_service_account_json(creds_path)
    local_creds = Path("gcp-credentials.json")
    if local_creds.exists():
        return bigquery.Client.from_service_account_json(str(local_creds))
    return bigquery.Client(project=BQ_PROJECT)


def _clean_key(value):
    if value in (None, ""):
        return None
    cleaned = re.sub(r"\s+", " ", str(value)).strip().lower()
    return cleaned or None


def _iter_product_files():
    for store in STORES:
        store_dir = SCRAPER_OUTPUT_ROOT / store
        if not store_dir.exists():
            continue
        for json_path in sorted(store_dir.rglob("*.json")):
            parts = {part.lower() for part in json_path.relative_to(store_dir).parts}
            name = json_path.name.lower()
            if "_metadata" in parts or name == "manifest.json" or name.endswith("_cookies.json"):
                continue
            yield store, json_path


CATEGORY_PRIORITY = {
    "football": 1,
    "basketball": 2,
    "gym": 3,
    "combat-sports": 4,
    "racket-sports": 5,
    "volleyball": 6,
}


def _category_priority(category):
    return CATEGORY_PRIORITY.get(str(category).lower(), 100)


def _load_category_map():
    by_key = {}
    conflicts_resolved = 0
    files = 0
    records = 0
    for store, json_path in _iter_product_files():
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"Skipping {json_path}: {exc}")
            continue
        if not isinstance(data, list):
            continue
        files += 1
        category = json_path.parent.name.lower()
        for record in data:
            if not isinstance(record, dict):
                continue
            records += 1
            source = _clean_key(record.get("source") or record.get("store") or store) or store
            product_url = _clean_key(record.get("product_url"))
            image_url = _clean_key(record.get("image_url"))
            product_name = _clean_key(record.get("name"))
            for key_type, key_value in (
                ("product_url", product_url),
                ("image_url", image_url),
                ("name", product_name),
            ):
                if not key_value:
                    continue
                key = (source, key_type, key_value)
                existing = by_key.get(key)
                if existing and existing["category"] != category:
                    conflicts_resolved += 1
                    if existing["category_priority"] <= _category_priority(category):
                        continue
                by_key[key] = {
                    "source_key": source,
                    "key_type": key_type,
                    "key_value": key_value,
                    "category": category,
                    "category_priority": _category_priority(category),
                }
    print(f"Scanned {files} scraper JSON files and {records} records")
    print(f"Built {len(by_key)} category mapping keys; resolved {conflicts_resolved} conflicting keys by priority")
    return list(by_key.values())


def _count_unknown(client, table_id):
    query = f"""
        select count(*) as row_count
        from `{table_id}`
        where category is null or trim(category) = '' or lower(trim(category)) = 'unknown'
    """
    return next(client.query(query).result()).row_count


def _cleanup_temp_tables(client):
    dataset_ref = bigquery.DatasetReference(BQ_PROJECT, BQ_DATASET)
    prefixes = ("_category_backfill_map_", "_products_category_backfill_")
    for table in client.list_tables(dataset_ref):
        if table.table_id.startswith(prefixes):
            full_table_id = f"{BQ_PROJECT}.{BQ_DATASET}.{table.table_id}"
            client.delete_table(full_table_id, not_found_ok=True)
            print(f"Deleted stale temporary table: {full_table_id}")


def main():
    mappings = _load_category_map()
    if not mappings:
        raise RuntimeError("No category mappings found from scraper JSON files")

    client = _get_bq_client()
    _cleanup_temp_tables(client)
    table_id = f"{BQ_PROJECT}.{BQ_DATASET}.{BQ_TABLE}"
    temp_table_id = f"{BQ_PROJECT}.{BQ_DATASET}._category_backfill_map_{uuid.uuid4().hex[:12]}"
    before = _count_unknown(client, table_id)
    print(f"Unknown categories before backfill: {before}")

    schema = [
        bigquery.SchemaField("source_key", "STRING"),
        bigquery.SchemaField("key_type", "STRING"),
        bigquery.SchemaField("key_value", "STRING"),
        bigquery.SchemaField("category", "STRING"),
        bigquery.SchemaField("category_priority", "INTEGER"),
    ]
    job = client.load_table_from_json(mappings, temp_table_id, job_config=bigquery.LoadJobConfig(schema=schema))
    job.result()
    print(f"Loaded mapping table: {temp_table_id}")

    replacement_table_id = f"{BQ_PROJECT}.{BQ_DATASET}._products_category_backfill_{uuid.uuid4().hex[:12]}"
    rewrite_query = f"""
        with map_url as (
          select source_key, key_value, array_agg(category order by category_priority limit 1)[offset(0)] as category
          from `{temp_table_id}`
          where key_type = 'product_url'
          group by 1, 2
        ),
        map_image as (
          select source_key, key_value, array_agg(category order by category_priority limit 1)[offset(0)] as category
          from `{temp_table_id}`
          where key_type = 'image_url'
          group by 1, 2
        ),
        map_name as (
          select source_key, key_value, array_agg(category order by category_priority limit 1)[offset(0)] as category
          from `{temp_table_id}`
          where key_type = 'name'
          group by 1, 2
        )
        select
          p.* replace (
            case
              when p.category is null or trim(p.category) = '' or lower(trim(p.category)) = 'unknown' then
                coalesce(map_url.category, map_image.category, map_name.category, p.category)
              else p.category
            end as category
          )
        from `{table_id}` as p
        left join map_url
          on lower(trim(coalesce(p.product_url, ''))) = map_url.key_value
         and (lower(trim(coalesce(p.source, p.store, 'unknown'))) = map_url.source_key or lower(trim(coalesce(p.source, p.store, 'unknown'))) = 'unknown')
        left join map_image
          on lower(trim(coalesce(p.image_url, ''))) = map_image.key_value
         and (lower(trim(coalesce(p.source, p.store, 'unknown'))) = map_image.source_key or lower(trim(coalesce(p.source, p.store, 'unknown'))) = 'unknown')
        left join map_name
          on regexp_replace(lower(trim(coalesce(p.name, ''))), r'\\s+', ' ') = map_name.key_value
         and (lower(trim(coalesce(p.source, p.store, 'unknown'))) = map_name.source_key or lower(trim(coalesce(p.source, p.store, 'unknown'))) = 'unknown')
    """

    rewrite_config = bigquery.QueryJobConfig(
        destination=replacement_table_id,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )
    rewrite_job = client.query(rewrite_query, job_config=rewrite_config)
    rewrite_job.result()
    print(f"Created replacement table: {replacement_table_id}")

    replacement_unknown = _count_unknown(client, replacement_table_id)
    print(f"Unknown categories in replacement table: {replacement_unknown}")

    copy_config = bigquery.CopyJobConfig(write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE)
    copy_job = client.copy_table(replacement_table_id, table_id, job_config=copy_config)
    copy_job.result()
    print(f"Replaced original table: {table_id}")

    after = _count_unknown(client, table_id)
    print(f"Unknown categories after backfill: {after}")

    client.delete_table(temp_table_id, not_found_ok=True)
    client.delete_table(replacement_table_id, not_found_ok=True)
    print(f"Deleted temporary tables: {temp_table_id}, {replacement_table_id}")
    print(f"Finished at {datetime.datetime.now(datetime.timezone.utc).isoformat()}")


if __name__ == "__main__":
    main()
