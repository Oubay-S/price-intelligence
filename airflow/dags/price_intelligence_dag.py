from airflow import DAG
# pyrefly: ignore [missing-import]
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os
import sys
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

def wait_for_nifi():
    from google.cloud import bigtable
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "price-intel-local")
    instance_id = os.environ.get("BIGTABLE_INSTANCE_ID", "price-intel-instance")
    client = bigtable.Client(project=project, admin=True)
    instance = client.instance(instance_id)
    table = instance.table("products")
    def count_rows():
        return sum(1 for _ in table.read_rows())
    stable_count = -1
    stable_checks = 0
    for attempt in range(40):
        current = count_rows()
        if current == stable_count:
            stable_checks += 1
            if stable_checks >= 3:
                print(f"Bigtable stable at {current} rows after {attempt} checks")
                return
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

def run_dbt():
    dbt_dir = "/usr/app/dbt/dbt"
    if not os.path.exists(dbt_dir):
        print(f"dbt project not found at {dbt_dir}, checking alternate paths...")
        for p in ["/opt/airflow/dbt", "/app/dbt", "/dbt"]:
            if os.path.exists(p):
                dbt_dir = p
                break
    print(f"Running dbt in {dbt_dir}")
    result = subprocess.run(
        ["dbt", "run"],
        cwd=dbt_dir,
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise Exception(f"dbt run failed with code {result.returncode}")

with DAG(
    'price_intelligence_pipeline',
    default_args=default_args,
    description='Scrape e-commerce data, ingest via NiFi, export to BigQuery, transform with dbt',
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

    task_wait_nifi = PythonOperator(
        task_id='wait_for_nifi',
        python_callable=wait_for_nifi,
    )

    task_export_bq = PythonOperator(
        task_id='export_to_bigquery',
        python_callable=run_export_to_bigquery,
    )

    task_dbt_run = PythonOperator(
        task_id='dbt_run',
        python_callable=run_dbt,
    )

    [task_jumia, task_walmart, task_ebay] >> task_wait_nifi >> task_export_bq >> task_dbt_run
