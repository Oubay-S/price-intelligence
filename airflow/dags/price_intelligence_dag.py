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
import time

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
    stores = ["jumia", "walmart", "ebay"]

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
            if json_path.name.lower() == "manifest.json":
                print(f"Skipping scraper metadata file: {json_path}")
                continue

            data = validate_scraper_json_file(json_path)
            if not data:
                print(f"Skipping empty scraper data file: {json_path}")
                continue

            relative_path = json_path.relative_to(source_root)
            target_path = inbox / relative_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(json_path, target_path)
            files_staged += 1
            records_expected += len(data)
            store_counts.setdefault(store, {"files": 0, "records": 0})
            store_counts[store]["files"] += 1
            store_counts[store]["records"] += len(data)

    if files_staged == 0:
        raise Exception(f"No scraper JSON files were staged for NiFi from {source_root}")

    for store, counts in sorted(store_counts.items()):
        print(f"Staged {store}: {counts['files']} files, {counts['records']} records")
    print(f"Staged total: {files_staged} JSON files for NiFi in {inbox}; expected records: {records_expected}")
    return records_expected

def wait_for_bigtable_stability(**context):
    from google.cloud import bigtable
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "price-intel-local")
    instance_id = os.environ.get("BIGTABLE_INSTANCE_ID", "price-intel-instance")
    client = bigtable.Client(project=project, admin=True)
    instance = client.instance(instance_id)
    table = instance.table("products")
    expected_records = context["ti"].xcom_pull(task_ids="stage_scraped_json_for_nifi") or 1
    print(f"Waiting for NiFi to ingest at least {expected_records} records into Bigtable")

    def count_rows():
        return sum(1 for _ in table.read_rows())
    stable_count = -1
    stable_checks = 0
    for attempt in range(40):
        current = count_rows()
        if current == stable_count:
            stable_checks += 1
            if stable_checks >= 3 and current >= expected_records:
                print(f"Bigtable stable at {current} rows after {attempt} checks")
                print(f"Bigtable ingestion delta vs staged records: {current - expected_records}")
                return current
        else:
            stable_count = current
            stable_checks = 0
        print(f"Bigtable rows: {current} (stable checks: {stable_checks}/3)")
        time.sleep(15)
    raise Exception(f"Bigtable did not stabilize. Last count: {stable_count}")

def run_export_to_bigquery():
    script = "/app/bigtable_to_bigquery.py"
    if not os.path.exists(script):
        raise Exception(f"Export script not found: {script}")
    result = subprocess.run(["python", "-u", script], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise Exception(f"Bigquery export failed with code {result.returncode}")


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

    task_walmart = PythonOperator(
        task_id='scrape_walmart',
        python_callable=run_scraper,
        op_kwargs={'script_name': 'walmart/run_walmart_scraping.py', 'cwd': '/app'}
    )

    task_ebay = PythonOperator(
        task_id='scrape_ebay',
        python_callable=run_scraper,
        op_kwargs={'script_name': 'ebay/run_ebay_scraping.py', 'cwd': '/app'}
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

    task_dbt_run = PythonOperator(
        task_id='dbt_run',
        python_callable=run_dbt,
    )

    [task_jumia, task_walmart, task_ebay] >> task_check_nifi >> task_stage_nifi >> task_wait_bigtable >> task_export_bq >> task_dbt_run
