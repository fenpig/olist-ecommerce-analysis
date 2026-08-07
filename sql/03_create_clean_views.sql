-- File: 03_create_clean_views.sql
-- Goal: Provide deterministic, auditable order-level review selection views for T09.
-- Input objects: `order_reviews_raw` only; no delivery, geography, product, seller, or order-analysis objects are referenced.
-- Output objects: `vw_review_ranked`, `vw_order_review_audit`, and `vw_order_review_selected`.
-- Prerequisites: T08 passed; the three target views do not already exist; MySQL 8.0.44.
-- Repeatable: No implicit replacement. Stop if a target view exists; do not use CREATE OR REPLACE.
-- Implementation task: T09.
-- Current status: implemented, created, and verified by T09 on 2026-08-06.
-- Safety: Creates only the three named views. It does not alter raw tables or execute DML.

CREATE VIEW `vw_review_ranked` AS
WITH raw_order_audit AS (
  SELECT
    order_id,
    COUNT(*) AS review_record_count,
    SUM(review_score BETWEEN 1 AND 5) AS valid_review_record_count,
    SUM(review_score IS NULL OR review_score NOT BETWEEN 1 AND 5) AS invalid_or_missing_score_count,
    COUNT(DISTINCT CASE WHEN review_score BETWEEN 1 AND 5 THEN review_score END) AS distinct_valid_score_count,
    SUM(review_answer_timestamp IS NULL OR review_creation_date IS NULL) AS time_field_missing_record_count
  FROM order_reviews_raw
  GROUP BY order_id
), valid_rank_source AS (
  SELECT
    r.review_row_id,
    r.order_id,
    r.review_id,
    r.review_score,
    r.review_creation_date,
    r.review_answer_timestamp,
    a.review_record_count,
    a.valid_review_record_count,
    a.invalid_or_missing_score_count,
    a.distinct_valid_score_count,
    a.time_field_missing_record_count,
    COUNT(*) OVER (PARTITION BY r.order_id, r.review_answer_timestamp) AS answer_timestamp_tie_count,
    COUNT(*) OVER (PARTITION BY r.order_id, r.review_answer_timestamp, r.review_creation_date) AS creation_timestamp_tie_count,
    COUNT(*) OVER (PARTITION BY r.order_id, r.review_answer_timestamp, r.review_creation_date, r.review_id) AS review_id_tie_count,
    ROW_NUMBER() OVER (
      PARTITION BY r.order_id
      ORDER BY
        CASE WHEN r.review_answer_timestamp IS NULL THEN 1 ELSE 0 END ASC,
        r.review_answer_timestamp DESC,
        CASE WHEN r.review_creation_date IS NULL THEN 1 ELSE 0 END ASC,
        r.review_creation_date DESC,
        r.review_id DESC,
        r.review_row_id DESC
    ) AS review_rank
  FROM order_reviews_raw AS r
  INNER JOIN raw_order_audit AS a ON r.order_id = a.order_id
  WHERE r.review_score BETWEEN 1 AND 5
)
SELECT
  order_id,
  review_id,
  review_score,
  review_creation_date,
  review_answer_timestamp,
  review_record_count,
  valid_review_record_count,
  invalid_or_missing_score_count,
  distinct_valid_score_count,
  (review_record_count > 1) AS has_multiple_reviews,
  (distinct_valid_score_count > 1) AS has_conflicting_review_scores,
  review_rank,
  CASE
    WHEN review_record_count = 1 THEN 'single_review'
    WHEN review_answer_timestamp IS NOT NULL AND answer_timestamp_tie_count = 1 THEN 'latest_answer_timestamp'
    WHEN creation_timestamp_tie_count = 1 THEN 'latest_creation_date'
    ELSE 'review_id_tiebreaker'
  END AS selection_basis
FROM valid_rank_source;

