-- MySQL 8.0+。在原始 CSV 已导入后执行，用于创建高频关联字段的索引。
USE olist_analysis;

-- 导入原始表后，为高频关联字段建立索引。
CREATE INDEX idx_orders_customer_id ON orders_raw (customer_id);
CREATE INDEX idx_orders_status_purchase ON orders_raw (order_status, order_purchase_timestamp);
CREATE INDEX idx_order_items_order_id ON order_items_raw (order_id);
CREATE INDEX idx_order_items_product_id ON order_items_raw (product_id);
CREATE INDEX idx_payments_order_id ON order_payments_raw (order_id);
CREATE INDEX idx_reviews_order_id ON order_reviews_raw (order_id);
CREATE INDEX idx_customers_unique_id ON customers_raw (customer_unique_id);
