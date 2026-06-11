Here is the translated English version of your documentation:

Price Intelligence - Data Analysis
Professional workspace for the Data Analyst part of the Price Intelligence project.

Role
The Data Analyst's work begins after data collection and storage. It covers: data understanding, analytical cleaning, descriptive statistics, inferential statistics, visualizations, business recommendations, and the final report.

Execution Order
notebooks/01_data_understanding.ipynb

notebooks/02_data_cleaning.ipynb

notebooks/03_exploratory_analysis.ipynb

notebooks/04_statistical_tests.ipynb

notebooks/05_final_insights.ipynb

Installation
Bash
conda activate price-analytics
cd C:\Users\Admin\Desktop\price-intelligence\data-analysis
pip install -r requirements.txt
Export for Dashboard / Full Stack
Bash
python export_for_dashboard.py
The export_for_dashboard.py script transforms the cleaned dataset and final conclusions into JSON files ready to be consumed by Streamlit, Plotly, a backend API, or a frontend interface.

Outputs generated in outputs/app/:

manifest.json: contract of the generated files.

kpis.json: global indicators.

price_by_store.json: prices by platform.

price_by_category.json: prices by category.

time_series_by_store.json: temporal price evolution by platform.

heatmap_store_category.json: data for platform/category heatmap.

top_discounts.json: products with the highest discounts.

recommendations.json: final business recommendations.

Automatic Execution After Scraping
To automate the Data Analyst workflow after a new data collection/scraping, use:

Bash
python run_eda_pipeline.py --scope eda
This command automatically executes:

notebooks/01_data_understanding.ipynb

notebooks/02_data_cleaning.ipynb

notebooks/03_exploratory_analysis.ipynb

export_for_dashboard.py

It therefore regenerates the EDA outputs, figures, and JSON files for the dashboard/full stack.

To execute the entire analytical deliverable, including statistical tests and final insights:

Bash
python run_eda_pipeline.py --scope full
To regenerate only the dashboard JSON files without rerunning the notebooks:

Bash
python run_eda_pipeline.py --scope export-only
A tracking file is generated here:

Plaintext
outputs/app/pipeline_status.json
PDF Coverage
Descriptive statistics: mean, median, standard deviation, distributions, trends by category.

Time-series plots: notebook 03.

Inferential tests: ANOVA, Kruskal-Wallis, Mann-Whitney, correlations.

Regression: notebook 04 with store, category, stars, discount, and time variables if multiple dates exist.

Confidence intervals: notebook 04.

Power analysis: notebook 04.

Effect size: notebook 04.

Streamlit Dashboard: dashboard/app.py.

Official BigQuery Source
After the last merge, the official table is:

Plaintext
price-intelligence-495411.price_intelligence.products
Observed profile in BigQuery:

Plaintext
total_rows       = 20908
null_name        = 192
null_price       = 192
store values     = ebay, jumia, sport-direct, unknown
Notebooks 01 and 02 now load BigQuery by priority. If BigQuery access is not available in Anaconda, place a CSV export of the table here:

Plaintext
outputs/raw_data/bigquery_products_export.csv
Mandatory Regeneration After BigQuery Update
The notebooks use live BigQuery as the official source: price-intelligence-495411.price_intelligence.products.
The old generated files have been archived in _backup_professional_bigquery_fix_20260520_154303/old_outputs_archived to avoid mixing old and new data.

Professional execution order:

notebooks/01_data_understanding.ipynb

notebooks/02_data_cleaning.ipynb

notebooks/03_exploratory_analysis.ipynb

notebooks/04_statistical_tests.ipynb

notebooks/05_final_insights.ipynb

Expected control in notebook 01: approximately 20,908 raw rows, sport-direct in the platforms, and about 192 null prices in the raw table.
If the notebook displays local_json_fallback, bigquery_export, or approximately 2,251 rows, you must close/reopen the notebook and restart the kernel.