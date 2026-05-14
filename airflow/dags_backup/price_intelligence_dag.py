from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os
import sys
import subprocess

# Add scrapers directory to path so we can import the scripts
SCRAPERS_DIR = "/opt/airflow/scrapers" # This is where it will be inside the container

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
    """Generic function to run a scraper script."""
    print(f"🚀 Starting scraper: {script_name} in {cwd}")
    # We use subprocess to run the scripts as standalone processes
    # This avoids import conflicts and issues with sys.path
    # Run the script and stream output in real-time
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
    
    print(f"✅ Finished scraper: {script_name}")

with DAG(
    'price_intelligence_pipeline',
    default_args=default_args,
    description='Scrape e-commerce data and load to Bigtable',
    schedule_interval='0 13 * * *',
    catchup=False
) as dag:

    task_jumia = PythonOperator(
        task_id='scrape_jumia',
        python_callable=run_scraper,
        op_kwargs={
            'script_name': 'jumia/run_jumia_scraping.py',
            'cwd': '/app' # Path inside the container (mounted via volumes)
        }
    )

    task_walmart = PythonOperator(
        task_id='scrape_walmart',
        python_callable=run_scraper,
        op_kwargs={
            'script_name': 'walmart/run_walmart_scraping.py',
            'cwd': '/app'
        }
    )

    task_ebay = PythonOperator(
        task_id='scrape_ebay',
        python_callable=run_scraper,
        op_kwargs={
            'script_name': 'ebay/run_ebay_scraping.py',
            'cwd': '/app'
        }
    )

    # Task to ensure everything is loaded to Bigtable (though scripts do it, this is a safety net)
    task_load_bigtable = PythonOperator(
        task_id='final_load_to_bigtable',
        python_callable=run_scraper,
        trigger_rule='all_done',
        op_kwargs={
            'script_name': 'load_all_to_bigtable.py',
            'cwd': '/app'
        }
    )
 
    # Parallel execution of scrapers
    # The final load will run as long as all scrapers have attempted to finish (even if one fails)
    [task_jumia, task_ebay, task_walmart] >> task_load_bigtable
