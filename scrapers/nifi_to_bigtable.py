import argparse
import datetime
import hashlib
import json
import os
import sys

from google.api_core.exceptions import AlreadyExists
from google.cloud import bigtable
from google.cloud.bigtable import column_family

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "price-intel-local")
INSTANCE_ID = os.environ.get("BIGTABLE_INSTANCE_ID", "price-intel-instance")
TABLE_ID = os.environ.get("BIGTABLE_TABLE_ID", "products")
COLUMN_FAMILY = "info"


def _get_table():
    client = bigtable.Client(project=PROJECT_ID, admin=True)
    instance = client.instance(INSTANCE_ID)
    table = instance.table(TABLE_ID)

    try:
        table.create()
    except AlreadyExists:
        pass

    try:
        table.column_family(COLUMN_FAMILY, column_family.MaxVersionsGCRule(100)).create()
    except AlreadyExists:
        pass

    return table


def _clean_metadata(value):
    if value in (None, ""):
        return None
    cleaned = str(value).strip()
    if not cleaned or cleaned.lower() == "unknown":
        return None
    if cleaned.startswith("${") and cleaned.endswith("}"):
        return None
    return cleaned


def _detect_source(row_data, source_arg):
    source = _clean_metadata(source_arg) or _clean_metadata(row_data.get("source")) or _clean_metadata(row_data.get("store"))
    if source:
        return source
    url = str(row_data.get("product_url", "")).lower()
    if "ebay." in url:
        return "ebay"
    if "sportsdirect" in url:
        return "sport-direct"
    if "jumia" in url:
        return "jumia"
    return "unknown"


def _detect_category(row_data, category_arg):
    return _clean_metadata(category_arg) or _clean_metadata(row_data.get("category")) or "unknown"


def _parse_timestamp(value):
    if not value:
        return datetime.datetime.now(datetime.timezone.utc)
    try:
        parsed = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=datetime.timezone.utc)
        return parsed
    except ValueError:
        return datetime.datetime.now(datetime.timezone.utc)


def _timestamp_key(value):
    parsed = _parse_timestamp(value)
    return parsed.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def _row_key(source, category, row_data):
    stable_part = row_data.get("product_url") or row_data.get("image_url") or row_data.get("name") or json.dumps(row_data, sort_keys=True)
    digest = hashlib.sha1(str(stable_part).encode("utf-8")).hexdigest()[:16]  # nosec B328
    scraped_at_key = _timestamp_key(row_data.get("scraped_at"))
    return f"{source}#{category}#{digest}#{scraped_at_key}".encode("utf-8")


def _cell_value(value):
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def main():
    parser = argparse.ArgumentParser(description="NiFi to Bigtable ingestion")
    parser.add_argument("--source", help="Scraping source: ebay, sport-direct, jumia")
    parser.add_argument("--category", help="Product category")
    args = parser.parse_args()

    data = sys.stdin.read().strip()
    if not data:
        print("No input received from NiFi", file=sys.stderr)
        return

    try:
        row_data = json.loads(data)
        if not isinstance(row_data, dict):
            raise ValueError("NiFi split record must be a JSON object")

        source = _detect_source(row_data, args.source)
        category = _detect_category(row_data, args.category)
        timestamp = _parse_timestamp(row_data.get("scraped_at"))

        table = _get_table()
        row_key = _row_key(source, category, row_data)
        row = table.direct_row(row_key)

        for key, value in row_data.items():
            if value is None:
                continue
            row.set_cell(COLUMN_FAMILY, str(key).encode("utf-8"), _cell_value(value).encode("utf-8"), timestamp=timestamp)

        ingestion_timestamp = datetime.datetime.now(datetime.timezone.utc)
        ingested_at = ingestion_timestamp.isoformat()
        row.set_cell(COLUMN_FAMILY, b"source", source.encode("utf-8"), timestamp=timestamp)
        row.set_cell(COLUMN_FAMILY, b"store", source.encode("utf-8"), timestamp=timestamp)
        row.set_cell(COLUMN_FAMILY, b"category", str(category).encode("utf-8"), timestamp=timestamp)
        row.set_cell(COLUMN_FAMILY, b"_bigtable_row_key", row_key, timestamp=ingestion_timestamp)
        row.set_cell(COLUMN_FAMILY, b"ingestion_method", b"nifi", timestamp=ingestion_timestamp)
        row.set_cell(COLUMN_FAMILY, b"ingested_at", ingested_at.encode("utf-8"), timestamp=ingestion_timestamp)
        row.commit()
        print(f"ingested source={source} category={category}")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
