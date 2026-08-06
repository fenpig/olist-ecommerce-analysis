"""Create and validate the T09 deterministic order-level review-selection views.

Run from the project root after T08:
    .\\.venv\\Scripts\\python.exe src\\03_validate_review_selection.py

After the three authorized views have been created, the explicit
--validate-existing mode performs only the read-only reconciliation and refuses
any partial or unexpected target-view set.

This task creates only vw_review_ranked, vw_order_review_audit, and
vw_order_review_selected. Raw review data is read but never changed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import pymysql
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SQL_FILE = PROJECT_ROOT / "sql" / "03_create_clean_views.sql"
REPORT_FILE = PROJECT_ROOT / "reports" / "validation" / "t09_review_selection_summary.json"
DATABASE_NAME = "olist_delivery_analysis"
TARGET_VIEWS = ("vw_review_ranked", "vw_order_review_audit", "vw_order_review_selected")
EXPECTED_MULTI_REVIEW_ORDERS = 547
EXPECTED_CONFLICTING_REVIEW_ORDERS = 202


def clean(value: Any) -> Any:
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

    def query(self, statement: str, params: Iterable[Any] | None = None) -> list[dict[str, Any]]:
        with self.connection.cursor() as cursor:
            if params is None:
                cursor.execute(statement)
            else:
                cursor.execute(statement, tuple(params))
            return list(cursor.fetchall())

    def execute(self, statement: str) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(statement)

    def close(self) -> None:
        self.connection.close()


def dataframe(db: Database, statement: str) -> pd.DataFrame:
    return pd.DataFrame(db.query(statement))


def script_statements() -> list[str]:
    without_comments = "\n".join(line for line in SQL_FILE.read_text(encoding="utf-8").splitlines() if not line.lstrip().startswith("--"))
    statements = [part.strip() for part in without_comments.split(";") if part.strip()]
    if len(statements) != 3:
        raise RuntimeError("T09 SQL must define exactly the three authorized views.")
    expected_prefixes = tuple(f"CREATE VIEW `{name}` AS" for name in TARGET_VIEWS)
    for statement, prefix in zip(statements, expected_prefixes, strict=True):
        if not statement.startswith(prefix):
            raise RuntimeError("T09 SQL contains an unauthorized or out-of-order database statement.")
    return statements


def scalar(db: Database, statement: str) -> dict[str, Any]:
    rows = db.query(statement)
    if len(rows) != 1:
        raise RuntimeError("Expected one SQL result row.")
    return {key: clean(value) for key, value in rows[0].items()}


def preflight(db: Database, *, validate_existing: bool = False) -> None:
    baseline = scalar(db, "SELECT COUNT(*) AS review_rows, COUNT(DISTINCT order_id) AS review_orders FROM order_reviews_raw")
    if baseline != {"review_rows": 99224, "review_orders": 98673}:
        raise RuntimeError(f"T08 review baseline changed: {baseline}")
    audit = scalar(db, "SELECT SUM(review_count > 1) AS multi_review_orders, SUM(score_count > 1) AS conflicting_review_orders FROM (SELECT order_id, COUNT(*) AS review_count, COUNT(DISTINCT CASE WHEN review_score BETWEEN 1 AND 5 THEN review_score END) AS score_count FROM order_reviews_raw GROUP BY order_id) a")
    if audit != {"multi_review_orders": EXPECTED_MULTI_REVIEW_ORDERS, "conflicting_review_orders": EXPECTED_CONFLICTING_REVIEW_ORDERS}:
        raise RuntimeError(f"T08 multi-review baseline changed: {audit}")
    existing = db.query("SELECT table_name AS object_name FROM information_schema.views WHERE table_schema = DATABASE() AND table_name IN (%s, %s, %s)", TARGET_VIEWS)
    existing_names = {str(next(iter(row.values()))) for row in existing}
    if validate_existing:
        if existing_names != set(TARGET_VIEWS):
            raise RuntimeError(
                "Validation-only mode requires exactly the three T09 views to exist; found: "
                + ", ".join(sorted(existing_names))
            )
    elif existing_names:
        raise RuntimeError(
            "T09 target view already exists; refusing to replace it: "
            + ", ".join(sorted(existing_names))
        )
    unstable = scalar(db, "SELECT COUNT(*) AS unstable_final_ties FROM (SELECT order_id, review_answer_timestamp, review_creation_date, review_id FROM order_reviews_raw WHERE review_score BETWEEN 1 AND 5 GROUP BY order_id, review_answer_timestamp, review_creation_date, review_id HAVING COUNT(*) > 1 AND COUNT(DISTINCT review_score) > 1) t")
    if unstable["unstable_final_ties"] != 0:
        raise RuntimeError("review_id cannot deterministically resolve conflicting final ties; stop for a new decision.")


def python_selection(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = raw.copy()
    raw["review_creation_date"] = pd.to_datetime(raw["review_creation_date"], errors="coerce")
    raw["review_answer_timestamp"] = pd.to_datetime(raw["review_answer_timestamp"], errors="coerce")
    raw["_is_valid_score"] = raw["review_score"].between(1, 5)
    raw["_valid_review_score"] = raw["review_score"].where(raw["_is_valid_score"])
    raw["_time_field_missing"] = raw["review_answer_timestamp"].isna() | raw["review_creation_date"].isna()
    audit = raw.groupby("order_id", dropna=False).agg(
        review_record_count=("review_row_id", "size"),
        valid_review_record_count=("_is_valid_score", "sum"),
        distinct_valid_score_count=("_valid_review_score", "nunique"),
        minimum_review_score=("_valid_review_score", "min"),
        maximum_review_score=("_valid_review_score", "max"),
        has_time_field_missing=("_time_field_missing", "any"),
    ).reset_index()
    audit["invalid_or_missing_score_count"] = audit["review_record_count"] - audit["valid_review_record_count"]
    audit["has_multiple_reviews"] = audit["review_record_count"] > 1
    audit["has_conflicting_review_scores"] = audit["distinct_valid_score_count"] > 1

    valid = raw.loc[raw["review_score"].between(1, 5)].copy()
    valid["answer_tie_count"] = valid.groupby(["order_id", "review_answer_timestamp"], dropna=False)["review_row_id"].transform("size")
    valid["creation_tie_count"] = valid.groupby(["order_id", "review_answer_timestamp", "review_creation_date"], dropna=False)["review_row_id"].transform("size")
    valid = valid.sort_values(
        ["order_id", "review_answer_timestamp", "review_creation_date", "review_id", "review_row_id"],
        ascending=[True, False, False, False, False],
        na_position="last",
        kind="mergesort",
    )
    valid["review_rank"] = valid.groupby("order_id").cumcount() + 1
    selected = valid.loc[valid["review_rank"] == 1].merge(audit, on="order_id", how="left")
    selected["selection_basis"] = "review_id_tiebreaker"
    selected.loc[selected["review_record_count"] == 1, "selection_basis"] = "single_review"
    selected.loc[(selected["review_record_count"] > 1) & selected["review_answer_timestamp"].notna() & (selected["answer_tie_count"] == 1), "selection_basis"] = "latest_answer_timestamp"
    selected.loc[(selected["review_record_count"] > 1) & (selected["answer_tie_count"] > 1) & (selected["creation_tie_count"] == 1), "selection_basis"] = "latest_creation_date"
    audit = audit.merge(selected[["order_id", "review_id", "review_score", "review_creation_date", "review_answer_timestamp", "selection_basis"]], on="order_id", how="left")
    audit = audit.rename(columns={"review_id": "latest_review_id", "review_score": "latest_review_score", "review_creation_date": "latest_review_creation_date", "review_answer_timestamp": "latest_review_answer_timestamp"})
    return selected, audit


def score_group(series: pd.Series) -> pd.Series:
    return pd.Series(pd.cut(series, bins=[0, 2, 3, 5], labels=["low", "neutral", "high"], include_lowest=True), index=series.index).astype("object")


def assert_equal(expected: Any, actual: Any, name: str, checks: list[str]) -> None:
    if expected != actual:
        raise RuntimeError(f"SQL/Python mismatch for {name}: SQL={actual}; Python={expected}")
    checks.append(name)


def validation(db: Database, raw: pd.DataFrame) -> tuple[list[str], dict[str, Any]]:
    selected_python, audit_python = python_selection(raw)
    selected_sql = dataframe(db, "SELECT order_id, selected_review_id, selected_review_score, selection_basis, minimum_review_score, latest_review_group, minimum_review_group, latest_is_low_review, minimum_is_low_review FROM vw_order_review_selected")
    audit_sql = dataframe(db, "SELECT order_id, review_record_count, valid_review_record_count, invalid_or_missing_score_count, distinct_valid_score_count, latest_review_id, latest_review_score, minimum_review_score, latest_review_group, minimum_review_group, has_multiple_reviews, has_conflicting_review_scores, has_time_field_missing, requires_review_id_tiebreaker, has_no_valid_order_review, selection_basis FROM vw_order_review_audit")
    checks: list[str] = []
    detail: dict[str, Any] = {}

    python_counts = {"raw_review_rows": int(len(raw)), "review_orders": int(raw["order_id"].nunique()), "single_review_orders": int((audit_python["review_record_count"] == 1).sum()), "multi_review_orders": int((audit_python["review_record_count"] > 1).sum()), "conflicting_review_orders": int((audit_python["distinct_valid_score_count"] > 1).sum()), "no_valid_score_orders": int((audit_python["valid_review_record_count"] == 0).sum())}
    sql_counts = {
        "raw_review_rows": int(len(raw)),
        "review_orders": int(len(audit_sql)),
        "single_review_orders": int((audit_sql["review_record_count"] == 1).sum()),
        "multi_review_orders": int((audit_sql["review_record_count"] > 1).sum()),
        "conflicting_review_orders": int(audit_sql["has_conflicting_review_scores"].astype(bool).sum()),
        "no_valid_score_orders": int(audit_sql["has_no_valid_order_review"].astype(bool).sum()),
    }
    assert_equal(python_counts, sql_counts, "review_population_and_conflicts", checks)

    python_basis = {str(key): int(value) for key, value in selected_python["selection_basis"].value_counts().sort_index().items()}
    sql_basis = {str(key): int(value) for key, value in selected_sql["selection_basis"].value_counts().sort_index().items()}
    assert_equal(python_basis, sql_basis, "selection_basis_distribution", checks)

    python_latest_scores = {str(int(key)): int(value) for key, value in selected_python["review_score"].value_counts().sort_index().items()}
    python_minimum_scores = {str(int(key)): int(value) for key, value in audit_python["minimum_review_score"].dropna().value_counts().sort_index().items()}
    sql_latest_scores = {str(int(key)): int(value) for key, value in selected_sql["selected_review_score"].value_counts().sort_index().items()}
    sql_minimum_scores = {str(int(key)): int(value) for key, value in audit_sql["minimum_review_score"].dropna().value_counts().sort_index().items()}
    assert_equal(python_latest_scores, sql_latest_scores, "latest_score_distribution", checks)
    assert_equal(python_minimum_scores, sql_minimum_scores, "minimum_score_distribution", checks)

    python_diff_score = int((audit_python["latest_review_score"] != audit_python["minimum_review_score"]).sum())
    python_diff_group = int((score_group(audit_python["latest_review_score"]) != score_group(audit_python["minimum_review_score"])).sum())
    python_review_id = int((selected_python["selection_basis"] == "review_id_tiebreaker").sum())
    sql_difference = {
        "different_score_orders": int((audit_sql["latest_review_score"] != audit_sql["minimum_review_score"]).sum()),
        "different_group_orders": int((audit_sql["latest_review_group"] != audit_sql["minimum_review_group"]).sum()),
        "review_id_tiebreaker_orders": int(audit_sql["requires_review_id_tiebreaker"].astype(bool).sum()),
    }
    assert_equal({"different_score_orders": python_diff_score, "different_group_orders": python_diff_group, "review_id_tiebreaker_orders": python_review_id}, sql_difference, "latest_vs_minimum_difference", checks)

    compare = selected_python[["order_id", "review_id", "review_score", "selection_basis"]].merge(selected_sql[["order_id", "selected_review_id", "selected_review_score", "selection_basis"]], on="order_id", how="outer", suffixes=("_python", "_sql"), indicator=True)
    mismatch = int(((compare["_merge"] != "both") | (compare["review_id"] != compare["selected_review_id"]) | (compare["review_score"] != compare["selected_review_score"]) | (compare["selection_basis_python"] != compare["selection_basis_sql"])).sum())
    assert_equal(0, mismatch, "per_order_selected_id_score_and_basis", checks)

    selected_source = selected_sql[["order_id", "selected_review_id"]].merge(
        raw[["order_id", "review_id"]].drop_duplicates(),
        left_on=["order_id", "selected_review_id"],
        right_on=["order_id", "review_id"],
        how="left",
        indicator=True,
    )
    duplicate_orders = selected_sql.loc[
        selected_sql["order_id"].duplicated(keep=False), "order_id"
    ].nunique()
    view_checks = {
        "duplicate_selected_orders": int(duplicate_orders),
        "selected_review_not_in_raw": int((selected_source["_merge"] != "both").sum()),
        "invalid_selected_scores": int((~selected_sql["selected_review_score"].between(1, 5)).sum()),
        "selected_orders": int(len(selected_sql)),
        "raw_review_orders": int(raw["order_id"].nunique()),
    }
    if view_checks["duplicate_selected_orders"] or view_checks["selected_review_not_in_raw"] or view_checks["invalid_selected_scores"] or view_checks["selected_orders"] > view_checks["raw_review_orders"]:
        raise RuntimeError(f"View validation failed: {view_checks}")
    checks.append("selected_view_uniqueness_and_source_validity")

    second_run = dataframe(db, "SELECT order_id, selected_review_id, selected_review_score, selection_basis FROM vw_order_review_selected ORDER BY order_id")
    first_run = selected_sql[["order_id", "selected_review_id", "selected_review_score", "selection_basis"]].sort_values("order_id").reset_index(drop=True)
    if not first_run.equals(second_run.reset_index(drop=True)):
        raise RuntimeError("Repeated view query produced a different selection result.")
    checks.append("repeated_view_query_stability")

    definitions = {}
    for view_name in TARGET_VIEWS:
        row = db.query(f"SHOW CREATE VIEW `{view_name}`")[0]
        definition = next(value for key, value in row.items() if key.lower().startswith("create view"))
        definitions[view_name] = hashlib.sha256(str(definition).encode("utf-8")).hexdigest().upper()

    detail.update({"population": sql_counts, "selection_basis_distribution": sql_basis, "latest_score_distribution": sql_latest_scores, "minimum_score_distribution": sql_minimum_scores, "latest_vs_minimum": sql_difference, "view_validation": view_checks, "view_definition_sha256": definitions})
    return checks, detail


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--validate-existing",
        action="store_true",
        help="Run only the read-only reconciliation for exactly the three existing T09 views.",
    )
    args = parser.parse_args()
    db = Database()
    try:
        preflight(db, validate_existing=args.validate_existing)
        if not args.validate_existing:
            for statement in script_statements():
                db.execute(statement)
            db.connection.commit()
        raw = dataframe(db, "SELECT review_row_id, order_id, review_id, review_score, review_creation_date, review_answer_timestamp FROM order_reviews_raw")
        checks, detail = validation(db, raw)
        report = {"task": "T09", "generated_at": datetime.now().isoformat(timespec="seconds"), "views_created": list(TARGET_VIEWS), "rule": "latest valid review by answer timestamp, creation date, then review_id", "reconciliation": {"status": "pass", "check_count": len(checks), "checks": checks, "details": detail}, "limitations": ["No delivery, geography, category, seller, or order-analysis data was joined.", "Minimum review score is recorded only for later sensitivity analysis.", "No claim is made that either review-selection rule is more accurate or causal."]}
        REPORT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("T09_VIEWS_CREATED=" + ",".join(TARGET_VIEWS))
        print("T09_RECONCILIATION_CHECKS=" + str(len(checks)))
        print("T09_RECONCILIATION=PASS")
        print("T09_REPORT=" + str(REPORT_FILE.relative_to(PROJECT_ROOT)))
    except Exception as error:
        REPORT_FILE.write_text(
            json.dumps(
                {
                    "task": "T09",
                    "generated_at": datetime.now().isoformat(timespec="seconds"),
                    "reconciliation": {"status": "failed", "error": repr(error)},
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
