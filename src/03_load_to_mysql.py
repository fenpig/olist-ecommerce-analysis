"""Load raw Olist CSV files into MySQL.

Copy .env.example to .env first, then run from the project root:
    python src/03_load_to_mysql.py
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL


PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_DIR / "data" / "raw"
TABLES = {
    "customers_raw": "olist_customers_dataset.csv",
    "orders_raw": "olist_orders_dataset.csv",
    "order_items_raw": "olist_order_items_dataset.csv",
    "order_payments_raw": "olist_order_payments_dataset.csv",
    "order_reviews_raw": "olist_order_reviews_dataset.csv",
    "products_raw": "olist_products_dataset.csv",
    "category_translation_raw": "product_category_name_translation.csv",
}


def make_engine():
    load_dotenv(PROJECT_DIR / ".env")
    required = ["MYSQL_HOST", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE"]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise ValueError(f".env missing settings: {', '.join(missing)}")
    url = URL.create(
        "mysql+pymysql",
        username=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"],
        host=os.environ["MYSQL_HOST"],
        port=int(os.getenv("MYSQL_PORT", "3306")),
        database=os.environ["MYSQL_DATABASE"],
    )
    return create_engine(url)


def main() -> None:
    engine = make_engine()
    with engine.begin() as connection:
        for table_name, filename in TABLES.items():
            dataframe = pd.read_csv(RAW_DIR / filename)
            dataframe.to_sql(table_name, connection, if_exists="replace", index=False, chunksize=10_000)
            print(f"Loaded {table_name}: {len(dataframe):,} rows")
    print("Import complete. Run sql/01_schema.sql next to create indexes.")


if __name__ == "__main__":
    main()
