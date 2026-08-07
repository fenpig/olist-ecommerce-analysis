# T11：订单级与订单商品明细分析数据验收记录

验收日期：2026-08-07
状态：已完成；T12 未开始。

## 新增对象与粒度

T11 新增四个可重建视图：`vw_order_items_aggregated`、`vw_order_payments_aggregated`、`vw_order_analysis`、`vw_order_item_analysis`。未创建永久表或执行 DML。

- `vw_order_analysis` 和 `order_analysis.csv`：99,441 行，一行一个 `order_id`，无缺失或重复。
- `vw_order_item_analysis` 和 `order_item_analysis.csv`：112,650 行，一行一个原始 `order_id + order_item_id`，组合键无重复。
- 订单层以 `vw_clean_orders` 为主表；商品、支付分别先聚合后才连接，避免多商品、多卖家、多支付放大订单指标。

客户通过 `customer_id` 连接，99,441 个订单均匹配；未用 `customer_unique_id` 作为连接键。类别翻译和客户键均在连接前验证唯一。

## 商品、支付与金额审计

| 项目 | 结果 |
| --- | ---: |
| 有商品 / 无商品订单 | 98,666 / 775 |
| 多商品 / 多产品 / 多卖家 / 多类别订单 | 9,803 / 3,236 / 1,278 / 727 |
| 有支付 / 无支付订单 | 99,440 / 1 |
| 多支付记录 / 多支付类型订单 | 2,961 / 2,246 |
| 商品金额 / 运费 / 支付总额 | 13,591,643.70 / 2,251,909.54 / 16,008,872.12 |
| 商品明细 `item_total` 总额 | 15,843,553.24 |
| 付款差额绝对值 <= 0.01 / 正差 / 负差 | 98,296 / 286 / 83 |

`payment_difference` 仅在同时存在商品和支付记录时计算；缺失商品或支付记录保留为缺失并单独计数。金额 SQL/Python 对账容差为绝对值 0.01。多支付类型的 `primary_payment_type` 先按订单—类型汇总支付金额，取金额最大者；同额时按 `payment_type` 升序稳定选择，且保留多类型标记。

商品明细中 `seller_id`、`product_id` 缺失均为 0；类别缺失 1,603 行，类别翻译缺失 24 行，均被保留标记而未删除。

## T10 字段与日期异常传播

订单层和商品明细层完整传播 T10 的延迟、评分、样本与日期异常字段：`has_date_anomaly=1` 为 1,382 个订单，`is_delivered_before_carrier=1` 为 23 个订单。新增 `is_transit_duration_eligible` 仅供未来依赖交运日期的时长指标使用；它不改写 `is_delivery_eligible`、`is_review_relation_eligible`，也不删除异常订单。

延迟分类和选择后评分分布与 T10 保持一致。T11 未做统计检验、最低样本量阈值、业务结论、Power BI 或 T12 工作。

## 交付物与回滚

- [T11 视图 SQL](../sql/04_create_order_analysis_table.sql)
- [构建与对账脚本](../src/05_build_analysis_datasets.py)
- 订单级 CSV：`data/processed/order_analysis.csv`
- 商品明细 CSV：`data/processed/order_item_analysis.csv`
- [非敏感汇总 JSON](../reports/validation/t11_analysis_datasets_summary.json)

回滚仅限在用户单独确认后删除这四个 T11 视图和两个 T11 CSV；不得触碰原始表、T09/T10 视图、原始 CSV、README 或 PBIX。
