-- File: 02_data_quality_checks.sql
-- Goal: Read-only, reproducible quality checks for the T07 raw layer.
-- Input objects: The seven raw tables loaded in T07.
-- Output objects: Result sets only; no tables, views, or persistent objects are created.
-- Prerequisites: MySQL 8.0.44 and `olist_delivery_analysis` populated by T07.
-- Repeatable: Yes. Every statement is SELECT, SHOW, DESCRIBE, or EXPLAIN.
-- Implementation task: T08.
-- Current status: implemented and verified in T08.
-- Safety: Do not add DDL/DML. Run in a read-only transaction or through src/02_validate_raw_data.py.

-- Schema and row-count inventory.
SHOW TABLES;
DESCRIBE `customers_raw`;
DESCRIBE `orders_raw`;
DESCRIBE `order_items_raw`;
DESCRIBE `order_payments_raw`;
DESCRIBE `order_reviews_raw`;
DESCRIBE `products_raw`;
DESCRIBE `category_translation_raw`;

SELECT 'category_translation_raw' AS table_name, COUNT(*) AS row_count FROM `category_translation_raw`
UNION ALL SELECT 'customers_raw', COUNT(*) FROM `customers_raw`
UNION ALL SELECT 'products_raw', COUNT(*) FROM `products_raw`
UNION ALL SELECT 'orders_raw', COUNT(*) FROM `orders_raw`
UNION ALL SELECT 'order_items_raw', COUNT(*) FROM `order_items_raw`
UNION ALL SELECT 'order_payments_raw', COUNT(*) FROM `order_payments_raw`
UNION ALL SELECT 'order_reviews_raw', COUNT(*) FROM `order_reviews_raw`;

-- Candidate-key duplicates and full-row duplicates. A repeated review_id is an expected audit finding, not a table primary key.
SELECT 'customers.customer_id' AS check_name, COUNT(*) AS duplicate_groups
FROM (SELECT customer_id FROM customers_raw GROUP BY customer_id HAVING COUNT(*) > 1) AS duplicates
UNION ALL SELECT 'orders.order_id', COUNT(*) FROM (SELECT order_id FROM orders_raw GROUP BY order_id HAVING COUNT(*) > 1) AS duplicates
UNION ALL SELECT 'products.product_id', COUNT(*) FROM (SELECT product_id FROM products_raw GROUP BY product_id HAVING COUNT(*) > 1) AS duplicates
UNION ALL SELECT 'order_items.order_id_order_item_id', COUNT(*) FROM (SELECT order_id, order_item_id FROM order_items_raw GROUP BY order_id, order_item_id HAVING COUNT(*) > 1) AS duplicates
UNION ALL SELECT 'payments.order_id_payment_sequential', COUNT(*) FROM (SELECT order_id, payment_sequential FROM order_payments_raw GROUP BY order_id, payment_sequential HAVING COUNT(*) > 1) AS duplicates
UNION ALL SELECT 'reviews.review_id', COUNT(*) FROM (SELECT review_id FROM order_reviews_raw GROUP BY review_id HAVING COUNT(*) > 1) AS duplicates;

-- Raw foreign-key integrity plus the available category-translation relationship.
SELECT 'orders.customer_id -> customers.customer_id' AS relationship_name,
       COUNT(*) AS child_rows, SUM(o.customer_id IS NOT NULL) AS nonnull_child_keys,
       SUM(c.customer_id IS NOT NULL) AS matched_rows,
       SUM(c.customer_id IS NULL) AS unmatched_rows
