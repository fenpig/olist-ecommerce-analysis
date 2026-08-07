# 一期任务计划（执行状态已更新）

计划周期：5 周，每周约 8–12 小时。  
前提：`PROJECT_REQUIREMENTS.md` 与本计划已确认；后续仍遵循单任务授权、验收后暂停的执行闸门。

## 当前任务状态

| 任务 | 状态 |
| --- | --- |
| T01–T11 | completed（均已验收） |
| T12 | planned / not started |
| T13–T20 | pending |

## 用户控制的执行与验收闸门

- 每个任务完成后必须暂停，报告完成内容、文件、实际命令、验证、未解决问题、风险与回滚方式；只有用户确认才开始下一任务。
- 每个里程碑（M0–M4）结束后必须单独暂停验收，不得自动跨里程碑。
- 每次移动或重命名前先将原路径、目标路径和文件指纹记录到 `LEGACY_MIGRATION_MANIFEST.md`；不得删除旧文件。
- 若 Git 工作区不干净，使用提交哈希和文件指纹建立显式恢复点；不自动创建混入用户改动的提交。

## 里程碑总览

| 里程碑 | 周次 | 完成条件 |
| --- | --- | --- |
| M0：实施基线 | 第 1 周前段 | 遗留资产、正式命名和环境重建方案可追溯。 |
| M1：可复现数据基础 | 第 1–2 周 | 新环境、MySQL 原始表、质量检查、清洗视图和订单级分析数据可复现。 |
| M2：分析与验证 | 第 3 周 | 描述性/细分/统计/敏感性分析完成且 SQL-Python 一致。 |
| M3：Power BI | 第 4 周 | 四页仪表盘可刷新、筛选正确、核心指标交叉一致。 |
| M4：最终交付 | 第 5 周 | 报告、README、字典、复现与验收全部完成。 |

## 任务清单

### T01：建立实施基线与遗留资产清单

- **任务目标**：冻结一期正式命名，识别旧 SQL、旧 README、旧 `.venv`、既有脚本/仪表盘与新流程的差异。
- **前置依赖**：无。
- **输入文件**：`docs/PROJECT_REQUIREMENTS.md`、`docs/DECISIONS.md`、`docs/METRICS.md`、现有 `sql/`、`src/`、README、`.venv` 元数据。
- **需要修改或创建的文件**：创建 `docs/LEGACY_MIGRATION_MANIFEST.md`；仅更新文档中的状态链接与执行闸门。
- **实施步骤**：先记录 Git 状态、分支、提交哈希和用户已有改动；逐项列出遗留文件、用途、历史数据库名、保留位置、目标替代文件和迁移方式；计算/记录文件指纹；不移动或删除任何文件。
- **输出结果**：可审计的遗留资产与迁移映射清单。
- **验收标准**：所有当前正式执行路径与遗留路径明确区分；`olist_analysis` 只标为历史名称；每个计划移动均有原/目标路径；旧 PBIX 和用户已有修改均被保护。
- **验证命令或验证方法**：`git status --short`、`git rev-parse HEAD`、文件 SHA-256、人工核对清单与 `rg --files sql src docs` 输出；检查无文件移动。
- **可能风险**：误把仍有价值的旧脚本当作废弃物；缓解方式是先标记，后续经验证再迁移。

### T02：非破坏性 Python 3.13 环境重建

- **任务目标**：在不删除旧环境的前提下，建立 Python 3.13.13 项目虚拟环境。
- **前置依赖**：T01。
- **输入文件**：Python 3.13.13 可执行文件、现有 `.venv` 状态、`docs/ENVIRONMENT_SETUP.md`。
- **需要修改或创建的文件**：重命名 `.venv` 为 `.venv_broken_backup_20260805`；创建新的 `.venv`；更新 `.gitignore`。
- **实施步骤**：记录旧环境启动错误；确认目标备份路径；重命名而非删除；用 Python 3.13.13 创建新 `.venv`；确认 `.venv` 和备份目录均被忽略。
- **输出结果**：可启动的新 `.venv` 与保留的旧环境备份。
- **验收标准**：新环境显示 Python 3.13.13；旧目录仍存在；Git 不追踪两个环境目录。
- **验证命令或验证方法**：`.venv\\Scripts\\python --version`；`git check-ignore .venv .venv_broken_backup_20260805`；记录旧环境错误。
- **可能风险**：目标备份名已存在或重命名中断；先检查目标不存在，若冲突则停止并请求新名称。

