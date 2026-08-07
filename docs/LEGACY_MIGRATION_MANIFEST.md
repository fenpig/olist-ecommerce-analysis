# 遗留资产与迁移清单（T01 实施基线）

记录时间：2026-08-05  
任务状态：T01 已执行；本文件只记录现状与未来目标路径，**没有移动、重命名、删除或覆盖任何遗留文件**。

## 1. Git 恢复点与工作区保护

- 仓库分支：`main`
- 基线提交：`4564602f8a072a2b3497c3504eb54089aecab705`
- 建立方式：显式恢复点，而非新建提交。原因是 T01 开始前工作区已有用户/既有未提交修改，不能将其混入自动提交。
- T01 开始前已修改的跟踪文件：`README.md`、`dashboard/olist_ecommerce_dashboard.pbix`。
- T01 开始前未跟踪的项目文档：`AGENTS.md`、`docs/DATA_INVENTORY.md`、`docs/DATA_QUALITY_REPORT.md`、`docs/DECISIONS.md`、`docs/ENVIRONMENT_SETUP.md`、`docs/METRICS.md`、`docs/PROJECT_REQUIREMENTS.md`、`docs/TASK_PLAN.md`。

恢复/核对原则：先使用下方 SHA-256 与当前文件比对；需要恢复跟踪文件时仅在用户确认的精确路径上使用 Git 的非批量操作。不得使用会丢失用户改动的 `git reset --hard` 或广泛 `git checkout`。

## 2. T01 文件指纹

| 当前路径 | 大小（字节） | SHA-256 |
| --- | ---: | --- |
| `README.md` | 7,004 | `77E4417DB45ED8FB718648946806750CE9329D9F11B7A844BB0D9B42D7049BAB` |
| `.env.example` | 189 | `5627038D704C170DD8655BC525C964C092ED6DE431CFED78F8948AE5624CB440` |
| `requirements.txt` | 118 | `2AD2E91F8BEE9B75445035A14B22C8DA18DC05FE43790A646FD5F18C9F0C54FF` |
| `sql/00_create_database.sql` | 99 | `5DB77A649E5F53B2CA528C758903A6EDA71BB8B78ACB0D7B6E52DDFF2C2C50C0` |
| `sql/01_schema.sql` | 691 | `1E3DDB1A42F2ACAC4EDCEAF358F892FCA80F0E72BDB39D0366BEDB4C3F96B459` |
| `sql/02_analysis_queries.sql` | 4,007 | `E8AB96947C2112AFF669E10C08D131FC83A4AFABCB787FEB618C111D6AAFA39E` |
| `src/01_data_quality.py` | 4,765 | `37271BD35CD61656B59B7CC4412CC03171D75E4652790D0672C2ABA19B25A180` |
| `src/02_build_analysis_tables.py` | 5,667 | `49A49BE058E4DC2A7F4C9EF6D48717001362F59ECF1C8C4828D8A4E7090EABFF` |
| `src/03_load_to_mysql.py` | 1,927 | `1C333C9C34724445911A606C99CB9E9701BC447EE7F6ACEB47113AADF5CAD7AD` |
| `data/processed/order_fact.csv` | 31,055,551 | `34327E8DC84EA7BA95D8C14118E6DF7B70C881BEB4F3AB634F9900C1E76CC07D` |
| `data/processed/order_item_fact.csv` | 34,420,521 | `729BE549250EB476866A1ED802538E225FD01BC893183D090A5BBBB1DFF8DF7F` |
| `data/processed/rfm_customers.csv` | 4,537,816 | `C983071A6F5EB5E50353E325B3C5307BBF87B362AFAE00454D483087DCAE54AA` |
| `dashboard/olist_ecommerce_dashboard.pbix` | 31,510,608 | `44336BB1F1154CB620572930DD6A80F24F8A96F6C3309E429964DFEDFDF53437` |

`.env` 的存在和忽略状态已核对，但其内容未读取、未打印、未纳入指纹。

## 3. 遗留资产、计划目标路径与移动前置条件

