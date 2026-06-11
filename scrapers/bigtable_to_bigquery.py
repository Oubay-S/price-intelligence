import os
import sys
import json
import datetime
import uuid
from io import BytesIO
from google.cloud import bigtable
from google.cloud import bigquery

from product_quality import is_relevant_product

# Make the data-quality GE gate importable. Candidate locations:
#   - host/dev:     <repo>/data-quality   (sibling of scrapers/)
#   - airflow ctr:  /opt/airflow/data-quality  (compose mount)
#   - env override: DQ_DIR
_DQ_CANDIDATES = [
    os.environ.get("DQ_DIR"),
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data-quality"),
    "/opt/airflow/data-quality",
]
for _cand in _DQ_CANDIDATES:
    if _cand and os.path.isdir(_cand) and _cand not in sys.path:
        sys.path.insert(0, _cand)
try:
    from validate_products import validate_products
except Exception as _exc:  # pragma: no cover - gate import is best-effort
    validate_products = None
    print(f"WARNING: GE gate unavailable ({_exc}); proceeding without validation")

# Set GE_GATE_BLOCK=0 to downgrade a failed gate from blocking to warn-only.
_GATE_BLOCKS = os.environ.get("GE_GATE_BLOCK", "1") != "0"

BT_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "price-intel-local")
BT_INSTANCE = os.environ.get("BIGTABLE_INSTANCE_ID", "price-intel-instance")
BT_TABLE = "products"
BQ_PROJECT = os.environ.get("BQ_PROJECT", "price-intelligence-495411")
BQ_DATASET = os.environ.get("BQ_DATASET", "price_intelligence")
BQ_TABLE = os.environ.get("BQ_TABLE", "products")

BQ_SCHEMA = [
    bigquery.SchemaField("name", "STRING"),
    bigquery.SchemaField("current_price", "STRING"),
    bigquery.SchemaField("price_before_discount", "STRING"),
    bigquery.SchemaField("discount", "STRING"),
    bigquery.SchemaField("stars", "STRING"),
    bigquery.SchemaField("availability", "STRING"),
    bigquery.SchemaField("product_url", "STRING"),
    bigquery.SchemaField("image_url", "STRING"),
    bigquery.SchemaField("features", "STRING"),
    bigquery.SchemaField("sizes", "STRING"),
    bigquery.SchemaField("scraped_at", "STRING"),
    bigquery.SchemaField("source", "STRING"),
    bigquery.SchemaField("store", "STRING"),
    bigquery.SchemaField("category", "STRING"),
    bigquery.SchemaField("_bigtable_row_key", "STRING"),
    bigquery.SchemaField("_ingestion_run_id", "STRING"),
    bigquery.SchemaField("_staged_at", "TIMESTAMP"),
    bigquery.SchemaField("ingested_at", "TIMESTAMP"),
    bigquery.SchemaField("ingestion_method", "STRING"),
    bigquery.SchemaField("_loaded_at", "TIMESTAMP"),
    bigquery.SchemaField("_export_run_id", "STRING"),
]
SCHEMA_FIELDS = {field.name for field in BQ_SCHEMA}
REQUIRED_PRODUCT_FIELDS = ("name", "current_price", "scraped_at")


def _get_bq_client():
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "/opt/airflow/gcp-credentials.json")
    if os.path.exists(creds_path):
        return bigquery.Client.from_service_account_json(creds_path)
    print("No GCP credentials file found, using default client")
    return bigquery.Client(project=BQ_PROJECT)


def _ensure_table(bq_client):
    dataset_ref = bigquery.DatasetReference(BQ_PROJECT, BQ_DATASET)
    table_ref = bigquery.TableReference(dataset_ref, BQ_TABLE)
    try:
        table = bq_client.get_table(table_ref)
        existing_fields = {field.name for field in table.schema}
        missing_fields = [field for field in BQ_SCHEMA if field.name not in existing_fields]
        if missing_fields:
            table.schema = list(table.schema) + missing_fields
            bq_client.update_table(table, ["schema"])
            print(f"Added BigQuery schema fields: {', '.join(field.name for field in missing_fields)}")
        return table_ref
    except Exception:
        try:
            bq_client.create_dataset(bigquery.Dataset(dataset_ref))
            print(f"Created dataset {BQ_PROJECT}.{BQ_DATASET}")
        except Exception:
            pass
        table = bigquery.Table(table_ref, schema=BQ_SCHEMA)
        bq_client.create_table(table)
        print(f"Created table {BQ_PROJECT}.{BQ_DATASET}.{BQ_TABLE}")
        return table_ref


def _count_bq_rows(bq_client, table_ref):
    query = f"select count(*) as row_count from `{table_ref.project}.{table_ref.dataset_id}.{table_ref.table_id}`"
    return next(bq_client.query(query).result()).row_count


