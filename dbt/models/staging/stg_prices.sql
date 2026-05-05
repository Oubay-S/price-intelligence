-- models/staging/stg_prices.sql

-- This model cleans and standardizes the raw data from the scrapers
-- We assume the data is available in a table named 'raw_products' in BigQuery

WITH source_data AS (
    SELECT * FROM {{ source('raw', 'products') }}
)

SELECT
    -- Generate a unique ID
    DISTINCT(MD5(CONCAT(store, category, name))) as product_id,
    
    -- Standardize names
    TRIM(name) as product_name,
    UPPER(store) as store_name,
    LOWER(category) as category_name,
    
    -- Convert price to float (handling currency and commas)
    SAFE_CAST(REGEXP_REPLACE(current_price, r'[^0-9.]', '') AS FLOAT64) as price_numeric,
    
    -- Date handling
    CAST(scraped_at AS TIMESTAMP) as scraped_at_ts,
    CURRENT_TIMESTAMP() as dbt_loaded_at

FROM source_data
WHERE current_price IS NOT NULL
