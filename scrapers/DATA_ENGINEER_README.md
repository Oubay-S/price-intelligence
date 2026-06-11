# 🏗️ Data Engineering — Price Intelligence Platform

This document covers the complete data engineering work done on the Price Intelligence Platform:
architecture decisions, pipeline design, tooling, infrastructure, and how all layers connect.

---

## 📐 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                                │
│        Jumia (MA)      Sport Direct (UK)      eBay (Global)         │
└────────────┬────────────────┬────────────────────┬──────────────────┘
             │  Selenium      │  Selenium          │  Selenium + xvfb
             ▼                ▼                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     SCRAPERS  (Python + Selenium)                   │
│  scrapers/jumia/    scrapers/sport-direct/    scrapers/ebay/        │
│  Raw JSON output per category (football, gym, basketball…)          │
└────────────────────────────┬────────────────────────────────────────┘
                             │ Airflow stages JSON → nifi_inbox/
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     APACHE NIFI  (Real-time ingestion)              │
│  Reads from nifi_inbox/ → calls nifi_to_bigtable.py                 │
│  Streams each product record into Google Cloud Bigtable             │
└────────────────────────────┬────────────────────────────────────────┘
                             │ Bigtable row writes
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│              GOOGLE CLOUD BIGTABLE  (Hot storage)                   │
│  Project : price-intelligence-495411                                │
│  Instance: price-intelligence                                       │
│  Table   : products  /  Column family: info                         │
│  Row key : {source}#{category}#{name_slug}#{uuid}                   │
│  Stores historical price versions (MaxVersions = 100)               │
└────────────────────────────┬────────────────────────────────────────┘
                             │ bigtable_to_bigquery.py (via Airflow)
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│           GOOGLE BIGQUERY  (Analytical storage)                     │
│  Dataset : price_intelligence                                       │
│  Table   : products  (append-only, deduped by _bigtable_row_key)    │
│  Cleaned by: bigquery_product_cleanup.py                            │
│              cleanup_irrelevant_bigquery_products.py                │
│              backfill_unknown_categories.py                         │
└────────────────────────────┬────────────────────────────────────────┘
                             │ dbt run
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     DBT  (SQL Transformations)                      │
│  stg_prices        → Cleaned & typed staging model                  │
│  int_price_daily   → Daily price aggregation (intermediate)         │
│  mart_price_trends → Final mart for the frontend & BI               │
└────────────────────────────┬────────────────────────────────────────┘
                             │ Notebooks + EDA scripts
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│              DATA ANALYSIS  (EDA & Exports)                         │
│  01_data_understanding.ipynb   02_data_cleaning.ipynb               │
│  03_exploratory_analysis.ipynb 04_statistical_tests.ipynb           │
│  05_final_insights.ipynb                                            │
│  → Results uploaded back to BigQuery via upload_analysis_to_bigquery│
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Airflow DAG — `price_intelligence_pipeline`

**Schedule:** Daily at 13:00 UTC  
**File:** [`airflow/dags/price_intelligence_dag.py`](airflow/dags/price_intelligence_dag.py)

The full pipeline is orchestrated as a single DAG with the following task graph:

```
[scrape_jumia]     ──┐
[scrape_sport_direct]─┤──► [ensure_nifi_available]
[scrape_ebay]      ──┘         │
                               ▼
                    [stage_scraped_json_for_nifi]
                               │
                               ▼
                    [wait_for_bigtable_stability]
                               │
                               ▼
                      [export_to_bigquery]
                               │
                               ▼
                  [remove_irrelevant_product_rows]
                               │
                               ▼
                  [remove_unknown_category_rows]
                          /         \
                         ▼           ▼
                    [dbt_run]   [run_data_analysis_eda]
                                      │
                                      ▼
                         [upload_analysis_to_bigquery]
```

### Key DAG Tasks

