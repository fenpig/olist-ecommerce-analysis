# 数据字典（第一阶段）

本项目只在第一阶段使用下列 7 张表；地理位置表和卖家表可在扩展阶段加入。

| 文件 | 主键 | 用途 | 关键字段 |
| --- | --- | --- | --- |
| `olist_orders_dataset.csv` | `order_id` | 订单生命周期 | 下单、审批、发货、交付、预计交付时间、状态 |
| `olist_order_items_dataset.csv` | `order_id` + `order_item_id` | 商品明细与收入 | 商品、卖家、价格、运费 |
| `olist_order_payments_dataset.csv` | `order_id` + `payment_sequential` | 支付方式与金额 | 支付类型、分期数、支付金额 |
| `olist_order_reviews_dataset.csv` | `review_id` | 客户体验 | 评分、评论创建与回复时间 |
| `olist_customers_dataset.csv` | `customer_id` | 客户与地区 | `customer_unique_id`、州、城市 |
| `olist_products_dataset.csv` | `product_id` | 商品属性 | 品类、重量、尺寸 |
| `product_category_name_translation.csv` | `product_category_name` | 品类英文映射 | 英文品类名称 |

## 口径约定

- **GMV**：已交付订单的商品价格与运费之和；不以支付金额代替，避免分期记录造成重复。
- **客户**：用 `customer_unique_id` 识别真实客户，不能只使用每单不同的 `customer_id`。
- **交付时长**：`order_delivered_customer_date - order_purchase_timestamp`，单位为天。
- **延迟订单**：实际交付日晚于预计交付日；未交付订单不计入该指标分母。
- **复购客户**：在分析期内成功购买至少 2 个已交付订单的 `customer_unique_id`。
