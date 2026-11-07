select
    to_date(snapshot_date) as snapshot_date,
    product_id,
    cast(on_hand_units as integer) as on_hand_units
from {{ source('raw', 'inventory_daily') }}
