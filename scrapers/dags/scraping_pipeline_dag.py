from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
import os

# Get the absolute path of the project directory
PROJECT_DIR = "/home/omar/Desktop/baaaaaaaaaaaaaaaaaaack-20260407T210643Z-3-001/baaaaaaaaaaaaaaaaaaack/projet_data_demo"

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2026, 5, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'ecommerce_scraping_pipeline',
    default_args=default_args,
    description='A pipeline to scrape eBay, Jumia and Walmart data',
    schedule_interval=timedelta(days=1),
    catchup=False,
    tags=['scraping', 'ecommerce'],
) as dag:

    # Task to run Jumia Scraper
    scrape_jumia = BashOperator(
        task_id='scrape_jumia',
        bash_command=f'python3 {PROJECT_DIR}/jumia/run_jumia_scraping.py',
    )

    # Task to run Walmart Scraper
    # Note: Walmart requires manual CAPTCHA solving if cookies expire.
    # We set a timeout and retries so it doesn't block the entire pipeline.
    scrape_walmart = BashOperator(
        task_id='scrape_walmart',
        bash_command=f'python3 {PROJECT_DIR}/walmart/run_walmart_scraping.py',
        execution_timeout=timedelta(minutes=15), # Max time for the entire Walmart run
        retries=1,
    )

    # Task to run eBay Scraper
    scrape_ebay = BashOperator(
        task_id='scrape_ebay',
        bash_command=f'python3 {PROJECT_DIR}/ebay/run_ebay_scraping.py',
    )

    # Task to load all JSON data into Bigtable
    load_to_bigtable = BashOperator(
        task_id='load_to_bigtable',
        bash_command=f'python3 {PROJECT_DIR}/load_all_to_bigtable.py',
    )

    # Task to generate the HTML Dashboard
    generate_dashboard = BashOperator(
        task_id='generate_dashboard',
        bash_command=f'python3 {PROJECT_DIR}/generate_filtered_dashboard.py',
    )

    # Define dependencies
    [scrape_jumia, scrape_walmart, scrape_ebay] >> load_to_bigtable >> generate_dashboard