def _existing_bigtable_keys(bq_client, table_ref):
    query = f"""
        select distinct _bigtable_row_key
        from `{table_ref.project}.{table_ref.dataset_id}.{table_ref.table_id}`
        where _bigtable_row_key is not null
    """
    return {row._bigtable_row_key for row in bq_client.query(query).result()}


def main():
    print("Connecting to Bigtable Emulator...")
    client = bigtable.Client(project=BT_PROJECT, admin=True)
    instance = client.instance(BT_INSTANCE)
    table = instance.table(BT_TABLE)

    rows = table.read_rows()
    products = []
    for row in rows:
        product = {"_bigtable_row_key": row.row_key.decode("utf-8")}
        for cf, cols in row.cells.items():
            for col_name, cells in cols.items():
                key = col_name.decode("utf-8")
                value = cells[0].value.decode("utf-8")
                product[key] = value
        if product:
            if "source" in product and "store" not in product:
                product["store"] = product["source"]
            products.append(product)

    print(f"Read {len(products)} products from Bigtable")
    export_ingestion_run_id = os.environ.get("EXPORT_INGESTION_RUN_ID")
    if export_ingestion_run_id:
        products = [
            p for p in products
            if p.get("_ingestion_run_id") == export_ingestion_run_id
        ]
        print(f"Filtered to {len(products)} products for ingestion_run_id={export_ingestion_run_id}")
    if not products:
        print("No data to export")
        return

    bq_client = _get_bq_client()
    table_ref = _ensure_table(bq_client)
    rows_before = _count_bq_rows(bq_client, table_ref)
    print(f"BigQuery raw rows before export: {rows_before}")
    existing_keys = _existing_bigtable_keys(bq_client, table_ref)
    if existing_keys:
        print(f"Found {len(existing_keys)} Bigtable row keys already exported to BigQuery")

    loaded_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    export_run_id = os.environ.get("EXPORT_RUN_ID", str(uuid.uuid4()))
    valid_products = [
        p for p in products
        if all(p.get(field) not in (None, "") for field in REQUIRED_PRODUCT_FIELDS)
    ]
    skipped_products = len(products) - len(valid_products)
    if skipped_products:
        print(f"Skipped {skipped_products} Bigtable rows missing required product fields: "
              f"{REQUIRED_PRODUCT_FIELDS}")

    relevant_products = [
        p for p in valid_products
        if is_relevant_product(
            p,
            store=p.get("store") or p.get("source"),
            category=p.get("category"),
        )
    ]
    skipped_irrelevant = len(valid_products) - len(relevant_products)
    if skipped_irrelevant:
        print(f"Skipped {skipped_irrelevant} irrelevant Bigtable rows before BigQuery export")

    new_products = [
        p for p in relevant_products
        if p.get("_bigtable_row_key") not in existing_keys
    ]
    duplicate_products = len(relevant_products) - len(new_products)
    if duplicate_products:
        print(f"Skipped {duplicate_products} Bigtable rows already exported to BigQuery")

    products = [
        {
            key: value
            for key, value in {**p, "_loaded_at": loaded_at, "_export_run_id": export_run_id}.items()
            if key in SCHEMA_FIELDS
        }
        for p in new_products
    ]
    if not products:
        if valid_products and not new_products:
            print("No new Bigtable rows to export; all valid observations are already in BigQuery")
        else:
            print("No valid products to export after required-field filtering")
        return

    # --- Great Expectations gate: validate raw rows before the BigQuery load ---
    if validate_products is not None:
        gate = validate_products(products)
        print(gate.summary())
        if not gate.ok:
            if _GATE_BLOCKS:
                raise SystemExit(
                    f"GE gate FAILED ({len(gate.failures)} critical expectations); "
                    f"BigQuery load blocked. Set GE_GATE_BLOCK=0 to override."
                )
            print("GE gate failed but GE_GATE_BLOCK=0 -> loading anyway (warn-only)")

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        schema=BQ_SCHEMA,
        schema_update_options=[
            bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION,
        ],
    )

    jsonl = "\n".join(json.dumps(p, ensure_ascii=False) for p in products)
    job = bq_client.load_table_from_file(
        BytesIO(jsonl.encode("utf-8")),
        table_ref,
        job_config=job_config,
    )
    job.result()

    if job.errors:
        print(f"BigQuery load errors: {job.errors}")
    else:
        rows_after = _count_bq_rows(bq_client, table_ref)
        print(f"Appended {len(products)} products to BigQuery "
              f"{BQ_PROJECT}.{BQ_DATASET}.{BQ_TABLE} with export_run_id={export_run_id}")
        print(f"BigQuery raw rows after export: {rows_after}")
        print(f"BigQuery raw row delta: {rows_after - rows_before}")


if __name__ == "__main__":
    main()
