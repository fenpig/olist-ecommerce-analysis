# 指标口径（一期）

本文件定义当前已确认的履约与客户满意度指标。除特别说明外，订单级指标的粒度均为 `order_id`；不得因订单多商品、多付款或多评价记录而重复计数。

## 1. 基础样本标记

| 字段/标记 | 定义 |
| --- | --- |
| `is_delivered_order` | `order_status = 'delivered'`。 |
| `is_delivery_eligible` | 已送达，且 `order_delivered_customer_date` 和 `order_estimated_delivery_date` 完整、可解析。 |
| `is_valid_review` | `review_score` 属于 1、2、3、4、5。未评价不填充评分。 |
| `is_review_relation_eligible` | `is_delivery_eligible = 1`，且存在按 DEC-002 选出的有效订单级评价；无法排序且评分冲突的订单为 0。 |
| `is_primary_month` | 订单下单月份不属于 2016-09、2016-12、2018-09、2018-10。仅用于主要月度趋势，不影响全量统计。 |
| `delivery_eligibility_reason` | 配送可用标记的固定优先级原因。 | `not_delivered`、缺失实际/预计送达日期或 `eligible` | 不删除原始订单。 |
| `review_relation_eligibility_reason` | 评分关系可用标记的固定优先级原因。 | `delivery_ineligible`、`no_selected_review`、`invalid_selected_review_score` 或 `eligible` | 不因多评或评分冲突自动排除。 |
| `is_transit_duration_eligible` | 已配送可用、交运日期完整且实际送达不早于交运。 | 不适用 | 仅控制交运到送达等依赖交运日期的时长指标；不改写配送或评分关系可用标记。 |

## 2. 履约与延迟指标

| 指标/字段 | 公式或定义 | 分子 / 分母 | 使用限制 |
| --- | --- | --- | --- |
| `delay_days` | `DATE(order_delivered_customer_date) - DATE(order_estimated_delivery_date)` | 不适用 | 整数日；仅 `is_delivery_eligible = 1`。 |
| `delay_hours_raw` | `order_delivered_customer_date - order_estimated_delivery_date` | 不适用 | 连续时间差；仅作审查/补充分析，不用于主分类。 |
| `has_date_anomaly` | 任一已定义订单日期顺序异常为真 | 不适用 | 仅审计和统计；未经确认不得作为排除条件。 |
| `delivery_timing_category` | `delay_days <= 0`：按时或提前；1–3：轻微；4–7：中度；>7：严重 | 不适用 | 类别互斥且覆盖全部 `delay_days` 整数值。 |
| `is_delayed` | 记录级日期差标记：`delay_days > 0` 为 1；`delay_days <= 0` 为 0；`delay_days` 为 `NULL` 时为 `NULL` | 不适用 | 该字段只陈述日期差事实，本身不判断订单是否属于正式配送分析样本。 |
| `delivery_eligible_delayed_order_count`（正式配送延迟订单数） | `COUNT(DISTINCT CASE WHEN is_delivery_eligible = 1 AND delay_days > 0 THEN order_id END)` | 配送可用且正延迟订单 | 当前验证结果为 6,534；这是正式配送延迟率的唯一分子。 |
| `all_records_positive_delay_count`（全量正延迟标记记录数） | `COUNT(DISTINCT CASE WHEN is_delayed = 1 THEN order_id END)` | 全部 `is_delayed = 1` 记录 | 当前验证结果为 6,535；仅用于全量字段分布审计，不能替代正式配送延迟订单数。 |
| 正式延迟率 | `delivery_eligible_delayed_order_count` ÷ `is_delivery_eligible = 1` 的订单数 | 6,534 / 96,470 | 当前验证结果为 6.77%；不得把全量 `is_delayed` 分布作为分子。 |
| 平均延迟天数 | `delay_days` 的均值 | 不适用 | 必须在图表与报告中注明样本范围；若指“延迟订单平均”，另明确筛选 `delay_days > 0`。 |
| 延迟天数中位数 | `delay_days` 的中位数 | 不适用 | 同上。 |

## 3. 客户满意度指标

订单级 `review_score` 均来自按 DEC-002 选出的最新有效评价。

| 指标/字段 | 定义 | 分子 / 分母 | 使用限制 |
| --- | --- | --- | --- |
| `review_record_count` | 同一 `order_id` 的原始评价记录数 | 不适用 | 审计字段；有效记录另见下行。 |
| `valid_review_record_count` | 同一 `order_id` 中 `review_score` 为 1–5 的记录数 | 不适用 | 审计字段；主评分只从这些记录选择。 |
| `invalid_or_missing_score_count` | 原始评价中分数为空或不在 1–5 的记录数 | 不适用 | 审计字段；不得静默删除。 |
| `has_multiple_reviews` | `review_record_count > 1` | 不适用 | 审计字段。 |
| `has_conflicting_review_scores` | 同一 `order_id` 的有效评价中评分去重数大于 1 | 不适用 | 审计字段。 |
| 低评分 | 订单级评分为 1 或 2 | 不适用 | 未评价不归为低评分。 |
| 中性评价 | 订单级评分为 3 | 不适用 | 同上。 |
| 高评分 | 订单级评分为 4 或 5 | 不适用 | 同上。 |
| 平均评分 | 订单级有效评分的均值 | 不适用 | 分母是有有效订单级评分的订单。 |
| 低评分率 | 低评分订单数 ÷ 有有效订单级评分的订单数 | 评分 1–2 / 有效评分订单 | 主关系分析时额外限定 `is_review_relation_eligible = 1`。 |
| 高评分率 | 高评分订单数 ÷ 有有效订单级评分的订单数 | 评分 4–5 / 有效评分订单 | 主关系分析时额外限定 `is_review_relation_eligible = 1`。 |
| 各评分等级订单数量 | 各订单级评分值（1–5）的订单数 | 不适用 | 每个订单最多贡献一次。 |

## 4. 分析维度与范围限制

| 维度 | 一期允许口径 | 限制 |
| --- | --- | --- |
| 地区 | `customer_state` | 不推断卖家地区，不计算距离。 |
| 卖家 | `seller_id` | 订单存在多个商品/卖家时，卖家指标须使用订单明细粒度或明确归因规则；不得把多卖家订单重复当作订单级总量。 |
| 商品 | `product_category_name`（必要时使用翻译名） | 2 个未映射类别和 610 个无品类商品必须标记为未映射/未知，不能静默丢弃。 |
| 时间趋势 | `order_purchase_timestamp` 按月 | 主要趋势使用 `is_primary_month = 1`；边界月另列附录。 |

## 5. 必做的口径对照

配送时效与评分关系的主分析使用“最新有效评价”。完成后必须以“同订单最低有效评分”重算同一组核心指标和图表，并记录与主口径的样本量、平均评分、低评分率及主要分层排名差异。该对照用于稳健性判断，不替代主口径。

同时必须进行日期异常敏感性验证：主口径保留符合样本条件的全部订单，对照口径排除 `has_date_anomaly = 1`。比较主要指标、关联方向和结论是否明显变化。日期异常订单保留在完整订单数据及 `delay_days` 分析中；仅 `is_delivered_before_carrier = 1` 的订单不得进入依赖交运日期的在途时长指标。
