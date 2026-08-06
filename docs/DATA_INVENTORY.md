# Olist 数据盘点（暂定口径的可行性审查）

审查日期：2026-08-05  
审查范围：`data/raw/` 中当前可见的原始 CSV。仅做读取与核验；未修改任何 CSV，未做正式清洗或业务推断。

## 1. 文件清单与标准清单差异

本阶段采用的标准 Olist 文件清单为 9 个文件（按项目当前需求定义）。目录中发现 7 个，缺少 2 个。

| 标准文件 | 当前状态 | 缺失对本项目的影响 |
| --- | --- | --- |
| `olist_customers_dataset.csv` | 已存在 | 可关联订单至客户所在州/城市/邮编前缀。 |
| `olist_orders_dataset.csv` | 已存在 | 履约日期、订单状态与延迟计算的核心表。 |
| `olist_order_items_dataset.csv` | 已存在 | 可关联商品、品类及 `seller_id`；可做按卖家 ID、品类的订单明细分析。 |
| `olist_order_payments_dataset.csv` | 已存在 | 可作为付款方式、金额等潜在控制变量；一单可多条付款记录。 |
| `olist_order_reviews_dataset.csv` | 已存在 | 客户评分主指标；一单可能多条评价，见质量报告。 |
| `olist_products_dataset.csv` | 已存在 | 可做品类及商品属性分析。 |
| `product_category_name_translation.csv` | 已存在 | 可将大多数葡语品类翻译为英语名称。 |
| `olist_sellers_dataset.csv` | **缺失** | 不妨碍按 `seller_id` 聚合履约/评分，但无法核验卖家主数据，也不能分析卖家所在州、城市、邮编或卖家地域与配送表现的关系。 |
| `olist_geolocation_dataset.csv` | **缺失** | 客户表仍可按州分析；但无法做邮编到经纬度、客户—卖家距离、精细地理聚合及地理主数据质量核验。 |

结论：现有数据足以启动订单履约、客户评分、州级地区、品类和卖家 ID 层面的可行性分析。卖家地域和距离类问题须待缺失两表补齐后再纳入范围。

## 2. 当前文件、规模与字段

以下数据类型为本次 CSV 读取时的推断类型；日期字段目前是文本，需在后续分析层显式解析为日期时间，原始文件保持不变。

| 文件 | 行数 | 列数 | 字段（推断类型） |
| --- | ---: | ---: | --- |
| `olist_customers_dataset.csv` | 99,441 | 5 | `customer_id`(str), `customer_unique_id`(str), `customer_zip_code_prefix`(int64), `customer_city`(str), `customer_state`(str) |
| `olist_orders_dataset.csv` | 99,441 | 8 | `order_id`(str), `customer_id`(str), `order_status`(str), `order_purchase_timestamp`(str), `order_approved_at`(str), `order_delivered_carrier_date`(str), `order_delivered_customer_date`(str), `order_estimated_delivery_date`(str) |
| `olist_order_items_dataset.csv` | 112,650 | 7 | `order_id`(str), `order_item_id`(int64), `product_id`(str), `seller_id`(str), `shipping_limit_date`(str), `price`(float64), `freight_value`(float64) |
| `olist_order_payments_dataset.csv` | 103,886 | 5 | `order_id`(str), `payment_sequential`(int64), `payment_type`(str), `payment_installments`(int64), `payment_value`(float64) |
| `olist_order_reviews_dataset.csv` | 99,224 | 7 | `review_id`(str), `order_id`(str), `review_score`(int64), `review_comment_title`(str), `review_comment_message`(str), `review_creation_date`(str), `review_answer_timestamp`(str) |
| `olist_products_dataset.csv` | 32,951 | 9 | `product_id`(str), `product_category_name`(str), `product_name_lenght`(float64), `product_description_lenght`(float64), `product_photos_qty`(float64), `product_weight_g`(float64), `product_length_cm`(float64), `product_height_cm`(float64), `product_width_cm`(float64) |
| `product_category_name_translation.csv` | 71 | 2 | `product_category_name`(str), `product_category_name_english`(str) |

## 3. 候选主键、粒度与重复检查

| 表 | 建议粒度 / 候选键 | 键空值行 | 键重复行 | 完全重复行 | 结论 |
| --- | --- | ---: | ---: | ---: | --- |
| customers | 客户订单地址：`customer_id` | 0 | 0 | 0 | 可作为客户表主键。`customer_unique_id` 是跨订单客户标识，不应假定唯一。 |
| orders | 订单：`order_id` | 0 | 0 | 0 | 可作为订单表主键。 |
| order_items | 订单明细：`order_id`, `order_item_id` | 0 | 0 | 0 | 复合键唯一。 |
| order_payments | 付款序列：`order_id`, `payment_sequential` | 0 | 0 | 0 | 复合键唯一；不可直接与订单一对一连接后汇总金额。 |
| order_reviews | 评价记录：`review_id` | 0 | 814 | 0 | `review_id` **不唯一**，不能单独用作主键；另有一单多评，详见质量报告。 |
| products | 商品：`product_id` | 0 | 0 | 0 | 可作为商品表主键。 |
| category translation | 品类名称：`product_category_name` | 0 | 0 | 0 | 可作为映射表键。 |