FROM orders_raw AS o LEFT JOIN customers_raw AS c ON o.customer_id = c.customer_id
UNION ALL
SELECT 'items.order_id -> orders.order_id', COUNT(*), SUM(i.order_id IS NOT NULL), SUM(o.order_id IS NOT NULL), SUM(o.order_id IS NULL)
FROM order_items_raw AS i LEFT JOIN orders_raw AS o ON i.order_id = o.order_id
UNION ALL
SELECT 'items.product_id -> products.product_id', COUNT(*), SUM(i.product_id IS NOT NULL), SUM(p.product_id IS NOT NULL), SUM(p.product_id IS NULL)
FROM order_items_raw AS i LEFT JOIN products_raw AS p ON i.product_id = p.product_id
UNION ALL
SELECT 'payments.order_id -> orders.order_id', COUNT(*), SUM(p.order_id IS NOT NULL), SUM(o.order_id IS NOT NULL), SUM(o.order_id IS NULL)
FROM order_payments_raw AS p LEFT JOIN orders_raw AS o ON p.order_id = o.order_id
UNION ALL
SELECT 'reviews.order_id -> orders.order_id', COUNT(*), SUM(r.order_id IS NOT NULL), SUM(o.order_id IS NOT NULL), SUM(o.order_id IS NULL)
FROM order_reviews_raw AS r LEFT JOIN orders_raw AS o ON r.order_id = o.order_id;

-- Orders: status distribution, nulls, ranges, and date-order anomalies. These are audit counts only.
SELECT order_status, COUNT(*) AS order_count,
       SUM(order_approved_at IS NULL) AS missing_approved_at,
       SUM(order_delivered_carrier_date IS NULL) AS missing_carrier_at,
       SUM(order_delivered_customer_date IS NULL) AS missing_delivered_at
FROM orders_raw GROUP BY order_status ORDER BY order_status;

SELECT MIN(order_purchase_timestamp) AS purchase_min, MAX(order_purchase_timestamp) AS purchase_max,
       MIN(order_approved_at) AS approved_min, MAX(order_approved_at) AS approved_max,
       MIN(order_delivered_carrier_date) AS carrier_min, MAX(order_delivered_carrier_date) AS carrier_max,
       MIN(order_delivered_customer_date) AS delivered_min, MAX(order_delivered_customer_date) AS delivered_max,
       MIN(order_estimated_delivery_date) AS estimated_min, MAX(order_estimated_delivery_date) AS estimated_max
FROM orders_raw;

SELECT SUM(order_approved_at < order_purchase_timestamp) AS approved_before_purchase,
       SUM(order_delivered_carrier_date < order_purchase_timestamp) AS carrier_before_purchase,
       SUM(order_delivered_carrier_date < order_approved_at) AS carrier_before_approved,
       SUM(order_delivered_customer_date < order_delivered_carrier_date) AS delivered_before_carrier,
       SUM(order_delivered_customer_date < order_purchase_timestamp) AS delivered_before_purchase,
       SUM(order_estimated_delivery_date < order_purchase_timestamp) AS estimated_before_purchase
FROM orders_raw;

-- Reviews: score distribution, duplicate review_id audit, multi-review and conflict counts.
SELECT review_score, COUNT(*) AS review_count FROM order_reviews_raw GROUP BY review_score ORDER BY review_score;

SELECT SUM(review_count > 1) AS multi_review_orders,
       SUM(score_count > 1) AS conflicting_score_orders,
       MAX(review_count) AS max_reviews_per_order
FROM (
  SELECT order_id, COUNT(*) AS review_count, COUNT(DISTINCT review_score) AS score_count
  FROM order_reviews_raw GROUP BY order_id
) AS review_orders;

-- Items, payments, products, and customers: selected numeric/nullable audit results.
SELECT SUM(price IS NULL) AS missing_price, SUM(price = 0) AS zero_price, SUM(price < 0) AS negative_price,
       SUM(freight_value IS NULL) AS missing_freight, SUM(freight_value < 0) AS negative_freight,
       SUM(seller_id IS NULL) AS missing_seller_id, SUM(product_id IS NULL) AS missing_product_id,
       MIN(price) AS min_price, MAX(price) AS max_price, MIN(freight_value) AS min_freight, MAX(freight_value) AS max_freight
FROM order_items_raw;

