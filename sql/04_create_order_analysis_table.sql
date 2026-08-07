-- T11: four reproducible views; no table or DML is created.
-- Run only after confirming all four target views are absent. Do not use CREATE OR REPLACE.

CREATE VIEW `vw_order_items_aggregated` AS
SELECT
  i.order_id,
  COUNT(*) AS item_row_count,
  COUNT(*) AS item_quantity,
  COUNT(DISTINCT i.product_id) AS distinct_product_count,
  COUNT(DISTINCT i.seller_id) AS distinct_seller_count,
  SUM(i.price) AS item_value_total,
  SUM(i.freight_value) AS freight_value_total,
  SUM(i.price + i.freight_value) AS merchandise_and_freight_total,
  MIN(i.price) AS min_item_price,
  MAX(i.price) AS max_item_price,
  AVG(i.price) AS average_item_price,
  (COUNT(*) > 1) AS has_multiple_items,
  (COUNT(DISTINCT i.product_id) > 1) AS has_multiple_products,
  (COUNT(DISTINCT i.seller_id) > 1) AS has_multiple_sellers,
  COUNT(DISTINCT CASE WHEN p.product_category_name IS NOT NULL THEN p.product_category_name END) AS distinct_category_count,
  (COUNT(DISTINCT CASE WHEN p.product_category_name IS NOT NULL THEN p.product_category_name END) > 1) AS has_multiple_categories,
  CASE WHEN COUNT(DISTINCT CASE WHEN p.product_category_name IS NOT NULL THEN p.product_category_name END) = 1 THEN MAX(p.product_category_name) END AS single_category_name,
  CASE WHEN COUNT(DISTINCT CASE WHEN p.product_category_name IS NOT NULL THEN p.product_category_name END) = 1 THEN MAX(t.product_category_name_english) END AS single_category_name_english,
  (SUM(p.product_id IS NULL OR p.product_category_name IS NULL) > 0) AS has_missing_product_category,
  (SUM(p.product_category_name IS NOT NULL AND t.product_category_name_english IS NULL) > 0) AS has_untranslated_category
FROM order_items_raw AS i
LEFT JOIN products_raw AS p ON i.product_id = p.product_id
LEFT JOIN category_translation_raw AS t ON p.product_category_name = t.product_category_name
GROUP BY i.order_id;

CREATE VIEW `vw_order_payments_aggregated` AS
WITH payment_type_totals AS (
  SELECT order_id, payment_type, SUM(payment_value) AS payment_type_value_total
  FROM order_payments_raw
  GROUP BY order_id, payment_type
), ranked_payment_types AS (
  SELECT
    order_id,
    payment_type,
    payment_type_value_total,
    ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY payment_type_value_total DESC, payment_type ASC) AS payment_type_rank
  FROM payment_type_totals
)
SELECT
  p.order_id,
  COUNT(*) AS payment_record_count,
  SUM(p.payment_value) AS payment_value_total,
  COUNT(DISTINCT p.payment_type) AS distinct_payment_type_count,
  MAX(p.payment_installments) AS max_installments,
  (COUNT(*) > 1) AS has_multiple_payment_records,
  (COUNT(DISTINCT p.payment_type) > 1) AS has_multiple_payment_types,
  1 AS has_payment_record,
  MAX(CASE WHEN r.payment_type_rank = 1 THEN r.payment_type END) AS primary_payment_type
FROM order_payments_raw AS p
INNER JOIN ranked_payment_types AS r
  ON p.order_id = r.order_id AND p.payment_type <=> r.payment_type
GROUP BY p.order_id;

CREATE VIEW `vw_order_analysis` AS
SELECT
  c.*,
  cu.customer_unique_id,
  cu.customer_city,
  cu.customer_state,
  cu.customer_zip_code_prefix,
  CASE WHEN i.order_id IS NULL THEN 0 ELSE 1 END AS has_item_record,
  COALESCE(i.item_row_count, 0) AS item_row_count,
  COALESCE(i.item_quantity, 0) AS item_quantity,
  COALESCE(i.distinct_product_count, 0) AS distinct_product_count,
  COALESCE(i.distinct_seller_count, 0) AS distinct_seller_count,
  COALESCE(i.item_value_total, 0.00) AS item_value_total,
  COALESCE(i.freight_value_total, 0.00) AS freight_value_total,
  COALESCE(i.merchandise_and_freight_total, 0.00) AS merchandise_and_freight_total,
  i.min_item_price, i.max_item_price, i.average_item_price,
  COALESCE(i.has_multiple_items, 0) AS has_multiple_items,
  COALESCE(i.has_multiple_products, 0) AS has_multiple_products,
  COALESCE(i.has_multiple_sellers, 0) AS has_multiple_sellers,
  COALESCE(i.distinct_category_count, 0) AS distinct_category_count,
  COALESCE(i.has_multiple_categories, 0) AS has_multiple_categories,
  i.single_category_name, i.single_category_name_english,
  COALESCE(i.has_missing_product_category, 0) AS has_missing_product_category,
  COALESCE(i.has_untranslated_category, 0) AS has_untranslated_category,
  CASE WHEN p.order_id IS NULL THEN 0 ELSE 1 END AS has_payment_record,
  COALESCE(p.payment_record_count, 0) AS payment_record_count,
  p.payment_value_total,
  COALESCE(p.distinct_payment_type_count, 0) AS distinct_payment_type_count,
  p.max_installments,
  COALESCE(p.has_multiple_payment_records, 0) AS has_multiple_payment_records,
  COALESCE(p.has_multiple_payment_types, 0) AS has_multiple_payment_types,
  p.primary_payment_type,
  CASE WHEN i.order_id IS NOT NULL AND p.order_id IS NOT NULL THEN p.payment_value_total - i.merchandise_and_freight_total END AS payment_difference,
  CASE WHEN c.is_delivery_eligible = 1
              AND c.order_delivered_carrier_date IS NOT NULL
              AND c.order_delivered_customer_date >= c.order_delivered_carrier_date THEN 1 ELSE 0 END AS is_transit_duration_eligible
FROM vw_clean_orders AS c
LEFT JOIN customers_raw AS cu ON c.customer_id = cu.customer_id
LEFT JOIN vw_order_items_aggregated AS i ON c.order_id = i.order_id
LEFT JOIN vw_order_payments_aggregated AS p ON c.order_id = p.order_id;

CREATE VIEW `vw_order_item_analysis` AS
SELECT
  i.order_item_id,
  i.product_id,
  i.seller_id,
  i.price,
  i.freight_value,
  i.price + i.freight_value AS item_total,
  i.shipping_limit_date,
  p.product_category_name,
  t.product_category_name_english,
  (p.product_id IS NULL OR p.product_category_name IS NULL) AS has_missing_product_category,
  (p.product_category_name IS NOT NULL AND t.product_category_name_english IS NULL) AS has_untranslated_category,
  c.*,
  cu.customer_unique_id,
  cu.customer_city,
  cu.customer_state,
  cu.customer_zip_code_prefix,
  CASE WHEN c.is_delivery_eligible = 1
              AND c.order_delivered_carrier_date IS NOT NULL
              AND c.order_delivered_customer_date >= c.order_delivered_carrier_date THEN 1 ELSE 0 END AS is_transit_duration_eligible
FROM order_items_raw AS i
INNER JOIN vw_clean_orders AS c ON i.order_id = c.order_id
LEFT JOIN products_raw AS p ON i.product_id = p.product_id
LEFT JOIN category_translation_raw AS t ON p.product_category_name = t.product_category_name
LEFT JOIN customers_raw AS cu ON c.customer_id = cu.customer_id;
