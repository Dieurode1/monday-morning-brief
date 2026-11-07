-- The facts behind the Monday Morning Brief: one row per finding for the latest full week.
-- Bedrock only explains these rows, and the number check verifies the brief against them.
-- Sections:
--   store_totals: revenue, orders, new customers, Meta spend, and refunds vs the prior four-week average
--   stockout: products at zero stock, their next arrival, and the sales at risk until then
--   refund_spike: products whose refunds jumped this week, with the most common reason

with orders as (
    select * from {{ ref('stg_orders') }}
),

order_lines as (
    select * from {{ ref('stg_order_lines') }}
),

refunds as (
    select * from {{ ref('stg_refunds') }}
),

inventory as (
    select * from {{ ref('stg_inventory_daily') }}
),

ad_spend as (
    select * from {{ ref('stg_ad_spend_daily') }}
),

products as (
    select * from {{ ref('stg_products') }}
),

supplier as (
    select * from {{ ref('stg_supplier_lead_times') }}
),

-- The report covers the latest full Monday-to-Sunday week in the data, not today's date,
-- so the same data always produces the same brief.
weeks as (
    select
        dateadd(day, -6, week_end) as week_start,
        week_end,
        dateadd(day, -34, week_end) as prior_start,
        dateadd(day, -7, week_end) as prior_end
    from (
        select
            case
                when dayofweekiso(max(order_date)) = 7 then max(order_date)
                else dateadd(day, -dayofweekiso(max(order_date)), max(order_date))
            end as week_end
        from orders
    ) as last_full_week
),

-- Store totals: every daily amount in one list, labeled by metric
daily_amounts as (
    select order_date as activity_date, 'revenue' as metric, order_total as amount from orders
    union all
    select order_date, 'orders', 1 from orders
    union all
    select order_date, 'new_customers', iff(is_first_order, 1, 0) from orders
    union all
    select spend_date, 'meta_spend', spend from ad_spend where platform = 'meta'
    union all
    select refund_date, 'refunds', refund_amount from refunds
),

store_totals as (
    select
        daily_amounts.metric,
        sum(iff(activity_date between weeks.week_start and weeks.week_end, amount, 0)) as this_week,
        sum(iff(activity_date between weeks.prior_start and weeks.prior_end, amount, 0)) / 4 as prior_4wk_avg
    from daily_amounts
    cross join weeks
    group by daily_amounts.metric
),

-- Stockouts: products with zero units on the last day of the report week
product_sales as (
    select
        order_lines.product_id,
        orders.order_date,
        order_lines.line_total
    from order_lines
    inner join orders on order_lines.order_id = orders.order_id
),

out_of_stock as (
    select
        inventory.product_id,
        dateadd(day, 1, max(iff(inventory.on_hand_units > 0, inventory.snapshot_date, null))) as out_of_stock_since
    from inventory
    cross join weeks
    where inventory.snapshot_date <= weeks.week_end
    group by inventory.product_id
    having max(iff(inventory.snapshot_date = weeks.week_end, inventory.on_hand_units, null)) = 0
),

stockout_sales as (
    select
        out_of_stock.product_id,
        out_of_stock.out_of_stock_since,
        sum(iff(product_sales.order_date between weeks.week_start and weeks.week_end, product_sales.line_total, 0)) as this_week,
        sum(iff(product_sales.order_date between weeks.prior_start and weeks.prior_end, product_sales.line_total, 0)) / 4 as prior_4wk_avg
    from out_of_stock
    cross join weeks
    left join product_sales on out_of_stock.product_id = product_sales.product_id
    group by out_of_stock.product_id, out_of_stock.out_of_stock_since
),

-- Sales at risk = usual weekly sales x weeks until the next shipment arrives
stockouts as (
    select
        stockout_sales.*,
        supplier.next_shipment_eta,
        supplier.units_on_order,
        round(datediff(day, weeks.week_end, supplier.next_shipment_eta) / 7, 1) as weeks_until_restock
    from stockout_sales
    cross join weeks
    left join supplier on stockout_sales.product_id = supplier.product_id
),

