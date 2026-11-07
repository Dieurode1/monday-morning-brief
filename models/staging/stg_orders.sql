-- One row per order. Converts the order time to a timestamp and a date,
-- the first-order flag to true or false, and dollar amounts to numbers.

select
    order_id,
    to_timestamp_ntz(order_ts) as ordered_at,
    cast(to_timestamp_ntz(order_ts) as date) as order_date,
    customer_id,
    to_boolean(is_first_order) as is_first_order,
    channel,
    cast(subtotal as number(12, 2)) as subtotal,
    cast(discount_amount as number(12, 2)) as discount_amount,
    cast(shipping_charged as number(12, 2)) as shipping_charged,
    cast(total as number(12, 2)) as order_total
from {{ source('raw', 'orders') }}
