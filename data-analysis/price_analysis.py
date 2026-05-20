from __future__ import annotations

import argparse
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

DEFAULT_PROJECT_ROOT = Path(r"C:\Users\Admin\Desktop\price-intelligence")
DEFAULT_BQ_TABLE = "price-intelligence-495411.price_intelligence.products"
DEFAULT_RAW_DATA_DIR = Path(r"C:\Users\Admin\Desktop\data-analysis\outputs\raw_data")
DEFAULT_RAW_EXPORT = DEFAULT_RAW_DATA_DIR / "bigquery_products_export.csv"


def clean_number(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"none", "null", "n/a", "nan"}:
        return None
    match = re.search(r"-?\d+(?:[.,]\d+)?", text.replace(" ", ""))
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", "."))
    except ValueError:
        return None


def resolve_project_root(project_root: str | None) -> Path:
    if project_root:
        return Path(project_root).expanduser().resolve()
    return DEFAULT_PROJECT_ROOT


def infer_store_and_category(file_path: Path, scrapers_dir: Path) -> tuple[str, str]:
    rel = file_path.relative_to(scrapers_dir).parts
    store = rel[0] if len(rel) > 0 else "unknown"
    category = rel[1] if len(rel) > 1 else "unknown"
    return store, category


def load_from_local_json(project_root: Path) -> list[dict[str, Any]]:
    scrapers_dir = project_root / "scrapers"
    if not scrapers_dir.is_dir():
        raise SystemExit(f"Scrapers directory not found: {scrapers_dir}")

    rows: list[dict[str, Any]] = []
    for file_path in scrapers_dir.rglob("*.json"):
        store, category = infer_store_and_category(file_path, scrapers_dir)
        try:
            items = json.loads(file_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"Skipped {file_path}: {exc}")
            continue

        if not isinstance(items, list):
            continue

        for item in items:
            if not isinstance(item, dict):
                continue
            record = dict(item)
            record.setdefault("store", store)
            record.setdefault("category", category)
            rows.append(record)
    return rows


def load_from_bigquery(table_id: str, cache_path: Path | None = DEFAULT_RAW_EXPORT) -> list[dict[str, Any]]:
    """Load the official product table from BigQuery.

    The query uses SELECT * because the schema can evolve after team merges.
    A CSV snapshot is saved locally so notebooks can be rerun/reviewed later.
    """
    try:
        from google.cloud import bigquery
    except ImportError as exc:
        raise SystemExit(
            "google-cloud-bigquery is not installed. Run: pip install -r requirements.txt"
        ) from exc

    client = bigquery.Client(project=table_id.split(".")[0])
    query = f"SELECT * FROM `{table_id}`"
    dataframe = client.query(query).to_dataframe()

    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        dataframe.to_csv(cache_path, index=False, encoding="utf-8-sig")

    return dataframe.where(dataframe.notna(), None).to_dict("records")


def load_from_bigquery_export(export_path: Path = DEFAULT_RAW_EXPORT) -> list[dict[str, Any]]:
    """Load a CSV export/snapshot of the BigQuery products table."""
    if not export_path.exists():
        raise FileNotFoundError(
            f"BigQuery export not found: {export_path}. "
            "Run with BigQuery credentials or export products from BigQuery to this CSV path."
        )
    import pandas as pd

    dataframe = pd.read_csv(export_path)
    return dataframe.where(dataframe.notna(), None).to_dict("records")


def load_project_rows(
    source: str = "bigquery",
    table_id: str = DEFAULT_BQ_TABLE,
    project_root: Path | None = None,
    export_path: Path = DEFAULT_RAW_EXPORT,
    allow_export_fallback: bool = False,
    allow_local_fallback: bool = False,
) -> tuple[list[dict[str, Any]], str]:
    """Load project rows with BigQuery as the official source.

    Priority for source="bigquery":
    1. live BigQuery query,
    2. cached/exported BigQuery CSV only if allow_export_fallback=True,
    3. local scraper JSON fallback only if allow_local_fallback=True.

    For the official analyst notebooks, fallbacks stay disabled so stale data
    cannot be used silently after a team merge or BigQuery refresh.
    """
    if source == "local":
        return load_from_local_json(project_root or DEFAULT_PROJECT_ROOT), "local_json"

    try:
        return load_from_bigquery(table_id, cache_path=export_path), "bigquery_live"
    except Exception as exc:
        if allow_export_fallback and export_path.exists():
            print(f"BigQuery live access unavailable: {exc}")
            print(f"Using cached/exported BigQuery snapshot: {export_path}")
            return load_from_bigquery_export(export_path), "bigquery_export"
        if allow_local_fallback:
            print(f"BigQuery unavailable and no export found: {exc}")
            print("WARNING: falling back to local scraper JSON. Use this only for offline development.")
            return load_from_local_json(project_root or DEFAULT_PROJECT_ROOT), "local_json_fallback"
        raise

