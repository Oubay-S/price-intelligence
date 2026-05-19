import os
import json
import datetime
import uuid
from io import BytesIO
from google.cloud import bigtable
from google.cloud import bigquery

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
        bq_client.get_table(table_ref)
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


def main():
    print("Connecting to Bigtable Emulator...")
    client = bigtable.Client(project=BT_PROJECT, admin=True)
    instance = client.instance(BT_INSTANCE)
    table = instance.table(BT_TABLE)

    rows = table.read_rows()
    products = []
    for row in rows:
        product = {}
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
    if not products:
        print("No data to export")
        return

    bq_client = _get_bq_client()
    table_ref = _ensure_table(bq_client)
    rows_before = _count_bq_rows(bq_client, table_ref)
    print(f"BigQuery raw rows before export: {rows_before}")

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

    products = [
        {
            key: value
            for key, value in {**p, "_loaded_at": loaded_at, "_export_run_id": export_run_id}.items()
            if key in SCHEMA_FIELDS
        }
        for p in valid_products
    ]
    if not products:
        print("No valid products to export after required-field filtering")
        return

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
