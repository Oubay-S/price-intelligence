from airflow import DAG
# pyrefly: ignore [missing-import]
from airflow.operators.python import PythonOperator
from airflow.utils.trigger_rule import TriggerRule
from datetime import datetime, timedelta
import json
import os
import re
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import uuid

default_args = {
    'owner': 'data_engineer',
    'depends_on_past': False,
    'start_date': datetime(2024, 5, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def run_scraper(script_name, cwd):
    print(f"Starting scraper: {script_name} in {cwd}")
    process = subprocess.Popen(
        ["python", "-u", script_name],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    for line in process.stdout:
        print(line, end='')
    process.wait()
    if process.returncode != 0:
        raise Exception(f"Scraper {script_name} failed with exit code {process.returncode}")
    print(f"Finished scraper: {script_name}")

def run_scraper_command(command, cwd):
    print(f"Starting command: {' '.join(command)} in {cwd}")
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    for line in process.stdout:
        print(line, end='')
    process.wait()
    if process.returncode != 0:
        raise Exception(f"Command {' '.join(command)} failed with exit code {process.returncode}")
    print(f"Finished command: {' '.join(command)}")

def ensure_nifi_available():
    host = os.environ.get("NIFI_HOST", "nifi")
    port = int(os.environ.get("NIFI_PORT", "8443"))
    timeout = int(os.environ.get("NIFI_WAIT_SECONDS", "300"))
    deadline = time.time() + timeout

    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=5):
                print(f"NiFi is reachable at {host}:{port}")
                return
        except OSError as exc:
            print(f"Waiting for NiFi at {host}:{port}: {exc}")
            time.sleep(10)

    raise Exception(f"NiFi was not reachable at {host}:{port} after {timeout} seconds")


REQUIRED_PRODUCT_FIELDS = ("name", "current_price", "scraped_at")


def _ensure_product_quality_path(source_root):
    candidates = [
        Path(source_root),
        Path(__file__).resolve().parents[2] / "scrapers",
    ]
    for candidate in candidates:
        if (candidate / "product_quality.py").exists():
            candidate_text = str(candidate)
            if candidate_text not in sys.path:
                sys.path.insert(0, candidate_text)
            return
    raise RuntimeError(f"product_quality.py not found in: {candidates}")


def _is_relevant_scraper_record(record, store, category, source_root):
    _ensure_product_quality_path(source_root)
    from product_quality import is_relevant_product

    return is_relevant_product(record, store=store, category=category)


def _parse_price(value):
    if value is None:
        return None
    match = re.search(r"\d+(?:\.\d+)?", str(value))
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _parse_scraped_at(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def validate_scraper_json_file(json_path):
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{json_path}: invalid JSON: {exc}") from exc

    if not isinstance(data, list):
        raise ValueError(f"{json_path}: expected a JSON array of product records")

    errors = []
    for index, record in enumerate(data, start=1):
        if not isinstance(record, dict):
            errors.append(f"record {index}: expected object, got {type(record).__name__}")
            continue

        missing = [field for field in REQUIRED_PRODUCT_FIELDS if record.get(field) in (None, "")]
        if missing:
            errors.append(f"record {index}: missing required fields {missing}")
            continue

        if _parse_price(record.get("current_price")) is None:
            errors.append(f"record {index}: invalid current_price={record.get('current_price')!r}")

        if _parse_scraped_at(record.get("scraped_at")) is None:
            errors.append(f"record {index}: invalid scraped_at={record.get('scraped_at')!r}")

    if errors:
        preview = "; ".join(errors[:5])
        extra = f"; and {len(errors) - 5} more" if len(errors) > 5 else ""
        raise ValueError(f"{json_path}: schema contract failed: {preview}{extra}")

    return data


def stage_scraped_json_for_nifi():
    source_root = Path(os.environ.get("SCRAPER_OUTPUT_ROOT", "/app"))
    inbox = Path(os.environ.get("NIFI_INBOX", "/app/nifi_inbox"))
    stores = ["jumia", "sport-direct", "ebay"]
    utc_now = datetime.utcnow().replace(microsecond=0)
    ingestion_run_id = os.environ.get("INGESTION_RUN_ID") or (
        f"airflow-{utc_now.strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}"
    )
    staged_at = f"{utc_now.isoformat()}Z"

    if inbox.exists():
        shutil.rmtree(inbox)
    inbox.mkdir(parents=True, exist_ok=True)

    files_staged = 0
    records_expected = 0
    store_counts = {}
    for store in stores:
        store_dir = source_root / store
        if not store_dir.exists():
            print(f"No scraper output directory for {store}: {store_dir}")
            continue

        for json_path in sorted(store_dir.rglob("*.json")):
            path_parts = {part.lower() for part in json_path.relative_to(store_dir).parts}
            if "_metadata" in path_parts:
                print(f"Skipping browser metadata file: {json_path}")
                continue

            name = json_path.name.lower()
            if name == "manifest.json" or name.endswith("_cookies.json"):
                print(f"Skipping scraper metadata file: {json_path}")
                continue

            data = validate_scraper_json_file(json_path)
            if not data:
                print(f"Skipping empty scraper data file: {json_path}")
                continue

            category = json_path.parent.name
            relevant_data = [
                record for record in data
                if _is_relevant_scraper_record(record, store, category, source_root)
            ]
            skipped_irrelevant = len(data) - len(relevant_data)
            if skipped_irrelevant:
                print(f"Skipping {skipped_irrelevant} irrelevant products from {json_path}")
            if not relevant_data:
                print(f"Skipping scraper data file with no relevant products: {json_path}")
                continue

            relative_path = json_path.relative_to(source_root)
            target_path = inbox / relative_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            enriched_data = [
                {
                    **record,
                    "source": record.get("source") or record.get("store") or store,
                    "store": record.get("store") or record.get("source") or store,
                    "category": record.get("category") or category,
                    "_ingestion_run_id": ingestion_run_id,
                    "_staged_at": staged_at,
                }
                for record in relevant_data
            ]
            target_path.write_text(json.dumps(enriched_data, ensure_ascii=False), encoding="utf-8")
            files_staged += 1
            records_expected += len(relevant_data)
            store_counts.setdefault(store, {"files": 0, "records": 0})
            store_counts[store]["files"] += 1
            store_counts[store]["records"] += len(relevant_data)

    if files_staged == 0:
        raise Exception(f"No scraper JSON files were staged for NiFi from {source_root}")

    for store, counts in sorted(store_counts.items()):
        print(f"Staged {store}: {counts['files']} files, {counts['records']} records")
    print(f"Staged total: {files_staged} JSON files for NiFi in {inbox}; expected records: {records_expected}")
    print(f"Ingestion run id: {ingestion_run_id}")
    return {"expected_records": records_expected, "ingestion_run_id": ingestion_run_id}

def wait_for_bigtable_stability(**context):
    from google.cloud import bigtable
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "price-intel-local")
    instance_id = os.environ.get("BIGTABLE_INSTANCE_ID", "price-intel-instance")
    client = bigtable.Client(project=project, admin=True)
    instance = client.instance(instance_id)
    table = instance.table("products")
    stage_result = context["ti"].xcom_pull(task_ids="stage_scraped_json_for_nifi") or {}
    if isinstance(stage_result, dict):
        expected_records = stage_result.get("expected_records") or 1
        ingestion_run_id = stage_result.get("ingestion_run_id")
    else:
        expected_records = stage_result or 1
        ingestion_run_id = None
    print(f"Waiting for NiFi to ingest {expected_records} records into Bigtable")
    if ingestion_run_id:
        print(f"Tracking ingestion run id: {ingestion_run_id}")

    def count_rows_for_run(limit):
        count = 0
        for row in table.read_rows():
            if ingestion_run_id:
                cells = row.cells.get("info", {}).get(b"_ingestion_run_id", [])
                if not cells or cells[0].value.decode("utf-8") != ingestion_run_id:
                    continue
            count += 1
            if count >= limit:
                return count
        return count

    max_checks = int(os.environ.get("BIGTABLE_STABILITY_CHECKS", "120"))
    check_interval = int(os.environ.get("BIGTABLE_STABILITY_INTERVAL_SECONDS", "15"))
    stable_count = -1
    stable_checks = 0
    print(f"Checking Bigtable up to {max_checks} times every {check_interval} seconds")
    for attempt in range(max_checks):
        current = count_rows_for_run(expected_records)
        if current == stable_count:
            stable_checks += 1
            if stable_checks >= 3 and current >= expected_records:
                print(f"Bigtable stable at {current} rows after {attempt} checks")
                print(f"Bigtable ingestion delta vs staged records: {current - expected_records}")
                return current
        else:
            stable_count = current
            stable_checks = 0
        print(f"Bigtable rows: {current}/{expected_records} (stable checks: {stable_checks}/3)")
        time.sleep(check_interval)
    raise Exception(
        f"Bigtable did not stabilize after {max_checks} checks. "
        f"Last count: {stable_count}/{expected_records}"
    )

def run_export_to_bigquery(**context):
    script = "/app/bigtable_to_bigquery.py"
    if not os.path.exists(script):
        raise Exception(f"Export script not found: {script}")
    env = os.environ.copy()
    stage_result = context["ti"].xcom_pull(task_ids="stage_scraped_json_for_nifi") or {}
    if isinstance(stage_result, dict) and stage_result.get("ingestion_run_id"):
        env["EXPORT_INGESTION_RUN_ID"] = stage_result["ingestion_run_id"]
        print(f"Exporting Bigtable rows for ingestion_run_id={stage_result['ingestion_run_id']}")
    result = subprocess.run(["python", "-u", script], env=env, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise Exception(f"Bigquery export failed with code {result.returncode}")



def remove_irrelevant_product_rows(**context):
    project = os.environ.get("BQ_PROJECT", "price-intelligence-495411")
    dataset = os.environ.get("BQ_DATASET", "price_intelligence")
    table = os.environ.get("BQ_TABLE", "products")
    table_id = f"{project}.{dataset}.{table}"
    client = _get_bigquery_client()

    _ensure_product_quality_path(os.environ.get("SCRAPER_OUTPUT_ROOT", "/app"))
    from bigquery_product_cleanup import cleanup_irrelevant_product_rows

    return cleanup_irrelevant_product_rows(client, table_id)

def remove_unknown_category_rows(**context):
    from google.cloud import bigquery

    stage_result = context["ti"].xcom_pull(task_ids="stage_scraped_json_for_nifi") or {}
    ingestion_run_id = stage_result.get("ingestion_run_id") if isinstance(stage_result, dict) else None
    if not ingestion_run_id:
        print("No ingestion_run_id found; skipping unknown-category cleanup")
        return 0

    project = os.environ.get("BQ_PROJECT", "price-intelligence-495411")
    dataset = os.environ.get("BQ_DATASET", "price_intelligence")
    table = os.environ.get("BQ_TABLE", "products")
    table_id = f"{project}.{dataset}.{table}"
    temp_table_id = f"{project}.{dataset}._products_without_unknown_categories_{uuid.uuid4().hex[:12]}"
    client = _get_bigquery_client()

    unknown_filter = "category is null or trim(category) = '' or lower(trim(category)) = 'unknown'"
    count_query = f"""
        select count(*) as row_count
        from `{table_id}`
        where _ingestion_run_id = @ingestion_run_id
          and ({unknown_filter})
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("ingestion_run_id", "STRING", ingestion_run_id),
        ]
    )
    unknown_count = next(client.query(count_query, job_config=job_config).result()).row_count
    print(f"Unknown-category rows in ingestion_run_id={ingestion_run_id}: {unknown_count}")
    if unknown_count == 0:
        print("No unknown-category rows to remove")
        return 0

    rewrite_query = f"""
        select *
        from `{table_id}`
        where not (
            _ingestion_run_id = @ingestion_run_id
            and ({unknown_filter})
        )
    """
    rewrite_config = bigquery.QueryJobConfig(
        destination=temp_table_id,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        query_parameters=[
            bigquery.ScalarQueryParameter("ingestion_run_id", "STRING", ingestion_run_id),
        ],
    )
    client.query(rewrite_query, job_config=rewrite_config).result()
    print(f"Created cleaned replacement table: {temp_table_id}")

    copy_config = bigquery.CopyJobConfig(write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE)
    client.copy_table(temp_table_id, table_id, job_config=copy_config).result()
    client.delete_table(temp_table_id, not_found_ok=True)
    print(f"Removed {unknown_count} unknown-category rows from {table_id}")
    return unknown_count


def _get_bigquery_client():
    from google.cloud import bigquery
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "/opt/airflow/gcp-credentials.json")
    if os.path.exists(creds_path):
        return bigquery.Client.from_service_account_json(creds_path)
    return bigquery.Client(project=os.environ.get("BQ_PROJECT", "price-intelligence-495411"))


def _log_dbt_model_counts():
    project = os.environ.get("BQ_PROJECT", "price-intelligence-495411")
    dataset = os.environ.get("BQ_DATASET", "price_intelligence")
    models = ["stg_prices", "mart_price_trends"]
    client = _get_bigquery_client()

    print("dbt model row counts:")
    for model in models:
        table_id = f"{project}.{dataset}.{model}"
        query = f"select count(*) as row_count from `{table_id}`"
        row_count = next(client.query(query).result()).row_count
        print(f"- {table_id}: {row_count} rows")


def run_data_analysis_eda():
    analysis_dir = Path(os.environ.get("DATA_ANALYSIS_DIR", "/opt/airflow/data-analysis"))
    script = analysis_dir / "run_eda_pipeline.py"

    if not script.exists():
        raise Exception(f"Data analysis pipeline not found: {script}")

    env = os.environ.copy()
    env.setdefault("GOOGLE_APPLICATION_CREDENTIALS", "/opt/airflow/gcp-credentials.json")
    notebooks_dir = analysis_dir / "notebooks"
    eda_notebooks = [
        notebooks_dir / "01_data_understanding.ipynb",
        notebooks_dir / "02_data_cleaning.ipynb",
        notebooks_dir / "03_exploratory_analysis.ipynb",
    ]
    missing_notebooks = [path.name for path in eda_notebooks if not path.exists()]
    scope = "eda" if not missing_notebooks else "export-only"
    if missing_notebooks:
        print(
            f"Missing notebooks under {notebooks_dir}: {', '.join(missing_notebooks)}; "
            f"running data-analysis in scope={scope}"
        )

    result = subprocess.run(
        ["python", "-u", str(script), "--scope", scope, "--kernel", "python3"],
        cwd=str(analysis_dir),
        env=env,
        capture_output=True,
        text=True,
    )

    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise Exception(f"Data analysis EDA pipeline failed with code {result.returncode}")


def upload_analysis_to_bigquery():
    analysis_dir = Path(os.environ.get("DATA_ANALYSIS_DIR", "/opt/airflow/data-analysis"))
    script = analysis_dir / "upload_analysis_to_bigquery.py"

    if not script.exists():
        raise Exception(f"Data analysis BigQuery upload script not found: {script}")

    env = os.environ.copy()
    env.setdefault("GOOGLE_APPLICATION_CREDENTIALS", "/opt/airflow/gcp-credentials.json")

    command = [
        "python",
        "-u",
        str(script),
        "--project",
        os.environ.get("BQ_PROJECT", "price-intelligence-495411"),
        "--dataset",
        os.environ.get("BQ_DATASET", "price_intelligence"),
        "--write-disposition",
        os.environ.get("ANALYSIS_BQ_WRITE_DISPOSITION", "WRITE_TRUNCATE"),
    ]

    location = os.environ.get("BQ_LOCATION")
    if location:
        command.extend(["--location", location])

    result = subprocess.run(
        command,
        cwd=str(analysis_dir),
        env=env,
        capture_output=True,
        text=True,
    )

    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise Exception(f"Data analysis BigQuery upload failed with code {result.returncode}")


def run_dbt():
    dbt_bin = shutil.which("dbt")
    if not dbt_bin:
        raise Exception("dbt executable not found in the Airflow image")

    candidates = ["/usr/app/dbt", "/opt/airflow/dbt", "/app/dbt", "/dbt"]
    dbt_dir = next((path for path in candidates if os.path.exists(os.path.join(path, "dbt_project.yml"))), None)
    if not dbt_dir:
        raise Exception(f"dbt project not found in any known path: {candidates}")

    dbt_log_path = "/tmp/dbt_logs"
    dbt_target_path = "/tmp/dbt_target"
    os.makedirs(dbt_log_path, exist_ok=True)
    os.makedirs(dbt_target_path, exist_ok=True)
    dbt_env = os.environ.copy()
    dbt_env["DBT_LOG_PATH"] = dbt_log_path
    dbt_env["DBT_TARGET_PATH"] = dbt_target_path

    print(f"Running dbt in {dbt_dir}")
    for command in ([dbt_bin, "deps"], [dbt_bin, "run"], [dbt_bin, "test"]):
        result = subprocess.run(command, cwd=dbt_dir, env=dbt_env, capture_output=True, text=True)
        print(result.stdout)
        if result.returncode != 0:
            print(result.stderr)
            raise Exception(f"{' '.join(command)} failed with code {result.returncode}")

    _log_dbt_model_counts()

with DAG(
    'price_intelligence_pipeline',
    default_args=default_args,
    description='Scrape e-commerce data, ingest through NiFi, export to BigQuery, transform with dbt',
    schedule_interval='0 13 * * *',
    catchup=False
) as dag:

    task_jumia = PythonOperator(
        task_id='scrape_jumia',
        python_callable=run_scraper,
        op_kwargs={'script_name': 'jumia/run_jumia_scraping.py', 'cwd': '/app'}
    )

    task_sport_direct = PythonOperator(
        task_id='scrape_sport_direct',
        python_callable=run_scraper_command,
        op_kwargs={
            'command': ['python', '-u', 'sport-direct/run_sport_direct_scraping.py'],
            'cwd': '/app',
        }
    )

    task_ebay = PythonOperator(
        task_id='scrape_ebay',
        python_callable=run_scraper_command,
        op_kwargs={
            'command': ['xvfb-run', '-a', 'python', '-u', 'ebay/run_ebay_scraping.py'],
            'cwd': '/app',
        }
    )

    task_check_nifi = PythonOperator(
        task_id='ensure_nifi_available',
        python_callable=ensure_nifi_available,
        trigger_rule=TriggerRule.ALL_DONE,
    )

    task_stage_nifi = PythonOperator(
        task_id='stage_scraped_json_for_nifi',
        python_callable=stage_scraped_json_for_nifi,
    )

    task_wait_bigtable = PythonOperator(
        task_id='wait_for_bigtable_stability',
        python_callable=wait_for_bigtable_stability,
    )

    task_export_bq = PythonOperator(
        task_id='export_to_bigquery',
        python_callable=run_export_to_bigquery,
    )

    task_remove_irrelevant_products = PythonOperator(
        task_id='remove_irrelevant_product_rows',
        python_callable=remove_irrelevant_product_rows,
    )

    task_remove_unknown_categories = PythonOperator(
        task_id='remove_unknown_category_rows',
        python_callable=remove_unknown_category_rows,
    )

    task_dbt_run = PythonOperator(
        task_id='dbt_run',
        python_callable=run_dbt,
    )

    task_data_analysis_eda = PythonOperator(
        task_id='run_data_analysis_eda',
        python_callable=run_data_analysis_eda,
    )

    task_upload_analysis_bq = PythonOperator(
        task_id='upload_analysis_to_bigquery',
        python_callable=upload_analysis_to_bigquery,
    )

    [task_jumia, task_sport_direct, task_ebay] >> task_check_nifi >> task_stage_nifi >> task_wait_bigtable >> task_export_bq >> task_remove_irrelevant_products >> task_remove_unknown_categories
    task_remove_unknown_categories >> [task_dbt_run, task_data_analysis_eda]
    task_data_analysis_eda >> task_upload_analysis_bq
