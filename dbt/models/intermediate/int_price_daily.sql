-- models/intermediate/int_price_daily.sql
-- Daily product price grain prepared for downstream marts.

with prices as (
    select
        product_id,
        product_name,
        store_name,
        category_name,
        date(scraped_at_ts) as price_date,
        price_numeric,
        scraped_at_ts
    from {{ ref('stg_prices') }}
),

daily_rollup as (
    select
        product_id,
        product_name,
        store_name,
        category_name,
        price_date,
        count(*) as observations_count,
        avg(price_numeric) as avg_price,
        min(price_numeric) as min_price,
        max(price_numeric) as max_price,
        array_agg(price_numeric order by scraped_at_ts desc limit 1)[offset(0)] as latest_price,
        max(scraped_at_ts) as latest_scraped_at
    from prices
    group by 1, 2, 3, 4, 5
)

select *
from daily_rollup
