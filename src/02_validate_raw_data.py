"""Run T08 read-only raw-data checks and reconcile SQL with Python results.

Run from the project root:
    .\\.venv\\Scripts\\python.exe src\\02_validate_raw_data.py

The program reads the seven CSV files and opens MySQL in a read-only
transaction. It writes only an aggregated, non-sensitive JSON report under
reports/validation/; it never changes CSV files or MySQL objects/data.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import pymysql
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
SQL_FILE = PROJECT_ROOT / "sql" / "02_data_quality_checks.sql"
REPORT_FILE = PROJECT_ROOT / "reports" / "validation" / "t08_reconciliation_summary.json"
DATABASE_NAME = "olist_delivery_analysis"
ALLOWED_HEADS = {"SELECT", "SHOW", "DESCRIBE", "EXPLAIN", "WITH"}
BLOCKED_TOKENS = re.compile(r"\b(INSERT|UPDATE|DELETE|TRUNCATE|CREATE|ALTER|DROP|REPLACE|LOAD|CALL|SET|USE)\b", re.IGNORECASE)


@dataclass(frozen=True)
class TableSpec:
    csv_name: str
    table_name: str
    keys: tuple[str, ...]
    date_columns: tuple[str, ...] = ()
    numeric_columns: tuple[str, ...] = ()


TABLES: tuple[TableSpec, ...] = (
    TableSpec("product_category_name_translation.csv", "category_translation_raw", ("product_category_name",)),
    TableSpec("olist_customers_dataset.csv", "customers_raw", ("customer_id",), numeric_columns=("customer_zip_code_prefix",)),
    TableSpec("olist_products_dataset.csv", "products_raw", ("product_id",), numeric_columns=("product_name_lenght", "product_description_lenght", "product_photos_qty", "product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm")),
    TableSpec("olist_orders_dataset.csv", "orders_raw", ("order_id",), date_columns=("order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date", "order_delivered_customer_date", "order_estimated_delivery_date")),
    TableSpec("olist_order_items_dataset.csv", "order_items_raw", ("order_id", "order_item_id"), date_columns=("shipping_limit_date",), numeric_columns=("order_item_id", "price", "freight_value")),
    TableSpec("olist_order_payments_dataset.csv", "order_payments_raw", ("order_id", "payment_sequential"), numeric_columns=("payment_sequential", "payment_installments", "payment_value")),
    TableSpec("olist_order_reviews_dataset.csv", "order_reviews_raw", ("review_id",), date_columns=("review_creation_date", "review_answer_timestamp"), numeric_columns=("review_score",)),
)
TABLE_BY_NAME = {spec.table_name: spec for spec in TABLES}


class ReadOnlyDatabase:
    """Small query gate: setup is read-only, public methods permit only read statements."""

    def __init__(self) -> None:
        load_dotenv(PROJECT_ROOT / ".env")
        required = ("MYSQL_HOST", "MYSQL_PORT", "MYSQL_DATABASE", "MYSQL_USER", "MYSQL_PASSWORD")
        missing = [key for key in required if not os.getenv(key)]
        if missing:
            raise ValueError(f"Missing required MySQL setting(s): {', '.join(missing)}")
        if os.environ["MYSQL_DATABASE"] != DATABASE_NAME:
            raise ValueError(f"MYSQL_DATABASE must be {DATABASE_NAME!r}.")
        self.connection = pymysql.connect(
            host=os.environ["MYSQL_HOST"],
            port=int(os.environ["MYSQL_PORT"]),
            user=os.environ["MYSQL_USER"],
            password=os.environ["MYSQL_PASSWORD"],
            database=os.environ["MYSQL_DATABASE"],
            charset=os.getenv("MYSQL_CHARSET", "utf8mb4"),
            autocommit=False,
            cursorclass=pymysql.cursors.DictCursor,
        )
        # This setup is deliberately not exposed through query(); it prevents writes at the server boundary.
        with self.connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION READ ONLY")
            cursor.execute("START TRANSACTION READ ONLY")

    @staticmethod
    def _assert_read_only(statement: str) -> None:
        cleaned = statement.strip().lstrip("(")
        head = cleaned.split(None, 1)[0].upper() if cleaned else ""
        if head not in ALLOWED_HEADS or BLOCKED_TOKENS.search(cleaned):
            raise ValueError(f"Blocked non-read-only SQL statement starting with {head or 'empty'}.")

    def query(self, statement: str, params: Iterable[Any] | None = None) -> list[dict[str, Any]]:
        self._assert_read_only(statement)
        with self.connection.cursor() as cursor:
            if params is None:
                cursor.execute(statement)
            else:
                cursor.execute(statement, tuple(params))
            return list(cursor.fetchall())

    def close(self) -> None:
        self.connection.rollback()
        self.connection.close()


def clean_value(value: Any) -> Any:
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_csv(spec: TableSpec) -> pd.DataFrame:
    path = RAW_DIR / spec.csv_name
    if not path.is_file():
        raise FileNotFoundError(f"Missing raw CSV: {spec.csv_name}")
    return pd.read_csv(path)


def dataframe_from_query(db: ReadOnlyDatabase, statement: str) -> pd.DataFrame:
    return pd.DataFrame(db.query(statement))


def parse_sql_file(db: ReadOnlyDatabase) -> int:
    """Execute the standalone T08 SQL file after removing comments; return statement count."""
    uncommented = "\n".join(line for line in SQL_FILE.read_text(encoding="utf-8").splitlines() if not line.lstrip().startswith("--"))
    statements = [statement.strip() for statement in uncommented.split(";") if statement.strip()]
    for statement in statements:
        db.query(statement)
    return len(statements)


def duplicate_groups(frame: pd.DataFrame, keys: tuple[str, ...]) -> int:
    return int((frame.groupby(list(keys), dropna=False).size() > 1).sum())


def complete_duplicates(frame: pd.DataFrame) -> int:
    return int(frame.duplicated().sum())


def date_bounds(frame: pd.DataFrame, column: str) -> dict[str, Any]:
    parsed = pd.to_datetime(frame[column], errors="coerce")
    return {"missing_or_invalid": int(parsed.isna().sum()), "min": clean_value(parsed.min()), "max": clean_value(parsed.max())}


def inventory(spec: TableSpec, csv_frame: pd.DataFrame, mysql_frame: pd.DataFrame, db: ReadOnlyDatabase) -> dict[str, Any]:
    describe = db.query(f"DESCRIBE `{spec.table_name}`")
    primary = [row["Field"] for row in describe if row["Key"] == "PRI"]
    foreign_keys = db.query(
        "SELECT column_name, referenced_table_name, referenced_column_name FROM information_schema.key_column_usage "
        "WHERE table_schema = DATABASE() AND table_name = %s AND referenced_table_name IS NOT NULL ORDER BY ordinal_position",
        (spec.table_name,),
    )
    numeric = {column: {"min": clean_value(pd.to_numeric(csv_frame[column], errors="coerce").min()), "max": clean_value(pd.to_numeric(csv_frame[column], errors="coerce").max())} for column in spec.numeric_columns}
    dates = {column: date_bounds(csv_frame, column) for column in spec.date_columns}
    return {
        "csv_file": spec.csv_name,
        "mysql_table": spec.table_name,
        "csv_rows": int(len(csv_frame)),
        "mysql_rows": int(len(mysql_frame)),
        "csv_column_count": int(len(csv_frame.columns)),
        "mysql_column_count": int(len(mysql_frame.columns)),
        "csv_fields": list(csv_frame.columns),
        "mysql_fields": list(mysql_frame.columns),
        "csv_inferred_dtypes": {column: str(dtype) for column, dtype in csv_frame.dtypes.items()},
        "mysql_types": {row["Field"]: row["Type"] for row in describe},
        "declared_primary_key": primary,
        "candidate_key": list(spec.keys),
        "foreign_keys": foreign_keys,
        "candidate_key_duplicate_groups": duplicate_groups(csv_frame, spec.keys),
        "complete_duplicate_rows": complete_duplicates(csv_frame),
        "mysql_complete_duplicate_rows": complete_duplicates(mysql_frame),
        "missing": {column: int(csv_frame[column].isna().sum()) for column in csv_frame.columns},
        "numeric_ranges": numeric,
        "date_ranges": dates,
    }


def sql_scalar(db: ReadOnlyDatabase, statement: str) -> dict[str, Any]:
    rows = db.query(statement)
    if len(rows) != 1:
        raise RuntimeError("Expected one SQL result row.")
    return {key: clean_value(value) for key, value in rows[0].items()}


def reconcile(expected: dict[str, Any], actual: dict[str, Any], name: str, checks: list[str]) -> None:
    if expected != actual:
        raise RuntimeError(f"SQL/Python reconciliation failed for {name}: SQL={actual}, Python={expected}")
    checks.append(name)


def build_reconciliation(db: ReadOnlyDatabase, frames: dict[str, pd.DataFrame]) -> tuple[list[str], dict[str, Any]]:
    checks: list[str] = []
    details: dict[str, Any] = {}
    python_counts = {name: int(len(frame)) for name, frame in frames.items()}
    sql_counts = {row["table_name"]: int(row["row_count"]) for row in db.query(
        "SELECT 'category_translation_raw' AS table_name, COUNT(*) AS row_count FROM category_translation_raw "
        "UNION ALL SELECT 'customers_raw', COUNT(*) FROM customers_raw "
        "UNION ALL SELECT 'products_raw', COUNT(*) FROM products_raw "
        "UNION ALL SELECT 'orders_raw', COUNT(*) FROM orders_raw "
        "UNION ALL SELECT 'order_items_raw', COUNT(*) FROM order_items_raw "
        "UNION ALL SELECT 'order_payments_raw', COUNT(*) FROM order_payments_raw "
        "UNION ALL SELECT 'order_reviews_raw', COUNT(*) FROM order_reviews_raw"
    )}
    reconcile(python_counts, sql_counts, "seven_table_row_counts", checks)
    details["table_counts"] = sql_counts

    key_defs = {
        "customers.customer_id": ("customers_raw", ("customer_id",)),
        "orders.order_id": ("orders_raw", ("order_id",)),
        "products.product_id": ("products_raw", ("product_id",)),
        "order_items.order_id_order_item_id": ("order_items_raw", ("order_id", "order_item_id")),
        "payments.order_id_payment_sequential": ("order_payments_raw", ("order_id", "payment_sequential")),
        "reviews.review_id": ("order_reviews_raw", ("review_id",)),
    }
    python_dups = {name: duplicate_groups(frames[table], keys) for name, (table, keys) in key_defs.items()}
    sql_dups = {row["check_name"]: int(row["duplicate_groups"]) for row in db.query(
        "SELECT 'customers.customer_id' AS check_name, COUNT(*) AS duplicate_groups FROM (SELECT customer_id FROM customers_raw GROUP BY customer_id HAVING COUNT(*) > 1) d "
        "UNION ALL SELECT 'orders.order_id', COUNT(*) FROM (SELECT order_id FROM orders_raw GROUP BY order_id HAVING COUNT(*) > 1) d "
        "UNION ALL SELECT 'products.product_id', COUNT(*) FROM (SELECT product_id FROM products_raw GROUP BY product_id HAVING COUNT(*) > 1) d "
        "UNION ALL SELECT 'order_items.order_id_order_item_id', COUNT(*) FROM (SELECT order_id, order_item_id FROM order_items_raw GROUP BY order_id, order_item_id HAVING COUNT(*) > 1) d "
        "UNION ALL SELECT 'payments.order_id_payment_sequential', COUNT(*) FROM (SELECT order_id, payment_sequential FROM order_payments_raw GROUP BY order_id, payment_sequential HAVING COUNT(*) > 1) d "
        "UNION ALL SELECT 'reviews.review_id', COUNT(*) FROM (SELECT review_id FROM order_reviews_raw GROUP BY review_id HAVING COUNT(*) > 1) d"
    )}
    reconcile(python_dups, sql_dups, "candidate_key_duplicate_groups", checks)
    details["candidate_key_duplicate_groups"] = sql_dups

    key_fields = {
        "customers_raw.customer_id": ("customers_raw", "customer_id"),
        "orders_raw.order_id": ("orders_raw", "order_id"),
        "orders_raw.customer_id": ("orders_raw", "customer_id"),
        "products_raw.product_id": ("products_raw", "product_id"),
        "order_items_raw.order_id": ("order_items_raw", "order_id"),
        "order_items_raw.product_id": ("order_items_raw", "product_id"),
        "order_items_raw.seller_id": ("order_items_raw", "seller_id"),
        "order_payments_raw.order_id": ("order_payments_raw", "order_id"),
        "order_reviews_raw.order_id": ("order_reviews_raw", "order_id"),
        "order_reviews_raw.review_score": ("order_reviews_raw", "review_score"),
    }
    python_missing = {name: int(frames[table][column].isna().sum()) for name, (table, column) in key_fields.items()}
    sql_missing = {name: int(sql_scalar(db, f"SELECT SUM(`{column}` IS NULL) AS missing_count FROM `{table}`")["missing_count"] or 0) for name, (table, column) in key_fields.items()}
    reconcile(python_missing, sql_missing, "key_field_missing_counts", checks)
    details["key_field_missing_counts"] = sql_missing

    relations = {
        "orders.customer_id_to_customers.customer_id": ("orders_raw", "customer_id", "customers_raw", "customer_id"),
        "items.order_id_to_orders.order_id": ("order_items_raw", "order_id", "orders_raw", "order_id"),
        "items.product_id_to_products.product_id": ("order_items_raw", "product_id", "products_raw", "product_id"),
        "payments.order_id_to_orders.order_id": ("order_payments_raw", "order_id", "orders_raw", "order_id"),
        "reviews.order_id_to_orders.order_id": ("order_reviews_raw", "order_id", "orders_raw", "order_id"),
    }
    python_orphans = {name: int((~frames[child][child_key].isin(set(frames[parent][parent_key])) & frames[child][child_key].notna()).sum()) for name, (child, child_key, parent, parent_key) in relations.items()}
    sql_orphans = {}
    for name, (child, child_key, parent, parent_key) in relations.items():
        result = sql_scalar(db, f"SELECT COUNT(*) AS orphan_count FROM `{child}` c LEFT JOIN `{parent}` p ON c.`{child_key}` = p.`{parent_key}` WHERE c.`{child_key}` IS NOT NULL AND p.`{parent_key}` IS NULL")
        sql_orphans[name] = int(result["orphan_count"])
    reconcile(python_orphans, sql_orphans, "foreign_key_orphan_counts", checks)
    details["foreign_key_orphan_counts"] = sql_orphans

    orders = frames["orders_raw"]
    reviews = frames["order_reviews_raw"]
    python_status = {str(key): int(value) for key, value in orders["order_status"].value_counts().sort_index().items()}
    sql_status = {str(row["order_status"]): int(row["order_count"]) for row in db.query("SELECT order_status, COUNT(*) AS order_count FROM orders_raw GROUP BY order_status ORDER BY order_status")}
    reconcile(python_status, sql_status, "order_status_distribution", checks)
    python_scores = {str(int(key)): int(value) for key, value in reviews["review_score"].value_counts().sort_index().items()}
    sql_scores = {str(int(row["review_score"])): int(row["review_count"]) for row in db.query("SELECT review_score, COUNT(*) AS review_count FROM order_reviews_raw GROUP BY review_score ORDER BY review_score")}
    reconcile(python_scores, sql_scores, "review_score_distribution", checks)
    details["order_status_distribution"] = sql_status
    details["review_score_distribution"] = sql_scores

    review_groups = reviews.groupby("order_id")["review_score"].agg(["size", "nunique"])
    python_multi = {"multi_review_orders": int((review_groups["size"] > 1).sum()), "conflicting_score_orders": int((review_groups["nunique"] > 1).sum()), "max_reviews_per_order": int(review_groups["size"].max())}
    sql_multi = sql_scalar(db, "SELECT SUM(review_count > 1) AS multi_review_orders, SUM(score_count > 1) AS conflicting_score_orders, MAX(review_count) AS max_reviews_per_order FROM (SELECT order_id, COUNT(*) AS review_count, COUNT(DISTINCT review_score) AS score_count FROM order_reviews_raw GROUP BY order_id) r")
    sql_multi = {key: int(value) for key, value in sql_multi.items()}
    reconcile(python_multi, sql_multi, "multi_review_and_conflict_counts", checks)
    details["review_audit"] = sql_multi

    date_columns = ("order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date", "order_delivered_customer_date", "order_estimated_delivery_date")
    python_dates = {column: date_bounds(orders, column) for column in date_columns}
    sql_date_row = sql_scalar(db, "SELECT MIN(order_purchase_timestamp) AS order_purchase_timestamp_min, MAX(order_purchase_timestamp) AS order_purchase_timestamp_max, MIN(order_approved_at) AS order_approved_at_min, MAX(order_approved_at) AS order_approved_at_max, MIN(order_delivered_carrier_date) AS order_delivered_carrier_date_min, MAX(order_delivered_carrier_date) AS order_delivered_carrier_date_max, MIN(order_delivered_customer_date) AS order_delivered_customer_date_min, MAX(order_delivered_customer_date) AS order_delivered_customer_date_max, MIN(order_estimated_delivery_date) AS order_estimated_delivery_date_min, MAX(order_estimated_delivery_date) AS order_estimated_delivery_date_max FROM orders_raw")
    compact_python_dates = {f"{column}_{bound}": python_dates[column][bound] for column in date_columns for bound in ("min", "max")}
    reconcile(compact_python_dates, sql_date_row, "order_date_boundaries", checks)
    details["order_date_ranges"] = python_dates

    python_review_dates = {f"{column}_{bound}": date_bounds(reviews, column)[bound] for column in ("review_creation_date", "review_answer_timestamp") for bound in ("min", "max")}
    sql_review_dates = sql_scalar(db, "SELECT MIN(review_creation_date) AS review_creation_date_min, MAX(review_creation_date) AS review_creation_date_max, MIN(review_answer_timestamp) AS review_answer_timestamp_min, MAX(review_answer_timestamp) AS review_answer_timestamp_max FROM order_reviews_raw")
    reconcile(python_review_dates, sql_review_dates, "review_date_boundaries", checks)
    details["review_date_ranges"] = {column: date_bounds(reviews, column) for column in ("review_creation_date", "review_answer_timestamp")}

    purchase_dates = pd.to_datetime(orders["order_purchase_timestamp"])
    python_months = {str(month): int(count) for month, count in purchase_dates.dt.to_period("M").astype(str).value_counts().sort_index().items()}
    sql_months = {row["order_month"]: int(row["order_count"]) for row in db.query("SELECT DATE_FORMAT(order_purchase_timestamp, '%Y-%m') AS order_month, COUNT(*) AS order_count FROM orders_raw GROUP BY DATE_FORMAT(order_purchase_timestamp, '%Y-%m') ORDER BY order_month")}
    reconcile(python_months, sql_months, "monthly_order_counts", checks)
    details["monthly_order_counts"] = sql_months

    valid_review_orders = set(reviews.loc[reviews["review_score"].between(1, 5), "order_id"])
    delivered = orders["order_status"].eq("delivered")
    actual = orders["order_delivered_customer_date"].notna()
    estimated = orders["order_estimated_delivery_date"].notna()
    python_funnel = {
        "all_orders": int(len(orders)),
        "delivered_orders": int(delivered.sum()),
        "delivered_with_actual_date": int((delivered & actual).sum()),
        "delivered_with_both_dates": int((delivered & actual & estimated).sum()),
        "delivery_review_sample": int((delivered & actual & estimated & orders["order_id"].isin(valid_review_orders)).sum()),
    }
    sql_funnel = {key: int(value) for key, value in sql_scalar(db, "SELECT COUNT(*) AS all_orders, SUM(order_status = 'delivered') AS delivered_orders, SUM(order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL) AS delivered_with_actual_date, SUM(order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL AND order_estimated_delivery_date IS NOT NULL) AS delivered_with_both_dates, SUM(order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL AND order_estimated_delivery_date IS NOT NULL AND EXISTS (SELECT 1 FROM order_reviews_raw r WHERE r.order_id = orders_raw.order_id AND r.review_score BETWEEN 1 AND 5)) AS delivery_review_sample FROM orders_raw").items()}
    reconcile(python_funnel, sql_funnel, "main_analysis_sample_funnel", checks)
    details["sample_funnel"] = python_funnel

    products = frames["products_raw"]
    translation = frames["category_translation_raw"]
    product_categories = set(products["product_category_name"].dropna())
    translated_categories = set(translation["product_category_name"])
    python_translation = {"source_categories": len(product_categories), "translated_categories": len(product_categories & translated_categories), "untranslated_product_rows": int((products["product_category_name"].notna() & ~products["product_category_name"].isin(translated_categories)).sum())}
    sql_translation = {key: int(value) for key, value in sql_scalar(db, "SELECT COUNT(DISTINCT p.product_category_name) AS source_categories, COUNT(DISTINCT t.product_category_name) AS translated_categories, SUM(t.product_category_name IS NULL AND p.product_category_name IS NOT NULL) AS untranslated_product_rows FROM products_raw p LEFT JOIN category_translation_raw t ON p.product_category_name = t.product_category_name").items()}
    reconcile(python_translation, sql_translation, "category_translation_counts", checks)
    details["category_translation"] = sql_translation
    return checks, details


def additional_findings(frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    orders, items, payments, reviews, products, customers = (frames[name] for name in ("orders_raw", "order_items_raw", "order_payments_raw", "order_reviews_raw", "products_raw", "customers_raw"))
    translation = frames["category_translation_raw"]
    item_counts = items.groupby("order_id").size().rename("item_count")
    payment_counts = payments.groupby("order_id").size().rename("payment_count")
    review_counts = reviews.groupby("order_id").size().rename("review_count")
    order_level = orders[["order_id"]].set_index("order_id").join([item_counts, payment_counts, review_counts]).fillna(0)
    order_level = order_level.astype(int)
    sequential_anomalies = int((payments.groupby("order_id")["payment_sequential"].apply(lambda values: sorted(values.tolist()) != list(range(1, len(values) + 1)))).sum())
    date_anomalies = {
        "approved_before_purchase": int(((pd.to_datetime(orders["order_approved_at"]) < pd.to_datetime(orders["order_purchase_timestamp"])).fillna(False)).sum()),
        "carrier_before_purchase": int(((pd.to_datetime(orders["order_delivered_carrier_date"]) < pd.to_datetime(orders["order_purchase_timestamp"])).fillna(False)).sum()),
        "carrier_before_approved": int(((pd.to_datetime(orders["order_delivered_carrier_date"]) < pd.to_datetime(orders["order_approved_at"])).fillna(False)).sum()),
        "delivered_before_carrier": int(((pd.to_datetime(orders["order_delivered_customer_date"]) < pd.to_datetime(orders["order_delivered_carrier_date"])).fillna(False)).sum()),
        "delivered_before_purchase": int(((pd.to_datetime(orders["order_delivered_customer_date"]) < pd.to_datetime(orders["order_purchase_timestamp"])).fillna(False)).sum()),
        "estimated_before_purchase": int(((pd.to_datetime(orders["order_estimated_delivery_date"]) < pd.to_datetime(orders["order_purchase_timestamp"])).fillna(False)).sum()),
    }
    purchase_dates = pd.to_datetime(orders["order_purchase_timestamp"])
    month_frame = pd.DataFrame({"month": purchase_dates.dt.to_period("M").astype(str), "day": purchase_dates.dt.date})
    monthly_coverage = {
        str(month): {
            "order_count": int(len(group)),
            "first_order_date": str(group["day"].min()),
            "last_order_date": str(group["day"].max()),
            "active_days": int(group["day"].nunique()),
        }
        for month, group in month_frame.groupby("month")
    }
    order_status_missing_dates = {
        str(status): {
            "orders": int(len(group)),
            "missing_approved_at": int(group["order_approved_at"].isna().sum()),
            "missing_carrier_at": int(group["order_delivered_carrier_date"].isna().sum()),
            "missing_delivered_at": int(group["order_delivered_customer_date"].isna().sum()),
        }
        for status, group in orders.groupby("order_status")
    }
    category_set = set(translation["product_category_name"])
    untranslated_categories = sorted(set(products.loc[products["product_category_name"].notna() & ~products["product_category_name"].isin(category_set), "product_category_name"]))
    valid_orders = orders.loc[(orders["order_status"] == "delivered") & orders["order_delivered_customer_date"].notna() & orders["order_estimated_delivery_date"].notna() & orders["order_id"].isin(set(reviews["order_id"]))]
    def distribution(counts: pd.Series) -> dict[str, Any]:
        return {"groups": int(len(counts)), "threshold_candidates": {str(threshold): int((counts >= threshold).sum()) for threshold in (10, 20, 30, 50)}, "quantiles": {str(q): clean_value(counts.quantile(q)) for q in (0.25, 0.5, 0.75, 0.9)}}
    valid_item_rows = items[items["order_id"].isin(set(valid_orders["order_id"]))]
    category_by_item = valid_item_rows.merge(products[["product_id", "product_category_name"]], on="product_id", how="left")
    valid_states = valid_orders.merge(customers[["customer_id", "customer_state"]], on="customer_id", how="left")
    return {
        "join_multiplication_risk": {"single_item_orders": int((order_level["item_count"] == 1).sum()), "multi_item_orders": int((order_level["item_count"] > 1).sum()), "single_payment_orders": int((order_level["payment_count"] == 1).sum()), "multi_payment_orders": int((order_level["payment_count"] > 1).sum()), "single_review_orders": int((order_level["review_count"] == 1).sum()), "multi_review_orders": int((order_level["review_count"] > 1).sum()), "multi_item_multi_payment_orders": int(((order_level["item_count"] > 1) & (order_level["payment_count"] > 1)).sum()), "three_way_inner_join_rows": int((order_level["item_count"] * order_level["payment_count"] * order_level["review_count"]).sum())},
        "date_order_anomalies": date_anomalies,
        "orders_by_status_date_missing": order_status_missing_dates,
        "monthly_order_coverage": monthly_coverage,
        "review_quality": {"missing_review_score": int(reviews["review_score"].isna().sum()), "invalid_review_score": int((~reviews["review_score"].between(1, 5)).sum()), "duplicate_review_id_rows_after_first": int(reviews.duplicated(["review_id"]).sum()), "complete_duplicate_rows": complete_duplicates(reviews)},
        "item_quality": {"missing_price": int(items["price"].isna().sum()), "zero_price": int((items["price"] == 0).sum()), "negative_price": int((items["price"] < 0).sum()), "missing_freight": int(items["freight_value"].isna().sum()), "negative_freight": int((items["freight_value"] < 0).sum())},
        "payment_quality": {"payment_type_distribution": {str(key): int(value) for key, value in payments["payment_type"].value_counts().sort_index().items()}, "missing_payment_value": int(payments["payment_value"].isna().sum()), "zero_payment_value": int((payments["payment_value"] == 0).sum()), "negative_payment_value": int((payments["payment_value"] < 0).sum()), "installment_min": int(payments["payment_installments"].min()), "installment_max": int(payments["payment_installments"].max())},
        "payment_sequential_anomaly_orders": sequential_anomalies,
        "product_quality": {"missing_category": int(products["product_category_name"].isna().sum()), "nonpositive_or_negative_dimension_values": {column: int((pd.to_numeric(products[column], errors="coerce") <= 0).fillna(False).sum()) for column in ("product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm")}, "untranslated_categories": untranslated_categories, "untranslated_order_item_rows": int(items.merge(products[["product_id", "product_category_name"]], on="product_id", how="left")["product_category_name"].isin(untranslated_categories).sum())},
        "customer_quality": {"duplicate_customer_unique_id_groups": duplicate_groups(customers, ("customer_unique_id",)), "state_distribution": {str(key): int(value) for key, value in customers["customer_state"].value_counts().sort_index().items()}},
        "minimum_sample_size_candidates": {"seller_id": distribution(valid_item_rows.groupby("seller_id")["order_id"].nunique()), "product_category": distribution(category_by_item.dropna(subset=["product_category_name"]).groupby("product_category_name")["order_id"].nunique()), "customer_state": distribution(valid_states.groupby("customer_state")["order_id"].nunique())},
    }


def main() -> None:
    db = ReadOnlyDatabase()
    try:
        script_statement_count = parse_sql_file(db)
        metadata = sql_scalar(db, "SELECT VERSION() AS mysql_version, DATABASE() AS database_name, @@character_set_database AS charset, @@collation_database AS collation")
        csv_frames = {spec.table_name: load_csv(spec) for spec in TABLES}
        mysql_frames = {spec.table_name: dataframe_from_query(db, f"SELECT * FROM `{spec.table_name}`") for spec in TABLES}
        for spec in TABLES:
            if len(csv_frames[spec.table_name]) != len(mysql_frames[spec.table_name]):
                raise RuntimeError(f"T07 baseline mismatch for {spec.table_name}; stopping before quality checks.")
        inventories = [inventory(spec, csv_frames[spec.table_name], mysql_frames[spec.table_name], db) for spec in TABLES]
        checks, reconciliation = build_reconciliation(db, mysql_frames)
        report = {
            "task": "T08",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "read_only_transaction": True,
            "database": metadata,
            "sql_file_statements_executed": script_statement_count,
            "raw_csv_hashes": {spec.csv_name: hash_file(RAW_DIR / spec.csv_name) for spec in TABLES},
            "table_inventory": inventories,
            "reconciliation": {"status": "pass", "check_count": len(checks), "checks": checks, "details": reconciliation},
            "quality_findings": additional_findings(mysql_frames),
        }
        REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
        REPORT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=clean_value) + "\n", encoding="utf-8")
        print(f"T08_READ_ONLY_SQL_STATEMENTS={script_statement_count}")
        print(f"T08_RECONCILIATION_CHECKS={len(checks)}")
        print("T08_RECONCILIATION=PASS")
        print(f"T08_REPORT={REPORT_FILE.relative_to(PROJECT_ROOT)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
