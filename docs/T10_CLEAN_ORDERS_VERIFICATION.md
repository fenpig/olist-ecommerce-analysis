# T10：清洗订单视图与主延迟字段验收记录

验收日期：2026-08-07
数据库：`olist_delivery_analysis`（MySQL 8.0.44）
状态：已完成；本任务结束后暂停，未开始 T11。

## 范围与安全边界

T10 只新增 `vw_clean_orders`。该视图从 `orders_raw` 左连接一行一个订单的 `vw_order_review_selected`，不连接 `order_items_raw`、`payments_raw`、`customers_raw`、`products_raw` 或任何 T11 分析对象。

首次 T10 执行只创建了一次该视图。随后以已有视图验证模式完成 CSV 导出和复核；未使用 `CREATE OR REPLACE VIEW`，未重建、替换或删除 T09 视图，也未执行 DML。原始表和原始 CSV 未修改。

## 数据粒度与口径

- `vw_clean_orders` 和 `data/processed/clean_orders.csv` 均为一行一个 `order_id`，共 99,441 行；`order_id` 唯一且无缺失。
- `delay_days = DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date)`。
- `delay_hours_raw = TIMESTAMPDIFF(SECOND, estimated, delivered) / 3600.0`，不使用截断式 `TIMESTAMPDIFF(HOUR)`。
- 缺少实际或预计送达日期时，两个延迟字段均为 `NULL`、分类为 `not_applicable`、`is_delayed` 为 `NULL`，未填充为零。
- `delay_category`：`<= 0` 为 `on_time_or_early`，1–3 为 `slight_delay`，4–7 为 `moderate_delay`，`> 7` 为 `severe_delay`。
- 四个边界购买月份仅标记 `is_primary_month = 0`，不从任何 T10 输出删除。

`delivery_eligibility_reason` 优先级固定为：`not_delivered`、`missing_both_delivery_dates`、`missing_actual_delivery_date`、`missing_estimated_delivery_date`、`eligible`。`review_relation_eligibility_reason` 优先级固定为：`delivery_ineligible`、`no_selected_review`、`invalid_selected_review_score`、`eligible`。

## SQL/Python 对账结果

`src/04_prepare_clean_orders.py --validate-existing` 完成全量逐字段 SQL/Python 对账。`delay_hours_raw` 的绝对容差为 `0.00005` 小时（0.18 秒）：MySQL 对秒差除以 `3600.0` 的十进制结果保留四位小时小数，但计算来源仍是精确秒，未按小时截断。

| 检查项 | 结果 |
| --- | ---: |
| 总订单 / 唯一订单 / 缺失订单 ID | 99,441 / 99,441 / 0 |
| 已送达 / 配送可用 / 评分关系可用 | 96,478 / 96,470 / 95,824 |
| 边界月份订单（2016-09、2016-12、2018-09、2018-10） | 4 / 1 / 16 / 4 |
| `is_primary_month` = 0 / 1 | 25 / 99,416 |
| 按时或提前 / 轻微 / 中度 / 严重 / 不适用 | 89,941 / 1,870 / 1,802 / 2,863 / 2,965 |
| `is_delayed` = 0 / 1 / NULL | 89,941 / 6,535 / 2,965 |
| 配送原因：eligible / missing actual / not delivered | 96,470 / 8 / 2,963 |
| 评分关系原因：eligible / delivery ineligible / no selected review | 95,824 / 2,971 / 646 |
| `delay_days` 最小 / 最大 / 中位数 | -147 / 188 / -12 |
| 多评 / 冲突评价订单 | 547 / 202 |

评分选择结果保持 T09 主口径不变；三个 T09 视图定义 SHA-256 均与 T09 PASS 报告一致。脚本还抽取了提前、当日、1/3/4/7 天、超过 7 天和日期缺失各一条订单进行公式复核，详细但有限的样本记录保存在 JSON 报告。

## 日期异常审计

| 标记 | 数量 |
| --- | ---: |
| `is_approved_before_purchase` | 0 |
| `is_carrier_before_purchase` | 166 |
| `is_carrier_before_approval` | 1,359 |
| `is_delivered_before_purchase` | 0 |
| `is_delivered_before_carrier` | 23 |
| `is_estimated_before_purchase` | 0 |
| `has_date_anomaly` | 1,382 |

这些异常只被标记，未修改日期或剔除订单。当前主 `delay_days` 仅使用实际送达与预计送达日期；上述异常标记不改变其公式。尤其是 23 条“实际送达早于交运”记录应在后续配送分析前作为敏感性/样本排除候选单独审查，但未经新的明确确认不得自行排除。

## 交付物、风险与回滚

- [视图 SQL](../sql/03_create_clean_views.sql)
- [构建与对账脚本](../src/04_prepare_clean_orders.py)
- 清洗订单 CSV：`data/processed/clean_orders.csv`
- [非敏感汇总 JSON](../reports/validation/t10_clean_orders_summary.json)

回滚仅限删除 T10 新增的 `vw_clean_orders` 和 `clean_orders.csv`，且必须经用户单独确认；不得触碰 T09 视图、原始表或原始 CSV。T11 尚未开始，继续前必须获得新的单独授权。

## 口径澄清 / 勘误（2026-08-07）

本记录中的 `is_delayed = 0 / 1 / NULL` 分布 `89,941 / 6,535 / 2,965` 保持原样。这里的 6,535 是全量订单中 `is_delayed = 1` 的字段分布，不是限制 `is_delivery_eligible = 1` 后的正式配送延迟订单数。

正式配送可用延迟订单数为 6,534，口径为 `is_delivery_eligible = 1 AND delay_days > 0`。两者差异仅为订单 `1950d777989f6a877539f53795b4c3c3`：其状态为 canceled、`delay_days = 12`、`is_delayed = 1`，但 `is_delivery_eligible = 0`。数据、`vw_clean_orders` 视图和字段计算均无错误；该订单应保留在全量字段审计中，但不进入正式配送延迟指标。
