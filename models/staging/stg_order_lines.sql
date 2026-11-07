-- One row per product on an order. Converts quantity and dollar amounts to numbers.

select
    order_line_id,
    order_id,
    product_id,
    cast(quantity as integer) as quantity,
    cast(unit_price as number(10, 2)) as unit_price,
    cast(line_total as number(12, 2)) as line_total
from {{ source('raw', 'order_lines') }}
