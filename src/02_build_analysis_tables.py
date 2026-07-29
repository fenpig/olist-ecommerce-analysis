"""第二阶段：将 Olist 原始表构造成订单级和订单明细级分析表。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_DIR / "data" / "raw"
OUTPUT_DIR = PROJECT_DIR / "data" / "processed"
DATE_COLUMNS = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]


def read_csv(filename: str, **kwargs: object) -> pd.DataFrame:
    return pd.read_csv(RAW_DIR / filename, **kwargs)


def build_order_fact() -> pd.DataFrame:
    orders = read_csv("olist_orders_dataset.csv", parse_dates=DATE_COLUMNS)
    customers = read_csv("olist_customers_dataset.csv")
    items = read_csv("olist_order_items_dataset.csv")
    payments = read_csv("olist_order_payments_dataset.csv")
    reviews = read_csv("olist_order_reviews_dataset.csv")

    # 一张订单可能有多项商品或多笔支付。先汇总到订单粒度，避免 merge 后金额被放大。
    item_summary = (
        items.groupby("order_id", as_index=False)
        .agg(
            item_count=("order_item_id", "count"),
            product_count=("product_id", "nunique"),
            item_price=("price", "sum"),
            freight_value=("freight_value", "sum"),
        )
    )
    item_summary["gmv"] = item_summary["item_price"] + item_summary["freight_value"]

    payment_summary = (
        payments.groupby("order_id", as_index=False)
        .agg(
            payment_value=("payment_value", "sum"),
            payment_installments=("payment_installments", "max"),
            payment_record_count=("payment_sequential", "count"),
        )
    )
    review_summary = (
        reviews.groupby("order_id", as_index=False)
        .agg(review_score=("review_score", "mean"), review_count=("review_id", "count"))
    )

    order_fact = (
        orders.merge(customers, on="customer_id", how="left", validate="many_to_one")
        .merge(item_summary, on="order_id", how="left", validate="one_to_one")
        .merge(payment_summary, on="order_id", how="left", validate="one_to_one")
        .merge(review_summary, on="order_id", how="left", validate="one_to_one")
    )

    order_fact["purchase_month"] = order_fact["order_purchase_timestamp"].dt.to_period("M").astype(str)
    order_fact["purchase_year"] = order_fact["order_purchase_timestamp"].dt.year
    order_fact["is_delivered"] = order_fact["order_status"].eq("delivered")
    order_fact["delivery_days"] = (
        order_fact["order_delivered_customer_date"] - order_fact["order_purchase_timestamp"]
    ).dt.total_seconds() / 86_400
    # 未交付或缺少实际/预计交付日的订单无法判断是否延迟，必须保留为未知值，
    # 而不是错误地归类为“准时”。
    order_fact["is_late_delivery"] = pd.Series(pd.NA, index=order_fact.index, dtype="boolean")
    delivery_comparable = (
        order_fact["is_delivered"]
        & order_fact["order_delivered_customer_date"].notna()
        & order_fact["order_estimated_delivery_date"].notna()
    )
    order_fact.loc[delivery_comparable, "is_late_delivery"] = (
        order_fact.loc[delivery_comparable, "order_delivered_customer_date"]
        > order_fact.loc[delivery_comparable, "order_estimated_delivery_date"]
    )
    return order_fact


def build_order_item_fact(order_fact: pd.DataFrame) -> pd.DataFrame:
    items = read_csv("olist_order_items_dataset.csv")
    products = read_csv("olist_products_dataset.csv")
    translations = read_csv("product_category_name_translation.csv")

    product_dim = products.merge(
        translations, on="product_category_name", how="left", validate="many_to_one"
    )
    order_columns = [
        "order_id",
        "customer_unique_id",
        "customer_state",
        "order_status",
        "order_purchase_timestamp",
        "purchase_month",
        "is_delivered",
        "delivery_days",
        "is_late_delivery",
        "review_score",
    ]
    return (
        items.merge(product_dim, on="product_id", how="left", validate="many_to_one")
        .merge(order_fact[order_columns], on="order_id", how="left", validate="many_to_one")
        .rename(columns={"product_category_name_english": "product_category_english"})
    )


def build_rfm(order_fact: pd.DataFrame) -> pd.DataFrame:
    delivered = order_fact.loc[order_fact["is_delivered"]].copy()
    reference_date = delivered["order_purchase_timestamp"].max().normalize() + pd.Timedelta(days=1)
    rfm = (
        delivered.groupby("customer_unique_id", as_index=False)
        .agg(
            last_purchase=("order_purchase_timestamp", "max"),
            frequency=("order_id", "nunique"),
            monetary=("gmv", "sum"),
        )
    )
    rfm["recency_days"] = (reference_date - rfm["last_purchase"].dt.normalize()).dt.days
    return rfm[["customer_unique_id", "recency_days", "frequency", "monetary"]]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    order_fact = build_order_fact()
    order_item_fact = build_order_item_fact(order_fact)
    rfm = build_rfm(order_fact)

    order_fact.to_csv(OUTPUT_DIR / "order_fact.csv", index=False)
    order_item_fact.to_csv(OUTPUT_DIR / "order_item_fact.csv", index=False)
    rfm.to_csv(OUTPUT_DIR / "rfm_customers.csv", index=False)

    print(f"order_fact: {len(order_fact):,} rows")
    print(f"order_item_fact: {len(order_item_fact):,} rows")
    print(f"rfm_customers: {len(rfm):,} rows")
    print(f"delivered orders: {order_fact['is_delivered'].sum():,}")


if __name__ == "__main__":
    main()
