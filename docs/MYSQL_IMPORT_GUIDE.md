# T07 MySQL 原始数据导入指南

本指南将当前 7 份原始 CSV 导入一期正式数据库 `olist_delivery_analysis`。原始目录始终只读；导入前后应使用 Git 状态和 SHA-256 核对，不能编辑 CSV 以“修复”导入错误。

## 前置条件

1. 使用项目 `.venv` 和非 root 的本地项目账号；真实 `.env` 不得提交或输出。
2. 已单独执行并确认 `sql/00_create_database.sql` 和 `sql/01_create_tables.sql`；后者只建表，不导入或删除数据。
3. 数据库必须是 `olist_delivery_analysis`，字符集为 `utf8mb4`。
4. 当前可导入的 CSV 只有 7 份；`olist_sellers_dataset.csv` 和 `olist_geolocation_dataset.csv` 尚缺失，不能自行补造空表或推断卖家地域。

| 目标表 | CSV | 预期行数 |
| --- | --- | ---: |
| `category_translation_raw` | `product_category_name_translation.csv` | 71 |
| `customers_raw` | `olist_customers_dataset.csv` | 99,441 |
| `products_raw` | `olist_products_dataset.csv` | 32,951 |
| `orders_raw` | `olist_orders_dataset.csv` | 99,441 |
| `order_items_raw` | `olist_order_items_dataset.csv` | 112,650 |
| `order_payments_raw` | `olist_order_payments_dataset.csv` | 103,886 |
| `order_reviews_raw` | `olist_order_reviews_dataset.csv` | 99,224 |

`order_reviews_raw` 使用自增 `review_row_id` 作为物理主键：当前 `review_id` 存在重复，不能作为主键。所有原始 CSV 列仍完整保留，后续 T09 才实现订单级评分选择和审计。

## 路线 A：Python（默认备用且推荐）

先只读验证 CSV 标头和行数：

```powershell
.\.venv\Scripts\python.exe src\01_load_raw_to_mysql.py --dry-run
```

确认数据库的七张表均为空后执行导入：

```powershell
.\.venv\Scripts\python.exe src\01_load_raw_to_mysql.py
```

脚本使用参数化批量插入，默认拒绝覆盖任一非空原始表。只有需要完整重新导入且已确认将替换现有原始层时，才显式使用：

```powershell
.\.venv\Scripts\python.exe src\01_load_raw_to_mysql.py --replace-existing
```

每张表的 `Loaded ...` 行和最后的 `Import complete` 即为本次可重跑导入日志；应保存脱敏终端输出或在任务记录中登记行数。发生字段、类型、连接或外键错误时，脚本会回滚整个事务并保留原始 CSV。

## 路线 B：MySQL Workbench 的 `LOAD DATA LOCAL INFILE`

1. 先运行 `SHOW VARIABLES LIKE 'local_infile';`，并确认 Workbench 客户端也允许 `LOCAL INFILE`。
2. 将 `sql/IMPORT_LOCAL_INFILE_TEMPLATE.sql` 复制为未提交的本地文件。
3. 在本地副本中逐段填入对应 CSV 的绝对路径，保留顺序：品类映射、客户、商品、订单、订单明细、付款、评价。绝对路径不得写回版本库。
4. 逐段执行；如 `local_infile` 被禁用、路径/编码不兼容或行数异常，停止并改用路线 A，不修改原始 CSV。
5. 执行模板末尾的七表计数查询，与本指南和 `docs/DATA_INVENTORY.md` 对账。

两条路线不能混合向同一批非空表追加数据。若此前导入不完整，先记录实际表行数、错误和处理决定；不要直接重新运行模板造成重复数据。

## 导入后的最小验证

1. 七张表行数分别与上表一致。
2. `orders_raw`、`customers_raw`、`products_raw`、订单明细、付款和评价的外键均可建立，说明当前已核验的关系没有孤儿键。
3. `git status --short data/raw` 为空；原始 CSV 的 SHA-256 与导入前记录一致。
4. T07 完成后暂停；T08 才能实现和执行可复现质量检查。