| Task | What it does |
|---|---|
| `scrape_jumia` | Runs `jumia/run_jumia_scraping.py` via Selenium |
| `scrape_sport_direct` | Runs `sport-direct/run_sport_direct_scraping.py` |
| `scrape_ebay` | Runs `ebay/run_ebay_scraping.py` under `xvfb-run` (headless display) |
| `ensure_nifi_available` | Waits up to 5 min for NiFi TCP connectivity before staging |
| `stage_scraped_json_for_nifi` | Validates JSON schemas, filters irrelevant products, enriches records with `_ingestion_run_id` + `_staged_at`, copies to `nifi_inbox/` |
| `wait_for_bigtable_stability` | Polls Bigtable until the ingested row count matches staged records (3 consecutive stable checks) |
| `export_to_bigquery` | Reads Bigtable → deduplicates by `_bigtable_row_key` → appends new rows to BigQuery |
| `remove_irrelevant_product_rows` | Runs `bigquery_product_cleanup.py` against BigQuery to remove junk rows |
| `remove_unknown_category_rows` | Deletes rows with null/unknown categories for the current ingestion run |
| `dbt_run` | Runs `dbt deps && dbt run && dbt test` inside the Airflow container |
| `run_data_analysis_eda` | Executes notebooks 01–03 via `run_eda_pipeline.py` using `nbconvert` |
| `upload_analysis_to_bigquery` | Uploads EDA outputs back to BigQuery |

---

## 🕷️ Scrapers

**Location:** `scrapers/jumia/`, `scrapers/sport-direct/`, `scrapers/ebay/`

All scrapers are built with **Python + Selenium** (no Scrapy). Each scraper:
- Uses a headless Chrome browser controlled by `webdriver-manager` (auto-downloads the right ChromeDriver)
- Scrapes sports products across categories: `football`, `gym`, `basketball`, `volleyball`, `combat-sports`, `Racket-Sports`
- Outputs raw JSON files per category into the store folder
- Data is then validated and staged by Airflow before being passed to NiFi

### Product Schema (fields captured)

| Field | Description |
|---|---|
| `name` | Product name |
| `current_price` | Current listed price |
| `price_before_discount` | Original price (if discounted) |
| `discount` | Discount percentage or value |
| `stars` | Rating |
| `availability` | In stock / Out of stock |
| `product_url` | Direct product link |
| `image_url` | Product image URL |
| `features` | Product description / features |
| `sizes` | Available sizes |
| `scraped_at` | ISO timestamp of scraping |
| `source` / `store` | Store identifier (jumia, sport-direct, ebay) |
| `category` | Product category |

---

## 🌊 NiFi — Real-Time Ingestion

**Container:** `nifi` (custom Docker image in `nifi/Dockerfile`)  
**Script:** [`scrapers/nifi_to_bigtable.py`](scrapers/nifi_to_bigtable.py)

NiFi watches the `nifi_inbox/` directory for JSON files staged by Airflow.
For each file it calls `nifi_to_bigtable.py` which:
1. Reads each product record from the JSON
2. Constructs a deterministic row key: `{source}#{category}#{slug}#{uuid}`
3. Writes all fields into the `info` column family in Bigtable
4. Adds ingestion metadata: `_ingestion_run_id`, `_staged_at`, `ingestion_method`

Credentials are mounted at `/opt/nifi/gcp-credentials.json` and set via `GOOGLE_APPLICATION_CREDENTIALS`.

---

## 🗄️ Google Cloud Bigtable

**Project:** `price-intelligence-495411`  
**Instance:** `price-intelligence`  
**Table:** `products`  
**Column Family:** `info` (MaxVersions = 100 → stores full price history per product)

### Why Bigtable?
- **Time-series price history**: MaxVersions=100 allows tracking up to 100 price changes per product
- **High write throughput**: handles concurrent writes from NiFi without bottlenecks
- **Low-latency reads**: the backend can query the latest price instantly

### Row Key Design
```
{source}#{category}#{name-slug}#{uuid4}
```
Example: `jumia#gym#optimum-nutrition-whey-3a4f`

This ensures:
- Rows are grouped by store and category (prefix scan efficiency)
- Product names are human-readable in the key
- UUID suffix prevents collisions on name clashes

---

## 📊 Google BigQuery

**Project:** `price-intelligence-495411`  
**Dataset:** `price_intelligence`  
**Table:** `products`

### Export Logic (`bigtable_to_bigquery.py`)
1. Reads all rows from Bigtable (optionally filtered by `EXPORT_INGESTION_RUN_ID`)
2. Deduplicates against existing BigQuery rows using `_bigtable_row_key`
3. Filters irrelevant products via `product_quality.is_relevant_product()`
4. Validates required fields (`name`, `current_price`, `scraped_at`)
5. Appends new rows with `_loaded_at` and `_export_run_id` metadata