### T03：依赖候选、安装与版本锁定

- **任务目标**：以实际验证结果建立 `requirements.in` 和固定版 `requirements.txt`。
- **前置依赖**：T02。
- **输入文件**：已启动的 `.venv`、现有 `requirements.txt`、需求中的直接依赖列表。
- **需要修改或创建的文件**：创建 `requirements.in`；修改 `requirements.txt`；创建 `docs/DEPENDENCY_VERIFICATION.md`。
- **实施步骤**：在 `requirements.in` 列出直接依赖；安装候选依赖；记录实际安装版本；验证八个主要包导入；只将实际成功版本写入 `requirements.txt`。
- **输出结果**：经过安装验证的固定依赖清单和版本证据。
- **验收标准**：pandas、numpy、scipy、matplotlib、jupyter、sqlalchemy、pymysql、python-dotenv 均可导入；未猜测版本。
- **验证命令或验证方法**：`.venv\\Scripts\\python -m pip check`；小型 import 脚本；`pip freeze` 与 `requirements.txt` 对照。
- **可能风险**：Python 3.13 兼容性失败；记录具体依赖/错误/可选版本与影响，暂停而不切换 Python 主版本。

### T04：配置文件与数据库名称迁移

- **任务目标**：统一正式名称 `olist_delivery_analysis`，并保持凭据安全。
- **前置依赖**：T01；T03 完成前不得测试真实连接。
- **输入文件**：`.env.example`、`.gitignore`、旧 SQL/README、环境说明。
- **需要修改或创建的文件**：修改 `.env.example`、`.gitignore`、README；创建 `docs/CONFIGURATION_CONTRACT.md`。
- **实施步骤**：将示例库名改为正式名称；确认 `.env`、`.venv`、旧环境备份均被忽略；记录变量名、默认值与禁止提交规则；在 README 统一正式数据库名。
- **输出结果**：安全、可复现的连接配置契约。
- **验收标准**：正式文件不再以 `olist_analysis` 作为执行数据库；仓库中不出现真实密码。
- **验证命令或验证方法**：`git check-ignore .env .venv .venv_broken_backup_20260805`；`rg -n "olist_analysis|MYSQL_PASSWORD"` 人工复核结果。
- **可能风险**：误将 `.env` 内容打印或提交；只检查文件名/忽略规则，不读取或输出真实 `.env`。

### T05：MySQL 8.0.44 连通性与空库验证

- **任务目标**：验证 Python、MySQL Workbench 与 MySQL 8.0.44 可在不泄露凭据的前提下连接正式数据库。
- **前置依赖**：T03、T04。
- **输入文件**：本地 `.env`、`.env.example`、MySQL 8.0.44、`sql/00_create_database.sql` 草案。
- **需要修改或创建的文件**：创建 `docs/MYSQL_CONNECTION_VERIFICATION.md`；后续修改正式 `sql/00_create_database.sql`。
- **实施步骤**：通过环境变量读取配置；执行最小连接测试；在空数据库流程中验证建库、字符集和当前数据库名；不导入业务数据。
- **输出结果**：已记录的连接验证与空库基线。
- **验收标准**：Python 和 Workbench 均能连接 `olist_delivery_analysis`；文档无密码。
- **验证命令或验证方法**：Python 最小连接测试；MySQL `SELECT VERSION()`、`SELECT DATABASE()`；截图/日志脱敏保存。
- **可能风险**：本机服务未启动或权限不足；报告错误和所需权限，不改动服务器配置。

