"""
Generate sample data for the Monday Morning Brief demo.

Fictional store: a Shopify-style coffee gear brand doing about $3M a year.
Date range: 12 full weeks, Mon 2026-08-10 through Sun 2026-11-01.

Run from the project root:
    uv run python data_generator/generate_data.py

Output: seven CSV files in data/raw/

Three problems are planted in the final week (Oct 26 - Nov 1):
    1. The best-selling grinder sells out, which pulls revenue down.
    2. Meta ad spend jumps about 30%, but new customers stay flat.
    3. Refunds spike on one travel mug because of a leaking lid.

The supplier file adds the fact standard tools may not see:
    the next grinder shipment is three weeks away.
"""

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
START = pd.Timestamp("2026-08-10")
END = pd.Timestamp("2026-11-01")
PROBLEM_WEEK_START = pd.Timestamp("2026-10-26")
OUTPUT_DIR = Path.cwd() / "data" / "raw"

BASE_ORDERS_PER_DAY = 104
GRINDER_ID = "P001"
MUG_ID = "P002"
GRINDER_LAST_RESTOCK = pd.Timestamp("2026-10-05")
GRINDER_DAYS_OF_STOCK = 22
GRINDER_NEXT_SHIPMENT = "2026-11-22"
MUG_REFUND_RATE = 0.20

WEEKDAY_FACTORS = [1.00, 0.95, 0.95, 0.97, 1.02, 1.12, 1.00]

CHANNELS = ["paid_meta", "paid_google", "organic", "email", "direct"]
CHANNEL_WEIGHTS = np.array([0.30, 0.15, 0.20, 0.20, 0.15])
NEW_CUSTOMER_RATE = {
    "paid_meta": 0.55,
    "paid_google": 0.45,
    "organic": 0.30,
    "email": 0.05,
    "direct": 0.15,
}

REFUND_REASONS = [
    "wrong item ordered",
    "changed mind",
    "arrived damaged",
    "did not match description",
]

# product_id, sku, name, category, price, cost, sales weight, supplier
PRODUCTS = [
    ("P001", "GRD-SUMMIT", "Summit Burr Grinder", "grinders", 189.00, 88.00, 10, "Kessler Precision"),
    ("P002", "MUG-DRIFT", "Drift Travel Mug", "drinkware", 34.00, 11.00, 12, "Harbor Goods Supply"),
    ("P003", "BRW-POUR", "Glass Pour-Over Brewer", "brewers", 42.00, 15.00, 9, "Northline Glass"),
    ("P004", "BRW-PRESS", "Steel French Press", "brewers", 58.00, 22.00, 7, "Harbor Goods Supply"),
    ("P005", "KTL-GOOSE", "Gooseneck Kettle", "kettles", 74.00, 31.00, 8, "Kessler Precision"),
    ("P006", "SCL-DRIP", "Precision Drip Scale", "accessories", 49.00, 19.00, 6, "Kessler Precision"),
    ("P007", "FLT-PAPER", "Paper Filters 100 Pack", "accessories", 12.00, 3.50, 14, "Northline Glass"),
    ("P008", "BEN-HOUSE", "House Blend Beans 12oz", "coffee", 18.00, 7.00, 16, "Red Clay Roasters"),
    ("P009", "BEN-DECAF", "Swiss Water Decaf 12oz", "coffee", 19.00, 8.00, 6, "Red Clay Roasters"),
    ("P010", "BEN-SINGLE", "Single Origin Beans 12oz", "coffee", 22.00, 9.00, 11, "Red Clay Roasters"),
    ("P011", "MUG-STONE", "Stoneware Mug Set", "drinkware", 38.00, 14.00, 6, "Harbor Goods Supply"),
    ("P012", "TMP-ESP", "Espresso Tamper", "accessories", 29.00, 10.00, 3, "Kessler Precision"),
    ("P013", "GRD-HAND", "Travel Hand Grinder", "grinders", 64.00, 27.00, 5, "Kessler Precision"),
    ("P014", "BRW-COLD", "Cold Brew Maker", "brewers", 46.00, 18.00, 5, "Northline Glass"),
    ("P015", "CAN-VAC", "Vacuum Coffee Canister", "accessories", 32.00, 12.00, 5, "Harbor Goods Supply"),
    ("P016", "FRT-MILK", "Electric Milk Frother", "accessories", 39.00, 16.00, 5, "Kessler Precision"),
    ("P017", "CLN-KIT", "Grinder Cleaning Kit", "accessories", 16.00, 5.00, 4, "Kessler Precision"),
    ("P018", "GFT-SET", "Home Barista Gift Set", "gift_sets", 95.00, 44.00, 3, "Harbor Goods Supply"),
    ("P019", "SUB-SAMPLER", "Roaster Sampler Box", "coffee", 36.00, 16.00, 4, "Red Clay Roasters"),
    ("P020", "BRW-AERO", "Compact Press Brewer", "brewers", 44.00, 18.00, 5, "Northline Glass"),
]


