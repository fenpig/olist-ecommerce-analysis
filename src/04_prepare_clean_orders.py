"""Create and validate the T10 one-row-per-order clean-order output.

Default execution creates only ``vw_clean_orders`` after strict T09 and raw
order preflight checks, then exports ``data/processed/clean_orders.csv``.
Neither raw tables nor the three T09 views are changed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections.abc import Iterable
from decimal import Decimal
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import pymysql
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SQL_FILE = PROJECT_ROOT / "sql" / "03_create_clean_views.sql"
CSV_FILE = PROJECT_ROOT / "data" / "processed" / "clean_orders.csv"
REPORT_FILE = PROJECT_ROOT / "reports" / "validation" / "t10_clean_orders_summary.json"
T09_REPORT_FILE = PROJECT_ROOT / "reports" / "validation" / "t09_review_selection_summary.json"
DATABASE_NAME = "olist_delivery_analysis"
T09_VIEWS = (
    "vw_review_ranked",
    "vw_order_review_audit",
    "vw_order_review_selected",
)
TARGET_VIEW = "vw_clean_orders"
EXPECTED_ORDER_ROWS = 99441
BOUNDARY_MONTHS = ("2016-09", "2016-12", "2018-09", "2018-10")
DATE_COLUMNS = (
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
    "selected_review_creation_date",
    "selected_review_answer_timestamp",
)
INTEGER_COLUMNS = (
    "delay_days",
    "is_delayed",
    "is_delivered_order",
    "is_delivery_eligible",
    "is_review_relation_eligible",
    "is_primary_month",
    "is_approved_before_purchase",
    "is_carrier_before_purchase",
    "is_carrier_before_approval",
    "is_delivered_before_purchase",
    "is_delivered_before_carrier",
    "is_estimated_before_purchase",
    "has_date_anomaly",
    "selected_review_score",
    "review_record_count",
    "valid_review_record_count",
    "invalid_or_missing_score_count",
    "distinct_valid_score_count",
    "has_multiple_reviews",
    "has_conflicting_review_scores",
    "minimum_review_score",
    "latest_is_low_review",
    "minimum_is_low_review",
)
CSV_COLUMNS = (
    "order_id",
    "customer_id",
    "order_status",
    *DATE_COLUMNS[:5],
    "purchase_month",
    "delay_days",
    "delay_hours_raw",
    "delay_category",
    "is_delayed",
    "is_delivered_order",
    "is_delivery_eligible",
    "delivery_eligibility_reason",
    "is_review_relation_eligible",
    "review_relation_eligibility_reason",
    "is_primary_month",
    "is_approved_before_purchase",
    "is_carrier_before_purchase",
    "is_carrier_before_approval",
    "is_delivered_before_purchase",
    "is_delivered_before_carrier",
    "is_estimated_before_purchase",
    "has_date_anomaly",
    "selected_review_id",
    "selected_review_score",
    "selected_review_creation_date",
    "selected_review_answer_timestamp",
    "review_record_count",
    "valid_review_record_count",
    "invalid_or_missing_score_count",
    "distinct_valid_score_count",
    "has_multiple_reviews",
    "has_conflicting_review_scores",
    "selection_basis",
    "minimum_review_score",
    "latest_review_group",
    "minimum_review_group",
    "latest_is_low_review",
    "minimum_is_low_review",
)


def json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


class Database:
    def __init__(self) -> None:
        load_dotenv(PROJECT_ROOT / ".env")
        required = ("MYSQL_HOST", "MYSQL_PORT", "MYSQL_DATABASE", "MYSQL_USER", "MYSQL_PASSWORD")
        missing = [key for key in required if not os.getenv(key)]
        if missing:
            raise ValueError("Missing required MySQL setting(s): " + ", ".join(missing))
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

    def query(self, statement: str, params: Iterable[Any] | None = None) -> list[dict[str, Any]]:
        with self.connection.cursor() as cursor:
            cursor.execute(statement, tuple(params) if params is not None else None)
            return list(cursor.fetchall())

    def execute(self, statement: str) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(statement)

    def close(self) -> None:
        self.connection.close()


def dataframe(db: Database, statement: str) -> pd.DataFrame:
    return pd.DataFrame(db.query(statement))


def scalar(db: Database, statement: str) -> dict[str, Any]:
    rows = db.query(statement)
    if len(rows) != 1:
        raise RuntimeError("Expected exactly one SQL result row.")
    return {key.lower(): json_value(value) for key, value in rows[0].items()}


def target_view_statement() -> str:
    text = SQL_FILE.read_text(encoding="utf-8")
    match = re.search(r"(?ms)^CREATE VIEW `vw_clean_orders` AS\n.*?;\s*$", text)
    if match is None or text.count("CREATE VIEW `vw_clean_orders` AS") != 1:
        raise RuntimeError("SQL file must contain exactly one authorized vw_clean_orders CREATE VIEW statement.")
    statement = match.group(0).strip()
    if "CREATE OR REPLACE" in statement.upper():
        raise RuntimeError("CREATE OR REPLACE VIEW is not permitted for T10.")
    return statement


def view_hash(db: Database, name: str) -> str:
    record = db.query(f"SHOW CREATE VIEW `{name}`")[0]
    definition = next(value for key, value in record.items() if key.lower().startswith("create view"))
    return hashlib.sha256(str(definition).encode("utf-8")).hexdigest().upper()


def t09_hashes_from_report() -> dict[str, str]:
    report = json.loads(T09_REPORT_FILE.read_text(encoding="utf-8"))
    if report.get("reconciliation", {}).get("status") != "pass":
        raise RuntimeError("T09 report is not PASS; T10 cannot proceed.")
    hashes = report.get("reconciliation", {}).get("details", {}).get("view_definition_sha256", {})
    if set(hashes) != set(T09_VIEWS):
        raise RuntimeError("T09 report does not contain all three view hashes.")
    return {name: str(hashes[name]) for name in T09_VIEWS}


def file_metadata(path: Path) -> dict[str, Any]:
    return {
        "path": str(path.relative_to(PROJECT_ROOT)),
        "size_bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest().upper(),
    }


def preflight(db: Database, *, validate_existing: bool) -> dict[str, Any]:
    baseline = scalar(db, "SELECT COUNT(*) AS order_rows, COUNT(DISTINCT order_id) AS distinct_order_ids, SUM(order_id IS NULL) AS missing_order_ids FROM orders_raw")
    if baseline != {"order_rows": EXPECTED_ORDER_ROWS, "distinct_order_ids": EXPECTED_ORDER_ROWS, "missing_order_ids": 0}:
        raise RuntimeError(f"orders_raw baseline changed: {baseline}")
    expected_hashes = t09_hashes_from_report()
    current_hashes = {name: view_hash(db, name) for name in T09_VIEWS}
    if current_hashes != expected_hashes:
        raise RuntimeError("T09 view definition changed; refusing to continue T10.")
    existing = db.query("SELECT table_name AS object_name FROM information_schema.views WHERE table_schema = DATABASE() AND table_name = %s", (TARGET_VIEW,))
    target_exists = bool(existing)
    if validate_existing:
        if not target_exists:
            raise RuntimeError("Validation-only mode requires vw_clean_orders to exist.")
    elif target_exists:
        raise RuntimeError("vw_clean_orders already exists; refusing to replace it.")
    if CSV_FILE.exists() and not validate_existing:
        raise RuntimeError("clean_orders.csv already exists; metadata recorded for manual review: " + json.dumps(file_metadata(CSV_FILE)))
    return {"orders_raw": baseline, "t09_view_hashes": current_hashes, "clean_orders_csv_before": file_metadata(CSV_FILE) if CSV_FILE.exists() else None}


def python_clean_orders(orders: pd.DataFrame, selected_reviews: pd.DataFrame) -> pd.DataFrame:
    frame = orders.merge(selected_reviews, on="order_id", how="left", validate="one_to_one")
    for column in DATE_COLUMNS[:5] + DATE_COLUMNS[5:]:
        if column in frame:
            frame[column] = pd.to_datetime(frame[column], errors="coerce")
    frame["purchase_month"] = frame["order_purchase_timestamp"].dt.strftime("%Y-%m")
    actual = frame["order_delivered_customer_date"]
    estimated = frame["order_estimated_delivery_date"]
    has_delivery_dates = actual.notna() & estimated.notna()
    frame["delay_days"] = pd.Series(pd.NA, index=frame.index, dtype="Int64")
    frame.loc[has_delivery_dates, "delay_days"] = (
        actual.loc[has_delivery_dates].dt.normalize() - estimated.loc[has_delivery_dates].dt.normalize()
    ).dt.days.astype("Int64")
    frame["delay_hours_raw"] = pd.NA
    frame.loc[has_delivery_dates, "delay_hours_raw"] = (
        actual.loc[has_delivery_dates] - estimated.loc[has_delivery_dates]
    ).dt.total_seconds() / 3600.0
    frame["delay_category"] = "not_applicable"
    frame.loc[frame["delay_days"].notna() & (frame["delay_days"] <= 0), "delay_category"] = "on_time_or_early"
    frame.loc[frame["delay_days"].between(1, 3), "delay_category"] = "slight_delay"
    frame.loc[frame["delay_days"].between(4, 7), "delay_category"] = "moderate_delay"
    frame.loc[frame["delay_days"] > 7, "delay_category"] = "severe_delay"
    frame["is_delayed"] = pd.Series(pd.NA, index=frame.index, dtype="Int64")
    frame.loc[frame["delay_days"].notna(), "is_delayed"] = (frame.loc[frame["delay_days"].notna(), "delay_days"] > 0).astype("Int64")
    frame["is_delivered_order"] = (frame["order_status"] == "delivered").astype("Int64")
    frame["is_delivery_eligible"] = ((frame["order_status"] == "delivered") & has_delivery_dates).astype("Int64")
    frame["delivery_eligibility_reason"] = "eligible"
    frame.loc[frame["order_status"] != "delivered", "delivery_eligibility_reason"] = "not_delivered"
    delivered = frame["order_status"] == "delivered"
    frame.loc[delivered & actual.isna() & estimated.isna(), "delivery_eligibility_reason"] = "missing_both_delivery_dates"
    frame.loc[delivered & actual.isna() & estimated.notna(), "delivery_eligibility_reason"] = "missing_actual_delivery_date"
    frame.loc[delivered & actual.notna() & estimated.isna(), "delivery_eligibility_reason"] = "missing_estimated_delivery_date"
    valid_score = frame["selected_review_score"].between(1, 5)
    frame["is_review_relation_eligible"] = ((frame["is_delivery_eligible"] == 1) & valid_score).astype("Int64")
    frame["review_relation_eligibility_reason"] = "eligible"
    frame.loc[frame["is_delivery_eligible"] != 1, "review_relation_eligibility_reason"] = "delivery_ineligible"
    delivery_eligible = frame["is_delivery_eligible"] == 1
    frame.loc[delivery_eligible & frame["selected_review_id"].isna(), "review_relation_eligibility_reason"] = "no_selected_review"
    frame.loc[delivery_eligible & frame["selected_review_id"].notna() & ~valid_score, "review_relation_eligibility_reason"] = "invalid_selected_review_score"
    frame["is_primary_month"] = pd.Series(pd.NA, index=frame.index, dtype="Int64")
    frame.loc[frame["purchase_month"].notna(), "is_primary_month"] = 1
    frame.loc[frame["purchase_month"].isin(BOUNDARY_MONTHS), "is_primary_month"] = 0
    comparisons = {
        "is_approved_before_purchase": (frame["order_approved_at"].notna() & frame["order_purchase_timestamp"].notna() & (frame["order_approved_at"] < frame["order_purchase_timestamp"])),
        "is_carrier_before_purchase": (frame["order_delivered_carrier_date"].notna() & frame["order_purchase_timestamp"].notna() & (frame["order_delivered_carrier_date"] < frame["order_purchase_timestamp"])),
        "is_carrier_before_approval": (frame["order_delivered_carrier_date"].notna() & frame["order_approved_at"].notna() & (frame["order_delivered_carrier_date"] < frame["order_approved_at"])),
        "is_delivered_before_purchase": (actual.notna() & frame["order_purchase_timestamp"].notna() & (actual < frame["order_purchase_timestamp"])),
        "is_delivered_before_carrier": (actual.notna() & frame["order_delivered_carrier_date"].notna() & (actual < frame["order_delivered_carrier_date"])),
        "is_estimated_before_purchase": (estimated.notna() & frame["order_purchase_timestamp"].notna() & (estimated < frame["order_purchase_timestamp"])),
    }
    for name, condition in comparisons.items():
        frame[name] = condition.astype("Int64")
    frame["has_date_anomaly"] = pd.concat([frame[name] for name in comparisons], axis=1).max(axis=1).astype("Int64")
    for column in ("review_record_count", "valid_review_record_count", "invalid_or_missing_score_count", "distinct_valid_score_count", "has_multiple_reviews", "has_conflicting_review_scores"):
        frame[column] = frame[column].fillna(0).astype("Int64")
    return frame.loc[:, CSV_COLUMNS].sort_values("order_id", kind="mergesort").reset_index(drop=True)


def comparable(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.loc[:, CSV_COLUMNS].copy().sort_values("order_id", kind="mergesort").reset_index(drop=True)
    for column in DATE_COLUMNS:
        result[column] = pd.to_datetime(result[column], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
    for column in INTEGER_COLUMNS:
        result[column] = pd.to_numeric(result[column], errors="coerce").astype("Int64")
    result["delay_hours_raw"] = pd.to_numeric(result["delay_hours_raw"], errors="coerce").round(9)
    return result


def count_distribution(series: pd.Series) -> dict[str, int]:
    return {"NULL" if pd.isna(key) else str(key): int(value) for key, value in series.value_counts(dropna=False).sort_index(key=lambda values: values.astype(str)).items()}


def reconciliation_details(frame: pd.DataFrame) -> dict[str, Any]:
    anomaly_columns = (
        "is_approved_before_purchase",
        "is_carrier_before_purchase",
        "is_carrier_before_approval",
        "is_delivered_before_purchase",
        "is_delivered_before_carrier",
        "is_estimated_before_purchase",
        "has_date_anomaly",
    )
    nonnull_delay = frame["delay_days"].dropna()
    return {
        "population": {
            "order_rows": int(len(frame)),
            "distinct_order_ids": int(frame["order_id"].nunique()),
            "missing_order_ids": int(frame["order_id"].isna().sum()),
            "delivered_orders": int((frame["is_delivered_order"] == 1).sum()),
            "delivery_eligible_orders": int((frame["is_delivery_eligible"] == 1).sum()),
            "review_relation_eligible_orders": int((frame["is_review_relation_eligible"] == 1).sum()),
        },
        "boundary_month_orders": {month: int((frame["purchase_month"] == month).sum()) for month in BOUNDARY_MONTHS},
        "is_primary_month_distribution": count_distribution(frame["is_primary_month"]),
        "delay_category_distribution": count_distribution(frame["delay_category"]),
        "is_delayed_distribution": count_distribution(frame["is_delayed"]),
        "delivery_eligibility_reason_distribution": count_distribution(frame["delivery_eligibility_reason"]),
        "review_relation_eligibility_reason_distribution": count_distribution(frame["review_relation_eligibility_reason"]),
        "date_anomaly_counts": {column: int((frame[column] == 1).sum()) for column in anomaly_columns},
        "delay_days_summary": {
            "minimum": int(nonnull_delay.min()) if not nonnull_delay.empty else None,
            "maximum": int(nonnull_delay.max()) if not nonnull_delay.empty else None,
            "median": float(nonnull_delay.median()) if not nonnull_delay.empty else None,
        },
        "selected_review_score_distribution": count_distribution(frame["selected_review_score"]),
        "review_audit_counts": {
            "multiple_review_orders": int((frame["has_multiple_reviews"] == 1).sum()),
            "conflicting_review_orders": int((frame["has_conflicting_review_scores"] == 1).sum()),
        },
    }


def sample_orders(frame: pd.DataFrame) -> dict[str, dict[str, Any] | None]:
    conditions = {
        "early_delivery": frame["delay_days"] < 0,
        "same_day_delivery": frame["delay_days"] == 0,
        "one_day_delay": frame["delay_days"] == 1,
        "three_day_delay": frame["delay_days"] == 3,
        "four_day_delay": frame["delay_days"] == 4,
        "seven_day_delay": frame["delay_days"] == 7,
        "over_seven_day_delay": frame["delay_days"] > 7,
        "missing_delivery_date": frame["delay_days"].isna(),
    }
    samples: dict[str, dict[str, Any] | None] = {}
    columns = ("order_id", "order_delivered_customer_date", "order_estimated_delivery_date", "delay_days", "delay_hours_raw", "delay_category")
    for name, condition in conditions.items():
        matches = frame.loc[condition, columns]
        samples[name] = None if matches.empty else {key: json_value(value) for key, value in matches.iloc[0].items()}
    return samples


def assert_equal(expected: Any, actual: Any, name: str, checks: list[str]) -> None:
    if expected != actual:
        raise RuntimeError(f"SQL/Python mismatch for {name}: SQL={actual}; Python={expected}")
    checks.append(name)


def validate(db: Database, *, write_csv: bool) -> tuple[list[str], dict[str, Any]]:
    sql_frame = dataframe(db, "SELECT * FROM vw_clean_orders ORDER BY order_id")
    orders = dataframe(db, "SELECT order_id, customer_id, order_status, order_purchase_timestamp, order_approved_at, order_delivered_carrier_date, order_delivered_customer_date, order_estimated_delivery_date FROM orders_raw")
    selected_reviews = dataframe(db, "SELECT order_id, selected_review_id, selected_review_score, selected_review_creation_date, selected_review_answer_timestamp, review_record_count, valid_review_record_count, invalid_or_missing_score_count, distinct_valid_score_count, has_multiple_reviews, has_conflicting_review_scores, selection_basis, minimum_review_score, latest_review_group, minimum_review_group, latest_is_low_review, minimum_is_low_review FROM vw_order_review_selected")
    python_frame = python_clean_orders(orders, selected_reviews)
    sql_comparable = comparable(sql_frame)
    python_comparable = comparable(python_frame)
    pd.testing.assert_frame_equal(sql_comparable, python_comparable, check_dtype=False, check_exact=False, rtol=0, atol=5e-5)
    checks = ["all_clean_order_fields_per_order_sql_python"]
    sql_details = reconciliation_details(sql_comparable)
    python_details = reconciliation_details(python_comparable)
    assert_equal(python_details, sql_details, "required_population_distributions_reasons_anomalies_and_review_audit", checks)
    if sql_details["population"]["order_rows"] != EXPECTED_ORDER_ROWS or sql_details["population"]["distinct_order_ids"] != EXPECTED_ORDER_ROWS or sql_details["population"]["missing_order_ids"] != 0:
        raise RuntimeError(f"vw_clean_orders grain validation failed: {sql_details['population']}")
    checks.append("one_row_per_order_and_no_missing_order_id")
    if sql_comparable["delay_days"].notna().any() and sql_comparable.loc[sql_comparable["delay_days"].notna(), "delay_category"].eq("not_applicable").any():
        raise RuntimeError("Non-null delay_days has not_applicable delay_category.")
    if sql_comparable.loc[sql_comparable["delay_days"].isna(), "delay_category"].ne("not_applicable").any() or sql_comparable.loc[sql_comparable["delay_days"].isna(), "is_delayed"].notna().any():
        raise RuntimeError("Missing delivery dates were not retained as null delays/not_applicable.")
    checks.append("delay_formula_category_coverage_and_null_handling")
    if sql_comparable["is_primary_month"].isna().sum() != sql_comparable["order_purchase_timestamp"].isna().sum():
        raise RuntimeError("is_primary_month null handling does not match purchase timestamp nulls.")
    checks.append("boundary_months_marked_without_row_exclusion")
    if write_csv:
        if CSV_FILE.exists():
            raise RuntimeError("clean_orders.csv exists at write time; refusing to overwrite it.")
        CSV_FILE.parent.mkdir(parents=True, exist_ok=True)
        sql_comparable.to_csv(CSV_FILE, index=False, encoding="utf-8", lineterminator="\n", na_rep="")
    csv_metadata = file_metadata(CSV_FILE) if CSV_FILE.exists() else None
    if csv_metadata is not None:
        csv_frame = pd.read_csv(CSV_FILE, dtype={"order_id": "string", "customer_id": "string", "selected_review_id": "string"}, keep_default_na=True)
        if len(csv_frame) != EXPECTED_ORDER_ROWS or csv_frame["order_id"].nunique() != EXPECTED_ORDER_ROWS or list(csv_frame.columns) != list(CSV_COLUMNS):
            raise RuntimeError("clean_orders.csv failed row-grain or fixed-column-order validation.")
        checks.append("csv_utf8_fixed_columns_sorted_and_one_row_per_order")
    post_hashes = {name: view_hash(db, name) for name in T09_VIEWS}
    if post_hashes != t09_hashes_from_report():
        raise RuntimeError("T09 views changed during T10; stop for investigation.")
    checks.append("t09_view_definitions_unchanged")
    detail = {
        "sql_python": sql_details,
        "sample_orders": sample_orders(sql_comparable),
        "float_tolerance": {
            "delay_hours_raw_absolute_tolerance_hours": 5e-5,
            "delay_hours_raw_absolute_tolerance_seconds": 0.18,
            "rationale": "MySQL decimal division by 3600.0 retains four decimal hours; the calculation still starts from precise seconds and does not use TIMESTAMPDIFF(HOUR).",
        },
        "csv": csv_metadata,
        "t09_view_hashes_after": post_hashes,
        "vw_clean_orders_definition_sha256": view_hash(db, TARGET_VIEW),
    }
    return checks, detail


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-existing", action="store_true", help="Do not run DDL; validate the existing T10 view and CSV.")
    args = parser.parse_args()
    db = Database()
    try:
        preflight_detail = preflight(db, validate_existing=args.validate_existing)
        if not args.validate_existing:
            db.execute(target_view_statement())
            db.connection.commit()
        checks, detail = validate(db, write_csv=not CSV_FILE.exists())
        report = {
            "task": "T10",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "database_object": TARGET_VIEW,
            "database_object_created_this_invocation": not args.validate_existing,
            "execution_mode": "validate_existing" if args.validate_existing else "create_and_validate",
            "rule": "calendar-day DATEDIFF delay_days; precise-second TIMESTAMPDIFF divided by 3600.0 delay_hours_raw",
            "preflight": preflight_detail,
            "reconciliation": {"status": "pass", "check_count": len(checks), "checks": checks, "details": detail},
            "limitations": [
                "Date anomalies are retained as flags; T10 does not alter sample inclusion beyond explicit eligibility markers.",
                "Boundary-month flags affect only later trend analysis; no T10 row is excluded.",
                "No T11 analysis table or business conclusion is created.",
            ],
        }
        REPORT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("T10_VIEW_CREATED=" + ("NO_VALIDATION_ONLY" if args.validate_existing else TARGET_VIEW))
        print("T10_RECONCILIATION_CHECKS=" + str(len(checks)))
        print("T10_RECONCILIATION=PASS")
        print("T10_REPORT=" + str(REPORT_FILE.relative_to(PROJECT_ROOT)))
    except Exception as error:
        REPORT_FILE.write_text(json.dumps({"task": "T10", "generated_at": datetime.now().isoformat(timespec="seconds"), "reconciliation": {"status": "failed", "error": repr(error)}}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
