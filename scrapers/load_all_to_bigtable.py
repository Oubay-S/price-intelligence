import datetime
import hashlib
import json
import os
import re
from pathlib import Path

from google.api_core.exceptions import AlreadyExists
from google.cloud import bigtable
from google.cloud.bigtable import column_family

if not os.environ.get("BIGTABLE_EMULATOR_HOST"):
    os.environ["BIGTABLE_EMULATOR_HOST"] = "localhost:8086"

REQUIRED_FIELDS = {"name", "current_price", "scraped_at"}


def get_bigtable_table(
    project_id=os.environ.get("GOOGLE_CLOUD_PROJECT", "price-intel-local"),
    instance_id=os.environ.get("BIGTABLE_INSTANCE_ID", "price-intel-instance"),
    table_id="products",
):
    """Connect to Bigtable and return the products table, creating local emulator objects if needed."""
    try:
        client = bigtable.Client(project=project_id, admin=True)
        instance = client.instance(instance_id)
        table = instance.table(table_id)

        try:
            table.create()
            print(f"  Table '{table_id}' created.")
        except AlreadyExists:
            pass

        cf_id = "info"
        try:
            table.column_family(cf_id, column_family.MaxVersionsGCRule(100)).create()
            print(f"  Column family '{cf_id}' created.")
        except AlreadyExists:
            pass

        return table
    except Exception as exc:
        print(f"Bigtable connection error: {exc}")
        return None


def _parse_scraped_at(value):
    if not value:
        return datetime.datetime.now(datetime.timezone.utc)
    try:
        parsed = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=datetime.timezone.utc)
        return parsed
    except ValueError:
        print(f"  Invalid scraped_at value '{value}', using current time")
        return datetime.datetime.now(datetime.timezone.utc)


def _row_key(store_name, category, item):
    name = str(item.get("name") or "unknown")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower()[:60] or "unknown"
    stable_part = item.get("product_url") or item.get("image_url") or name
    digest = hashlib.sha1(str(stable_part).encode("utf-8")).hexdigest()[:12]  # nosec B328
    scraped_at = _parse_scraped_at(item.get("scraped_at"))
    scraped_at_key = scraped_at.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    return f"{store_name}#{category}#{slug}#{digest}#{scraped_at_key}".encode("utf-8")


def _load_json_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("expected a JSON array of product objects")
    return data


def load_file_to_bigtable(table, file_path, store_name):
    """Load a single scraper JSON file into Bigtable."""
    if not os.path.exists(file_path):
        return 0

    try:
        data = _load_json_file(file_path)
    except Exception as exc:
        print(f"  Skipping {file_path}: {exc}")
        return 0

    category = os.path.basename(os.path.dirname(file_path))
    rows_added = 0
    rows_skipped = 0

    for item in data:
        if not isinstance(item, dict):
            rows_skipped += 1
            continue

        missing = [field for field in REQUIRED_FIELDS if not item.get(field)]
        if missing:
            rows_skipped += 1
            print(f"  Skipping product missing {missing}: {item.get('name', 'unknown')}")
            continue

        row_key = _row_key(store_name, category, item)
        row = table.direct_row(row_key)
        ts = _parse_scraped_at(item.get("scraped_at"))

        for key, value in item.items():
            if value is None:
                continue
            if isinstance(value, (list, dict)):
                cell_value = json.dumps(value, ensure_ascii=False)
            else:
                cell_value = str(value)
            row.set_cell("info", str(key).encode("utf-8"), cell_value.encode("utf-8"), timestamp=ts)

        row.set_cell("info", b"source", store_name.encode("utf-8"), timestamp=ts)
        row.set_cell("info", b"store", store_name.encode("utf-8"), timestamp=ts)
        row.set_cell("info", b"category", category.encode("utf-8"), timestamp=ts)
        row.set_cell("info", b"_bigtable_row_key", row_key, timestamp=ts)
        row.commit()
        rows_added += 1

    if rows_skipped:
        print(f"  {file_path}: loaded {rows_added}, skipped {rows_skipped}")
    return rows_added


def load_all():
    print(f"Connecting to Bigtable Emulator ({os.environ['BIGTABLE_EMULATOR_HOST']})...")
    table = get_bigtable_table()
    if not table:
        raise RuntimeError("Could not connect to Bigtable")

    total_rows = 0
    for store in ["jumia", "sport-direct", "ebay"]:
        store_path = Path(store)
        if not store_path.exists():
            print(f"Skipping missing store directory: {store}")
            continue

        print(f"Processing store: {store}")
        for path in sorted(store_path.rglob("*.json")):
            total_rows += load_file_to_bigtable(table, str(path), store)

    print(f"Successfully loaded {total_rows} records into Bigtable")


if __name__ == "__main__":
    load_all()