def build_products():
    columns = ["product_id", "sku", "product_name", "category", "unit_price", "unit_cost", "weight", "supplier"]
    return pd.DataFrame(PRODUCTS, columns=columns)


def simulate_store(rng, products):
    """Walk through each day, creating orders and tracking inventory."""
    product_ids = products["product_id"].tolist()
    prices = dict(zip(products["product_id"], products["unit_price"]))
    weights = products["weight"].to_numpy(dtype=float)
    weights = weights / weights.sum()

    average_lines = 1.48
    expected_weekly_units = BASE_ORDERS_PER_DAY * 7 * average_lines * weights
    restock_target = dict(zip(product_ids, np.ceil(expected_weekly_units * 2.5)))
    on_hand = dict(restock_target)

    orders, lines, inventory = [], [], []
    existing_customers = [f"C{number:06d}" for number in range(1, 4001)]
    next_customer_number = 4001
    order_number = 100000
    line_number = 500000
    grinder_units_recent = []

    for day in pd.date_range(START, END):
        week_index = (day - START).days // 7

        # Weekly restock. The grinder stops getting restocked after Oct 5.
        if day.weekday() == 0:
            for product_id in product_ids:
                if product_id == GRINDER_ID:
                    continue
                on_hand[product_id] = max(on_hand[product_id], restock_target[product_id])

            if day < GRINDER_LAST_RESTOCK:
                on_hand[GRINDER_ID] = max(on_hand[GRINDER_ID], restock_target[GRINDER_ID])
            elif day == GRINDER_LAST_RESTOCK:
                daily_rate = np.mean(grinder_units_recent[-14:])
                on_hand[GRINDER_ID] = int(daily_rate * GRINDER_DAYS_OF_STOCK)

        weekly_noise = 1 + np.sin(week_index * 1.7) * 0.025
        expected_orders = BASE_ORDERS_PER_DAY * WEEKDAY_FACTORS[day.weekday()] * weekly_noise

        # Order volume and channel mix stay the same in the final week, so the
        # extra Meta spend buys clicks but no additional new customers.
        grinder_units_today = 0

        for _ in range(rng.poisson(expected_orders)):
            line_count = rng.choice([1, 2, 3], p=[0.62, 0.28, 0.10])
            picks = rng.choice(product_ids, size=line_count, replace=False, p=weights)

            order_lines = []
            for product_id in picks:
                quantity = int(rng.choice([1, 2], p=[0.9, 0.1]))
                if on_hand[product_id] < quantity:
                    continue
                on_hand[product_id] -= quantity
                if product_id == GRINDER_ID:
                    grinder_units_today += quantity
                order_lines.append((str(product_id), quantity, prices[product_id]))

            # A customer who only wanted the sold-out item leaves without buying.
            if not order_lines:
                continue

            channel = str(rng.choice(CHANNELS, p=CHANNEL_WEIGHTS))
            is_first_order = bool(rng.random() < NEW_CUSTOMER_RATE[channel])
            if is_first_order:
                customer_id = f"C{next_customer_number:06d}"
                next_customer_number += 1
                existing_customers.append(customer_id)
            else:
                customer_id = existing_customers[rng.integers(len(existing_customers))]

            subtotal = round(sum(quantity * price for _, quantity, price in order_lines), 2)
            discount_rate = 0.25 if channel == "email" else 0.15
            discount = round(subtotal * 0.10, 2) if rng.random() < discount_rate else 0.0
            shipping = 0.0 if subtotal >= 75 else 6.95
            order_number += 1
            order_id = f"O{order_number}"
            order_time = day + pd.Timedelta(seconds=int(rng.integers(0, 86400)))

            orders.append(
                {
                    "order_id": order_id,
                    "order_ts": order_time,
                    "customer_id": customer_id,
                    "is_first_order": is_first_order,
                    "channel": channel,
                    "subtotal": subtotal,
                    "discount_amount": discount,
                    "shipping_charged": shipping,
                    "total": round(subtotal - discount + shipping, 2),
                }
            )

            for product_id, quantity, price in order_lines:
                line_number += 1
                lines.append(
                    {
                        "order_line_id": f"L{line_number}",
                        "order_id": order_id,
                        "product_id": product_id,
                        "quantity": quantity,
                        "unit_price": price,
                        "line_total": round(quantity * price, 2),
                    }
                )

        grinder_units_recent.append(grinder_units_today)

        for product_id in product_ids:
            inventory.append(
                {
                    "snapshot_date": day.date(),
                    "product_id": product_id,
                    "on_hand_units": int(on_hand[product_id]),
                }
            )

    return pd.DataFrame(orders), pd.DataFrame(lines), pd.DataFrame(inventory)