### T06：正式 SQL 结构与遗留 SQL 隔离

- **任务目标**：建立 `00`–`08` 正式 SQL 执行顺序，隔离历史 `olist_analysis` 脚本。
- **前置依赖**：T01、T05。
- **输入文件**：遗留 SQL 清单、需求说明、MySQL 8.0.44 语法约束。
- **需要修改或创建的文件**：创建/迁移 `sql/00_create_database.sql` 至 `sql/08_validation_queries.sql`；创建 `legacy/README.md` 和迁移后的遗留文件位置；更新 `docs/LEGACY_MIGRATION_MANIFEST.md`。
- **实施步骤**：先建立旧/新文件映射；创建正式编号文件；移动而非删除被替代的旧 SQL，并标记 deprecated；确保正式脚本不引用历史库名或手动隐含步骤。
- **输出结果**：正式 SQL 目录和可追溯遗留目录。
- **验收标准**：正式执行序列完整、仅使用 `olist_delivery_analysis`、旧脚本不再出现在 README 正式运行步骤。
- **验证命令或验证方法**：`rg -n "USE olist_analysis|olist_analysis" sql README.md`；人工核对编号完整性与 manifest。
- **可能风险**：移动脚本破坏历史复现；先完成 manifest，移动后保留历史说明和 Git 追踪记录。

### T07：原始表结构与可复现导入流程

- **任务目标**：在空数据库创建原始表，并通过相对路径的可执行流程导入 7 个现有 CSV。
- **前置依赖**：T05、T06。
- **输入文件**：`data/raw/*.csv`、`sql/01_create_tables.sql`、本地 `.env`。
- **需要修改或创建的文件**：修改 `sql/01_create_tables.sql`；创建 `sql/IMPORT_LOCAL_INFILE_TEMPLATE.sql`、`src/01_load_raw_to_mysql.py`、`docs/MYSQL_IMPORT_GUIDE.md`；更新 README 导入章节。
- **实施步骤**：定义与 CSV 对应的原始表和数据类型；设计并验证两条路线：(a) `LOAD DATA LOCAL INFILE` 模板，要求用户在未提交的本地配置中提供路径、记录 `local_infile` 前置条件，不在提交 SQL 中硬编码绝对路径；(b) Python + SQLAlchemy/PyMySQL，从项目根目录相对路径读取 CSV 的可复现备用导入。两条路线均记录每表行数和失败信息。
- **输出结果**：7 张原始 MySQL 表、两条已文档化的导入路线和可重跑导入日志。
- **验收标准**：空库可按说明用至少一条路线完整导入；两条路线均有清晰的前置条件/回退说明；不含硬编码绝对路径/凭据；原始 CSV 未改变。
- **验证命令或验证方法**：逐表 `COUNT(*)` 与 CSV 行数对比；分别验证 `LOAD DATA LOCAL INFILE` 的模板预检和 Python 导入；文件哈希或 Git 状态确认 `data/raw/` 未修改。
- **可能风险**：`local_infile` 被服务器/客户端禁用，或 CSV 类型/编码导致导入失败；立即切换至 Python 备用路线并记录表、列和错误，不修改原始文件。

### T08：可复现数据质量检查

- **任务目标**：把现有只读审查转化为可重复执行的 Python/SQL 质量检查。
- **前置依赖**：T03、T07。
- **输入文件**：原始 CSV、原始 MySQL 表、当前质量报告、指标与决策文档。
- **需要修改或创建的文件**：创建/修改 `src/02_data_quality.py`、`sql/02_data_quality_checks.sql`、`notebooks/01_data_quality_review.ipynb`；更新 `docs/DATA_QUALITY_REPORT.md`。
- **实施步骤**：检查行列、键唯一性、重复、缺失、日期、状态、关联匹配、边界月和多评价；输出处理前后的样本审计；比较 Python 与 SQL 的关键计数。
- **输出结果**：可复现质量检查输出和更新报告。
- **验收标准**：报告保留异常/未评价/边界月，且关键计数与当前审查基线可解释地一致。
- **验证命令或验证方法**：运行脚本、Notebook 与 SQL；对比订单总数、状态数、日期完整样本、多评订单数。
- **可能风险**：数据版本变化造成数值漂移；记录文件清单/哈希与差异原因。

