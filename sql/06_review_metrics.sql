-- T12：客户评分核心描述性指标（只读）。
-- 唯一输入：vw_order_analysis；该视图为一行一个 order_id，selected_review_score 是最新有效评价主口径。
-- 不重新连接评价明细，不平均多条评价，不创建、替换或修改任何数据库对象。

-- 查询 1：评分样本边界与评价覆盖。
-- 粒度：订单（order_id）；评分关系主样本的定义为 is_review_relation_eligible = 1。
SELECT
  COUNT(DISTINCT order_id) AS total_orders,
  COUNT(DISTINCT CASE WHEN selected_review_score BETWEEN 1 AND 5 THEN order_id END) AS selected_valid_review_orders,
  COUNT(DISTINCT CASE WHEN is_review_relation_eligible = 1 THEN order_id END) AS review_relation_eligible_orders,
  COUNT(DISTINCT CASE WHEN is_delivery_eligible = 1 AND is_review_relation_eligible = 0 THEN order_id END) AS delivery_eligible_but_review_relation_ineligible_orders
FROM vw_order_analysis;

-- 查询 2：评分等级分布。
-- 粒度：订单（order_id）；分母固定为 is_review_relation_eligible = 1 的订单。
WITH review_denominator AS (
  SELECT COUNT(DISTINCT order_id) AS review_relation_eligible_orders
  FROM vw_order_analysis
  WHERE is_review_relation_eligible = 1
)
SELECT
  a.selected_review_score AS review_score,
  COUNT(DISTINCT a.order_id) AS order_count,
  COUNT(DISTINCT a.order_id) / NULLIF(d.review_relation_eligible_orders, 0) AS order_rate,
  d.review_relation_eligible_orders AS denominator_review_relation_eligible_orders
FROM vw_order_analysis AS a
CROSS JOIN review_denominator AS d
WHERE a.is_review_relation_eligible = 1
GROUP BY a.selected_review_score, d.review_relation_eligible_orders
ORDER BY a.selected_review_score;

-- 查询 3：平均评分、低评分率和高评分率。
-- 粒度：订单（order_id）；低评分为 1–2，高评分为 4–5，三个指标的样本均为评分关系主样本。
SELECT
  COUNT(DISTINCT order_id) AS review_relation_eligible_orders,
  AVG(selected_review_score) AS average_review_score,
  COUNT(DISTINCT CASE WHEN selected_review_score IN (1, 2) THEN order_id END) AS low_review_orders,
  COUNT(DISTINCT CASE WHEN selected_review_score IN (1, 2) THEN order_id END) / NULLIF(COUNT(DISTINCT order_id), 0) AS low_review_rate,
  COUNT(DISTINCT CASE WHEN selected_review_score IN (4, 5) THEN order_id END) AS high_review_orders,
  COUNT(DISTINCT CASE WHEN selected_review_score IN (4, 5) THEN order_id END) / NULLIF(COUNT(DISTINCT order_id), 0) AS high_review_rate
FROM vw_order_analysis
WHERE is_review_relation_eligible = 1;

-- 查询 4：日期异常敏感性对照（评分指标）。
-- 粒度：订单（order_id）；主口径保留全部评分关系主样本，对照口径额外排除 has_date_anomaly = 1。
WITH scoped_review_sample AS (
  SELECT
    'primary_all_eligible' AS sample_scope,
    order_id,
    selected_review_score
  FROM vw_order_analysis
  WHERE is_review_relation_eligible = 1
  UNION ALL
  SELECT
    'exclude_date_anomaly' AS sample_scope,
    order_id,
    selected_review_score
  FROM vw_order_analysis
  WHERE is_review_relation_eligible = 1
    AND has_date_anomaly = 0
)
SELECT
  sample_scope,
  COUNT(DISTINCT order_id) AS review_relation_eligible_orders,
  AVG(selected_review_score) AS average_review_score,
  COUNT(DISTINCT CASE WHEN selected_review_score IN (1, 2) THEN order_id END) AS low_review_orders,
  COUNT(DISTINCT CASE WHEN selected_review_score IN (1, 2) THEN order_id END) / NULLIF(COUNT(DISTINCT order_id), 0) AS low_review_rate,
  COUNT(DISTINCT CASE WHEN selected_review_score IN (4, 5) THEN order_id END) AS high_review_orders,
  COUNT(DISTINCT CASE WHEN selected_review_score IN (4, 5) THEN order_id END) / NULLIF(COUNT(DISTINCT order_id), 0) AS high_review_rate
FROM scoped_review_sample
GROUP BY sample_scope
ORDER BY FIELD(sample_scope, 'primary_all_eligible', 'exclude_date_anomaly');

-- 查询 5：订单级粒度与评分值保护检查。
-- 预期：order_rows = distinct_order_ids = 99,441，且评分关系主样本不存在 1–5 之外的 selected_review_score。
SELECT
  COUNT(*) AS order_rows,
  COUNT(DISTINCT order_id) AS distinct_order_ids,
  COUNT(*) = COUNT(DISTINCT order_id) AS order_id_is_unique,
  SUM(is_review_relation_eligible = 1 AND selected_review_score NOT BETWEEN 1 AND 5) AS invalid_scores_in_review_relation_sample
FROM vw_order_analysis;
