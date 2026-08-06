# T07 原始表与导入验证记录

验证日期：2026-08-06  
数据库：`olist_delivery_analysis`（MySQL 8.0.44，`utf8mb4` / `utf8mb4_unicode_ci`）

## 实施范围

- 已执行 `sql/01_create_tables.sql`：创建 7 张 InnoDB 原始表、5 个外键和 1 个 `review_score` 检查约束。
- 已执行 `src/01_load_raw_to_mysql.py --dry-run`：逐文件验证标头与行数，不连接数据库且不写入数据。
- 已执行 `src/01_load_raw_to_mysql.py`：参数化批量插入并在单一事务中提交；导入前 7 张原始表均为空。
- 已检查 `SHOW VARIABLES LIKE 'local_infile'`：结果为 `OFF`。因此未运行 `LOAD DATA LOCAL INFILE` 模板，按既定回退策略使用 Python 导入路线。

首次用于执行 SQL 的临时辅助命令错误地按注释分号切分脚本，在第一个 `CREATE TABLE` 前停止；之后改为忽略注释行的执行方式并成功完成建表。该失败没有创建表或写入 CSV/数据库记录。

## 输入、输出与对账

| 目标表 | CSV | CSV 行数 | MySQL 行数 | 结果 |
| --- | --- | ---: | ---: | --- |
| `category_translation_raw` | `product_category_name_translation.csv` | 71 | 71 | 一致 |
| `customers_raw` | `olist_customers_dataset.csv` | 99,441 | 99,441 | 一致 |
| `products_raw` | `olist_products_dataset.csv` | 32,951 | 32,951 | 一致 |
| `orders_raw` | `olist_orders_dataset.csv` | 99,441 | 99,441 | 一致 |
| `order_items_raw` | `olist_order_items_dataset.csv` | 112,650 | 112,650 | 一致 |
| `order_payments_raw` | `olist_order_payments_dataset.csv` | 103,886 | 103,886 | 一致 |
| `order_reviews_raw` | `olist_order_reviews_dataset.csv` | 99,224 | 99,224 | 一致 |
| **合计** | **7 份 CSV** | **547,664** | **547,664** | **一致** |

约束检查：`FOREIGN_KEY_COUNT=5`，`CHECK_CONSTRAINT_COUNT=1`。评价表以自增 `review_row_id` 作物理主键，完整保留重复的 `review_id`；这与当前多评事实一致，订单级评分选择仍留待 T09。

## 可复现命令

```powershell
.\.venv\Scripts\python.exe src\01_load_raw_to_mysql.py --dry-run
.\.venv\Scripts\python.exe src\01_load_raw_to_mysql.py
```

默认运行若发现任一原始表非空会失败并不写入。只有在有意完整替换原始层时，才使用 `--replace-existing`；该开关会在同一事务中按依赖逆序清空 7 张原始表并重载，不能与 `LOAD DATA LOCAL INFILE` 路线混用。

## 原始 CSV 完整性

导入前后均未修改 `data/raw/`；`git status --short data/raw` 无输出。导入后 SHA-256：

| 文件 | SHA-256 |
| --- | --- |
| `olist_customers_dataset.csv` | `983A422239E1712DED753B3BF9ECF47DC73F144D306029DCFA99E70A226883D2` |
| `olist_order_items_dataset.csv` | `0BC4D068C4FE38CBB01BD90E8746E3C613FE7B4BAEF75FAB7B0E329701C3E279` |
| `olist_order_payments_dataset.csv` | `4F713964F2815DBBAA40B9488268C55AAC3627BFCE5AA96CF58D1F3616DE3CC0` |
| `olist_order_reviews_dataset.csv` | `012B61C7593E34F51FA614EFDF802B9C7056CE6AAE5307DDB93236E7CFC797D7` |
| `olist_orders_dataset.csv` | `8DF58EF3D2D7E9944010F7BEECD9B75367F5588EC6E3C91CEC19AE3345EF9ECF` |
| `olist_products_dataset.csv` | `3E6569628A17FBC75FD206EE357B59E20364B9AFA90F5B6CD5B4D624C58AA9CC` |
| `product_category_name_translation.csv` | `A81F0D1F27B27E7293F761BC79E3CE8F348EE39C4B3ED3E49BDE38F478586278` |

## 任务边界与下一步

T07 不清洗数据、不计算指标、不选择订单级评分，也不执行 `sql/02`–`08`。下一任务为 T08：实现并运行可复现、只读的数据质量检查，保留异常样本并将 SQL/Python 关键计数对账。
