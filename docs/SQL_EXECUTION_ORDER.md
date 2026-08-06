# 一期 SQL 执行顺序与职责

本文件定义一期正式 SQL 的执行顺序。T06 仅建立结构和安全边界；T07 已实现并执行 `sql/01_create_tables.sql`，随后通过 Python 路线完成 7 张原始表导入；T08 已实现并运行只读 `sql/02_data_quality_checks.sql`。`legacy/sql/` 是旧版资产，不属于本顺序，也不得在 `olist_delivery_analysis` 中直接执行。

| 顺序 | 文件 | 当前状态 | 输入 | 目标输出 | 后续完善/验证任务 |
| ---: | --- | --- | --- | --- | --- |
| 00 | `sql/00_create_database.sql` | scaffold | 无 | `olist_delivery_analysis` 数据库 | 后续获授权的数据库初始化步骤 |
| 01 | `sql/01_create_tables.sql` | implemented and verified | 已验证的 CSV 字段和导入设计 | 7 张原始层表、键、索引和关系 | T07 已完成；T08 使用 |
| 02 | `sql/02_data_quality_checks.sql` | implemented and verified | T07 原始层表 | 只读质量检查结果 | T08 已完成；T09/T10 使用 |
| 03 | `sql/03_create_clean_views.sql` | pending implementation | T08–T10 审计和清洗规则 | 可追溯清洗视图 | T09、T10 |
| 04 | `sql/04_create_order_analysis_table.sql` | pending implementation | 已验证的聚合与粒度规则 | 一行一个 `order_id` 的分析表 | T11 |
| 05 | `sql/05_delivery_metrics.sql` | pending implementation | T11 分析表、指标口径 | 配送指标结果 | T12 |
| 06 | `sql/06_review_metrics.sql` | pending implementation | 评价审计、T11 分析表、指标口径 | 评分指标结果 | T12、T15 |
| 07 | `sql/07_segment_analysis.sql` | pending implementation | 分析表、已确认的最低样本量阈值 | 州/品类/卖家/时间细分结果 | T13 |
| 08 | `sql/08_validation_queries.sql` | pending implementation | SQL/Python/Power BI 对账范围 | 只读对账和粒度验证结果 | T16 |

## 执行前条件

1. 用户单独授权数据库操作；`sql/00_create_database.sql` scaffold 不能视为已运行或已验证。
2. 执行后续 SQL 前先确认 MySQL 服务、目标库和数据状态；T07 已将 7 张原始表导入当前数据库。
3. 先完成上一顺序文件的实施与验证，再执行依赖它的文件。
4. 所有正式 SQL 使用 MySQL 8.0.44 兼容语法、`olist_delivery_analysis`、明确样本/粒度约束，并且不含凭据或本机路径。
5. 若字段、阈值或规则尚未确认，保持 pending 状态并停止实施，而非自行补充假设。

## T07/T08 验证状态

- Python 导入路线已将 7 份 CSV 完整导入，七表行数与 CSV 一致；具体计数、约束与 SHA-256 见 `docs/T07_RAW_IMPORT_VERIFICATION.md`。
- `LOAD DATA LOCAL INFILE` 模板已提供于 `sql/IMPORT_LOCAL_INFILE_TEMPLATE.sql`，但当前服务器 `local_infile=OFF`；因此它是已预检的回退路线，未在当前数据库执行。
- T08 的 25 条只读 SQL 语句、12 组 SQL/Python 对账和非敏感汇总结果已完成；详见 `docs/T08_SQL_PYTHON_RECONCILIATION.md`。
- 下一项为 T09 的评价选择与冲突审计；不得将 T08 完成视为已选择订单级主评分、已创建清洗视图或已完成业务分析。