-- Refund spikes: at least 10 refunds this week and at least three times the usual weekly count
refund_counts as (
    select
        refunds.product_id,
        count_if(refund_date between weeks.week_start and weeks.week_end) as this_week,
        count_if(refund_date between weeks.prior_start and weeks.prior_end) / 4 as prior_4wk_avg,
        sum(iff(refund_date between weeks.week_start and weeks.week_end, refund_amount, 0)) as refund_dollars_this_week
    from refunds
    cross join weeks
    group by refunds.product_id
),

top_reasons as (
    select
        refunds.product_id,
        refunds.reason as top_reason,
        count(*) as top_reason_count
    from refunds
    cross join weeks
    where refunds.refund_date between weeks.week_start and weeks.week_end
    group by refunds.product_id, refunds.reason
    qualify row_number() over (partition by refunds.product_id order by count(*) desc) = 1
),

refund_spikes as (
    select
        refund_counts.*,
        top_reasons.top_reason,
        top_reasons.top_reason_count
    from refund_counts
    left join top_reasons on refund_counts.product_id = top_reasons.product_id
    where refund_counts.this_week >= 10
        and refund_counts.this_week >= 3 * refund_counts.prior_4wk_avg
),

findings as (
    select
        'store_totals' as section,
        metric,
        cast(null as varchar) as product_id,
        'Store' as subject,
        this_week,
        prior_4wk_avg,
        cast(null as date) as out_of_stock_since,
        cast(null as date) as next_shipment_eta,
        cast(null as integer) as units_on_order,
        cast(null as number(6, 1)) as weeks_until_restock,
        cast(null as number(12, 2)) as sales_at_risk,
        cast(null as number(12, 2)) as refund_dollars_this_week,
        cast(null as varchar) as top_reason,
        cast(null as integer) as top_reason_count
    from store_totals

    union all

    select
        'stockout',
        'product_sales',
        stockouts.product_id,
        products.product_name,
        stockouts.this_week,
        stockouts.prior_4wk_avg,
        stockouts.out_of_stock_since,
        stockouts.next_shipment_eta,
        stockouts.units_on_order,
        stockouts.weeks_until_restock,
        stockouts.prior_4wk_avg * stockouts.weeks_until_restock,
        null,
        null,
        null
    from stockouts
    inner join products on stockouts.product_id = products.product_id

    union all

    select
        'refund_spike',
        'refund_count',
        refund_spikes.product_id,
        products.product_name,
        refund_spikes.this_week,
        refund_spikes.prior_4wk_avg,
        null,
        null,
        null,
        null,
        null,
        refund_spikes.refund_dollars_this_week,
        refund_spikes.top_reason,
        refund_spikes.top_reason_count
    from refund_spikes
    inner join products on refund_spikes.product_id = products.product_id
)

select
    findings.section || ':' || coalesce(findings.product_id, findings.metric) as fact_id,
    findings.section,
    findings.metric,
    findings.product_id,
    findings.subject,
    weeks.week_start,
    weeks.week_end,
    round(findings.this_week, 2) as this_week,
    round(findings.prior_4wk_avg, 2) as prior_4wk_avg,
    round((findings.this_week - findings.prior_4wk_avg) / nullif(findings.prior_4wk_avg, 0) * 100, 1) as pct_change,
    findings.out_of_stock_since,
    findings.next_shipment_eta,
    findings.units_on_order,
    findings.weeks_until_restock,
    round(findings.sales_at_risk, 2) as sales_at_risk,
    round(findings.refund_dollars_this_week, 2) as refund_dollars_this_week,
    findings.top_reason,
    findings.top_reason_count
from findings
cross join weeks
order by
    case findings.section when 'stockout' then 1 when 'refund_spike' then 2 else 3 end,
    findings.metric
