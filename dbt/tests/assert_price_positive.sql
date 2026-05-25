-- Fails if any staged product has a zero or negative price.
select
    product_id,
    product_name,
    store_name,
    category_name,
    price_numeric
from {{ ref('stg_prices') }}
where price_numeric <= 0
