-- Olist core business analysis (MySQL 8.0+).
-- Run src/03_load_to_mysql.py and sql/01_schema.sql first.
USE olist_analysis;

-- Q1. Monthly GMV, delivered orders, average order value and month-over-month growth.
WITH order_value AS (
    SELECT
        o.order_id,
        DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m-01') AS order_month,
        SUM(oi.price + oi.freight_value) AS gmv
    FROM orders_raw AS o
    JOIN order_items_raw AS oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY o.order_id, DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m-01')
), monthly AS (
    SELECT
        order_month,
        COUNT(*) AS delivered_orders,
        ROUND(SUM(gmv), 2) AS gmv,
        ROUND(AVG(gmv), 2) AS avg_order_value
    FROM order_value
    GROUP BY order_month
)
SELECT
    order_month,
    delivered_orders,
    gmv,
    avg_order_value,
    ROUND(100 * (gmv - LAG(gmv) OVER (ORDER BY order_month)) /
        NULLIF(LAG(gmv) OVER (ORDER BY order_month), 0), 2) AS gmv_mom_pct
FROM monthly
ORDER BY order_month;

-- Q2. Product category contribution. Revenue uses item price + freight, not payment rows.
SELECT
    COALESCE(t.product_category_name_english, 'unknown') AS product_category,
    COUNT(DISTINCT o.order_id) AS delivered_orders,
    ROUND(SUM(oi.price + oi.freight_value), 2) AS gmv,
    ROUND(AVG(oi.price + oi.freight_value), 2) AS avg_item_value,
    ROUND(AVG(r.review_score), 2) AS avg_review_score
FROM orders_raw AS o
JOIN order_items_raw AS oi ON o.order_id = oi.order_id
LEFT JOIN products_raw AS p ON oi.product_id = p.product_id
LEFT JOIN category_translation_raw AS t ON p.product_category_name = t.product_category_name
LEFT JOIN order_reviews_raw AS r ON o.order_id = r.order_id
WHERE o.order_status = 'delivered'
GROUP BY COALESCE(t.product_category_name_english, 'unknown')
ORDER BY gmv DESC;

-- Q3. RFM customer segmentation using the real customer identifier.
WITH customer_rfm AS (
    SELECT
        c.customer_unique_id,
        MAX(o.order_purchase_timestamp) AS last_purchase_at,
        COUNT(DISTINCT o.order_id) AS frequency,
        SUM(oi.price + oi.freight_value) AS monetary
    FROM customers_raw AS c
    JOIN orders_raw AS o ON c.customer_id = o.customer_id
    JOIN order_items_raw AS oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id
), scored AS (
    SELECT
        customer_unique_id,
        DATEDIFF((SELECT DATE_ADD(MAX(order_purchase_timestamp), INTERVAL 1 DAY) FROM orders_raw), last_purchase_at) AS recency_days,
        frequency,
        ROUND(monetary, 2) AS monetary,
        NTILE(5) OVER (ORDER BY last_purchase_at DESC) AS r_score,
        NTILE(5) OVER (ORDER BY frequency) AS f_score,
        NTILE(5) OVER (ORDER BY monetary) AS m_score
    FROM customer_rfm
)
SELECT
    customer_unique_id,
    recency_days,
    frequency,
    monetary,
    CONCAT(r_score, f_score, m_score) AS rfm_score,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'champion'
        WHEN r_score >= 3 AND f_score >= 3 THEN 'loyal'
        WHEN r_score <= 2 AND f_score >= 3 THEN 'at_risk'
        ELSE 'other'
    END AS customer_segment
FROM scored
ORDER BY monetary DESC;

-- Q4. Delivery experience. Only actually delivered orders enter the denominator.
SELECT
    CASE
        WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 'late'
        ELSE 'on_time'
    END AS delivery_status,
    COUNT(DISTINCT o.order_id) AS delivered_orders,
    ROUND(AVG(DATEDIFF(o.order_delivered_customer_date, o.order_purchase_timestamp)), 2) AS avg_delivery_days,
    ROUND(AVG(r.review_score), 2) AS avg_review_score,
    ROUND(100 * AVG(r.review_score <= 2), 2) AS low_score_rate_pct
FROM orders_raw AS o
LEFT JOIN order_reviews_raw AS r ON o.order_id = r.order_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
  AND o.order_estimated_delivery_date IS NOT NULL
GROUP BY delivery_status;