SELECT payment_type, COUNT(*) AS payment_records FROM order_payments_raw GROUP BY payment_type ORDER BY payment_type;
SELECT SUM(payment_value IS NULL) AS missing_value, SUM(payment_value = 0) AS zero_value, SUM(payment_value < 0) AS negative_value,
       MIN(payment_value) AS min_value, MAX(payment_value) AS max_value,
       MIN(payment_installments) AS min_installments, MAX(payment_installments) AS max_installments
FROM order_payments_raw;

SELECT SUM(product_category_name IS NULL) AS missing_category,
       SUM(product_weight_g IS NULL) AS missing_weight, SUM(product_weight_g = 0) AS zero_weight, SUM(product_weight_g < 0) AS negative_weight,
       SUM(product_length_cm IS NULL) AS missing_length, SUM(product_height_cm IS NULL) AS missing_height, SUM(product_width_cm IS NULL) AS missing_width
FROM products_raw;

SELECT COUNT(DISTINCT p.product_category_name) AS source_categories,
       COUNT(DISTINCT t.product_category_name) AS translated_categories,
       SUM(t.product_category_name IS NULL AND p.product_category_name IS NOT NULL) AS untranslated_product_rows
FROM products_raw AS p LEFT JOIN category_translation_raw AS t ON p.product_category_name = t.product_category_name;

SELECT SUM(customer_id IS NULL) AS missing_customer_id, SUM(customer_unique_id IS NULL) AS missing_unique_id,
       SUM(customer_state IS NULL) AS missing_state, SUM(customer_city IS NULL) AS missing_city,
       SUM(customer_zip_code_prefix IS NULL) AS missing_zip,
       COUNT(DISTINCT customer_unique_id) AS distinct_customer_unique_id
FROM customers_raw;

-- Order-grain join multiplication and monthly coverage diagnostics.
WITH item_counts AS (SELECT order_id, COUNT(*) AS item_count FROM order_items_raw GROUP BY order_id),
payment_counts AS (SELECT order_id, COUNT(*) AS payment_count FROM order_payments_raw GROUP BY order_id),
review_counts AS (SELECT order_id, COUNT(*) AS review_count FROM order_reviews_raw GROUP BY order_id)
SELECT SUM(COALESCE(i.item_count, 0) > 1) AS multi_item_orders,
       SUM(COALESCE(p.payment_count, 0) > 1) AS multi_payment_orders,
       SUM(COALESCE(r.review_count, 0) > 1) AS multi_review_orders,
       SUM(COALESCE(i.item_count, 0) > 1 AND COALESCE(p.payment_count, 0) > 1) AS multi_item_multi_payment_orders,
       SUM(COALESCE(i.item_count, 0) * COALESCE(p.payment_count, 0) * COALESCE(r.review_count, 0)) AS three_way_inner_join_rows
FROM orders_raw AS o
LEFT JOIN item_counts AS i ON o.order_id = i.order_id
LEFT JOIN payment_counts AS p ON o.order_id = p.order_id
LEFT JOIN review_counts AS r ON o.order_id = r.order_id;

SELECT DATE_FORMAT(order_purchase_timestamp, '%Y-%m') AS order_month,
       COUNT(*) AS order_count, MIN(DATE(order_purchase_timestamp)) AS first_order_date,
       MAX(DATE(order_purchase_timestamp)) AS last_order_date,
       COUNT(DISTINCT DATE(order_purchase_timestamp)) AS active_days
FROM orders_raw GROUP BY DATE_FORMAT(order_purchase_timestamp, '%Y-%m') ORDER BY order_month;

-- Sample funnel only; this does not select a main review or create an analysis table.
SELECT COUNT(*) AS all_orders,
       SUM(order_status = 'delivered') AS delivered_orders,
       SUM(order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL) AS delivered_with_actual_date,
       SUM(order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL AND order_estimated_delivery_date IS NOT NULL) AS delivered_with_both_dates,
       SUM(order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL AND order_estimated_delivery_date IS NOT NULL
           AND EXISTS (SELECT 1 FROM order_reviews_raw AS r WHERE r.order_id = orders_raw.order_id AND r.review_score BETWEEN 1 AND 5)) AS delivery_review_sample
FROM orders_raw;
