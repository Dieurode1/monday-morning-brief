select
    product_id,
    sku,
    product_name,
    category,
    cast(unit_price as number(10, 2)) as unit_price,
    cast(unit_cost as number(10, 2)) as unit_cost,
    supplier
from {{ source('raw', 'products') }}