### BigQuery Schema

| Column | Type | Description |
|---|---|---|
| `name` | STRING | Product name |
| `current_price` | STRING | Price at scrape time |
| `price_before_discount` | STRING | Original price |
| `discount` | STRING | Discount value |
| `stars` | STRING | Rating |
| `availability` | STRING | Stock status |
| `product_url` | STRING | Product page URL |
| `image_url` | STRING | Product image |
| `features` | STRING | Description |
| `sizes` | STRING | Available sizes |
| `scraped_at` | STRING | When scraped |
| `source` | STRING | Store name |
| `store` | STRING | Store name (alias) |
| `category` | STRING | Product category |
| `_bigtable_row_key` | STRING | Dedup key from Bigtable |
| `_ingestion_run_id` | STRING | Tracks which pipeline run |
| `_staged_at` | TIMESTAMP | When staged by Airflow |
| `ingested_at` | TIMESTAMP | When written to Bigtable |
| `ingestion_method` | STRING | e.g. `nifi` |
| `_loaded_at` | TIMESTAMP | When exported to BigQuery |
| `_export_run_id` | STRING | UUID of the export job |

---

## 🔧 dbt Transformations

**Location:** `dbt/`  
**Target:** BigQuery (`price-intelligence-495411.price_intelligence`)

### Model Lineage

```
products (BigQuery raw table)
    └── stg_prices          [staging]     → type casting, field normalization
            └── int_price_daily    [intermediate] → daily price aggregation per product
                    └── mart_price_trends  [mart]  → final model for frontend & BI dashboards
```

| Model | Layer | Description |
|---|---|---|
| `stg_prices` | Staging | Cleans and types the raw `products` table. Casts prices to FLOAT, normalizes timestamps, standardizes store names |
| `int_price_daily` | Intermediate | Aggregates prices to daily granularity per product (min, max, avg price per day) |
| `mart_price_trends` | Mart | Final analytical table consumed by the FastAPI backend for price trend charts and analytics endpoints |

---

## 🧹 Data Quality

### Pre-ingestion (Airflow `stage_scraped_json_for_nifi`)
- Validates JSON schema: every record must have `name`, `current_price`, `scraped_at`
- Validates `current_price` is a parseable number
- Validates `scraped_at` is a valid ISO timestamp
- Filters irrelevant products using `product_quality.py` rules (see below)

### Product Quality Rules (`scrapers/product_quality.py`)
A pure-Python filtering library (no external dependencies) with:
- **`ALWAYS_EXCLUDED_PRODUCT_PATTERNS`** — products excluded regardless of store (e.g. dental mouthguard cases)
- **`JUMIA_EXCLUDED_PRODUCT_PATTERNS`** — Jumia-specific junk (VR headsets, toothpaste, garden tools, etc. mistakenly scraped)
- **`SPORT_DIRECT_EXCLUDED_PRODUCT_PATTERNS`** — Sport Direct-specific junk (laptop sleeves, women's clothing appearing in wrong categories)
- **Smart mouthguard filtering** — mouthguards are KEPT if in combat-sports context (boxing/MMA), EXCLUDED if in dental/sleep context

### Post-export BigQuery cleanup
- `bigquery_product_cleanup.py` — removes products that slipped through pre-ingestion filters
- `cleanup_irrelevant_bigquery_products.py` — removes irrelevant products by category/keyword matching directly in BigQuery
- `backfill_unknown_categories.py` — re-classifies products with `null` or `unknown` category using name-based heuristics

---

## 🚀 Running the Stack

```bash
# Start all services
sudo docker compose up -d --remove-orphans

# Check services are healthy
sudo docker compose ps

# View Airflow UI
open http://localhost:8080   # admin / admin123

# View NiFi UI
open https://localhost:8443  # admin / adminpassword123

# Trigger the pipeline manually (Airflow CLI)
sudo docker exec airflow-webserver airflow dags trigger price_intelligence_pipeline

# Run dbt manually
sudo docker compose run --rm dbt dbt run
sudo docker compose run --rm dbt dbt test

# Bulk load historical data into Bigtable
sudo docker exec airflow-scheduler python /app/load_all_to_bigtable.py
```