### T09：评价选择与冲突审计视图

- **任务目标**：实现最新有效评价主口径与最低评分对照口径，且不平均多条评价。
- **前置依赖**：T07、T08。
- **输入文件**：原始评价表、DEC-002、`METRICS.md`。
- **需要修改或创建的文件**：修改 `sql/03_create_clean_views.sql`；创建/修改 `src/03_prepare_reviews.py`；创建 `data/processed/review_order_audit.csv`。
- **实施步骤**：计算三项审计字段；按确认的时间戳/创建日/review_id 排序选主评分；标记无法排序且冲突记录；创建最低评分对照字段/视图。
- **输出结果**：订单级评价审计表与主/敏感性评分字段。
- **验收标准**：每个订单主分析最多一条评分；多评/冲突计数可追溯；不使用平均分。
- **验证命令或验证方法**：SQL/Python 检查 `COUNT(*)` 与 `COUNT(DISTINCT order_id)`；抽样核对排序；统计冲突排除数。
- **可能风险**：同一排序字段冲突或重复 review_id；保持审计记录并排除无法决定先后的冲突订单。

### T10：清洗视图与主延迟字段

- **任务目标**：建立包含样本标记、日历日 `delay_days`、连续 `delay_hours_raw` 的清洗订单视图。
- **前置依赖**：T08、T09。
- **输入文件**：orders 原始表、评价审计表、`METRICS.md`。
- **需要修改或创建的文件**：修改 `sql/03_create_clean_views.sql`；创建/修改 `src/04_prepare_clean_orders.py`；输出 `data/processed/clean_orders.csv`。
- **实施步骤**：解析日期，保留异常标记；计算日历日差和连续小时差；生成 delivered、delivery eligible、review relation eligible、primary month 等标记；不删除不合格订单。
- **输出结果**：可审计清洗订单数据与等价 MySQL 视图。
- **验收标准**：延迟分类无空档；边界月仅在趋势标记中排除；所有排除原因可统计。
- **验证命令或验证方法**：检查分类覆盖和样本计数；抽样手算日期差；SQL/Python 对比 `delay_days` 与标记数。
- **可能风险**：日期顺序异常或空日期；保留原记录和异常原因，按已确认样本规则处理。

### T11：订单级与订单明细级分析表

- **任务目标**：生成可供 Power BI 和 SQL 使用的订单级、订单明细级分析数据集，避免多商品/多卖家放大订单指标。
- **前置依赖**：T09、T10。
- **输入文件**：清洗订单、客户、订单明细、商品、品类翻译、付款数据。
- **需要修改或创建的文件**：修改 `sql/04_create_order_analysis_table.sql`；创建/修改 `src/05_build_analysis_tables.py`；输出 `data/processed/order_analysis.csv`、`data/processed/order_item_analysis.csv`、`data/processed/payment_order_summary.csv`。
- **实施步骤**：先聚合付款；建立一行一订单的 `order_analysis`；建立一行一订单明细的 `order_item_analysis`；保留未知/未映射品类；对卖家/品类订单指标规定 `COUNT(DISTINCT order_id)`。
- **输出结果**：经建模的 MySQL 分析表和 CSV 备用数据源。
- **验收标准**：订单级表 `order_id` 唯一；明细级表粒度明确；连接前后订单数和异常样本可追溯。
- **验证命令或验证方法**：主键唯一性检查；CSV/MySQL 行数和关键字段比较；多卖家订单抽样检查。
- **可能风险**：多个卖家/类别导致归因歧义；订单级总量严格使用去重订单，明细分析明确分母。

