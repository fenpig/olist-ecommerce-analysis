# 项目交接文档：Olist 配送履约与客户满意度分析（一期）

交接日期：2026-08-06  
项目根目录：`D:\CodexProjects\p1\olist-ecommerce-analysis`  
Git 分支：`main`  
T01 恢复锚点：`4564602f8a072a2b3497c3504eb54089aecab705`

本文件供后续接手者继续工作。项目采用“每次只执行一个已授权任务，完成后暂停验收”的方式推进。当前不得自动开始下一任务。

## 1. 项目目标与当前范围

一期在 Olist 公开数据集基础上分析订单履约、配送时效与客户评分的关联，服务于数据分析招聘作品集和模拟电商运营汇报。

- 主问题：配送延迟、客户评分、客户州、商品类别、`seller_id` 之间有哪些具有业务意义的关联。
- 表述限制：只能报告关联、差异和优先关注方向；不得把观察性结果表述为因果。
- 一期范围：客户 `customer_state`、商品类别、`seller_id`；不推断卖家地区，不计算客户—卖家距离，不制作经纬度地图。
- 一期不含：预测模型、逻辑回归、低评分预警、正式 Power BI 自动生成承诺、演示文稿。

正式需求、指标和决策以以下文档为准：

- `docs/PROJECT_REQUIREMENTS.md`
- `docs/DECISIONS.md`
- `docs/METRICS.md`
- `docs/TASK_PLAN.md`
- `AGENTS.md`

## 2. 已完成工作

### 2.1 需求、数据与决策

1. 已完成需求访谈和一期正式需求说明书。
2. 已对当前原始数据做只读盘点和质量审查，未修改 CSV。
3. 已确认数据边界、延迟、评价、多评处理、趋势边界、一期地域范围、分析深度、交付物与验收标准。
4. 已形成完整的 20 项任务计划与单任务暂停验收机制。

关键数据事实：

- 当前 `data/raw/` 有 7 张表，缺少 `olist_sellers_dataset.csv` 和 `olist_geolocation_dataset.csv`。
- 共 99,441 个订单；主配送—评分关系可用订单上限为 95,824（订单级、未最终业务实现）。
- 547 个订单有多条评价，202 个多评订单的评分冲突；主口径选最新有效评价，最低评分用于敏感性分析。
- `order_estimated_delivery_date` 的可解析时间部分均为 `00:00:00`，因此主 `delay_days` 使用日历日期差；连续 `delay_hours_raw` 仅作审查/补充分析。
- 月度主趋势排除 2016-09、2016-12、2018-09、2018-10，但这些记录继续用于总体统计和边界附录。

详细证据：`docs/DATA_INVENTORY.md`、`docs/DATA_QUALITY_REPORT.md`。

### 2.2 T01：实施基线与遗留资产盘点（已验收）

- 建立 `docs/LEGACY_MIGRATION_MANIFEST.md`。
- 记录 Git 恢复锚点、用户已有未提交改动、遗留文件的 SHA-256、未来移动路径和回滚原则。
- 未移动、删除或修改遗留资产。

### 2.3 T02：Python 环境重建（已验收）

- 旧失效 `.venv/` 已重命名为 `.venv_broken_backup_20260805/`，未删除。
- 新 `.venv/` 由 `D:\python\python.exe` 创建，Python 3.13.13。
- `.gitignore` 已忽略新环境、旧环境备份和 T03 临时环境目录。

### 2.4 T03：依赖锁定与复现验证（已验收）

- 已创建 `requirements.in`，仅含直接依赖。
- 已生成 110 行固定版 `requirements.txt`；无本机路径、`file://`、editable 或 Git 依赖。
- 正式 `.venv` 与临时全新环境均通过 `pip check`、导入、pandas/NumPy、三项 SciPy 检验、matplotlib 临时图、Jupyter/ipykernel、SQLAlchemy/PyMySQL 非连接测试。
- 临时 `.venv_t03_verify` 已删除；正式 `.venv` 和旧备份均保留。

已验证的直接依赖：numpy 2.5.1、pandas 3.0.5、scipy 1.18.0、matplotlib 3.11.1、jupyter 1.1.1、ipykernel 7.3.0、SQLAlchemy 2.0.51、PyMySQL 1.2.0、python-dotenv 1.2.2。

详细证据：`docs/DEPENDENCY_VERIFICATION.md`。

### 2.5 T04：配置契约（已验收）

- `.env.example` 已改为安全占位模板，正式数据库名为 `olist_delivery_analysis`。
- 变量：`MYSQL_HOST`、`MYSQL_PORT`、`MYSQL_DATABASE`、`MYSQL_USER`、`MYSQL_PASSWORD`、`MYSQL_CHARSET`。
- `.env`、`.env.local`、`.env.*.local` 被忽略；`.env.example` 未被忽略且受 Git 跟踪。
- 已在系统临时目录复制模板并用 python-dotenv 验证；未读取或输出真实 `.env`。

