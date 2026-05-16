-- models/mart/mart_price_trends.sql
-- Analytics-ready price trend table at product/store/category/day grain.

with daily_prices as (
    select *
    from {{ ref('int_price_daily') }}
),

with_history as (
    select
        *,
        lag(latest_price) over (
            partition by product_id, store_name, category_name
            order by price_date
        ) as previous_price,
        lag(price_date) over (
            partition by product_id, store_name, category_name
            order by price_date
        ) as previous_price_date
    from daily_prices
)

select
    product_id,
    product_name,
    store_name,
    category_name,
    price_date,
    observations_count,
    avg_price,
    min_price,
    max_price,
    latest_price,
    previous_price,
    latest_price - previous_price as price_change,
    safe_divide(latest_price - previous_price, previous_price) as price_change_pct,
    case
        when previous_price is null then 'new'
        when latest_price > previous_price then 'increased'
        when latest_price < previous_price then 'decreased'
        else 'unchanged'
    end as price_trend_direction,
    previous_price_date,
    latest_scraped_at,
    current_timestamp() as mart_loaded_at
from with_history