### T12：履约与评分核心指标 SQL

- **任务目标**：实现可单独运行的配送和评价指标查询。
- **前置依赖**：T11。
- **输入文件**：MySQL 分析表、`METRICS.md`。
- **需要修改或创建的文件**：修改 `sql/05_delivery_metrics.sql`、`sql/06_review_metrics.sql`；创建 `reports/metric_sql_outputs/README.md`。
- **实施步骤**：编写有效订单、已送达、延迟订单、延迟率、配送时长、平均延迟、评分和高/低评分率查询；在查询中显式体现分子分母和样本条件。
- **输出结果**：独立可运行的核心指标 SQL 与结果说明。
- **验收标准**：指标命名、样本和口径与 `METRICS.md` 一致；订单整数指标无重复放大。
- **验证命令或验证方法**：逐条 MySQL 执行；检查订单去重；保存脱敏结果快照。
- **可能风险**：同名指标使用不同分母；每条查询旁注样本条件并交叉审核。

### T13：Python 描述性与分层分析

- **任务目标**：完成延迟、评分、客户州、品类和卖家 ID 的描述性及分层比较。
- **前置依赖**：T11、T12。
- **输入文件**：`order_analysis`、`order_item_analysis`、`METRICS.md`。
- **需要修改或创建的文件**：创建 `notebooks/02_descriptive_and_segment_analysis.ipynb`；创建 `reports/tables/` 下的汇总 CSV/图片；修改 `sql/07_segment_analysis.sql`。
- **实施步骤**：先基于样本分布提出卖家、品类和地区的最低样本量阈值及其依据，取得用户确认后才用于排名/主要问题解释；比较按时/延迟及各延迟等级的评分；按州、类别、卖家 ID 分层；始终展示样本量、差异幅度和指标值；不推断卖家地域或距离。
- **输出结果**：可追溯的分层表和图表。
- **验收标准**：所有细分有明确粒度、已确认的最低样本量和可见样本数；低于阈值的细分不得作为主要问题排名；不以统计显著性单独判定业务重要性。
- **验证命令或验证方法**：Notebook 从首至尾运行；关键分层与 SQL 输出交叉比较；抽样复算。
- **可能风险**：小样本卖家/品类排名不稳定；展示样本数并设置在报告中说明的最小样本规则。

### T14：统计检验与效应量

- **任务目标**：完成一期必需的 Spearman、卡方和适用的 Mann–Whitney U/置信区间分析。
- **前置依赖**：T03、T11、T13。
- **输入文件**：订单级分析数据、明确的检验问题、`METRICS.md`。
- **需要修改或创建的文件**：创建 `notebooks/03_statistical_tests.ipynb`、`reports/statistical_test_results.csv`、`docs/STATISTICAL_METHODS.md`。
- **实施步骤**：定义零/备择假设和样本；计算 Spearman；构造延迟状态×低评分列联表并做 Chi-square；在适用时做 Mann–Whitney U；选择并报告效应量和置信区间；说明大样本下 p 值限制。
- **输出结果**：可复现检验结果与方法说明。
- **验收标准**：不堆叠无业务问题的检验；每项有样本量、统计量、p 值、效应量/CI（适用时）及非因果解释。
- **验证命令或验证方法**：Notebook 全量运行；独立重算一个列联表；代码审阅输入筛选与输出解释。
- **可能风险**：小分层样本或独立性假设不满足；限制检验到合适粒度，记录限制而非夸大结论。

### T15：评分口径敏感性分析

