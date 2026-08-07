-- T12：配送履约核心描述性指标（只读）。
-- 唯一输入：vw_order_analysis；该视图为一行一个 order_id。
-- 不创建、替换或修改任何数据库对象。请在 olist_delivery_analysis 中逐条执行以下 SELECT。

-- 查询 1：订单总体与配送样本边界。
-- 粒度：订单（order_id）；配送可用订单的定义为 is_delivery_eligible = 1。
SELECT
  COUNT(DISTINCT order_id) AS total_orders,
  COUNT(DISTINCT CASE WHEN is_delivered_order = 1 THEN order_id END) AS delivered_orders,
  COUNT(DISTINCT CASE WHEN is_delivery_eligible = 1 THEN order_id END) AS delivery_eligible_orders,
  COUNT(DISTINCT CASE WHEN is_delivered_order = 1 AND is_delivery_eligible = 0 THEN order_id END) AS delivered_but_delivery_ineligible_orders
FROM vw_order_analysis;

-- 查询 2：延迟订单数、延迟率和延迟天数。
-- 粒度：订单（order_id）；分母固定为 is_delivery_eligible = 1 的订单。
-- 平均值和中位数均覆盖全部配送可用订单；“仅延迟订单”的均值单独列示。
WITH delivery_sample AS (
  SELECT order_id, delay_days
  FROM vw_order_analysis
  WHERE is_delivery_eligible = 1
), ranked_delay AS (
  SELECT
    order_id,
    delay_days,
    ROW_NUMBER() OVER (ORDER BY delay_days) AS row_number_ascending,
    COUNT(*) OVER () AS sample_size
  FROM delivery_sample
)
SELECT
  COUNT(DISTINCT order_id) AS delivery_eligible_orders,
  COUNT(DISTINCT CASE WHEN delay_days > 0 THEN order_id END) AS delayed_orders,
  COUNT(DISTINCT CASE WHEN delay_days <= 0 THEN order_id END) AS on_time_or_early_orders,
  COUNT(DISTINCT CASE WHEN delay_days > 0 THEN order_id END) / NULLIF(COUNT(DISTINCT order_id), 0) AS delayed_order_rate,
  AVG(delay_days) AS average_delay_days_all_delivery_eligible_orders,
  AVG(CASE WHEN delay_days > 0 THEN delay_days END) AS average_delay_days_delayed_orders,
  AVG(CASE
    WHEN row_number_ascending IN (FLOOR((sample_size + 1) / 2), FLOOR((sample_size + 2) / 2))
    THEN delay_days
  END) AS median_delay_days_all_delivery_eligible_orders
FROM ranked_delay;

-- 查询 3：配送可用订单的延迟等级分布。
-- 粒度：订单（order_id）；每个订单恰好归入一个已确认的 delay_category。
-- 分母固定为 is_delivery_eligible = 1 的订单，而非全部订单。
WITH delivery_denominator AS (
  SELECT COUNT(DISTINCT order_id) AS delivery_eligible_orders
  FROM vw_order_analysis
  WHERE is_delivery_eligible = 1
)
SELECT
  a.delay_category,
  COUNT(DISTINCT a.order_id) AS order_count,
  COUNT(DISTINCT a.order_id) / NULLIF(d.delivery_eligible_orders, 0) AS order_rate,
  d.delivery_eligible_orders AS denominator_delivery_eligible_orders
FROM vw_order_analysis AS a
CROSS JOIN delivery_denominator AS d
WHERE a.is_delivery_eligible = 1
GROUP BY a.delay_category, d.delivery_eligible_orders
ORDER BY FIELD(a.delay_category, 'on_time_or_early', 'slight_delay', 'moderate_delay', 'severe_delay');

-- 查询 4：交运至客户送达的配送时长。
-- 粒度：订单（order_id）；样本为 is_transit_duration_eligible = 1。
-- 23 条实际送达早于交运的订单被排除，但不改变其 delay_days 或配送可用标记。
WITH transit_sample AS (
  SELECT
    order_id,
    TIMESTAMPDIFF(SECOND, order_delivered_carrier_date, order_delivered_customer_date) / 86400.0 AS transit_duration_days
  FROM vw_order_analysis
  WHERE is_transit_duration_eligible = 1
), ranked_transit AS (
  SELECT
    order_id,
    transit_duration_days,
    ROW_NUMBER() OVER (ORDER BY transit_duration_days) AS row_number_ascending,
    COUNT(*) OVER () AS sample_size
  FROM transit_sample
)
SELECT
  COUNT(DISTINCT order_id) AS transit_duration_eligible_orders,
  AVG(transit_duration_days) AS average_transit_duration_days,
  AVG(CASE
    WHEN row_number_ascending IN (FLOOR((sample_size + 1) / 2), FLOOR((sample_size + 2) / 2))
    THEN transit_duration_days
  END) AS median_transit_duration_days
FROM ranked_transit;

-- 查询 5：日期异常敏感性对照（配送指标）。
-- 粒度：订单（order_id）；主口径保留全部配送可用订单，对照口径额外排除 has_date_anomaly = 1。
WITH scoped_delivery_sample AS (
  SELECT
    CASE WHEN has_date_anomaly = 0 THEN 'exclude_date_anomaly' ELSE 'primary_all_eligible' END AS sample_scope,
    order_id,
    delay_days
  FROM vw_order_analysis
  WHERE is_delivery_eligible = 1
  UNION ALL
  SELECT
    'primary_all_eligible' AS sample_scope,
    order_id,
    delay_days
  FROM vw_order_analysis
  WHERE is_delivery_eligible = 1
    AND has_date_anomaly = 0
)
SELECT
  sample_scope,
  COUNT(DISTINCT order_id) AS delivery_eligible_orders,
  COUNT(DISTINCT CASE WHEN delay_days > 0 THEN order_id END) AS delayed_orders,
  COUNT(DISTINCT CASE WHEN delay_days > 0 THEN order_id END) / NULLIF(COUNT(DISTINCT order_id), 0) AS delayed_order_rate,
  AVG(delay_days) AS average_delay_days_all_delivery_eligible_orders
FROM scoped_delivery_sample
GROUP BY sample_scope
ORDER BY FIELD(sample_scope, 'primary_all_eligible', 'exclude_date_anomaly');

-- 查询 6：订单级粒度保护检查。
-- 预期：order_rows = distinct_order_ids = 99,441；若不一致，停止后续指标解读。
SELECT
  COUNT(*) AS order_rows,
  COUNT(DISTINCT order_id) AS distinct_order_ids,
  COUNT(*) = COUNT(DISTINCT order_id) AS order_id_is_unique
FROM vw_order_analysis;
