# Olist 配送履约与客户满意度项目协作规则

本项目的需求说明书已正式确认，当前等待用户确认 `docs/TASK_PLAN.md`。在任务计划确认前，不得开始环境迁移、正式编码、重构、重命名、删除现有实现文件、数据库操作、数据清洗、正式分析或仪表盘制作。

## 需求与口径优先级

1. `docs/DECISIONS.md`：已确认业务决策。
2. `docs/METRICS.md`：指标、分子分母、样本和粒度定义。
3. `docs/PROJECT_REQUIREMENTS.md`：范围、交付物、技术栈、方法与验收标准。
4. `docs/DATA_QUALITY_REPORT.md` 与 `docs/DATA_INVENTORY.md`：当前数据事实和限制。

发生冲突时，先说明影响、替代方案并请求确认；不得自行改写已确认口径。

## 数据、质量与分析规则

- `data/raw/` 只读，任何清洗、派生或导出只能写入 `data/processed/`。
- 订单级指标以 `order_id` 为粒度。连接订单明细、付款或评价前后，必须核验订单数和重复放大风险。
- 主延迟字段为日历日 `delay_days`；保留 `delay_hours_raw` 但不以它做主分类。
- 订单级主评分取最新有效评价；多评审计字段和最低评分敏感性分析为必做项。
- 一期只分析客户 `customer_state`、`seller_id` 和商品类别；不得推断卖家地区、计算客户—卖家距离或制作经纬度地图。
- 结论只能描述关联和业务优先级，不得声称因果关系。

## 技术与安全规则

- SQL 必须兼容本地 MySQL 8.0.44，目标数据库为 `olist_delivery_analysis`，并按 `sql/00` 至 `sql/08` 编号顺序可在空数据库执行。`olist_analysis` 仅为历史名称。
- Python 使用当前 Python 3.13.13、项目 `.venv`、`requirements.in` 和经验证的固定版 `requirements.txt`；所有路径由项目根目录构造，不得使用本机绝对路径。没有兼容性证据和用户确认，不得切换到 Python 3.12/3.11。
- 数据库配置使用环境变量。不得提交 `.env`、密码、用户名或连接字符串中的真实凭据。
- 失效 `.venv` 必须先记录并重命名为 `.venv_broken_backup_20260805`，再重建新 `.venv`；旧备份不得删除，除非用户之后明确要求。`.venv` 与备份目录都必须被 `.gitignore` 忽略。
- 在 Python 3.13.13 环境完成安装、导入、数据读取、MySQL 连接、SciPy 检验、Notebook 与关键脚本测试前，不得声称 `requirements.txt` 已验证。
- MySQL 8.0.44 仅为学习/作品集验证环境，不应描述为推荐生产版本；MySQL 8.4 LTS 升级验证为后续非阻塞工作，不得擅自升级或卸载。
- 所有主体文档、Notebook 说明、图表标题和 Power BI 页面使用中文；原始字段、数据库对象和代码标识符可保留英文。

## 验证与交付规则

- 每项脚本/Notebook 记录输入、输出、运行命令及处理前后行数。
- 关键订单数必须在 SQL、Python、Power BI 三处一致；比例显示差异不超过 0.1 个百分点。
- README 必须提供 MySQL 建库、CSV 导入、SQL 顺序、Power BI 连接/刷新和 Python 环境复现说明。
- 发现环境、数据或遗留文件冲突时，保留原文件并记录迁移方案；不得直接删除或覆盖。
