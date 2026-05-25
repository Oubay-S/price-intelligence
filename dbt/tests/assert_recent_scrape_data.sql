-- Fails if the staged data has no recent warehouse load.
select *
from (select 1 as missing_recent_data)
where not exists (
    select 1
    from {{ ref('stg_prices') }}
    where coalesce(raw_loaded_at, scraped_at_ts) >= timestamp_sub(current_timestamp(), interval 2 day)
)
