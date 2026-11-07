-- One row per ad platform per day. Converts spend to dollars and clicks to whole numbers.

select
    to_date(spend_date) as spend_date,
    platform,
    cast(spend as number(12, 2)) as spend,
    cast(clicks as integer) as clicks
from {{ source('raw', 'ad_spend_daily') }}
