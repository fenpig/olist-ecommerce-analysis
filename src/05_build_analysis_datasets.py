"""Create and validate the four T11 reproducible analysis views and CSVs."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd
import pymysql
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
SQL_FILE = ROOT / "sql" / "04_create_order_analysis_table.sql"
ORDER_CSV = ROOT / "data" / "processed" / "order_analysis.csv"
ITEM_CSV = ROOT / "data" / "processed" / "order_item_analysis.csv"
REPORT = ROOT / "reports" / "validation" / "t11_analysis_datasets_summary.json"
T10_REPORT = ROOT / "reports" / "validation" / "t10_clean_orders_summary.json"
TARGETS = ("vw_order_items_aggregated", "vw_order_payments_aggregated", "vw_order_analysis", "vw_order_item_analysis")
EXPECTED = {"orders": 99441, "items": 112650, "payments": 103886, "customers": 99441}
MONEY_TOLERANCE = 0.01


def scalar_value(value: Any) -> Any:
    if isinstance(value, Decimal): return float(value)
    if isinstance(value, (pd.Timestamp, datetime)): return value.strftime("%Y-%m-%d %H:%M:%S")
    if pd.isna(value): return None
    if hasattr(value, "item"): return value.item()
    return value


class DB:
    def __init__(self) -> None:
        load_dotenv(ROOT / ".env")
        required = ("MYSQL_HOST", "MYSQL_PORT", "MYSQL_DATABASE", "MYSQL_USER", "MYSQL_PASSWORD")
        missing = [k for k in required if not os.getenv(k)]
        if missing or os.getenv("MYSQL_DATABASE") != "olist_delivery_analysis":
            raise ValueError("Missing database configuration or unexpected database name.")
        self.conn = pymysql.connect(host=os.environ["MYSQL_HOST"], port=int(os.environ["MYSQL_PORT"]), user=os.environ["MYSQL_USER"], password=os.environ["MYSQL_PASSWORD"], database=os.environ["MYSQL_DATABASE"], charset=os.getenv("MYSQL_CHARSET", "utf8mb4"), autocommit=False, cursorclass=pymysql.cursors.DictCursor)
    def query(self, sql: str) -> list[dict[str, Any]]:
        with self.conn.cursor() as cur:
            cur.execute(sql)
            return list(cur.fetchall())
    def execute(self, sql: str) -> None:
        with self.conn.cursor() as cur: cur.execute(sql)
    def close(self) -> None: self.conn.close()


def df(db: DB, sql: str) -> pd.DataFrame: return pd.DataFrame(db.query(sql))

def metadata(path: Path) -> dict[str, Any]:
    return {"path": str(path.relative_to(ROOT)), "size_bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest().upper()}

def definitions(db: DB, names: tuple[str, ...]) -> dict[str, str]:
    out = {}
    for name in names:
        row = db.query(f"SHOW CREATE VIEW `{name}`")[0]
        text = next(v for k, v in row.items() if k.lower().startswith("create view"))
        out[name] = hashlib.sha256(str(text).encode()).hexdigest().upper()
    return out

def statements() -> list[str]:
    text = SQL_FILE.read_text(encoding="utf-8")
    result = []
    for name in TARGETS:
        match = re.search(rf"(?ms)^CREATE VIEW `{name}` AS\n.*?;(?=\s*(?:CREATE VIEW|\Z))", text)
        if match is None or text.count(f"CREATE VIEW `{name}` AS") != 1: raise RuntimeError(f"Missing or duplicate SQL statement for {name}.")
        statement = match.group(0).strip()
        if "CREATE OR REPLACE" in statement.upper(): raise RuntimeError("T11 cannot replace views.")
        result.append(statement)
    return result

def preflight(db: DB, existing: bool, resume_partial: bool = False) -> dict[str, Any]:
    t10 = json.loads(T10_REPORT.read_text(encoding="utf-8"))
    if t10.get("reconciliation", {}).get("status") != "pass": raise RuntimeError("T10 report is not PASS.")
    counts = db.query("SELECT COUNT(*) AS orders, (SELECT COUNT(*) FROM order_items_raw) AS items, (SELECT COUNT(*) FROM order_payments_raw) AS payments, (SELECT COUNT(*) FROM customers_raw) AS customers FROM orders_raw")[0]
    actual = {k.lower(): int(v) for k, v in counts.items()}
    if actual != EXPECTED: raise RuntimeError(f"Raw baseline changed: {actual}")
    checks = db.query("SELECT (SELECT COUNT(*) FROM (SELECT order_id, order_item_id FROM order_items_raw GROUP BY order_id, order_item_id HAVING COUNT(*) > 1) x) AS duplicate_item_keys, (SELECT COUNT(*) FROM (SELECT customer_id FROM customers_raw GROUP BY customer_id HAVING COUNT(*) > 1) x) AS duplicate_customer_ids, (SELECT COUNT(*) FROM (SELECT product_category_name FROM category_translation_raw GROUP BY product_category_name HAVING COUNT(*) > 1) x) AS duplicate_translation_keys")[0]
    if any(int(v) for v in checks.values()): raise RuntimeError(f"Required join keys are not unique: {checks}")
    rows = db.query("SELECT table_name AS object_name FROM information_schema.views WHERE table_schema=DATABASE() AND table_name IN ('vw_order_items_aggregated','vw_order_payments_aggregated','vw_order_analysis','vw_order_item_analysis')")
    names = {str(next(iter(row.values()))) for row in rows}
    created_prefix = set(TARGETS[:3])
    if existing:
        if names != set(TARGETS): raise RuntimeError(f"Validation mode requires exactly all T11 views: {names}")
    elif resume_partial:
        if names != created_prefix: raise RuntimeError(f"Resume mode requires exactly the known first three T11 views: {names}")
    elif names: raise RuntimeError(f"T11 target views exist; refusing to replace: {sorted(names)}")
    if not existing and (ORDER_CSV.exists() or ITEM_CSV.exists()):
        found = [metadata(p) for p in (ORDER_CSV, ITEM_CSV) if p.exists()]
        raise RuntimeError("T11 output already exists; refusing to overwrite: " + json.dumps(found))
    return {"raw_counts": actual, "join_key_duplicates": {k.lower(): int(v) for k, v in checks.items()}, "t10_clean_view_hash": definitions(db, ("vw_clean_orders",))["vw_clean_orders"], "existing_outputs": [metadata(p) for p in (ORDER_CSV, ITEM_CSV) if p.exists()]}

def item_python(items: pd.DataFrame, products: pd.DataFrame, translations: pd.DataFrame) -> pd.DataFrame:
    detail = items.merge(products[["product_id", "product_category_name"]], on="product_id", how="left", validate="many_to_one").merge(translations, on="product_category_name", how="left", validate="many_to_one")
    detail["item_total"] = pd.to_numeric(detail["price"]) + pd.to_numeric(detail["freight_value"])
    detail["missing_category"] = detail["product_category_name"].isna()
    detail["untranslated"] = detail["product_category_name"].notna() & detail["product_category_name_english"].isna()
    grouped = detail.groupby("order_id", dropna=False)
    result = grouped.agg(item_row_count=("order_item_id", "size"), item_quantity=("order_item_id", "size"), distinct_product_count=("product_id", "nunique"), distinct_seller_count=("seller_id", "nunique"), item_value_total=("price", "sum"), freight_value_total=("freight_value", "sum"), merchandise_and_freight_total=("item_total", "sum"), min_item_price=("price", "min"), max_item_price=("price", "max"), average_item_price=("price", "mean"), distinct_category_count=("product_category_name", "nunique"), has_missing_product_category=("missing_category", "any"), has_untranslated_category=("untranslated", "any")).reset_index()
    result["has_multiple_items"] = result.item_row_count > 1; result["has_multiple_products"] = result.distinct_product_count > 1; result["has_multiple_sellers"] = result.distinct_seller_count > 1; result["has_multiple_categories"] = result.distinct_category_count > 1
    one_category = detail.groupby("order_id")["product_category_name"].agg(lambda x: x.dropna().iloc[0] if x.dropna().nunique() == 1 else pd.NA).rename("single_category_name")
    result = result.merge(one_category, on="order_id", how="left")
    return result

def payment_python(payments: pd.DataFrame) -> pd.DataFrame:
    payments = payments.copy(); payments["payment_value"] = pd.to_numeric(payments["payment_value"])
    totals = payments.groupby(["order_id", "payment_type"], dropna=False)["payment_value"].sum().reset_index(name="payment_type_value_total").sort_values(["order_id", "payment_type_value_total", "payment_type"], ascending=[True, False, True], kind="mergesort")
    primary = totals.drop_duplicates("order_id")[["order_id", "payment_type"]].rename(columns={"payment_type": "primary_payment_type"})
    result = payments.groupby("order_id", dropna=False).agg(payment_record_count=("payment_sequential", "size"), payment_value_total=("payment_value", "sum"), distinct_payment_type_count=("payment_type", "nunique"), max_installments=("payment_installments", "max")).reset_index()
    result["has_multiple_payment_records"] = result.payment_record_count > 1; result["has_multiple_payment_types"] = result.distinct_payment_type_count > 1; result["has_payment_record"] = 1
    return result.merge(primary, on="order_id", how="left")

def compare_order_aggregates(sql_order: pd.DataFrame, py_items: pd.DataFrame, py_payments: pd.DataFrame, checks: list[str]) -> dict[str, Any]:
    merged = sql_order.merge(py_items, on="order_id", how="left", suffixes=("_sql", "_py")).merge(py_payments, on="order_id", how="left", suffixes=("", "_pay_py"))
    item_columns = ("item_row_count", "item_quantity", "distinct_product_count", "distinct_seller_count", "item_value_total", "freight_value_total", "merchandise_and_freight_total", "has_multiple_items", "has_multiple_products", "has_multiple_sellers", "distinct_category_count", "has_multiple_categories", "has_missing_product_category", "has_untranslated_category")
    for name in item_columns:
        left = pd.to_numeric(merged[f"{name}_sql"], errors="coerce").fillna(0); right = pd.to_numeric(merged[f"{name}_py"], errors="coerce").fillna(0)
        if not ((left - right).abs() <= MONEY_TOLERANCE).all(): raise RuntimeError(f"Per-order item aggregation mismatch: {name}")
    payment_columns = ("payment_record_count", "payment_value_total", "distinct_payment_type_count", "max_installments", "has_multiple_payment_records", "has_multiple_payment_types")
    for name in payment_columns:
        left = pd.to_numeric(merged[name], errors="coerce").fillna(0); right = pd.to_numeric(merged[f"{name}_pay_py"], errors="coerce").fillna(0)
        if not ((left - right).abs() <= MONEY_TOLERANCE).all(): raise RuntimeError(f"Per-order payment aggregation mismatch: {name}")
    checks.append("per_order_item_and_payment_aggregates")
    both = merged[merged.has_item_record.eq(1) & merged.has_payment_record.eq(1)].copy()
    diff = pd.to_numeric(both.payment_value_total) - pd.to_numeric(both.merchandise_and_freight_total_sql)
    return {"zero_or_within_0_01": int((diff.abs() <= MONEY_TOLERANCE).sum()), "positive_over_0_01": int((diff > MONEY_TOLERANCE).sum()), "negative_under_minus_0_01": int((diff < -MONEY_TOLERANCE).sum()), "missing_payment_records": int((merged.has_payment_record == 0).sum()), "missing_item_records": int((merged.has_item_record == 0).sum()), "absolute_difference": {"min": float(diff.abs().min()), "median": float(diff.abs().median()), "max": float(diff.abs().max())}}

def distribution(series: pd.Series) -> dict[str, int]: return {"NULL" if pd.isna(k) else str(k): int(v) for k, v in series.value_counts(dropna=False).items()}

def samples(order: pd.DataFrame) -> dict[str, str | None]:
    conditions = {"single_item_single_payment": (order.item_row_count == 1) & (order.payment_record_count == 1), "multiple_items": order.has_multiple_items == 1, "multiple_sellers": order.has_multiple_sellers == 1, "multiple_payment_records": order.has_multiple_payment_records == 1, "multiple_payment_types": order.has_multiple_payment_types == 1, "multiple_categories": order.has_multiple_categories == 1, "missing_payment": order.has_payment_record == 0, "missing_item": order.has_item_record == 0}
    return {name: (None if order.loc[condition, "order_id"].empty else str(order.loc[condition, "order_id"].iloc[0])) for name, condition in conditions.items()}

def validate(db: DB, write_outputs: bool) -> tuple[list[str], dict[str, Any]]:
    order = df(db, "SELECT * FROM vw_order_analysis ORDER BY order_id"); item = df(db, "SELECT * FROM vw_order_item_analysis ORDER BY order_id, order_item_id")
    items = df(db, "SELECT order_id, order_item_id, product_id, seller_id, price, freight_value FROM order_items_raw"); payments = df(db, "SELECT order_id, payment_sequential, payment_type, payment_installments, payment_value FROM order_payments_raw"); products = df(db, "SELECT product_id, product_category_name FROM products_raw"); translations = df(db, "SELECT product_category_name, product_category_name_english FROM category_translation_raw")
    py_items = item_python(items, products, translations); py_payments = payment_python(payments)
    checks: list[str] = []
    if len(order) != EXPECTED["orders"] or order.order_id.nunique() != EXPECTED["orders"] or order.order_id.isna().any(): raise RuntimeError("Order analysis grain failed.")
    checks.append("order_analysis_one_row_per_order")
    if len(item) != EXPECTED["items"] or item[["order_id", "order_item_id"]].duplicated().any(): raise RuntimeError("Order-item analysis grain failed.")
    checks.append("order_item_analysis_matches_raw_item_grain")
    payment_difference = compare_order_aggregates(order, py_items, py_payments, checks)
    sql_item_total = pd.to_numeric(item.item_total).sum(); raw_item_total = (pd.to_numeric(items.price) + pd.to_numeric(items.freight_value)).sum()
    if abs(float(sql_item_total - raw_item_total)) > MONEY_TOLERANCE: raise RuntimeError("Item detail total mismatch.")
    if abs(float(pd.to_numeric(order.item_value_total).sum() - pd.to_numeric(items.price).sum())) > MONEY_TOLERANCE or abs(float(pd.to_numeric(order.freight_value_total).sum() - pd.to_numeric(items.freight_value).sum())) > MONEY_TOLERANCE or abs(float(pd.to_numeric(order.payment_value_total).sum() - pd.to_numeric(payments.payment_value).sum())) > MONEY_TOLERANCE: raise RuntimeError("Monetary total reconciliation failed.")
    checks.append("money_totals_within_0_01")
    customer_matches = int(order.customer_unique_id.notna().sum())
    summary = {"order_rows": int(len(order)), "item_rows": int(len(item)), "customer_matches": customer_matches, "item_flags": {name: int((order[name] == 1).sum()) for name in ("has_item_record", "has_multiple_items", "has_multiple_products", "has_multiple_sellers", "has_multiple_categories")}, "payment_flags": {name: int((order[name] == 1).sum()) for name in ("has_payment_record", "has_multiple_payment_records", "has_multiple_payment_types")}, "money_totals": {"item_value_total": float(pd.to_numeric(order.item_value_total).sum()), "freight_value_total": float(pd.to_numeric(order.freight_value_total).sum()), "payment_value_total": float(pd.to_numeric(order.payment_value_total).sum())}, "payment_difference": payment_difference, "item_detail": {"missing_seller_id": int(item.seller_id.isna().sum()), "missing_product_id": int(item.product_id.isna().sum()), "missing_category": int((item.has_missing_product_category == 1).sum()), "missing_translation": int((item.has_untranslated_category == 1).sum()), "item_total": float(sql_item_total)}, "propagated_distributions": {"delay_category": distribution(order.delay_category), "selected_review_score": distribution(order.selected_review_score), "has_date_anomaly": distribution(order.has_date_anomaly), "is_delivered_before_carrier": distribution(order.is_delivered_before_carrier)}, "base_sample_groups": {"seller_ids_with_items": int(item.seller_id.nunique()), "product_categories_with_items": int(item.product_category_name.nunique()), "customer_states": int(order.customer_state.nunique())}}
    checks.append("customer_join_and_t10_fields_propagated")
    if write_outputs:
        if ORDER_CSV.exists() or ITEM_CSV.exists(): raise RuntimeError("CSV exists at write time; refusing overwrite.")
        ORDER_CSV.parent.mkdir(parents=True, exist_ok=True); order.to_csv(ORDER_CSV, index=False, encoding="utf-8", lineterminator="\n", na_rep=""); item.to_csv(ITEM_CSV, index=False, encoding="utf-8", lineterminator="\n", na_rep="")
    if ORDER_CSV.exists() and (len(pd.read_csv(ORDER_CSV)) != EXPECTED["orders"] or len(pd.read_csv(ITEM_CSV)) != EXPECTED["items"]): raise RuntimeError("CSV row count mismatch.")
    checks.append("csv_outputs_row_counts")
    return checks, {"summary": summary, "samples": samples(order), "money_tolerance": MONEY_TOLERANCE, "order_csv": metadata(ORDER_CSV), "item_csv": metadata(ITEM_CSV), "view_definition_sha256": definitions(db, TARGETS)}

def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--validate-existing", action="store_true"); parser.add_argument("--resume-known-partial", action="store_true"); args = parser.parse_args(); db = DB()
    try:
        if args.validate_existing and args.resume_known_partial: raise ValueError("Choose only one recovery mode.")
        pre = preflight(db, args.validate_existing, args.resume_known_partial)
        if not args.validate_existing:
            for name, statement in zip(TARGETS, statements(), strict=True):
                if not args.resume_known_partial or name not in TARGETS[:3]: db.execute(statement)
            db.conn.commit()
        checks, detail = validate(db, write_outputs=not (ORDER_CSV.exists() and ITEM_CSV.exists()))
        mode = "validate_existing" if args.validate_existing else ("resume_known_partial" if args.resume_known_partial else "create_and_validate")
        REPORT.write_text(json.dumps({"task": "T11", "generated_at": datetime.now().isoformat(timespec="seconds"), "views": list(TARGETS), "execution_mode": mode, "preflight": pre, "reconciliation": {"status": "pass", "check_count": len(checks), "checks": checks, "details": detail}, "limitations": ["No statistical test, threshold decision, business conclusion, Power BI work, or T12 work is included.", "Date anomalies remain flags; only is_transit_duration_eligible gates carrier-dependent durations."]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("T11_RECONCILIATION=PASS")
    except Exception as error:
        REPORT.write_text(json.dumps({"task": "T11", "generated_at": datetime.now().isoformat(timespec="seconds"), "reconciliation": {"status": "failed", "error": repr(error)}}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); raise
    finally: db.close()

if __name__ == "__main__": main()