def build_refunds(rng, orders, lines):
    """Create normal refunds, plus the planted travel mug spike."""
    order_dates = orders.set_index("order_id")["order_ts"]
    records = []

    for line in lines.itertuples(index=False):
        order_date = order_dates[line.order_id].normalize()
        is_spike_order = (
            line.product_id == MUG_ID
            and pd.Timestamp("2026-10-14") <= order_date <= pd.Timestamp("2026-10-31")
        )

        if is_spike_order and rng.random() < MUG_REFUND_RATE:
            earliest = max(PROBLEM_WEEK_START, order_date + pd.Timedelta(days=1))
            days_available = (END - earliest).days + 1
            refund_date = earliest + pd.Timedelta(days=int(rng.integers(0, days_available)))
            reason = "defective: lid leaks"
        elif rng.random() < 0.03:
            refund_date = order_date + pd.Timedelta(days=int(rng.integers(3, 13)))
            reason = str(rng.choice(REFUND_REASONS))
        else:
            continue

        if refund_date > END:
            continue

        records.append(
            {
                "order_line_id": line.order_line_id,
                "order_id": line.order_id,
                "product_id": line.product_id,
                "refund_date": refund_date.date(),
                "refund_amount": line.line_total,
                "reason": reason,
            }
        )

    refunds = pd.DataFrame(records).sort_values(["refund_date", "order_line_id"]).reset_index(drop=True)
    refunds.insert(0, "refund_id", [f"R{number}" for number in range(700001, 700001 + len(refunds))])
    return refunds


def build_ad_spend(rng):
    records = []
    for day in pd.date_range(START, END):
        meta_spend = 800 * rng.normal(1.0, 0.05)
        google_spend = 350 * rng.normal(1.0, 0.05)
        if day >= PROBLEM_WEEK_START:
            meta_spend *= 1.30

        for platform, spend, cost_per_click in [
            ("meta", meta_spend, 1.15),
            ("google", google_spend, 1.40),
        ]:
            records.append(
                {
                    "spend_date": day.date(),
                    "platform": platform,
                    "spend": round(spend, 2),
                    "clicks": int(spend / (cost_per_click * rng.normal(1.0, 0.04))),
                }
            )
    return pd.DataFrame(records)