详细契约：`docs/CONFIGURATION_CONTRACT.md`。

### 2.6 T05：MySQL 最小只读验证（已验收）

- 使用真实 `.env` 的内存配置连接 MySQL，未输出密码或完整 URL。
- MySQL 版本：8.0.44。
- 当前数据库：`olist_delivery_analysis`；字符集：`utf8mb4`；排序规则：`utf8mb4_unicode_ci`。
- `SHOW TABLES` 返回 0；当前账号为非 root 的 `olist_project@localhost`。
- `SHOW GRANTS` 显示项目账号在 `olist_delivery_analysis.*` 上有授权。
- 仅执行 `SELECT` / `SHOW` 查询；未运行项目 SQL、未创建/修改/删除任何对象。

详细证据：`docs/MYSQL_CONNECTION_VERIFICATION.md`。

### 2.7 T06：正式 SQL 结构与遗留 SQL 隔离（已验收）

- 正式 `sql/00`–`08` 顺序和 `legacy/sql/` 隔离已完成；三份历史 SQL 的 SHA-256 保持与 T01 基线一致。
- 正式 SQL 不使用 `olist_analysis`，且不含凭据、本机绝对路径或破坏性数据库语句。
- 仅完成静态验收；T06 未执行 SQL。

### 2.8 T07：原始表结构与可复现导入流程（已验收）

- 已实现并执行 `sql/01_create_tables.sql`，在 `olist_delivery_analysis` 创建 7 张 InnoDB 原始表、5 个外键和 1 个评分检查约束。
- 新 `src/01_load_raw_to_mysql.py` 已完成 CSV 标头/行数预检，并以参数化批量插入加载全部 547,664 条原始记录；七表数据库行数与 CSV 行数完全一致。
- `LOAD DATA LOCAL INFILE` 模板及其 Workbench 回退说明已提供，但当前 MySQL 的 `local_infile=OFF`，因此本次验证采用 Python 路线。
- 原始 CSV 未修改；旧导入脚本已完整移至 `legacy/src/03_load_to_mysql.py`。详细证据：`docs/T07_RAW_IMPORT_VERIFICATION.md`。

### 2.9 T08：可复现只读数据质量检查（已验收）

- `sql/02_data_quality_checks.sql` 的 25 条只读语句与 `src/02_validate_raw_data.py` 均已运行；脚本以 MySQL 只读事务和 SQL 白名单执行。
- 7 张表行数、候选键重复、关键字段缺失、外键孤立、状态/评分分布、评价重复、日期边界、月度订单数、样本漏斗和品类翻译共 12 组 SQL/Python 对账全部通过。
- 仅产生非敏感聚合验证结果 `reports/validation/t08_reconciliation_summary.json`；未修改 MySQL 数据、CSV、processed 数据、README 或 PBIX。
- 旧质量脚本已完整移至 `legacy/src/01_data_quality.py`。详细证据：`docs/T08_SQL_PYTHON_RECONCILIATION.md`。

## 3. 修改或创建的文件

### 已修改的项目文件

| 文件 | 状态/用途 |
| --- | --- |
| `.gitignore` | 忽略 `.env`、本地环境、环境备份和临时验证环境。 |
| `.env.example` | 一期安全配置模板，使用 `olist_delivery_analysis`。 |
| `requirements.txt` | T03 验证后冻结的完整依赖清单。 |
| `README.md` | 先前已存在未提交修改；含一期重构提示。后续 T19 才重构为最终招聘 README。 |
| `dashboard/olist_ecommerce_dashboard.pbix` | T01 前已有用户未提交修改；不得触碰。 |

### 已创建的需求、记录与验证文档

