-- Fails if the same product appears more than once for the same store/category/day.
select
    product_id,
    store_name,
    category_name,
    date(scraped_at_ts) as scraped_date,
    count(*) as row_count
from {{ ref('stg_prices') }}
group by 1, 2, 3, 4
having count(*) > 1
