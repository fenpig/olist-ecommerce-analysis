-- File: 01_create_tables.sql
-- Goal: Create the seven raw-layer tables used by the Phase 1 Olist delivery and customer-satisfaction analysis.
-- Input objects: Database `olist_delivery_analysis` created by 00_create_database.sql and the seven verified CSV schemas.
-- Output objects: Raw MySQL tables, primary keys, relationship constraints, and analysis-supporting indexes.
-- Prerequisites: Explicit authorization to execute SQL; MySQL 8.0.44; empty or intentionally prepared target database.
-- Repeatable: Yes. Existing tables are preserved through IF NOT EXISTS; this script does not load or delete data.
-- Implementation task: T07.
-- Current status: implemented and verified in T07.
-- Safety: No credentials, local paths, DROP statements, or data-changing statements are included. Raw CSV files remain read-only.

USE `olist_delivery_analysis`;

CREATE TABLE IF NOT EXISTS `category_translation_raw` (
  `product_category_name` VARCHAR(100) NOT NULL,
  `product_category_name_english` VARCHAR(100) NOT NULL,
  PRIMARY KEY (`product_category_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `customers_raw` (
  `customer_id` CHAR(32) NOT NULL,
  `customer_unique_id` CHAR(32) NOT NULL,
  `customer_zip_code_prefix` INT UNSIGNED NOT NULL,
  `customer_city` VARCHAR(100) NOT NULL,
  `customer_state` CHAR(2) NOT NULL,
  PRIMARY KEY (`customer_id`),
  KEY `idx_customers_raw_unique_id` (`customer_unique_id`),
  KEY `idx_customers_raw_state` (`customer_state`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `products_raw` (
  `product_id` CHAR(32) NOT NULL,
  `product_category_name` VARCHAR(100) NULL,
  `product_name_lenght` INT UNSIGNED NULL,
  `product_description_lenght` INT UNSIGNED NULL,
  `product_photos_qty` INT UNSIGNED NULL,
  `product_weight_g` INT UNSIGNED NULL,
  `product_length_cm` INT UNSIGNED NULL,
  `product_height_cm` INT UNSIGNED NULL,
  `product_width_cm` INT UNSIGNED NULL,
  PRIMARY KEY (`product_id`),
  KEY `idx_products_raw_category` (`product_category_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `orders_raw` (
  `order_id` CHAR(32) NOT NULL,
  `customer_id` CHAR(32) NOT NULL,
  `order_status` VARCHAR(20) NOT NULL,
  `order_purchase_timestamp` DATETIME NOT NULL,
  `order_approved_at` DATETIME NULL,
  `order_delivered_carrier_date` DATETIME NULL,
  `order_delivered_customer_date` DATETIME NULL,
  `order_estimated_delivery_date` DATETIME NOT NULL,
  PRIMARY KEY (`order_id`),
  KEY `idx_orders_raw_customer_id` (`customer_id`),
  KEY `idx_orders_raw_status_purchase` (`order_status`, `order_purchase_timestamp`),
  CONSTRAINT `fk_orders_raw_customer`
    FOREIGN KEY (`customer_id`) REFERENCES `customers_raw` (`customer_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `order_items_raw` (
  `order_id` CHAR(32) NOT NULL,
  `order_item_id` INT UNSIGNED NOT NULL,
  `product_id` CHAR(32) NOT NULL,
  `seller_id` CHAR(32) NOT NULL,
  `shipping_limit_date` DATETIME NOT NULL,
  `price` DECIMAL(12, 2) NOT NULL,
  `freight_value` DECIMAL(12, 2) NOT NULL,
  PRIMARY KEY (`order_id`, `order_item_id`),
  KEY `idx_order_items_raw_product_id` (`product_id`),
  KEY `idx_order_items_raw_seller_id` (`seller_id`),
  CONSTRAINT `fk_order_items_raw_order`
    FOREIGN KEY (`order_id`) REFERENCES `orders_raw` (`order_id`),
  CONSTRAINT `fk_order_items_raw_product`
    FOREIGN KEY (`product_id`) REFERENCES `products_raw` (`product_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `order_payments_raw` (
  `order_id` CHAR(32) NOT NULL,
  `payment_sequential` INT UNSIGNED NOT NULL,
  `payment_type` VARCHAR(30) NOT NULL,
  `payment_installments` INT UNSIGNED NOT NULL,
  `payment_value` DECIMAL(12, 2) NOT NULL,
  PRIMARY KEY (`order_id`, `payment_sequential`),
  KEY `idx_order_payments_raw_type` (`payment_type`),
  CONSTRAINT `fk_order_payments_raw_order`
    FOREIGN KEY (`order_id`) REFERENCES `orders_raw` (`order_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `order_reviews_raw` (
  `review_row_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `review_id` CHAR(32) NOT NULL,
  `order_id` CHAR(32) NOT NULL,
  `review_score` TINYINT UNSIGNED NOT NULL,
  `review_comment_title` TEXT NULL,
  `review_comment_message` TEXT NULL,
  `review_creation_date` DATETIME NOT NULL,
  `review_answer_timestamp` DATETIME NOT NULL,
  PRIMARY KEY (`review_row_id`),
  KEY `idx_order_reviews_raw_review_id` (`review_id`),
  KEY `idx_order_reviews_raw_order_id` (`order_id`),
  CONSTRAINT `chk_order_reviews_raw_score` CHECK (`review_score` BETWEEN 1 AND 5),
  CONSTRAINT `fk_order_reviews_raw_order`
    FOREIGN KEY (`order_id`) REFERENCES `orders_raw` (`order_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