| 文件 | 用途 |
| --- | --- |
| `AGENTS.md` | 项目协作、安全、环境和验收规则。 |
| `docs/PROJECT_REQUIREMENTS.md` | 一期正式需求说明书。 |
| `docs/TASK_PLAN.md` | 20 个任务、依赖、验收、暂停闸门和回滚设计。 |
| `docs/DECISIONS.md` | 业务口径决策。 |
| `docs/METRICS.md` | 指标、样本、粒度和敏感性分析口径。 |
| `docs/DATA_INVENTORY.md` | 原始数据盘点与表关系。 |
| `docs/DATA_QUALITY_REPORT.md` | 数据质量、日期、样本和边界月审查。 |
| `docs/ENVIRONMENT_SETUP.md` | Python/MySQL 环境和迁移说明。 |
| `docs/CONFIGURATION_CONTRACT.md` | 环境变量配置契约。 |
| `docs/DEPENDENCY_VERIFICATION.md` | T03 依赖、功能与复现验证。 |
| `docs/MYSQL_CONNECTION_VERIFICATION.md` | T05 只读连接、空库和权限验证。 |
| `docs/LEGACY_MIGRATION_MANIFEST.md` | 资产指纹、迁移路径和 T01–T08 执行记录。 |
| `docs/SQL_EXECUTION_ORDER.md` | 正式 SQL 执行顺序及 T07/T08 实施状态。 |
| `docs/MYSQL_IMPORT_GUIDE.md` | Python 与 `LOAD DATA LOCAL INFILE` 两条原始导入路线及回退说明。 |
| `docs/T07_RAW_IMPORT_VERIFICATION.md` | T07 的 CSV、MySQL 行数、约束与环境验证记录。 |
| `docs/T08_SQL_PYTHON_RECONCILIATION.md` | T08 的只读 SQL/Python 对账范围、结果与暂停点。 |

## 4. 当前代码与 Git 状态

### 4.1 Git 基线与保护资产

- Git 分支：`main`；恢复锚点见文件开头。
- 不得使用 `git reset --hard`、`git clean -fd` 或广泛恢复命令，因为工作区包含用户已有的 README/PBIX 改动和本会话未提交文档。
- T01 基线验证持续确认以下资产未被本会话后续任务改动：
  - `README.md`
  - `dashboard/olist_ecommerce_dashboard.pbix`
  - `sql/00_create_database.sql`、`sql/01_schema.sql`、`sql/02_analysis_queries.sql` 的**旧内容**（现已在 `legacy/sql/` 中）

真实 `.env` 未被 Git 跟踪、从未输出；不要读取、打印或提交它。

### 4.2 T06/T08 文件与数据库状态

在本会话尝试启动 T06 的**前置检查**时，发现以下变更已在工作区存在；随后在用户授权下完成了 T06 静态验收、T07 实施和 T08 只读验证：

1. Git 已显示三项暂存重命名：
   - `sql/00_create_database.sql → legacy/sql/00_create_database.sql`
   - `sql/01_schema.sql → legacy/sql/01_schema.sql`
   - `sql/02_analysis_queries.sql → legacy/sql/02_analysis_queries.sql`
2. `legacy/sql/` 与 `legacy/sql/README.md` 已存在。
3. 新的正式 scaffold 已存在：`sql/00_create_database.sql` 至 `sql/08_validation_queries.sql`。
4. `docs/SQL_EXECUTION_ORDER.md` 已存在。

旧 SQL 在 `legacy/sql/` 的 SHA-256 与 T01 基线一致：

| 旧文件 | SHA-256 | 结果 |
| --- | --- | --- |
| `legacy/sql/00_create_database.sql` | `5DB77A649E5F53B2CA528C758903A6EDA71BB8B78ACB0D7B6E52DDFF2C2C50C0` | 与 T01 一致 |
| `legacy/sql/01_schema.sql` | `1E3DDB1A42F2ACAC4EDCEAF358F892FCA80F0E72BDB39D0366BEDB4C3F96B459` | 与 T01 一致 |
| `legacy/sql/02_analysis_queries.sql` | `E8AB96947C2112AFF669E10C08D131FC83A4AFABCB787FEB618C111D6AAFA39E` | 与 T01 一致 |

`sql/00_create_database.sql` 仍为未执行的可重复建库 scaffold；现有数据库由 T05 前创建。T07 已执行正式 `sql/01_create_tables.sql` 并通过 Python 导入器加载 7 张原始表。T08 已执行正式 `sql/02_data_quality_checks.sql` 的只读检查；行数、约束、CSV 哈希和对账结果见 `docs/T07_RAW_IMPORT_VERIFICATION.md` 与 `docs/T08_SQL_PYTHON_RECONCILIATION.md`。`sql/03`–`08` 仍为 pending，未执行。

T06 已于 2026-08-06 在用户明确要求继续该任务后完成静态验收。验收仅采纳并检查既有 T06 文件：三份 legacy SQL 的 SHA-256 均与 T01 基线一致，`legacy/sql/README.md` 已明确其 legacy/deprecated 边界，正式 `sql/00`–`08` 编号完整且都有 scaffold/pending 状态与安全头部；正式 SQL 不含 `olist_analysis`、凭据、本机绝对路径、`DROP DATABASE`、`DROP SCHEMA` 或 `TRUNCATE`。`git diff --check` 和暂存区检查均通过。T07 后的数据库状态以本文件和 T07 验收记录为准。

## 5. 关键设计决策

