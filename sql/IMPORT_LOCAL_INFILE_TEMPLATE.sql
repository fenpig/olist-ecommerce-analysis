-- File: IMPORT_LOCAL_INFILE_TEMPLATE.sql
-- Goal: Provide the MySQL Workbench alternative to the Python raw CSV import route.
-- Prerequisites: Execute 00_create_database.sql and 01_create_tables.sql first. Confirm both server and client allow LOCAL INFILE.
-- Safety: Replace each placeholder with a local path only in an uncommitted local copy. Do not put absolute paths, credentials, or secrets in Git.
-- Current status: T07 implementation template; execute only after confirming local_infile and the target database.

USE `olist_delivery_analysis`;
SHOW VARIABLES LIKE 'local_infile';

-- For every block below, replace REPLACE_WITH_LOCAL_CSV_PATH locally. Keep the path out of committed files.
LOAD DATA LOCAL INFILE 'REPLACE_WITH_LOCAL_CSV_PATH'
INTO TABLE `category_translation_raw`
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' ENCLOSED BY '"' ESCAPED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(`product_category_name`, `product_category_name_english`);

LOAD DATA LOCAL INFILE 'REPLACE_WITH_LOCAL_CSV_PATH'
INTO TABLE `customers_raw`
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' ENCLOSED BY '"' ESCAPED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(`customer_id`, `customer_unique_id`, `customer_zip_code_prefix`, `customer_city`, `customer_state`);

LOAD DATA LOCAL INFILE 'REPLACE_WITH_LOCAL_CSV_PATH'
INTO TABLE `products_raw`
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' ENCLOSED BY '"' ESCAPED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(`product_id`, `product_category_name`, @product_name_lenght, @product_description_lenght,
 @product_photos_qty, @product_weight_g, @product_length_cm, @product_height_cm, @product_width_cm)
SET `product_name_lenght` = NULLIF(@product_name_lenght, ''),
    `product_description_lenght` = NULLIF(@product_description_lenght, ''),
    `product_photos_qty` = NULLIF(@product_photos_qty, ''),
    `product_weight_g` = NULLIF(@product_weight_g, ''),
    `product_length_cm` = NULLIF(@product_length_cm, ''),
    `product_height_cm` = NULLIF(@product_height_cm, ''),
    `product_width_cm` = NULLIF(@product_width_cm, '');

LOAD DATA LOCAL INFILE 'REPLACE_WITH_LOCAL_CSV_PATH'
INTO TABLE `orders_raw`
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' ENCLOSED BY '"' ESCAPED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(`order_id`, `customer_id`, `order_status`, `order_purchase_timestamp`, @order_approved_at,
 @order_delivered_carrier_date, @order_delivered_customer_date, `order_estimated_delivery_date`)
SET `order_approved_at` = NULLIF(@order_approved_at, ''),
    `order_delivered_carrier_date` = NULLIF(@order_delivered_carrier_date, ''),
    `order_delivered_customer_date` = NULLIF(@order_delivered_customer_date, '');

LOAD DATA LOCAL INFILE 'REPLACE_WITH_LOCAL_CSV_PATH'
INTO TABLE `order_items_raw`
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' ENCLOSED BY '"' ESCAPED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(`order_id`, `order_item_id`, `product_id`, `seller_id`, `shipping_limit_date`, `price`, `freight_value`);

LOAD DATA LOCAL INFILE 'REPLACE_WITH_LOCAL_CSV_PATH'
INTO TABLE `order_payments_raw`
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' ENCLOSED BY '"' ESCAPED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(`order_id`, `payment_sequential`, `payment_type`, `payment_installments`, `payment_value`);

LOAD DATA LOCAL INFILE 'REPLACE_WITH_LOCAL_CSV_PATH'
INTO TABLE `order_reviews_raw`
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' ENCLOSED BY '"' ESCAPED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(`review_id`, `order_id`, `review_score`, @review_comment_title, @review_comment_message,
 `review_creation_date`, `review_answer_timestamp`)
SET `review_comment_title` = NULLIF(@review_comment_title, ''),
    `review_comment_message` = NULLIF(@review_comment_message, '');

-- Verify the seven table counts after either import route. Compare them with docs/DATA_INVENTORY.md.
SELECT 'category_translation_raw' AS table_name, COUNT(*) AS row_count FROM `category_translation_raw`
UNION ALL SELECT 'customers_raw', COUNT(*) FROM `customers_raw`
UNION ALL SELECT 'products_raw', COUNT(*) FROM `products_raw`
UNION ALL SELECT 'orders_raw', COUNT(*) FROM `orders_raw`
UNION ALL SELECT 'order_items_raw', COUNT(*) FROM `order_items_raw`
UNION ALL SELECT 'order_payments_raw', COUNT(*) FROM `order_payments_raw`
UNION ALL SELECT 'order_reviews_raw', COUNT(*) FROM `order_reviews_raw`;