| 当前路径 | 当前用途/冲突 | 计划目标路径或处理 | 允许执行任务 | 移动/修改前置条件 |
| --- | --- | --- | --- | --- |
| `.venv/` | 失效，指向不存在的 Python 3.12 | `.venv_broken_backup_20260805/` | T02 | 先确认目标路径不存在、记录启动错误、更新 `.gitignore`；只重命名，不删除。 |
| `requirements.txt` | 旧的宽松依赖，缺 SciPy，未验证 | 先复制到 `legacy/requirements.pre_validation.txt`，再在原路径写入已验证固定版 | T03 | 复制指纹一致后才更新原文件；不猜测版本。 |
| `.env.example` | 历史数据库名 `olist_analysis` | **T04 已在原路径安全迁移**；修改前哈希和回滚方式见第 8 节 | T04（完成） | 只处理示例文件；绝不读取/移动 `.env`。 |
| `sql/00_create_database.sql` | 历史库名 `olist_analysis`，与正式同名文件冲突 | `legacy/sql/00_create_database.sql` | T06 | 先记录哈希和目标，再使用 `git mv` 移动旧文件；新正式同名文件随后在 `sql/` 创建。 |
| `sql/01_schema.sql` | 旧的索引脚本，不符合正式编号 | `legacy/sql/01_schema.sql` | T06 | 先建立正式 `sql/01_create_tables.sql`，再移动。 |
| `sql/02_analysis_queries.sql` | 旧经营/RFM 查询，不符合一期问题 | `legacy/sql/02_analysis_queries.sql` | T06 | 先建立正式 `sql/02_data_quality_checks.sql`，再移动。 |
| `src/01_data_quality.py` | 遗留质量逻辑、旧评价键假设待复核 | `legacy/src/01_data_quality.py` | T06/T08 | 先完成正式脚本命名和质量规则设计，再移动。 |
| `src/02_build_analysis_tables.py` | 遗留分析表逻辑 | `legacy/src/02_build_analysis_tables.py` | T06/T11 | 先建立新订单级/明细级设计，再移动。 |
| `src/03_load_to_mysql.py` | 遗留导入逻辑和历史库名待复核 | `legacy/src/03_load_to_mysql.py` | T06/T07 | 先实现正式的相对路径导入方案，再移动。 |
| `data/processed/order_fact.csv`、`order_item_fact.csv`、`rfm_customers.csv` 及其质量 CSV | 遗留派生数据，不能作为一期结论 | 在新数据集验证后移至 `legacy/data/processed/` 或明确标记 legacy | T11/T20 | 新数据集已生成、CSV 备用源已验证、路径和哈希先更新到 manifest。 |
| `docs/data_dictionary.md` | Windows 大小写不敏感；与目标 `docs/DATA_DICTIONARY.md` 不能共存 | `legacy/docs/data_dictionary_legacy.md` | T19 | 先复制/移动旧文件并核对内容，再创建正式数据字典。 |
| `docs/mysql_setup.md`、`docs/power_bi_dashboard.md`、`docs/power_bi_measures.dax` | 遗留安装、仪表盘和度量说明 | `legacy/docs/` 下保留同名文件，或在原文件顶部标记 deprecated | T17/T19 | 与正式 MySQL/Power BI 指南交叉核对后处理。 |
| `README.md` | 含历史经营/RFM叙事；当前已有一期重构提示 | 保留根 README；在 T19 前将旧正文副本写入 `legacy/README_legacy_baseline.md` | T19 | 先核对当前 SHA-256，保留旧正文后再重构招聘版 README。 |
| `dashboard/olist_ecommerce_dashboard.pbix` | T01 前已修改，且是用户所有未提交变更 | 保持原路径，不移动、不重命名；一期新文件为 `dashboard/olist_delivery_analysis.pbix` | T17/T18 | 只能在用户明确允许且已备份/确认后触碰旧 PBIX；新 PBIX 使用新路径。 |

## 4. 当前正式流程与遗留流程边界

- 正式目标数据库：`olist_delivery_analysis`；`olist_analysis` 仅作历史标记。
- 正式目标 SQL：未来的 `sql/00_create_database.sql` 至 `sql/08_validation_queries.sql`；T01 时尚未创建或执行。
- 当前 T01 不将任何遗留脚本、派生 CSV、PBIX 或文档纳入一期运行流程。
- Power BI 旧 PBIX 的状态不可由文本文件推断；后续必须通过 Power BI Desktop 进行人工验证，不能宣称自动生成/验证完整 PBIX。

## 5. 未解决事项

1. 卖家/地区/品类细分的最低样本量尚未指定具体阈值。后续 T13 在排名和业务解释前必须先提出阈值及依据并取得确认；阈值确认前只展示样本数并标记小样本，不作主要问题排名。
2. MySQL 的 `LOAD DATA LOCAL INFILE` 和 Python + SQLAlchemy/PyMySQL 两条导入路线均需在 T07 设计、验证和文档化；前者的本地路径不得写入提交的 SQL，后者作为可复现备用路线。