def normalize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for row in rows:
        price = clean_number(row.get("current_price"))
        if price is None or price <= 0:
            continue

        cleaned.append(
            {
                "store": str(row.get("store") or row.get("source") or "unknown").lower(),
                "category": str(row.get("category") or "unknown").lower(),
                "name": str(row.get("name") or "").strip(),
                "price": price,
                "price_before_discount": clean_number(row.get("price_before_discount")),
                "discount": clean_number(row.get("discount")),
                "stars": clean_number(row.get("stars")),
                "availability": str(row.get("availability") or "").strip(),
                "scraped_at": str(row.get("scraped_at") or "").strip(),
            }
        )
    return cleaned


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else math.nan


def summarize_group(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    groups: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        groups[str(row[key])].append(float(row["price"]))

    summary = []
    for name, prices in groups.items():
        summary.append(
            {
                key: name,
                "products": len(prices),
                "avg_price": mean(prices),
                "median_price": statistics.median(prices),
                "min_price": min(prices),
                "max_price": max(prices),
                "std_price": statistics.stdev(prices) if len(prices) > 1 else 0.0,
            }
        )
    return sorted(summary, key=lambda item: item["avg_price"])


def format_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def print_table(rows: list[dict[str, Any]], columns: list[str], limit: int | None = None) -> None:
    rows = rows[:limit] if limit else rows
    widths = {
        col: max(len(col), *(len(format_value(row.get(col))) for row in rows)) if rows else len(col)
        for col in columns
    }
    print(" | ".join(col.upper().ljust(widths[col]) for col in columns))
    print("-+-".join("-" * widths[col] for col in columns))
    for row in rows:
        print(" | ".join(format_value(row.get(col)).ljust(widths[col]) for col in columns))


def run_optional_anova(rows: list[dict[str, Any]]) -> None:
    groups: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        groups[row["store"]].append(row["price"])

    usable = [prices for prices in groups.values() if len(prices) >= 2]
    if len(usable) < 2:
        print("\nANOVA: not enough groups.")
        return

    try:
        from scipy import stats
    except ImportError:
        print("\nANOVA skipped: scipy is not installed yet.")
        return

    statistic, p_value = stats.f_oneway(*usable)
    print("\nInferential test: ANOVA price difference between stores")
    print(f"F-statistic: {statistic:.4f}")
    print(f"p-value:     {p_value:.6f}")


def print_report(rows: list[dict[str, Any]], raw_count: int) -> None:
    prices = [row["price"] for row in rows]
    print("\nPRICE INTELLIGENCE - DATA ANALYST REPORT")
    print("=" * 48)
    print(f"Raw records loaded:   {raw_count}")
    print(f"Valid price records:  {len(rows)}")
    print(f"Stores:               {', '.join(sorted({row['store'] for row in rows}))}")
    print(f"Categories:           {len({row['category'] for row in rows})}")

    print("\nGlobal price KPIs")
    print(f"Average price:        {mean(prices):.2f}")
    print(f"Median price:         {statistics.median(prices):.2f}")
    print(f"Min price:            {min(prices):.2f}")
    print(f"Max price:            {max(prices):.2f}")
    print(f"Std deviation:        {statistics.stdev(prices):.2f}")

    print("\nAverage price by store")
    print_table(summarize_group(rows, "store"), ["store", "products", "avg_price", "median_price", "min_price", "max_price", "std_price"])

    print("\nAverage price by category")
    print_table(summarize_group(rows, "category"), ["category", "products", "avg_price", "median_price", "min_price", "max_price", "std_price"])

    discounted = [row for row in rows if row["discount"] is not None]
    top_discounts = sorted(discounted, key=lambda row: row["discount"], reverse=True)[:10]
    if top_discounts:
        print("\nTop 10 discounts")
        print_table(top_discounts, ["store", "category", "discount", "price", "name"], limit=10)

    print("\nRecord counts")
    print(f"By store:    {dict(sorted(Counter(row['store'] for row in rows).items()))}")
    print(f"By category: {dict(sorted(Counter(row['category'] for row in rows).items()))}")
    run_optional_anova(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the first data analyst report.")
    parser.add_argument("--source", choices=["local", "bigquery"], default="bigquery")
    parser.add_argument("--bq-table", default=DEFAULT_BQ_TABLE)
    parser.add_argument("--project-root", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = resolve_project_root(args.project_root)
    raw_rows, effective_source = load_project_rows(args.source, args.bq_table, project_root)
    print(f"Data source used: {effective_source}")
    cleaned_rows = normalize_rows(raw_rows)
    if not cleaned_rows:
        raise SystemExit("No valid rows found. Check the data source and price column.")
    print_report(cleaned_rows, raw_count=len(raw_rows))


if __name__ == "__main__":
    main()
