select
    refund_id,
    order_line_id,
    order_id,
    product_id,
    to_date(refund_date) as refund_date,
    cast(refund_amount as number(12, 2)) as refund_amount,
    reason
from {{ source('raw', 'refunds') }}