## 6. T02 环境迁移执行记录

执行状态：已完成并等待用户验收；未安装项目依赖、未执行 SQL、未连接数据库、未运行数据脚本或 Notebook。

| 项目 | 执行前记录 | 实际结果 |
| --- | --- | --- |
| Git 跟踪检查 | `git ls-files .venv` 无输出 | `.venv` 不受 Git 跟踪。 |
| 备份目标 | `.venv_broken_backup_20260805/` 不存在 | 可安全使用目标名称。 |
| Python 解释器 | `py -0p` 与 `Get-Command python -All` | 明确使用 `D:\python\python.exe`，版本 3.13.13。 |
| 旧环境移动 | 原路径 `.venv/`，目标 `.venv_broken_backup_20260805/` | 已重命名；旧目录完整保留，未删除。 |
| 新环境创建 | 目标 `.venv/` | 已由 `D:\python\python.exe -m venv .venv` 创建。 |
| 新环境配置 | `pyvenv.cfg` | `home = D:\python`、`version = 3.13.13`、`include-system-site-packages = false`。 |
| 已安装包 | `pip list` | 仅 venv 自带的 `pip 26.0.1`，未安装任何项目依赖。 |
| Git 忽略 | `.gitignore` | `.venv/` 与 `.venv_broken_backup_20260805/` 均已匹配忽略规则。 |

如需回滚，不删除任何目录：先将新 `.venv` 重命名为新的临时故障目录（名称须先确认不存在），再将 `.venv_broken_backup_20260805` 重命名回 `.venv`。该动作需用户单独确认后执行。

## 7. T03 依赖安装记录（已完成）

- 已创建 `requirements.in`，仅包含一期直接依赖及 Python 3.13 兼容的最低版本边界；未写入传递依赖。
- 第一次普通安装因沙箱网络返回 `WinError 10013` 失败；第一次受控网络安装在 124 秒超时，均未安装项目包。
- 经用户授权，以相同 Python 3.13.13、相同 `.venv` 和相同 `requirements.in`，使用 `--prefer-binary --timeout 120 --retries 5 --progress-bar off --disable-pip-version-check` 重试成功。
- 已从正式环境生成 110 行固定版 `requirements.txt`（SHA-256：`1E94EDC9A92EF78AA99F55F4476FA4F8261BF610E6583D99304E0913EE9DC4DB`），并通过路径/URL/editable 扫描。
- 正式环境及新的临时环境均通过 `pip check`、导入、pandas、三项 SciPy、matplotlib、Jupyter/ipykernel 和 SQLAlchemy/PyMySQL 非连接测试；直接依赖版本完全一致。
- 完整证据见 `docs/DEPENDENCY_VERIFICATION.md`。临时验证环境将在本任务完成前删除；正式环境与旧备份保留。

## 8. T04 配置模板迁移记录

- 原配置模板：`.env.example`，修改前 SHA-256 为 `5627038D704C170DD8655BC525C964C092ED6DE431CFED78F8948AE5624CB440`；模板使用历史数据库名 `olist_analysis`，示例用户为 `root`，且未提供 `MYSQL_CHARSET`。
- 新配置模板：`.env.example` 使用一期正式名称 `olist_delivery_analysis`、非 root 占位用户名 `your_username`、非真实密码占位值 `your_password` 与 `MYSQL_CHARSET=utf8mb4`。
- 修改原因：统一一期正式数据库名称，形成独立变量的安全配置接口，避免历史名称、root 示例账号和隐式字符集。
- 修改时间：2026-08-05（T04）。真实 `.env` 的内容未读取、未记录、未移动。
- 回滚方式：在用户确认后，将 `.env.example` 精确恢复到本节记录的修改前 Git/哈希基线；不操作真实 `.env`，不移动其他历史配置文件。
- 旧名称保留位置：现有 `sql/`、`docs/mysql_setup.md` 和遗留 `src/03_load_to_mysql.py` 仍为历史/legacy 内容，T04 不修改；它们将在后续 SQL/遗留迁移任务中隔离或标记 deprecated，不属于一期正式执行流程。

## 9. T05 MySQL 最小验证记录