- **任务目标**：检验“最新有效评分”与“最低有效评分”是否改变核心结论。
- **前置依赖**：T09、T12、T14。
- **输入文件**：主评分/最低评分字段、核心指标 SQL/Python 逻辑。
- **需要修改或创建的文件**：创建 `notebooks/04_review_score_sensitivity.ipynb`、`reports/review_sensitivity_analysis.md`。
- **实施步骤**：在相同配送样本下分别重算样本量、平均评分、低评分率、延迟分层结果和主要细分排名；逐项比较差异。
- **输出结果**：评分口径稳健性结论和差异表。
- **验收标准**：最低评分仅作对照，不替代主口径；任何明显变化均在最终报告中披露。
- **验证命令或验证方法**：Notebook 从首至尾运行；主/对照输出共享相同样本筛选审计。
- **可能风险**：评分规则更改造成误读；表头、图例和报告明确标注主/对照口径。

### T16：SQL 与 Python 指标交叉验证

- **任务目标**：建立可重复的跨工具指标对账。
- **前置依赖**：T12、T13、T14、T15。
- **输入文件**：SQL 指标结果、Python 指标结果、`METRICS.md`。
- **需要修改或创建的文件**：修改 `sql/08_validation_queries.sql`；创建 `src/06_validate_metrics.py`、`reports/METRIC_RECONCILIATION.md`。
- **实施步骤**：对订单数、已送达数、延迟订单数、延迟率、平均/中位配送时长、平均延迟、平均评分、低/高评分率建立对账表；解释每个差异。
- **输出结果**：SQL-Python 对账报告。
- **验收标准**：整数指标完全一致；比例差异为 0（计算值）或仅在展示层不超过 0.1 个百分点；无未解释差异。
- **验证命令或验证方法**：运行验证脚本与 SQL；在 CI/手工复现记录中保存结果。
- **可能风险**：日期、去重或四舍五入规则不同；回到 `METRICS.md` 统一实现而不是调整输出掩盖差异。

### T17：Power BI 数据模型与备用数据源

- **任务目标**：搭建可刷新且粒度正确的 Power BI 模型，并配置 MySQL 优先/CSV 备用数据源。
- **前置依赖**：T11、T16。
- **输入文件**：MySQL 分析表、`data/processed/` CSV、数据字典、对账结果。
- **需要修改或创建的文件**：创建 `dashboard/olist_delivery_analysis.pbix`；创建 `docs/POWER_BI_DATA_MODEL.md`；更新 README 刷新说明。
- **实施步骤**：Codex 可自动完成：准备 MySQL/CSV 数据集、关系与字段映射文档、DAX 度量建议/定义、Power Query 说明、对账数据和页面设计规范。用户必须在 Power BI Desktop 中手动完成：建立或确认数据连接/凭据、导入数据、创建关系和度量、保存 PBIX、刷新并提供截图/错误信息。配置切换/备用数据源说明并记录字段、关系和刷新步骤。
- **输出结果**：Codex 可验证的数据模型规范与 DAX/刷新说明；经用户在 Desktop 完成并反馈后，才可称为可刷新的 PBIX 数据模型。
- **验收标准**：关系正确，无多对多误放大；核心度量与 T16 一致；无卖家地域/距离字段；未获得 Desktop 验证前不得宣称 PBIX 已完整可用。
- **验证命令或验证方法**：Codex 验证数据、DAX 逻辑与 SQL/Python 对账；用户在 Power BI Desktop 刷新、筛选抽查并反馈结果。
- **可能风险**：本环境无法自动操作/验证 Power BI Desktop、MySQL 驱动或权限问题；以用户 Desktop 验证为准，CSV 备用源可降低展示风险。

### T18：Power BI 四页仪表盘

