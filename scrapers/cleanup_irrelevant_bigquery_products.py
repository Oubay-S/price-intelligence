import argparse
import os

from google.cloud import bigquery

from bigquery_product_cleanup import (
    cleanup_irrelevant_product_rows,
    count_irrelevant_product_rows,
)


def _get_client(project, credentials):
    if credentials and os.path.exists(credentials):
        return bigquery.Client.from_service_account_json(credentials, project=project)
    return bigquery.Client(project=project)


def main():
    parser = argparse.ArgumentParser(
        description="Remove known irrelevant Jumia/false-positive rows from the BigQuery products table."
    )
    parser.add_argument("--project", default=os.environ.get("BQ_PROJECT", "price-intelligence-495411"))
    parser.add_argument("--dataset", default=os.environ.get("BQ_DATASET", "price_intelligence"))
    parser.add_argument("--table", default=os.environ.get("BQ_TABLE", "products"))
    parser.add_argument(
        "--credentials",
        default=os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "gcp-credentials.json"),
    )
    parser.add_argument("--dry-run", action="store_true", help="Count matching rows without modifying BigQuery.")
    args = parser.parse_args()

    table_id = f"{args.project}.{args.dataset}.{args.table}"
    client = _get_client(args.project, args.credentials)

    if args.dry_run:
        row_count = count_irrelevant_product_rows(client, table_id)
        print(f"Irrelevant product rows in {table_id}: {row_count}")
        print("Dry run completed. No BigQuery table was modified.")
        return

    cleanup_irrelevant_product_rows(client, table_id)


if __name__ == "__main__":
    main()
