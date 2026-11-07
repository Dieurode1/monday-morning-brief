"""
Load the sample CSV files into Snowflake's RAW schema.

Every column lands as text, exactly as it appears in the file.
dbt cleans and types the data later, so the raw layer stays a faithful copy.

Run from the project root:
    uv run python snowflake/load_raw.py
"""

import csv
import os
from pathlib import Path

import snowflake.connector
from dotenv import load_dotenv

RAW_DIR = Path("data/raw")
FILES = [
    "products",
    "orders",
    "order_lines",
    "refunds",
    "inventory_daily",
    "ad_spend_daily",
    "supplier_lead_times",
]


def connect():
    load_dotenv(".env")
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        authenticator="SNOWFLAKE_JWT",
        private_key_file=os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"],
        role=os.environ["SNOWFLAKE_ROLE"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        database=os.environ["SNOWFLAKE_DATABASE"],
        schema=os.environ["SNOWFLAKE_SCHEMA"],
    )


def read_file(path):
    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        row_count = sum(1 for _ in reader)
    return header, row_count


def load_table(cursor, name):
    path = RAW_DIR / f"{name}.csv"
    header, expected_rows = read_file(path)
    table = name.upper()
    columns = ", ".join(f"{column.upper()} VARCHAR" for column in header)

    cursor.execute(f"CREATE OR REPLACE TABLE {table} ({columns})")
    cursor.execute(f"PUT 'file://{path.resolve()}' @%{table} OVERWRITE = TRUE")
    cursor.execute(
        f"""
        COPY INTO {table}
        FROM @%{table}
        FILE_FORMAT = (
            TYPE = CSV
            SKIP_HEADER = 1
            FIELD_OPTIONALLY_ENCLOSED_BY = '"'
            EMPTY_FIELD_AS_NULL = TRUE
        )
        ON_ERROR = ABORT_STATEMENT
        PURGE = TRUE
        """
    )

    loaded_rows = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    status = "OK" if loaded_rows == expected_rows else "MISMATCH"
    print(f"{table:<22} file: {expected_rows:>6,}  loaded: {loaded_rows:>6,}  {status}")
    return loaded_rows == expected_rows


def main():
    missing = [name for name in FILES if not (RAW_DIR / f"{name}.csv").exists()]
    if missing:
        raise SystemExit(f"Missing files: {missing}. Run the data generator first.")

    conn = connect()
    try:
        cursor = conn.cursor()
        results = [load_table(cursor, name) for name in FILES]
    finally:
        conn.close()

    if not all(results):
        raise SystemExit("At least one table did not match its file. Check the lines marked MISMATCH.")
    print("\nAll seven tables loaded and match their files.")


if __name__ == "__main__":
    main()