## 4. 已核验的表关系

匹配率均按左侧非空去重键计算，方向只表示本次核验方向。

| 关系 | 左侧去重键数 | 匹配数 | 匹配率 | 备注 |
| --- | ---: | ---: | ---: | --- |
| orders.`customer_id` → customers.`customer_id` | 99,441 | 99,441 | 100.0000% | 客户关联完整。 |
| order_items.`order_id` → orders.`order_id` | 98,666 | 98,666 | 100.0000% | 明细不存在孤儿订单键。 |
| order_payments.`order_id` → orders.`order_id` | 99,440 | 99,440 | 100.0000% | 付款不存在孤儿订单键。 |
| order_reviews.`order_id` → orders.`order_id` | 98,673 | 98,673 | 100.0000% | 评价不存在孤儿订单键。 |
| order_items.`product_id` → products.`product_id` | 32,951 | 32,951 | 100.0000% | 商品关联完整。 |
| products.`product_category_name` → translation.`product_category_name` | 73 | 71 | 97.2603% | 缺少 `pc_gamer`、`portateis_cozinha_e_preparadores_de_alimentos` 两个映射；涉及 13 个商品记录、24 条订单明细。 |
| order_items.`seller_id` → sellers.`seller_id` | 3,095 | — | 不可测试 | 卖家表当前缺失。 |

从订单主表反向查看覆盖：99,441 单中 98,666 单有订单明细（99.2206%），99,440 单有付款记录（99.9990%），98,673 单有至少一条评价（99.2277%）。这些不是孤儿键问题，但会影响相应主题的样本分母。

## 5. 当前可回答与暂不可回答的问题

### 当前可回答（经后续口径确认与分析验证）

- 已送达订单的实际送达、预计送达和连续 `delay_days` 的分布；
- 延迟分层与评分、低评分率之间的描述性关系；
- 客户州级的履约和评分比较；
- 商品品类的平均配送时间、延迟率与评分比较；
- 基于 `seller_id` 的卖家履约和评分筛查；
- 订单状态、付款方式、商品价格/运费和部分商品属性作为候选分层或控制变量。

### 暂不可回答或只能部分回答

- 卖家所在地区、卖家—客户距离、卖家地理特征：需 `olist_sellers_dataset.csv` 与 `olist_geolocation_dataset.csv`；
- 精确到经纬度/邮编的地理效率、距离对延迟/评分的影响：需 `olist_geolocation_dataset.csv`，且需确认邮编匹配规则；
- 将“配送延迟造成低评分”表述为因果结论：现有观察性数据最多先验证关联，尚无实验或明确识别设计；
- 一单多条评价时的单一评分：需在需求中确认保留规则，不能静默去重。

## 6. 建议补充与下一道门槛

1. 补齐 `olist_sellers_dataset.csv`，随后重跑卖家关联、卖家地理维度和主键检查。
2. 补齐 `olist_geolocation_dataset.csv`，随后确认是否真的需要“距离”指标，以及邮编前缀与经纬度的聚合规则。
3. 在正式关系分析前确认两项口径：一单多评的处理，以及含时间戳的 `delay_days` 如何落入整数日延迟分层。后一项已有 1,292 单落入现行分类空档，详见质量报告。

## 7. T08 可复现盘点复核（2026-08-06）

T08 在只读 MySQL 事务中重新读取 7 份 CSV 与 7 张原始表。CSV/MySQL 行数逐表完全一致，原始 CSV 的 SHA-256 与 T07 基线一致，未发现新增表、视图或分析对象。

`order_reviews_raw` 有 8 个 MySQL 字段而 CSV 有 7 个字段，差异仅为 T07 建表时生成的物理主键 `review_row_id`；所有 CSV 原字段均完整保留。其余 6 张表的 CSV/MySQL 列数一致。每张表的字段、CSV 推断类型、MySQL 类型、主键/候选键、外键、重复、缺失、数值范围和日期范围均已写入非敏感聚合结果 `reports/validation/t08_reconciliation_summary.json`。

已声明的 5 条外键均无孤立键：订单—客户、明细—订单、明细—商品、付款—订单、评价—订单均为 100% 匹配。`seller_id` 仍不能与卖家主数据匹配；品类翻译为 71/73 个非空品类，未翻译 `pc_gamer` 与 `portateis_cozinha_e_preparadores_de_alimentos`，涉及 13 个商品和 24 条订单明细。卖家地域和客户—卖家距离仍不在当前数据支持范围内。