- **任务目标**：完成管理概览、配送履约、客户评分、地区/品类/卖家细分四页仪表盘。
- **前置依赖**：T17。
- **输入文件**：Power BI 数据模型、指标口径、分层分析图表/表、边界月说明。
- **需要修改或创建的文件**：修改 `dashboard/olist_delivery_analysis.pbix`；创建/更新 `docs/POWER_BI_DASHBOARD_GUIDE.md`。
- **实施步骤**：Codex 可自动完成：四页线框、视觉规范、图表/字段映射、中文标题文案、DAX 建议、边界提示与验收用对账清单。用户必须在 Power BI Desktop 中手动完成：将规范落入可视化页面、配置切片器/交互、保存 PBIX、逐页刷新和点击测试，并反馈截图或错误。添加不完整月份与数据边界说明。
- **输出结果**：可实施的仪表盘设计包；只有用户完成 Desktop 操作并验证后，才形成四页可交互 PBIX。
- **验收标准**：图表无错误、筛选器正确联动、所有必需指标可见、边界/限制明显、中文标签完整；未验证的 Desktop 部分必须明确标为待用户操作。
- **验证命令或验证方法**：Codex 对图表字段/指标与 SQL/Python 对账；用户在 Desktop 逐页刷新、点击筛选并提供截图/结果。
- **可能风险**：页面过载、筛选错误或无法自动生成 PBIX；先验收设计和数据，再由用户完成 Desktop 验证，不能提前承诺 PBIX 可用。

### T19：最终报告、数据字典与招聘 README

- **任务目标**：形成面向业务与招聘者的可追溯中文文档。
- **前置依赖**：T08、T13–T18。
- **输入文件**：质量报告、指标、统计结果、分层输出、仪表盘截图、对账报告。
- **需要修改或创建的文件**：创建 `reports/FINAL_ANALYSIS_REPORT.md`、`docs/DATA_DICTIONARY.md`；重构 README 的最终内容。
- **实施步骤**：报告区分事实/解释/建议/未验证假设；每项发现链接到表格/图表；输出 3–5 条建议与限制；README 加入背景、技术、结构、流程、能力、核心发现、建议、预览和运行方法。
- **输出结果**：最终业务报告、数据字典和招聘者 README。
- **验收标准**：结论可追溯、无因果表述、中文主体完整；README 可指导从头复现。
- **验证命令或验证方法**：链接/路径检查；从报告抽取每条结论追溯来源；独立读者按 README 审阅。
- **可能风险**：把临时结果写成结论；仅引用已通过 T16/T15 验证的指标与发现。

### T20：端到端复现与最终验收

- **任务目标**：在干净流程中验证全部一期交付物和验收标准。
- **前置依赖**：T02–T19。
- **输入文件**：README、固定依赖、SQL 序列、Notebook、处理后数据、Power BI 文件、所有报告。
- **需要修改或创建的文件**：创建 `reports/FINAL_ACCEPTANCE_CHECKLIST.md`、`reports/REPRODUCTION_LOG.md`；仅按发现修复相关文件。
- **实施步骤**：按 README 重建/验证环境；顺序执行导入、SQL、Python、Notebook；重新生成 processed；刷新 Power BI；逐项核对验收标准和跨工具指标；记录问题与修复。
- **输出结果**：验收清单、复现日志与最终交付目录。
- **验收标准**：所有必需交付存在；关键指标一致；Power BI 可刷新；原始数据未改；未解决问题被明确列为限制。
- **验证命令或验证方法**：README 逐步执行；SQL `08_validation_queries.sql`；Python 验证脚本；Notebook “Run All”；Power BI 刷新/筛选测试。
- **可能风险**：环境/权限差异导致最后阶段失败；保留 CSV 备用源、脱敏日志和可回滚的环境备份。

## 关键依赖链与回滚原则

`T01 → T02 → T03 → T04 → T05 → T06 → T07 → T08 → T09/T10 → T11 → T12/T13 → T14/T15 → T16 → T17 → T18 → T19 → T20`

- 环境回滚：保留 `.venv_broken_backup_20260805`，不删除；新环境失败时停止并报告兼容性证据。
- 数据回滚：`data/raw/` 从不写入；所有派生结果可由脚本/Notebook 重建。
- SQL 回滚：旧 SQL 先列入 manifest，迁移后保留 legacy/deprecated 副本；正式脚本不再调用历史库名。
- 指标回滚：发现不一致时以 `METRICS.md` 和 `DECISIONS.md` 为准，修正实现并重跑对账，不能人工修改展示结果。