def build_supplier_lead_times(rng, products):
    """Stands in for the spreadsheet a brand keeps outside its store tools."""
    records = []
    for product in products.itertuples(index=False):
        is_grinder = product.product_id == GRINDER_ID
        records.append(
            {
                "product_id": product.product_id,
                "supplier": product.supplier,
                "lead_time_days": 42 if is_grinder else int(rng.choice([14, 21, 28, 35])),
                "units_on_order": 300 if is_grinder else 0,
                "next_shipment_eta": GRINDER_NEXT_SHIPMENT if is_grinder else "",
            }
        )
    return pd.DataFrame(records)


def print_summary(orders, lines, refunds, ad_spend, inventory):
    orders = orders.copy()
    orders["week_start"] = orders["order_ts"].dt.to_period("W-SUN").dt.start_time
    weekly = orders.groupby("week_start").agg(
        revenue=("total", "sum"),
        order_count=("order_id", "count"),
        new_customers=("is_first_order", "sum"),
    )

    ad_spend = ad_spend.copy()
    ad_spend["week_start"] = pd.to_datetime(ad_spend["spend_date"]).dt.to_period("W-SUN").dt.start_time
    weekly["meta_spend"] = ad_spend[ad_spend["platform"] == "meta"].groupby("week_start")["spend"].sum()

    refunds = refunds.copy()
    refunds["week_start"] = pd.to_datetime(refunds["refund_date"]).dt.to_period("W-SUN").dt.start_time
    weekly["refund_dollars"] = refunds.groupby("week_start")["refund_amount"].sum()
    weekly["mug_refunds"] = refunds[refunds["product_id"] == MUG_ID].groupby("week_start")["refund_id"].count()
    weekly = weekly.fillna(0).round(0).astype(int)

    print(weekly.to_string())

    problem_week = weekly.iloc[-1]
    prior_average = weekly.iloc[-5:-1].mean()
    change = (problem_week / prior_average - 1) * 100

    grinder_stock = inventory[inventory["product_id"] == GRINDER_ID].set_index("snapshot_date")["on_hand_units"]
    sold_out_day = grinder_stock[grinder_stock == 0].index.min()

    print("\nFinal week vs prior 4-week average")
    for metric in ["revenue", "order_count", "new_customers", "meta_spend", "refund_dollars", "mug_refunds"]:
        print(f"{metric:>16}: {problem_week[metric]:>8,.0f} vs {prior_average[metric]:>9,.0f} ({change[metric]:+.1f}%)")

    print(f"\nGrinder first hit zero stock on: {sold_out_day}")
    print(f"Estimated annual revenue pace: ${weekly['revenue'].iloc[:-1].mean() * 52:,.0f}")


def main():
    rng = np.random.default_rng(SEED)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    products = build_products()
    orders, lines, inventory = simulate_store(rng, products)
    refunds = build_refunds(rng, orders, lines)
    ad_spend = build_ad_spend(rng)
    supplier_lead_times = build_supplier_lead_times(rng, products)

    tables = {
        "products": products.drop(columns="weight"),
        "orders": orders,
        "order_lines": lines,
        "refunds": refunds,
        "inventory_daily": inventory,
        "ad_spend_daily": ad_spend,
        "supplier_lead_times": supplier_lead_times,
    }
    for name, table in tables.items():
        table.to_csv(OUTPUT_DIR / f"{name}.csv", index=False)
        print(f"{name}.csv: {len(table):,} rows")

    print()
    print_summary(orders, lines, refunds, ad_spend, inventory)


if __name__ == "__main__":
    main()