1. **延迟口径**：主 `delay_days` = `DATE(actual_delivery) - DATE(estimated_delivery)`；保留连续 `delay_hours_raw`，但不用于主分类。
2. **延迟分类**：`<=0` 按时/提前，1–3 轻微，4–7 中度，`>7` 严重。
3. **评分口径**：主评分取同订单最新有效评价（answer timestamp → creation date → review ID）；无法排序且冲突的订单不进主关系样本；最低评分作敏感性分析。
4. **评分分类**：1–2 低分、3 中性、4–5 高分；未评价单独标记，不填充。
5. **月度趋势**：排除四个已确认的不完整下单月，仅影响月度趋势/环比/增长率，不影响总体统计。
6. **分析方法**：描述性、分层、Spearman、Chi-square、适用时 Mann–Whitney U、效应量和置信区间；不开发一期预测模型。
7. **技术环境**：Python 3.13.13、项目 `.venv`、MySQL 8.0.44、Power BI；不切换 Python 主版本，除非有证据并经用户确认。
8. **数据库**：一期唯一正式名称 `olist_delivery_analysis`；`olist_analysis` 只可作为 legacy/historical 说明。
9. **SQL/数据安全**：不在代码或文档中写密码/URL/绝对路径；`data/raw/` 永远只读；异常和排除样本必须保留审计。
10. **Power BI 边界**：Codex 可准备数据模型规范、DAX 建议、设计和对账；实际 Power BI Desktop 连接、关系、可视化、保存 PBIX、刷新和交互验证需用户完成/确认。

## 6. 未解决问题、风险与依赖

| 项目 | 当前状态 | 后续处理 |
| --- | --- | --- |
| T08 质量检查与对账 | 已完成只读验收；未创建清洗对象或分析对象 | T09 仍需新的单独授权；不得自动开始。 |
| 细分最低样本量 | 未定义具体阈值 | T13 在排名/主要问题解释前提出阈值与依据并取得确认；阈值前仅展示样本数并标记小样本。 |
| 卖家表 | `olist_sellers_dataset.csv` 缺失 | 一期可按 `seller_id` 分析；卖家地域不做。建议最终交付前补齐。 |
| 地理表 | `olist_geolocation_dataset.csv` 缺失 | 二期增强；不计算距离或精确地图。 |
| 真实 `.env` | 已用于 T05，但不应再展示或读取其内容 | T05 后续连接任务可在内存读取；不得打印、提交或复制。 |
| 数据库权限 | 项目账号仅限目标库，但该库内为 `ALL PRIVILEGES` | 足以支持后续建表；若需最小权限，可二期新增 Power BI 只读账号。 |
| Windows 文件名大小写 | 现有 `docs/data_dictionary.md` 与目标 `docs/DATA_DICTIONARY.md` 不能共存 | T19 前先按 manifest 迁移/保留旧文件，不能同时创建两者。 |
| MySQL 生命周期 | 8.0.44 是本地学习/作品集验证环境 | MySQL 8.4 LTS 验证为后续非阻塞工作，不在一期自行升级。 |

## 7. 下一步执行计划

### 当前立即下一步：等待 T09 的单独授权

T08 已完成并暂停。后续不得因已完成质量检查而推定可以开始评价选择或创建清洗视图。T09 获得单独授权后，才可实现评价选择与冲突审计。

### 后续已确认任务顺序（每项均需单独用户授权）

| 任务 | 内容 | 关键边界 |
| --- | --- | --- |
| T09 | 评价选择与冲突审计 | 最新评分主口径、最低评分对照；不取平均。需新的单独授权。 |
| T10 | 清洗视图与延迟字段 | 原始表不变，生成样本标记和日历日延迟。 |
| T11 | 订单级/明细级分析表 | 防止多商品、多付款、多评价造成重复放大。 |
| T12–T16 | 指标、分层、统计、敏感性、SQL/Python 对账 | T13 前确认最低样本量；不作因果结论。 |
| T17–T18 | Power BI 模型与四页仪表盘 | 明确用户 Power BI Desktop 手动操作与验证。 |
| T19–T20 | 报告、README、数据字典、端到端验收 | 处理 Windows 数据字典大小写冲突；按 README 复现。 |

## 8. 交接操作守则

1. 每次只执行用户明确授权的一个任务；任务结束后必须暂停并报告文件、命令、验证、问题、风险和回滚方式。
2. 任何移动或重命名前，先记录原路径、目标路径和 SHA-256；不得静默删除。
3. 不读取/输出 `.env` 内容、密码或完整连接 URL。
4. 不在未授权时连接 MySQL、执行 SQL、处理 CSV、修改 PBIX 或进入下一任务。
5. 保留 `.venv_broken_backup_20260805/`；不删除已有用户 PBIX/README 改动。
6. 继续前优先阅读 `AGENTS.md`、本文件、`TASK_PLAN.md`、`LEGACY_MIGRATION_MANIFEST.md` 和与当前任务对应的验收记录。
