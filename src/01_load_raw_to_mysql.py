"""Load the seven verified raw Olist CSV files into the Phase 1 MySQL raw layer.

Run from the project root after executing sql/00_create_database.sql and
sql/01_create_tables.sql in MySQL Workbench:

    .\\.venv\\Scripts\\python.exe src/01_load_raw_to_mysql.py

The default run refuses to change non-empty raw tables. Use
--replace-existing only when deliberately replacing every raw-layer table.
"""

from __future__ import annotations

import argparse
import csv
import os
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pymysql
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
DATABASE_NAME = "olist_delivery_analysis"
DATETIME_COLUMNS = {
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
    "shipping_limit_date",
    "review_creation_date",
    "review_answer_timestamp",
}
INTEGER_COLUMNS = {
    "customer_zip_code_prefix",
    "order_item_id",
    "payment_sequential",
    "payment_installments",
    "review_score",
    "product_name_lenght",
    "product_description_lenght",
    "product_photos_qty",
    "product_weight_g",
    "product_length_cm",
    "product_height_cm",
    "product_width_cm",
}
DECIMAL_COLUMNS = {"price", "freight_value", "payment_value"}


@dataclass(frozen=True)
class TableSpec:
    table_name: str
    filename: str
    columns: tuple[str, ...]


TABLES: tuple[TableSpec, ...] = (
    TableSpec(
        "category_translation_raw",
        "product_category_name_translation.csv",
        ("product_category_name", "product_category_name_english"),
    ),
    TableSpec(
        "customers_raw",
        "olist_customers_dataset.csv",
        (
            "customer_id",
            "customer_unique_id",
            "customer_zip_code_prefix",
            "customer_city",
            "customer_state",
        ),
    ),
    TableSpec(
        "products_raw",
        "olist_products_dataset.csv",
        (
            "product_id",
            "product_category_name",
            "product_name_lenght",
            "product_description_lenght",
            "product_photos_qty",
            "product_weight_g",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm",
        ),
    ),
    TableSpec(
        "orders_raw",
        "olist_orders_dataset.csv",
        (
            "order_id",
            "customer_id",
            "order_status",
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ),
    ),
    TableSpec(
        "order_items_raw",
        "olist_order_items_dataset.csv",
        (
            "order_id",
            "order_item_id",
            "product_id",
            "seller_id",
            "shipping_limit_date",
            "price",
            "freight_value",
        ),
    ),
    TableSpec(
        "order_payments_raw",
        "olist_order_payments_dataset.csv",
        (
            "order_id",
            "payment_sequential",
            "payment_type",
            "payment_installments",
            "payment_value",
        ),
    ),
    TableSpec(
        "order_reviews_raw",
        "olist_order_reviews_dataset.csv",
        (
            "review_id",
            "order_id",
            "review_score",
            "review_comment_title",
            "review_comment_message",
            "review_creation_date",
            "review_answer_timestamp",
        ),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Validate CSV headers and row counts only.")
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Explicitly delete existing raw-layer rows before a complete reload.",
    )
    parser.add_argument("--chunk-size", type=int, default=5_000, help="Rows per parameterized insert batch.")
    args = parser.parse_args()
    if args.chunk_size < 1:
        parser.error("--chunk-size must be at least 1")
    return args


def read_config() -> dict[str, object]:
    load_dotenv(PROJECT_ROOT / ".env")
    required = ("MYSQL_HOST", "MYSQL_PORT", "MYSQL_DATABASE", "MYSQL_USER", "MYSQL_PASSWORD")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise ValueError(f"Missing required MySQL setting(s): {', '.join(missing)}")

    database = os.environ["MYSQL_DATABASE"]
    if database != DATABASE_NAME:
        raise ValueError(f"MYSQL_DATABASE must be {DATABASE_NAME!r}; legacy database names are not allowed.")
    if os.environ["MYSQL_USER"].lower() == "root":
        raise ValueError("MYSQL_USER must be a non-root project account.")
    if os.environ["MYSQL_PASSWORD"] == "your_password":
        raise ValueError("MYSQL_PASSWORD still contains the template placeholder.")
    try:
        port = int(os.environ["MYSQL_PORT"])
    except ValueError as error:
        raise ValueError("MYSQL_PORT must be an integer.") from error
    if not 1 <= port <= 65535:
        raise ValueError("MYSQL_PORT must be between 1 and 65535.")

    return {
        "host": os.environ["MYSQL_HOST"],
        "port": port,
        "user": os.environ["MYSQL_USER"],
        "password": os.environ["MYSQL_PASSWORD"],
        "database": database,
        "charset": os.getenv("MYSQL_CHARSET", "utf8mb4"),
    }


def normalize_value(column: str, value: str, source: Path, row_number: int) -> object | None:
    if value == "":
        return None
    try:
        if column in INTEGER_COLUMNS:
            return int(value)
        if column in DECIMAL_COLUMNS:
            return Decimal(value)
        if column in DATETIME_COLUMNS:
            datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except (ValueError, InvalidOperation) as error:
        raise ValueError(f"Invalid {column!r} in {source.name} row {row_number}: {value!r}") from error
    return value


def iter_rows(spec: TableSpec) -> Iterator[tuple[object | None, ...]]:
    source = RAW_DIR / spec.filename
    if not source.is_file():
        raise FileNotFoundError(f"Required raw CSV is missing: {source.name}")
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != spec.columns:
            raise ValueError(f"Unexpected header in {source.name}; raw CSV must not be changed.")
        for row_number, row in enumerate(reader, start=2):
            yield tuple(normalize_value(column, row[column], source, row_number) for column in spec.columns)


def chunked(rows: Iterable[tuple[object | None, ...]], size: int) -> Iterator[list[tuple[object | None, ...]]]:
    batch: list[tuple[object | None, ...]] = []
    for row in rows:
        batch.append(row)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch


def row_count(spec: TableSpec) -> int:
    return sum(1 for _ in iter_rows(spec))


def check_headers_and_counts() -> dict[str, int]:
    counts = {spec.table_name: row_count(spec) for spec in TABLES}
    for table_name, count in counts.items():
        print(f"Validated {table_name}: {count:,} CSV rows")
    return counts


def connect(config: dict[str, object]) -> pymysql.connections.Connection:
    return pymysql.connect(autocommit=False, local_infile=False, **config)


def table_counts(connection: pymysql.connections.Connection) -> dict[str, int]:
    placeholders = ", ".join(["%s"] * len(TABLES))
    query = "SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name IN (" + placeholders + ")"
    with connection.cursor() as cursor:
        cursor.execute(query, tuple(spec.table_name for spec in TABLES))
        present = {name for (name,) in cursor.fetchall()}
    missing = [spec.table_name for spec in TABLES if spec.table_name not in present]
    if missing:
        raise RuntimeError("Raw tables are missing. Execute sql/01_create_tables.sql first: " + ", ".join(missing))

    counts: dict[str, int] = {}
    with connection.cursor() as cursor:
        for spec in TABLES:
            cursor.execute(f"SELECT COUNT(*) FROM `{spec.table_name}`")
            counts[spec.table_name] = int(cursor.fetchone()[0])
    return counts


def delete_existing_rows(connection: pymysql.connections.Connection) -> None:
    with connection.cursor() as cursor:
        for spec in reversed(TABLES):
            cursor.execute(f"DELETE FROM `{spec.table_name}`")


def insert_rows(connection: pymysql.connections.Connection, spec: TableSpec, chunk_size: int) -> int:
    columns = ", ".join(f"`{column}`" for column in spec.columns)
    values = ", ".join(["%s"] * len(spec.columns))
    statement = f"INSERT INTO `{spec.table_name}` ({columns}) VALUES ({values})"
    inserted = 0
    with connection.cursor() as cursor:
        for batch in chunked(iter_rows(spec), chunk_size):
            cursor.executemany(statement, batch)
            inserted += len(batch)
    print(f"Loaded {spec.table_name}: {inserted:,} rows")
    return inserted


def main() -> None:
    args = parse_args()
    source_counts = check_headers_and_counts()
    if args.dry_run:
        print("Dry run complete: no database connection or data change was made.")
        return

    connection = connect(read_config())
    try:
        existing = table_counts(connection)
        occupied = {name: count for name, count in existing.items() if count > 0}
        if occupied and not args.replace_existing:
            detail = ", ".join(f"{name}={count:,}" for name, count in sorted(occupied.items()))
            raise RuntimeError("Raw tables are not empty; refusing to overwrite data. Use --replace-existing deliberately. " + detail)
        if occupied:
            delete_existing_rows(connection)
            print("Cleared existing raw-layer rows after explicit --replace-existing.")

        inserted = {spec.table_name: insert_rows(connection, spec, args.chunk_size) for spec in TABLES}
        if inserted != source_counts:
            raise RuntimeError("Inserted row counts do not match CSV row counts; transaction will be rolled back.")
        connection.commit()
        print("Import complete. Row counts match the seven verified raw CSV files.")
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
