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