- 使用本地 `.env` 的独立变量建立连接；密码、完整 URL 和 `.env` 内容均未输出。
- 只执行 `SELECT VERSION()`、`DATABASE()`、字符集/排序规则查询、`SELECT 1`、`SHOW TABLES`、`SHOW GRANTS FOR CURRENT_USER()` 与 `SELECT CURRENT_USER()`。
- 验证环境为 MySQL 8.0.44；当前数据库为 `olist_delivery_analysis`，字符集 `utf8mb4`、排序规则 `utf8mb4_unicode_ci`，空库表数为 0。
- 当前账号为非 root 的本地项目账号；`SHOW GRANTS` 显示其在 `olist_delivery_analysis` 上具有授权。没有通过写操作测试权限，也没有创建、修改或删除对象。
- 完整脱敏验证结果见 `docs/MYSQL_CONNECTION_VERIFICATION.md`；T05 完成后暂停，等待下一任务授权。

## 10. T06 SQL 文件移动预记录（移动前）

本节在实际移动前记录原路径、目标路径和 T01 一致的 SHA-256；目标目录及三个目标文件已确认不存在。

| 原路径 | 目标路径 | 移动前 SHA-256 |
| --- | --- | --- |
| `sql/00_create_database.sql` | `legacy/sql/00_create_database.sql` | `5DB77A649E5F53B2CA528C758903A6EDA71BB8B78ACB0D7B6E52DDFF2C2C50C0` |
| `sql/01_schema.sql` | `legacy/sql/01_schema.sql` | `1E3DDB1A42F2ACAC4EDCEAF358F892FCA80F0E72BDB39D0366BEDB4C3F96B459` |
| `sql/02_analysis_queries.sql` | `legacy/sql/02_analysis_queries.sql` | `E8AB96947C2112AFF669E10C08D131FC83A4AFABCB787FEB618C111D6AAFA39E` |

这些文件是旧版 Olist 项目的历史资产；T06 只隔离，不修订内容、不替换历史数据库名、不改变换行符，也不执行任何 SQL。

移动结果：三个文件已使用 `git mv` 移至上表目标路径；移动后 SHA-256 与表中值完全一致。`legacy/sql/README.md` 已单独创建说明历史数据库名、非正式执行状态和保留目的。新的正式 `sql/00`–`sql/08` scaffold 已创建，执行顺序见 `docs/SQL_EXECUTION_ORDER.md`。

## 11. T06 静态验收记录

- 验收日期：2026-08-06；用户明确要求继续 T06，并同意将现有 T06 文件作为既有变更进行审查和验收。
- 三份 `legacy/sql/` 文件的 SHA-256 与第 10 节记录和 T01 基线完全一致；未修订历史内容。
- `legacy/sql/README.md` 明确其使用历史数据库名、非正式执行状态和保留目的。
- `sql/00_create_database.sql` 至 `sql/08_validation_queries.sql` 均存在，包含文件、目标、状态和安全头部；除 `00` 的可重复建库 scaffold 外，其余文件均明确延后至后续任务实现。
- 正式 `sql/` 已检查为不含 `olist_analysis`、凭据、完整连接 URL、本机绝对路径、`DROP DATABASE`、`DROP SCHEMA` 或 `TRUNCATE`。
- `git diff --check` 和 `git diff --cached --check` 通过。未连接 MySQL、未执行 SQL、未处理 CSV，数据库状态仍以 T05 的空库验证记录为准。

## 12. T07 遗留导入脚本隔离记录

- 原路径：`src/03_load_to_mysql.py`；移动前 SHA-256：`1C333C9C34724445911A606C99CB9E9701BC447EE7F6ACEB47113AADF5CAD7AD`，与 T01 基线一致。
- 目标路径：`legacy/src/03_load_to_mysql.py`；移动后 SHA-256 与移动前完全一致。该文件保留历史数据库名和 `to_sql(..., if_exists="replace")` 行为，不属于一期正式运行流程。
- T07 正式替代实现为 `src/01_load_raw_to_mysql.py`：它使用正式数据库名、相对路径、CSV 标头验证、参数化批量插入、默认非覆盖保护和显式 `--replace-existing` 开关。

## 13. T07 表结构与导入验收记录

- `sql/01_create_tables.sql` 已在 `olist_delivery_analysis` 成功执行，创建 7 张 InnoDB 原始表、5 个外键和 1 个评分检查约束；不包含本机路径、凭据、旧数据库名或破坏性 DDL。
- Python 正式导入器已完成 CSV 预检和一次完整加载，七表总计 547,664 行；每表计数与原始 CSV 完全一致。完整命令、行数、哈希和 `local_infile` 预检结果见 `docs/T07_RAW_IMPORT_VERIFICATION.md`。
- 原始 CSV 保持只读；导入后的 SHA-256 与导入前记录一致。当前 `local_infile=OFF`，故 `LOAD DATA LOCAL INFILE` 模板仅完成预检和文档化，未在当前数据库执行。

