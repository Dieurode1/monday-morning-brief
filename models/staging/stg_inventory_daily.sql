-- One row per product per day. Converts the date and units on hand,
-- which the brief uses to spot stockouts.

select
    to_date(snapshot_date) as snapshot_date,
    product_id,
    cast(on_hand_units as integer) as on_hand_units
from {{ source('raw', 'inventory_daily') }}