CREATE VIEW `vw_order_review_audit` AS
WITH per_order AS (
  SELECT
    order_id,
    COUNT(*) AS review_record_count,
    SUM(review_score BETWEEN 1 AND 5) AS valid_review_record_count,
    SUM(review_score IS NULL OR review_score NOT BETWEEN 1 AND 5) AS invalid_or_missing_score_count,
    COUNT(DISTINCT CASE WHEN review_score BETWEEN 1 AND 5 THEN review_score END) AS distinct_valid_score_count,
    MIN(CASE WHEN review_score BETWEEN 1 AND 5 THEN review_score END) AS minimum_review_score,
    MAX(CASE WHEN review_score BETWEEN 1 AND 5 THEN review_score END) AS maximum_review_score,
    SUM(review_answer_timestamp IS NULL OR review_creation_date IS NULL) > 0 AS has_time_field_missing
  FROM order_reviews_raw
  GROUP BY order_id
), selected AS (
  SELECT * FROM vw_review_ranked WHERE review_rank = 1
)
SELECT
  a.order_id,
  a.review_record_count,
  a.valid_review_record_count,
  a.invalid_or_missing_score_count,
  a.distinct_valid_score_count,
  s.review_id AS latest_review_id,
  s.review_score AS latest_review_score,
  s.review_creation_date AS latest_review_creation_date,
  s.review_answer_timestamp AS latest_review_answer_timestamp,
  a.minimum_review_score,
  a.maximum_review_score,
  CASE WHEN s.review_score BETWEEN 1 AND 2 THEN 'low' WHEN s.review_score = 3 THEN 'neutral' WHEN s.review_score BETWEEN 4 AND 5 THEN 'high' END AS latest_review_group,
  CASE WHEN a.minimum_review_score BETWEEN 1 AND 2 THEN 'low' WHEN a.minimum_review_score = 3 THEN 'neutral' WHEN a.minimum_review_score BETWEEN 4 AND 5 THEN 'high' END AS minimum_review_group,
  (s.review_score BETWEEN 1 AND 2) AS latest_is_low_review,
  (a.minimum_review_score BETWEEN 1 AND 2) AS minimum_is_low_review,
  (a.review_record_count > 1) AS has_multiple_reviews,
  (a.distinct_valid_score_count > 1) AS has_conflicting_review_scores,
  a.has_time_field_missing,
  (s.selection_basis = 'review_id_tiebreaker') AS requires_review_id_tiebreaker,
  (a.valid_review_record_count = 0) AS has_no_valid_order_review,
  COALESCE(s.selection_basis, 'no_valid_score') AS selection_basis
FROM per_order AS a
LEFT JOIN selected AS s ON a.order_id = s.order_id;

CREATE VIEW `vw_order_review_selected` AS
SELECT
  r.order_id,
  r.review_id AS selected_review_id,
  r.review_score AS selected_review_score,
  r.review_creation_date AS selected_review_creation_date,
  r.review_answer_timestamp AS selected_review_answer_timestamp,
  r.review_record_count,
  r.valid_review_record_count,
  r.invalid_or_missing_score_count,
  r.distinct_valid_score_count,
  r.has_multiple_reviews,
  r.has_conflicting_review_scores,
  r.selection_basis,
  a.minimum_review_score,
  a.latest_review_group,
  a.minimum_review_group,
  a.latest_is_low_review,
  a.minimum_is_low_review
FROM vw_review_ranked AS r
INNER JOIN vw_order_review_audit AS a ON r.order_id = a.order_id
WHERE r.review_rank = 1;

-- T10 addition: one immutable order-level cleaning view. This statement is the
-- only T10 database change and must not be run if `vw_clean_orders` exists.
-- It joins only the one-row-per-order T09 selected-review view; it does not
-- join items, payments, customers, products, or any analysis object.

