-- models/staging/stg_prices.sql

with source_data as (
    select * from {{ source('raw', 'products') }}
),

normalized as (
    select
        coalesce(store, source) as store_name_raw,
        category,
        name,
        current_price,
        scraped_at,
        _loaded_at,
        _export_run_id
    from source_data
    where current_price is not null
      and name is not null
),

typed as (
    select
        md5(concat(coalesce(store_name_raw, ''), coalesce(category, ''), coalesce(name, ''))) as product_id,
        trim(name) as product_name,
        upper(store_name_raw) as store_name,
        lower(category) as category_name,
        safe_cast(regexp_extract(current_price, r'\d+(?:\.\d+)?') as float64) as price_numeric,
        safe_cast(scraped_at as timestamp) as scraped_at_ts,
        safe_cast(_loaded_at as timestamp) as raw_loaded_at,
        _export_run_id,
        current_timestamp() as dbt_loaded_at
    from normalized
),

valid_prices as (
    select *
    from typed
    where price_numeric is not null
      and scraped_at_ts is not null
),

deduplicated as (
    select *
    from valid_prices
    qualify row_number() over (
        partition by product_id, store_name, category_name, date(scraped_at_ts)
        order by scraped_at_ts desc, raw_loaded_at desc, dbt_loaded_at desc
    ) = 1
)

select *
from deduplicated
