# T08 SQL/Python 只读对账记录

验证日期：2026-08-06  
范围：7 份 `data/raw/*.csv` 与 `olist_delivery_analysis` 的 7 张 T07 原始表。

## 只读边界

`src/02_validate_raw_data.py` 从 `.env` 读取本地配置但不输出密码或完整连接 URL；连接后设置 MySQL 只读事务。其公共查询入口仅允许 `SELECT`、`SHOW`、`DESCRIBE`、`EXPLAIN`（以及只读 CTE），并拒绝 DDL/DML 关键字。脚本结束时回滚并关闭连接。

`sql/02_data_quality_checks.sql` 共执行 25 条只读语句；未执行 `INSERT`、`UPDATE`、`DELETE`、`TRUNCATE`、`CREATE`、`ALTER` 或 `DROP`，未创建表、视图或临时表。

## 对账结果

12 组 SQL/Python 对账全部通过：

1. 7 张表行数；
2. 6 个主键/候选键重复组；
3. 10 个关键字段缺失数；
4. 5 条外键的孤立键数；
5. `order_status` 分布；
6. `review_score` 分布；
7. 多评价、评分冲突和单订单最大评价数；
8. 5 个订单日期字段边界；
9. 2 个评价日期字段边界；
10. 月度订单数；
11. 主分析样本漏斗；
12. 品类翻译的类别数和未翻译商品行数。

所有计数、分类分布和日期边界完全一致；未涉及金额汇总，因此不需要 0.01 的金额容差。机器可读明细：`reports/validation/t08_reconciliation_summary.json`。

## CSV/MySQL 行数

| 表 | CSV 行数 | MySQL 行数 |
| --- | ---: | ---: |
| `category_translation_raw` | 71 | 71 |
| `customers_raw` | 99,441 | 99,441 |
| `products_raw` | 32,951 | 32,951 |
| `orders_raw` | 99,441 | 99,441 |
| `order_items_raw` | 112,650 | 112,650 |
| `order_payments_raw` | 103,886 | 103,886 |
| `order_reviews_raw` | 99,224 | 99,224 |

## 运行命令与暂停点

```powershell
.\.venv\Scripts\python.exe src\02_validate_raw_data.py
```

T08 已完成并暂停。下一项 T09 需获得新的单独授权；T08 未实现最新评价选择、未创建清洗视图、未生成订单级分析表。