CREATE VIEW `vw_clean_orders` AS
WITH source_orders AS (
  SELECT
    o.order_id,
    o.customer_id,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_approved_at,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    r.selected_review_id,
    r.selected_review_score,
    r.selected_review_creation_date,
    r.selected_review_answer_timestamp,
    COALESCE(r.review_record_count, 0) AS review_record_count,
    COALESCE(r.valid_review_record_count, 0) AS valid_review_record_count,
    COALESCE(r.invalid_or_missing_score_count, 0) AS invalid_or_missing_score_count,
    COALESCE(r.distinct_valid_score_count, 0) AS distinct_valid_score_count,
    COALESCE(r.has_multiple_reviews, 0) AS has_multiple_reviews,
    COALESCE(r.has_conflicting_review_scores, 0) AS has_conflicting_review_scores,
    r.selection_basis,
    r.minimum_review_score,
    r.latest_review_group,
    r.minimum_review_group,
    r.latest_is_low_review,
    r.minimum_is_low_review
  FROM orders_raw AS o
  LEFT JOIN vw_order_review_selected AS r ON o.order_id = r.order_id
), date_flags AS (
  SELECT
    s.*,
    DATEDIFF(s.order_delivered_customer_date, s.order_estimated_delivery_date) AS delay_days,
    TIMESTAMPDIFF(
      SECOND,
      s.order_estimated_delivery_date,
      s.order_delivered_customer_date
    ) / 3600.0 AS delay_hours_raw,
    CASE WHEN s.order_approved_at IS NOT NULL
              AND s.order_purchase_timestamp IS NOT NULL
              AND s.order_approved_at < s.order_purchase_timestamp THEN 1 ELSE 0 END AS is_approved_before_purchase,
    CASE WHEN s.order_delivered_carrier_date IS NOT NULL
              AND s.order_purchase_timestamp IS NOT NULL
              AND s.order_delivered_carrier_date < s.order_purchase_timestamp THEN 1 ELSE 0 END AS is_carrier_before_purchase,
    CASE WHEN s.order_delivered_carrier_date IS NOT NULL
              AND s.order_approved_at IS NOT NULL
              AND s.order_delivered_carrier_date < s.order_approved_at THEN 1 ELSE 0 END AS is_carrier_before_approval,
    CASE WHEN s.order_delivered_customer_date IS NOT NULL
              AND s.order_purchase_timestamp IS NOT NULL
              AND s.order_delivered_customer_date < s.order_purchase_timestamp THEN 1 ELSE 0 END AS is_delivered_before_purchase,
    CASE WHEN s.order_delivered_customer_date IS NOT NULL
              AND s.order_delivered_carrier_date IS NOT NULL
              AND s.order_delivered_customer_date < s.order_delivered_carrier_date THEN 1 ELSE 0 END AS is_delivered_before_carrier,
    CASE WHEN s.order_estimated_delivery_date IS NOT NULL
              AND s.order_purchase_timestamp IS NOT NULL
              AND s.order_estimated_delivery_date < s.order_purchase_timestamp THEN 1 ELSE 0 END AS is_estimated_before_purchase
  FROM source_orders AS s
)
SELECT
  order_id,
  customer_id,
  order_status,
  order_purchase_timestamp,
  order_approved_at,
  order_delivered_carrier_date,
  order_delivered_customer_date,
  order_estimated_delivery_date,
  DATE_FORMAT(order_purchase_timestamp, '%Y-%m') AS purchase_month,
  delay_days,
  delay_hours_raw,
  CASE
    WHEN delay_days IS NULL THEN 'not_applicable'
    WHEN delay_days <= 0 THEN 'on_time_or_early'
    WHEN delay_days BETWEEN 1 AND 3 THEN 'slight_delay'
    WHEN delay_days BETWEEN 4 AND 7 THEN 'moderate_delay'
    WHEN delay_days > 7 THEN 'severe_delay'
  END AS delay_category,
  CASE WHEN delay_days IS NULL THEN NULL WHEN delay_days > 0 THEN 1 ELSE 0 END AS is_delayed,
  (order_status = 'delivered') AS is_delivered_order,
  (order_status = 'delivered'
    AND order_delivered_customer_date IS NOT NULL
    AND order_estimated_delivery_date IS NOT NULL) AS is_delivery_eligible,
  CASE
    WHEN order_status <> 'delivered' THEN 'not_delivered'
    WHEN order_delivered_customer_date IS NULL AND order_estimated_delivery_date IS NULL THEN 'missing_both_delivery_dates'
    WHEN order_delivered_customer_date IS NULL THEN 'missing_actual_delivery_date'
    WHEN order_estimated_delivery_date IS NULL THEN 'missing_estimated_delivery_date'
    ELSE 'eligible'
  END AS delivery_eligibility_reason,
  CASE
    WHEN order_status = 'delivered'
      AND order_delivered_customer_date IS NOT NULL
      AND order_estimated_delivery_date IS NOT NULL
      AND selected_review_score BETWEEN 1 AND 5 THEN 1
    ELSE 0
  END AS is_review_relation_eligible,
  CASE
    WHEN NOT (order_status = 'delivered'
      AND order_delivered_customer_date IS NOT NULL
      AND order_estimated_delivery_date IS NOT NULL) THEN 'delivery_ineligible'
    WHEN selected_review_id IS NULL THEN 'no_selected_review'
    WHEN selected_review_score NOT BETWEEN 1 AND 5 OR selected_review_score IS NULL THEN 'invalid_selected_review_score'
    ELSE 'eligible'
  END AS review_relation_eligibility_reason,
  CASE
    WHEN order_purchase_timestamp IS NULL THEN NULL
    WHEN DATE_FORMAT(order_purchase_timestamp, '%Y-%m') IN ('2016-09', '2016-12', '2018-09', '2018-10') THEN 0
    ELSE 1
  END AS is_primary_month,
  is_approved_before_purchase,
  is_carrier_before_purchase,
  is_carrier_before_approval,
  is_delivered_before_purchase,
  is_delivered_before_carrier,
  is_estimated_before_purchase,
  CASE
    WHEN is_approved_before_purchase = 1
      OR is_carrier_before_purchase = 1
      OR is_carrier_before_approval = 1
      OR is_delivered_before_purchase = 1
      OR is_delivered_before_carrier = 1
      OR is_estimated_before_purchase = 1 THEN 1
    ELSE 0
  END AS has_date_anomaly,
  selected_review_id,
  selected_review_score,
  selected_review_creation_date,
  selected_review_answer_timestamp,
  review_record_count,
  valid_review_record_count,
  invalid_or_missing_score_count,
  distinct_valid_score_count,
  has_multiple_reviews,
  has_conflicting_review_scores,
  selection_basis,
  minimum_review_score,
  latest_review_group,
  minimum_review_group,
  latest_is_low_review,
  minimum_is_low_review
FROM date_flags;
