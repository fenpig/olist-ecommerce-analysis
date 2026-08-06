"""第一阶段：对 Olist 原始数据进行可复现的数据质量检查。

运行方式（在项目根目录）：
    python src/01_data_quality.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_DIR / "data" / "raw"
OUTPUT_DIR = PROJECT_DIR / "data" / "processed"

DATASETS = {
    "customers": ("olist_customers_dataset.csv", "customer_id"),
    "orders": ("olist_orders_dataset.csv", "order_id"),
    "order_items": ("olist_order_items_dataset.csv", None),
    "payments": ("olist_order_payments_dataset.csv", None),
    "reviews": ("olist_order_reviews_dataset.csv", "review_id"),
    "products": ("olist_products_dataset.csv", "product_id"),
    "category_translation": ("product_category_name_translation.csv", "product_category_name"),
}


def load_data() -> dict[str, pd.DataFrame]:
    """读取全部原始 CSV；缺失文件立即报错，避免静默得到不完整分析。"""
    frames: dict[str, pd.DataFrame] = {}
    for name, (filename, _) in DATASETS.items():
        path = RAW_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"找不到 {path}")
        frames[name] = pd.read_csv(path)
    return frames


def profile_tables(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """输出每张表的行数、列数、重复行和主键空值。"""
    records = []
    for name, frame in frames.items():
        _, primary_key = DATASETS[name]
        records.append(
            {
                "table_name": name,
                "rows": len(frame),
                "columns": len(frame.columns),
                "duplicate_rows": int(frame.duplicated().sum()),
                "primary_key": primary_key or "composite / none",
                "primary_key_nulls": int(frame[primary_key].isna().sum()) if primary_key else pd.NA,
                "primary_key_duplicates": int(frame[primary_key].duplicated().sum()) if primary_key else pd.NA,
                "missing_cells": int(frame.isna().sum().sum()),
            }
        )
    return pd.DataFrame(records)


def profile_missing_values(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """仅保留确实有缺失值的字段，方便优先处理。"""
    records = []
    for name, frame in frames.items():
        for column, missing_count in frame.isna().sum().items():
            if missing_count:
                records.append(
                    {
                        "table_name": name,
                        "column_name": column,
                        "missing_count": int(missing_count),
                        "missing_rate": round(missing_count / len(frame), 4),
                    }
                )
    return pd.DataFrame(records).sort_values(["missing_rate", "table_name"], ascending=[False, True])


def profile_relationships(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """检查关联完整性；目标是找出无法关联到订单、客户或商品的事实记录。"""
    checks = [
        ("orders -> customers", frames["orders"]["customer_id"], frames["customers"]["customer_id"]),
        ("order_items -> orders", frames["order_items"]["order_id"], frames["orders"]["order_id"]),
        ("payments -> orders", frames["payments"]["order_id"], frames["orders"]["order_id"]),
        ("reviews -> orders", frames["reviews"]["order_id"], frames["orders"]["order_id"]),
        ("order_items -> products", frames["order_items"]["product_id"], frames["products"]["product_id"]),
    ]
    records = []
    for relationship, foreign_keys, parent_keys in checks:
        orphan_count = int((~foreign_keys.isin(parent_keys)).sum())
        records.append(
            {
                "relationship": relationship,
                "child_rows": len(foreign_keys),
                "orphan_rows": orphan_count,
                "orphan_rate": round(orphan_count / len(foreign_keys), 6),
            }
        )
    return pd.DataFrame(records)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    frames = load_data()

    tables = profile_tables(frames)
    missing = profile_missing_values(frames)
    relationships = profile_relationships(frames)

    tables.to_csv(OUTPUT_DIR / "data_quality_tables.csv", index=False)
    missing.to_csv(OUTPUT_DIR / "data_quality_missing_values.csv", index=False)
    relationships.to_csv(OUTPUT_DIR / "data_quality_relationships.csv", index=False)

    print("\n=== 表概况 ===")
    print(tables.to_string(index=False))
    print("\n=== 关联完整性 ===")
    print(relationships.to_string(index=False))
    print("\n已生成 data/processed/ 下的三份质量检查报告。")


if __name__ == "__main__":
    main()