## 14. T08 遗留质量脚本隔离与只读验收记录

- 原路径：`src/01_data_quality.py`；移动前 SHA-256：`37271BD35CD61656B59B7CC4412CC03171D75E4652790D0672C2ABA19B25A180`，与 T01 基线一致。
- 目标路径：`legacy/src/01_data_quality.py`；移动后 SHA-256 与移动前一致。该脚本保留历史实现，不属于一期正式质量流程。
- T08 正式替代实现为 `src/02_validate_raw_data.py` 和 `sql/02_data_quality_checks.sql`。它们只读取 7 份 CSV 与 7 张原始表，并将非敏感聚合结果写至 `reports/validation/t08_reconciliation_summary.json`。
- 运行结果：25 条只读 SQL 语句、12 组 SQL/Python 对账均通过；未修改数据库、CSV、`data/processed/`、README 或 PBIX。详细结果见 `docs/T08_SQL_PYTHON_RECONCILIATION.md`。

## 15. T09 评价选择与冲突审计记录

- 实现文件：`sql/03_create_clean_views.sql` 与 `src/03_validate_review_selection.py`；验收说明为 `docs/T09_REVIEW_SELECTION_AUDIT.md`，非敏感聚合结果为 `reports/validation/t09_review_selection_summary.json`。
- 当前数据库只新增三个 T09 视图：`vw_review_ranked`、`vw_order_review_audit`、`vw_order_review_selected`。未创建表或其它业务对象，未执行 DML，未修改 CSV、`data/processed/`、README、PBIX 或遗留资产。
- 创建前基线为 99,224 条评价、98,673 个评价订单、547 个多评订单和 202 个有效评分冲突订单；创建后 Python 与 SQL 的 8 项对账全部通过，逐订单选择差异为 0。
- 主评分严格按有效评分的回复时间、创建时间、`review_id` 选择；最低有效评分仅保留为 T15 的敏感性字段，不取平均。当前数据没有需要 `review_id` 兜底或无法稳定排序的订单。
- 后续 T10 未执行，必须另行授权；任何继续动作前先确认三个视图和上述原始评价基线未漂移。

## 16. T10 清洗订单视图与延迟字段记录

- 新增对象仅为 `vw_clean_orders`；它以 `orders_raw` 为一行一订单基础，左连接 T09 的 `vw_order_review_selected`，不连接订单明细、支付、客户、商品或 T11 对象。
- `data/processed/clean_orders.csv` 已从该视图输出为 UTF-8、固定列顺序、按 `order_id` 稳定排序的 99,441 行文件；SHA-256 为 `8441544F3B96F761939D16778841DFAC489360CC6BCAF3EF33835FC4F3DA1E5E`。
- SQL/Python 全量逐字段对账及粒度、样本标记、延迟分类、排除原因、日期异常、评分分布和多评冲突计数均通过。T09 三视图定义哈希保持不变；未修改原始表、原始 CSV、README、PBIX 或 legacy 内容。
- 日期异常保留标记而非删除。`has_date_anomaly=1` 为 1,382，其中 23 条为实际送达早于交运；后续分析若需排除必须另行确认。
- 完整验收记录见 `docs/T10_CLEAN_ORDERS_VERIFICATION.md` 和 `reports/validation/t10_clean_orders_summary.json`。T11 未开始，必须另行授权。

## 17. T11 订单级与商品明细分析层记录

- 新增四个可重建视图：商品聚合、支付聚合、订单分析及订单商品明细分析。没有创建永久表或执行 DML；订单层以 T10 `vw_clean_orders` 为主表，商品和支付均先按订单聚合。
- 订单分析层为 99,441 行且 `order_id` 唯一；商品明细层为 112,650 行且 `order_id + order_item_id` 唯一。客户、翻译及原始商品键的连接前唯一性均已验证。
- 两个 CSV 已生成并有 SHA-256；SQL/Python 粒度、每订单商品/支付聚合、金额总和（绝对容差 0.01）、客户匹配和 T10 日期异常字段传播均通过。
- T09/T10 视图、原始表、原始 CSV、README、PBIX 与 legacy 内容均未修改。日期异常继续保留；T12 未开始，必须另行授权。
