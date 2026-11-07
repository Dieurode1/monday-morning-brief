-- Cleans the hand-kept supplier tracker.
-- Matches each casual item name to a product ID, then converts lead times,
-- units on order, and arrival dates into values the brief can use.
-- Original values are kept beside the cleaned ones so every conversion can be checked.

with tracker as (
    select * from {{ source('raw', 'supplier_lead_times') }}
),

item_map as (
    select * from {{ ref('supplier_item_map') }}
)

select
    item_map.product_id,
    tracker.item as item_name_raw,
    tracker.vendor as vendor_raw,
    tracker.lead_time as lead_time_raw,

    -- "6 wks", "3 weeks", and "21 days" all become a number of days
    cast(regexp_substr(tracker.lead_time, '[0-9]+') as integer)
        * case
            when lower(tracker.lead_time) like '%wk%' or lower(tracker.lead_time) like '%week%' then 7
            when lower(tracker.lead_time) like '%day%' then 1
        end as lead_time_days,

    -- "50 units" becomes 50; a blank stays unknown rather than becoming 0
    cast(regexp_substr(tracker.on_order, '[0-9]+') as integer) as units_on_order,

    tracker.next_eta as next_eta_raw,

    -- Three date formats appear in the tracker; "TBD" and blanks stay unknown
    case
        when regexp_like(trim(tracker.next_eta), '[0-9]{4}-[0-9]{2}-[0-9]{2}')
            then to_date(trim(tracker.next_eta), 'YYYY-MM-DD')
        when regexp_like(trim(tracker.next_eta), '[0-9]{1,2}/[0-9]{1,2}/[0-9]{2}')
            then date_from_parts(
                2000 + cast(split_part(trim(tracker.next_eta), '/', 3) as integer),
                cast(split_part(trim(tracker.next_eta), '/', 1) as integer),
                cast(split_part(trim(tracker.next_eta), '/', 2) as integer)
            )
        when regexp_like(trim(tracker.next_eta), '[A-Za-z]{3} [0-9]{1,2}')
            then to_date(trim(tracker.next_eta) || ' {{ var("tracker_year", 2026) }}', 'MON DD YYYY')
    end as next_shipment_eta,

    tracker.notes
from tracker
left join item_map
    on trim(tracker.item) = trim(item_map.item_name)
